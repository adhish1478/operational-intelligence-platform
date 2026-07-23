import re
import uuid
from typing import Any, Sequence
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.integrations.models import Integration
from app.investigations.models import Investigation
from app.evidence.schemas import EvidenceCreate
from app.evidence.services import EvidenceService


class IngestService:
    @staticmethod
    def extract_keywords(text: str) -> set[str]:
        """
        Tokenize text to extract unique keywords, ignoring common stop words.
        """
        if not text:
            return set()
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        stop_words = {
            "the", "and", "for", "from", "with", "this", "that", "alert", 
            "error", "sentry", "github", "slack", "jira", "gmail", "message", 
            "commit", "issue", "incident", "outage", "broken", "failed"
        }
        return {word for word in words if word not in stop_words}

    @staticmethod
    def platform_filter(integration: Integration, raw_payload: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Stage 1: Platform Filter.
        Validates basic integration boundary rules (tracked repos, channels, project keys).
        """
        platform = integration.platform
        config = integration.config or {}

        if platform == "github":
            repo_name = raw_payload.get("repository", {}).get("full_name")
            tracked_repos = config.get("tracked_repos", [])
            if tracked_repos and repo_name and repo_name not in tracked_repos:
                return False, f"Repository '{repo_name}' is not in the tracked repositories list."
        elif platform == "slack":
            event = raw_payload.get("event", {})
            channel_id = event.get("channel")
            configured_channel_id = config.get("channel_id")
            if configured_channel_id and channel_id and channel_id != configured_channel_id:
                return False, f"Slack event channel '{channel_id}' does not match configured triage channel."
        elif platform == "jira":
            issue = raw_payload.get("issue", {})
            project_key = issue.get("fields", {}).get("project", {}).get("key")
            tracked_projects = config.get("tracked_projects", [])
            if tracked_projects and project_key and project_key not in tracked_projects:
                return False, f"Jira project '{project_key}' is not in the tracked projects list."

        return True, None

    @staticmethod
    def normalize_payload(platform: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Stage 2: Normalize Payload.
        Extracts summary, author, source_url, and structured metadata.
        """
        summary = "Unrecognized telemetry payload"
        author_name = None
        source_url = None
        metadata = payload

        if platform == "slack":
            event = payload.get("event", {})
            text = event.get("text", "")
            summary = f"{text[:100]}..." if len(text) > 100 else text
            author_name = event.get("user")
            
        elif platform == "github":
            commit = payload.get("head_commit", {})
            if commit:
                msg = commit.get("message", "")
                summary = f"{msg[:100]}..." if len(msg) > 100 else msg
                author_name = commit.get("author", {}).get("username") or commit.get("author", {}).get("name")
                source_url = commit.get("url")
            else:
                repo_name = payload.get("repository", {}).get("full_name", "Unknown Repo")
                summary = f"GitHub Event on repository: {repo_name}"

        elif platform == "jira":
            issue = payload.get("issue", {})
            if issue:
                key = issue.get("key", "JIRA-KEY")
                fields = issue.get("fields", {})
                title = fields.get("summary", "No Summary")
                summary = f"Jira Issue {key}: {title}"
                author_name = fields.get("creator", {}).get("displayName")
                
        elif platform == "gmail":
            email = payload.get("email", {})
            if email:
                subject = email.get("subject", "No Subject")
                summary = subject
                author_name = email.get("from")

        return {
            "type": platform,
            "summary": summary,
            "author_name": author_name,
            "source_url": source_url,
            "metadata": metadata
        }

    # Alias for backward compatibility
    parse_webhook_payload = normalize_payload

    @staticmethod
    def classify_signal(integration: Integration, parsed: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Stage 3: Signal / Noise Classification.
        Inclusive OR Signal Classification Model:
        If ANY configured trigger (Allowed Senders, Subject Rules, or Keyword Rules) matches,
        the incoming telemetry is classified as a valid operational Signal.
        """
        config = integration.config or {}
        author = (parsed.get("author_name") or "").lower()
        summary = (parsed.get("summary") or "").lower()
        metadata = parsed.get("metadata") or {}
        full_text = f"{summary} {str(metadata)}".lower()

        allowed_senders = [s.lower() for s in config.get("allowed_senders", []) if s and s.strip()]
        required_keywords = [k.lower() for k in config.get("required_keywords", []) if k and k.strip()]
        subject_contains = [sc.lower() for sc in config.get("subject_contains", []) if sc and sc.strip()]
        subject_starts_with = [ss.lower() for ss in config.get("subject_starts_with", []) if ss and ss.strip()]

        has_any_configured_rules = bool(allowed_senders or required_keywords or subject_contains or subject_starts_with)

        if has_any_configured_rules:
            # Trigger 1: Allowed Sender Match
            if allowed_senders and any(sender in author for sender in allowed_senders):
                return True, None

            # Trigger 2: Subject Rule Match (Contains or Starts With)
            if subject_contains and any(sc in summary for sc in subject_contains):
                return True, None

            if subject_starts_with and any(
                summary.startswith(ss) or summary.startswith(f"gmail alert: {ss}")
                for ss in subject_starts_with
            ):
                return True, None

            # Trigger 3: Keyword Rule Match
            if required_keywords and any(kw in full_text for kw in required_keywords):
                return True, None

            # None of the configured OR triggers matched -> Reject as noise
            return False, "Signal does not match any of the configured allowed senders, subject rules, or keyword rules."

        # Trivial content noise check if no rules are configured
        if not summary or summary.strip() in ["No Subject", "Unrecognized telemetry payload"]:
            return False, "Signal classified as operational noise due to missing or empty summary content."

        return True, None

    @staticmethod
    async def correlate_signal(
        db: AsyncSession, organization_id: uuid.UUID, incoming_keywords: set[str]
    ) -> Investigation | None:
        """
        Stage 4: Correlation Engine.
        Finds an active Investigation container with token overlap.
        """
        if not incoming_keywords:
            return None

        statement = select(Investigation).where(
            Investigation.organization_id == organization_id,
            Investigation.status.in_(["open", "investigating"])
        )
        result = await db.execute(statement)
        active_investigations = result.scalars().all()

        for inv in active_investigations:
            inv_keywords = IngestService.extract_keywords(inv.title)
            overlap = inv_keywords.intersection(incoming_keywords)
            if len(overlap) > 0:
                return inv

        return None

    @staticmethod
    def is_incident_worthy(parsed: dict[str, Any]) -> bool:
        """
        Evaluates whether an un-correlated signal is incident-worthy
        justifying the creation of a new Investigation container in PostgreSQL.
        """
        summary = (parsed.get("summary") or "").lower()
        metadata_str = str(parsed.get("metadata") or {}).lower()
        full_text = f"{summary} {metadata_str}"

        # High-impact operational incident indicators
        incident_keywords = {
            "critical", "outage", "error", "failed", "failure", "spiked",
            "leak", "exception", "down", "breach", "vulnerability", "emergency",
            "alert", "timeout", "latency", "exhaustion", "panic", "fatal"
        }

        # Check keyword presence
        words = re.findall(r'\b[a-zA-Z]{3,}\b', full_text)
        if any(word in incident_keywords for word in words):
            return True

        # Check metadata priority/severity
        metadata = parsed.get("metadata") or {}
        if isinstance(metadata, dict):
            sev = str(metadata.get("severity") or metadata.get("priority") or "").lower()
            if sev in ["critical", "high", "p0", "p1", "blocker"]:
                return True

        return False

    @staticmethod
    def compute_severity(summary: str) -> str:
        """
        Heuristic severity classifier for newly created investigations.
        """
        lower_summary = summary.lower()
        if "critical" in lower_summary or "outage" in lower_summary or "severity 1" in lower_summary or "p0" in lower_summary:
            return "critical"
        elif "error" in lower_summary or "failed" in lower_summary or "spiked" in lower_summary or "leak" in lower_summary or "p1" in lower_summary:
            return "high"
        return "medium"

    @staticmethod
    async def correlate_and_process(
        db: AsyncSession,
        mongo_db: AsyncIOMotorDatabase,
        integration: Integration,
        raw_payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Ingestion Pipeline Orchestrator:
        1. Platform Filter
        2. Normalize Payload
        3. Signal / Noise Classification
        4. Correlation Engine
        5. Incident-Worthiness Evaluation & Storage Routing
        """
        # Step 1: Platform Filter
        allowed, filter_reason = IngestService.platform_filter(integration, raw_payload)
        if not allowed:
            return {"status": "ignored", "reason": filter_reason}

        # Step 2: Normalize Payload
        parsed = IngestService.normalize_payload(integration.platform, raw_payload)

        # Step 3: Signal / Noise Classification
        is_signal, noise_reason = IngestService.classify_signal(integration, parsed)
        if not is_signal:
            return {"status": "ignored", "reason": noise_reason}

        # Step 4: Correlation Engine
        incoming_keywords = IngestService.extract_keywords(parsed["summary"])
        matched_inv = await IngestService.correlate_signal(db, integration.organization_id, incoming_keywords)

        if matched_inv is not None:
            # Match Found -> Attach Evidence to Existing Investigation Container
            evidence_in = EvidenceCreate(
                type=parsed["type"],
                summary=parsed["summary"],
                author_name=parsed["author_name"],
                source_url=parsed["source_url"],
                metadata=parsed["metadata"]
            )
            evidence = await EvidenceService.create_evidence(mongo_db, matched_inv.id, evidence_in)
            return {
                "status": "correlated",
                "investigation_id": matched_inv.id,
                "evidence_id": evidence.id
            }

        # Step 5: Un-correlated Signal -> Evaluate Incident-Worthiness
        if not IngestService.is_incident_worthy(parsed):
            # Not Incident-Worthy -> Store as standalone Evidence Only (do NOT pollute SQL investigations)
            evidence_in = EvidenceCreate(
                type=parsed["type"],
                summary=parsed["summary"],
                author_name=parsed["author_name"],
                source_url=parsed["source_url"],
                metadata=parsed["metadata"]
            )
            evidence = await EvidenceService.create_evidence(mongo_db, None, evidence_in)
            return {
                "status": "evidence_only",
                "evidence_id": evidence.id,
                "reason": "Signal stored as standalone evidence; not incident-worthy for new Investigation creation."
            }

        # Incident-Worthy -> Create new SQL Investigation & attach Evidence
        severity = IngestService.compute_severity(parsed["summary"])
        new_inv = Investigation(
            organization_id=integration.organization_id,
            title=parsed["summary"],
            description=f"Auto-created from incoming {integration.platform} event signal.",
            severity=severity,
            status="open"
        )
        db.add(new_inv)
        await db.commit()
        await db.refresh(new_inv)

        evidence_in = EvidenceCreate(
            type=parsed["type"],
            summary=parsed["summary"],
            author_name=parsed["author_name"],
            source_url=parsed["source_url"],
            metadata=parsed["metadata"]
        )
        evidence = await EvidenceService.create_evidence(mongo_db, new_inv.id, evidence_in)

        return {
            "status": "created",
            "investigation_id": new_inv.id,
            "evidence_id": evidence.id
        }
