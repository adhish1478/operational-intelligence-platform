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
from app.core.config import settings


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

        # Git branch patterns (e.g. fix/auth-gateway-oom -> auth-gateway)
        branch_matches = re.findall(r'(?:fix|hotfix|bugfix|feature|incident)/([a-z0-9-]+)', text.lower())
        for bm in branch_matches:
            sub_services = set(re.findall(r'\b[a-z0-9]+(?:-[a-z0-9]+)+\b', bm))
            services = services.union(sub_services)

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
    async def generate_embedding(text: str) -> list[float] | None:
        """
        Phase 2 - Step 1: Text Embedding Generator.
        Calls OpenAI text-embedding-3-small API to generate a 1536-dimensional vector.
        Returns None gracefully if OPENAI_API_KEY is not configured or request fails.
        """
        if not text or not settings.OPENAI_API_KEY:
            return None

        clean_text = text.replace("\n", " ").strip()
        if not clean_text:
            return None

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": clean_text[:2000],
                        "model": "text-embedding-3-small"
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("data", [{}])[0].get("embedding")
                    if isinstance(embedding, list):
                        return [float(v) for v in embedding]
        except Exception:
            pass

        return None

    @staticmethod
    def cosine_similarity(vec_a: list[float] | None, vec_b: list[float] | None) -> float:
        """
        Phase 2 - Step 2: Cosine Similarity Calculator.
        Computes cosine similarity between two vector embeddings.
        Returns float between 0.0 and 1.0.
        """
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        import math
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        similarity = dot_product / (norm_a * norm_b)
        # Normalize to 0.0 - 1.0 range
        return float(max(min(similarity, 1.0), 0.0))

    @staticmethod
    async def get_investigation_vector(
        investigation: Investigation, mongo_db: AsyncIOMotorDatabase
    ) -> list[float] | None:
        """
        Phase 2 - Step 3: Investigation Vector Centroid Builder.
        Generates 1536-dimensional vector embedding for an investigation's composite fingerprint.
        """
        fingerprint = await IngestService.build_investigation_fingerprint(investigation, mongo_db)
        return await IngestService.generate_embedding(fingerprint)

    @staticmethod
    def score_hybrid_correlation(
        incoming_text: str,
        investigation_fingerprint: str,
        detected_at: datetime | None,
        inc_vector: list[float] | None = None,
        inv_vector: list[float] | None = None
    ) -> float:
        """
        Phase 2 - Step 4: Hybrid Correlation Scorer.
        Combines Entity Match (40%), Vector Cosine Similarity (40%),
        and Keyword Overlap (20%) multiplied by Time Decay.
        Falls back to Phase 1 scoring if vector embeddings are unavailable.
        """
        # If vector embeddings are unavailable, fallback to Phase 1 scoring
        if inc_vector is None or inv_vector is None:
            return IngestService.score_correlation(incoming_text, investigation_fingerprint, detected_at)

        if not incoming_text or not investigation_fingerprint:
            return 0.0

        # 1. Entity Extraction Comparison (40% Weight)
        inc_entities = IngestService.extract_entities(incoming_text)
        inv_entities = IngestService.extract_entities(investigation_fingerprint)

        entity_score = 0.0
        if inc_entities["services"].intersection(inv_entities["services"]):
            entity_score += 0.60
        if inc_entities["errors"].intersection(inv_entities["errors"]):
            entity_score += 0.25
        if inc_entities["alert_ids"].intersection(inv_entities["alert_ids"]):
            entity_score += 0.15
        entity_score = min(entity_score, 1.0)

        # 2. Vector Cosine Similarity (40% Weight)
        vector_score = IngestService.cosine_similarity(inc_vector, inv_vector)

        # 3. Keyword Jaccard Similarity (20% Weight)
        inc_keywords = IngestService.extract_keywords(incoming_text)
        inv_keywords = IngestService.extract_keywords(investigation_fingerprint)
        keyword_score = 0.0
        if inc_keywords and inv_keywords:
            intersection = len(inc_keywords.intersection(inv_keywords))
            union = len(inc_keywords.union(inv_keywords))
            keyword_score = intersection / union if union > 0 else 0.0

        # 4. Exponential Time Decay
        time_decay = IngestService.compute_time_decay(detected_at)

        # 5. Composite Hybrid Score
        base_score = (entity_score * 0.40) + (vector_score * 0.40) + (keyword_score * 0.20)
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
            # 1. Pull Request Event
            pr = payload.get("pull_request", {})
            if pr:
                pr_title = pr.get("title", "No PR Title")
                branch = pr.get("head", {}).get("ref", "")
                action = payload.get("action", "updated")
                merged = pr.get("merged", False)
                pr_state = "merged" if merged else action

                summary = f"GitHub PR ({pr_state}): [{branch}] {pr_title}"
                author_name = pr.get("user", {}).get("login")
                source_url = pr.get("html_url")
                metadata = {
                    "event_type": "pull_request",
                    "action": pr_state,
                    "title": pr_title,
                    "branch": branch,
                    "base_branch": pr.get("base", {}).get("ref", ""),
                    "body": pr.get("body") or pr_title,
                    "repo": payload.get("repository", {}).get("full_name", "")
                }
            # 2. Workflow Run / CI Build Event
            elif "workflow_run" in payload:
                wf = payload.get("workflow_run", {})
                wf_name = wf.get("name", "Workflow")
                conclusion = wf.get("conclusion") or wf.get("status", "unknown")
                head_branch = wf.get("head_branch", "")

                summary = f"GitHub CI ({conclusion}): {wf_name} on branch {head_branch}"
                author_name = wf.get("actor", {}).get("login")
                source_url = wf.get("html_url")
                metadata = {
                    "event_type": "workflow_run",
                    "conclusion": conclusion,
                    "workflow": wf_name,
                    "branch": head_branch,
                    "body": f"Workflow run {wf_name} status: {conclusion} on branch {head_branch}",
                    "repo": payload.get("repository", {}).get("full_name", "")
                }
            # 3. Issue Event
            elif "issue" in payload:
                issue = payload.get("issue", {})
                issue_title = issue.get("title", "No Issue Title")
                number = issue.get("number")
                labels = [l.get("name") for l in issue.get("labels", []) if isinstance(l, dict)]

                summary = f"GitHub Issue #{number}: {issue_title}"
                author_name = issue.get("user", {}).get("login")
                source_url = issue.get("html_url")
                metadata = {
                    "event_type": "issues",
                    "number": number,
                    "title": issue_title,
                    "labels": labels,
                    "body": issue.get("body") or issue_title,
                    "repo": payload.get("repository", {}).get("full_name", "")
                }
            # 4. Push / Commit Event
            else:
                commit = payload.get("head_commit", {})
                ref = payload.get("ref", "")
                branch = ref.replace("refs/heads/", "") if ref else "main"
                if commit:
                    msg = commit.get("message", "")
                    summary = f"GitHub Push [{branch}]: {msg[:80]}"
                    author_name = commit.get("author", {}).get("username") or commit.get("author", {}).get("name")
                    source_url = commit.get("url")
                    metadata = {
                        "event_type": "push",
                        "branch": branch,
                        "commit_msg": msg,
                        "body": msg,
                        "repo": payload.get("repository", {}).get("full_name", "")
                    }
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

        # GitHub Noise Filtering: Filter out Dependabot, chore/docs branches, and redundant push-to-PR-branch events
        if parsed.get("type") == "github":
            branch = str(metadata.get("branch") or "").lower()
            event_type = metadata.get("event_type")
            if "dependabot" in author or any(branch.startswith(prefix) for prefix in ["chore/", "docs/", "style/", "renovate/"]):
                return False, f"Filtered out GitHub background noise ({author} on {branch})."
            # Push events to non-default branches are redundant (the PR event already captures them)
            if event_type == "push" and branch not in ["main", "master", "develop", "production"]:
                return False, f"Filtered redundant push to PR branch ({branch})."

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
        Stage 4: Advanced Correlation Engine (Phase 2 Hybrid Model).
        Finds an active Investigation container with highest weighted correlation score
        combining Entity Extraction, Vector Embeddings (or Phase 1 fallback), Keyword Similarity, and Time Decay.
        """
        if not incoming_text:
            return None

        statement = select(Investigation).where(
            Investigation.organization_id == organization_id,
            Investigation.status.in_(["open", "investigating"])
        )
        result = await db.execute(statement)
        active_investigations = result.scalars().all()

        if not active_investigations:
            return None

        # Generate incoming signal vector embedding if OPENAI_API_KEY is configured
        inc_vector = await IngestService.generate_embedding(incoming_text)

        best_match = None
        best_score = 0.0

        for inv in active_investigations:
            fingerprint = await IngestService.build_investigation_fingerprint(inv, mongo_db)
            inv_vector = await IngestService.generate_embedding(fingerprint) if inc_vector else None

            score = IngestService.score_hybrid_correlation(
                incoming_text=incoming_text,
                investigation_fingerprint=fingerprint,
                detected_at=inv.detected_at,
                inc_vector=inc_vector,
                inv_vector=inv_vector
            )

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

        # GitHub Conservative Routing Rules:
        # CI workflow failures, P0/bug-labeled issues, or PRs on incident branches with critical keywords spawn NEW Investigations.
        # Regular PRs/commits that don't match an active investigation go to standalone evidence.
        if integration.platform == "github":
            metadata = parsed.get("metadata") or {}
            event_type = metadata.get("event_type")
            conclusion = str(metadata.get("conclusion") or "").lower()
            labels = [str(l).lower() for l in (metadata.get("labels") or [])]
            branch = str(metadata.get("branch") or "").lower()

            if event_type == "workflow_run" and conclusion in ["failure", "cancelled", "timed_out"]:
                return True
            if event_type == "issues" and any(l in labels for l in ["bug", "p0", "critical", "blocker"]):
                return True
            # PRs on incident-relevant branches (bug/*, hotfix/*, incident/*) with critical keywords -> incident-worthy
            if event_type == "pull_request":
                incident_branches = ["bug/", "hotfix/", "bugfix/", "incident/"]
                incident_keywords = {"critical", "outage", "error", "failed", "failure", "leak", "crash", "panic", "fatal", "p0", "p1"}
                if any(branch.startswith(prefix) for prefix in incident_branches):
                    pr_text_words = set(re.findall(r'\b[a-zA-Z]{2,}\b', full_text))
                    if pr_text_words.intersection(incident_keywords):
                        return True
            # Otherwise, regular PRs/pushes that didn't correlate are stored as Standalone Evidence
            return False

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
