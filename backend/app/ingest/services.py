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
            "commit", "issue", "incident", "outage", "broken", "failed",
            "gateway", "service", "system", "high", "critical", "bad",
            "datadog", "stripe", "pagerduty", "spike", "spikes", "status",
            "update", "notice", "info", "warning", "email", "report"
        }
        return {word for word in words if word not in stop_words}

    @staticmethod
    def extract_entities(text: str) -> dict[str, set[str]]:
        """
        Phase 1 - Step 1: Entity Extraction.
        Extracts structured system entities from text:
        - Services/Pods (e.g. auth-gateway, postgres-primary-east)
        - Errors/Exceptions (e.g. 502, 504, OutOfMemoryError, ECONNRESET)
        - Alert/Incident IDs (e.g. PD4920, STRIPE-CRIT-9021)
        """
        if not text:
            return {"services": set(), "errors": set(), "alert_ids": set()}

        # 1. Microservice / Pod Identifiers (hyphenated names containing lowercase letters/numbers)
        services = set(re.findall(r'\b[a-z0-9]+(?:-[a-z0-9]+)+\b', text.lower()))

        # 2. Error Codes & Exception Class Names (HTTP 5xx/4xx codes, or Java/Python Exception names)
        error_codes = set(re.findall(r'\b[45]\d\d\b', text))
        exceptions = set(re.findall(r'\b[A-Z][a-zA-Z0-9]*(?:Exception|Error)\b', text))
        common_errors = set(re.findall(r'\b(?:ECONNRESET|ETIMEDOUT|OOM)\b', text, re.IGNORECASE))
        errors = error_codes.union(exceptions).union({e.upper() for e in common_errors})

        # 3. Alert & Incident Tracking IDs (e.g. PD4920, STRIPE-CRIT-9021, ISSUE-104)
        alert_ids = set(re.findall(r'\b[A-Z]{2,}(?:-[A-Z0-9]+)+\b|\bPD\d+\b', text))

        return {
            "services": services,
            "errors": errors,
            "alert_ids": alert_ids,
        }

    @staticmethod
    async def build_investigation_fingerprint(
        investigation: Investigation, mongo_db: AsyncIOMotorDatabase
    ) -> str:
        """
        Phase 1 - Step 2: Composite Investigation Fingerprint Builder.
        Combines the Investigation title with summaries of all evidence previously attached to it in MongoDB.
        """
        title = investigation.title or ""
        evidence_cursor = mongo_db.evidence.find({"investigation_id": str(investigation.id)})
        evidence_list = await evidence_cursor.to_list(length=50)

        evidence_summaries = [e.get("summary", "") for e in evidence_list if e.get("summary")]
        composite_text = " ".join([title] + evidence_summaries)
        return composite_text

    @staticmethod
    def compute_time_decay(detected_at: datetime | None, half_life_hours: float = 24.0) -> float:
        """
        Phase 1 - Step 3: Exponential Time-Decay Weighting.
        Computes a score multiplier from 1.0 (brand new) down towards 0.0 (stale)
        based on hours elapsed since the investigation was created.
        """
        if not detected_at:
            return 1.0

        now = datetime.now(timezone.utc)
        if detected_at.tzinfo is None:
            detected_at = detected_at.replace(tzinfo=timezone.utc)

        elapsed_seconds = max((now - detected_at).total_seconds(), 0.0)
        elapsed_hours = elapsed_seconds / 3600.0

        decay = 0.5 ** (elapsed_hours / half_life_hours)
        return float(decay)

    @staticmethod
    def score_correlation(
        incoming_text: str,
        investigation_fingerprint: str,
        detected_at: datetime | None
    ) -> float:
        """
        Phase 1 - Step 4: Weighted Correlation Scorer.
        Calculates weighted composite score combining Entity Match (50%),
        Keyword Similarity (30%), and Time Decay (Multiplier).
        Returns float score between 0.0 and 1.0.
        """
        if not incoming_text or not investigation_fingerprint:
            return 0.0

        # 1. Entity Extraction Comparison
        inc_entities = IngestService.extract_entities(incoming_text)
        inv_entities = IngestService.extract_entities(investigation_fingerprint)

        entity_score = 0.0
        # Service/Pod Match (+0.60)
        svc_overlap = inc_entities["services"].intersection(inv_entities["services"])
        if svc_overlap:
            entity_score += 0.60

        # Error/Exception Match (+0.25)
        err_overlap = inc_entities["errors"].intersection(inv_entities["errors"])
        if err_overlap:
            entity_score += 0.25

        # Alert ID Match (+0.15)
        alert_overlap = inc_entities["alert_ids"].intersection(inv_entities["alert_ids"])
        if alert_overlap:
            entity_score += 0.15

        entity_score = min(entity_score, 1.0)

        # 2. Keyword Jaccard Similarity Comparison
        inc_keywords = IngestService.extract_keywords(incoming_text)
        inv_keywords = IngestService.extract_keywords(investigation_fingerprint)

        keyword_score = 0.0
        if inc_keywords and inv_keywords:
            intersection = len(inc_keywords.intersection(inv_keywords))
            union = len(inc_keywords.union(inv_keywords))
            keyword_score = intersection / union if union > 0 else 0.0

        # 3. Time Decay Multiplier
        time_decay = IngestService.compute_time_decay(detected_at)

        # 4. Composite Weighted Score
        base_score = (entity_score * 0.50) + (keyword_score * 0.30)
        final_score = base_score * time_decay

        return float(final_score)

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
                snippet = email.get("snippet", "")
                body = email.get("body") or snippet or summary
                metadata = {
                    "email_id": email.get("id"),
                    "from": email.get("from"),
                    "subject": subject,
                    "snippet": snippet,
                    "body": body
                }

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
        db: AsyncSession,
        mongo_db: AsyncIOMotorDatabase,
        organization_id: uuid.UUID,
        incoming_text: str
    ) -> Investigation | None:
        """
        Stage 4: Advanced Correlation Engine (Phase 1).
        Finds an active Investigation container with highest weighted correlation score
        combining Entity Extraction, Composite Fingerprints, Keyword Similarity, and Time Decay.
        """
        if not incoming_text:
            return None

        statement = select(Investigation).where(
            Investigation.organization_id == organization_id,
            Investigation.status.in_(["open", "investigating"])
        )
        result = await db.execute(statement)
        active_investigations = result.scalars().all()

        best_match = None
        best_score = 0.0

        for inv in active_investigations:
            fingerprint = await IngestService.build_investigation_fingerprint(inv, mongo_db)
            score = IngestService.score_correlation(incoming_text, fingerprint, inv.detected_at)

            # Minimum correlation confidence threshold (0.25)
            if score >= 0.25 and score > best_score:
                best_score = score
                best_match = inv

        return best_match

    @staticmethod
    def is_incident_worthy(integration: Integration, parsed: dict[str, Any]) -> bool:
        """
        Evaluates whether an un-correlated signal is incident-worthy
        justifying the creation of a new Investigation container in PostgreSQL.
        Checks both user-configured integration rules and system incident keywords.
        """
        summary = (parsed.get("summary") or "").lower()
        metadata_str = str(parsed.get("metadata") or {}).lower()
        full_text = f"{summary} {metadata_str}"
        config = integration.config or {}

        # 1. User-configured rule matches (required_keywords, subject_contains, subject_starts_with)
        required_keywords = [k.lower() for k in config.get("required_keywords", []) if k and k.strip()]
        if required_keywords and any(kw in full_text for kw in required_keywords):
            return True

        subject_contains = [sc.lower() for sc in config.get("subject_contains", []) if sc and sc.strip()]
        if subject_contains and any(sc in summary for sc in subject_contains):
            return True

        subject_starts_with = [ss.lower() for ss in config.get("subject_starts_with", []) if ss and ss.strip()]
        if subject_starts_with and any(summary.startswith(ss) for ss in subject_starts_with):
            return True

        # 2. High-impact operational incident indicators
        incident_keywords = {
            "critical", "outage", "error", "failed", "failure", "spiked",
            "leak", "exception", "down", "breach", "vulnerability", "emergency",
            "alert", "timeout", "latency", "exhaustion", "panic", "fatal"
        }

        words = re.findall(r'\b[a-zA-Z]{3,}\b', full_text)
        if any(word in incident_keywords for word in words):
            return True

        # 3. Check metadata priority/severity
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

        # Step 4: Correlation Engine (Phase 1 Advanced Weighted Scoring)
        incoming_text = f"{parsed['summary']} {str(parsed.get('metadata') or {})}"
        matched_inv = await IngestService.correlate_signal(db, mongo_db, integration.organization_id, incoming_text)

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
        if not IngestService.is_incident_worthy(integration, parsed):
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
