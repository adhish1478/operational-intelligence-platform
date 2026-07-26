import re
import uuid
import zoneinfo
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


import httpx

def get_ist_time_str() -> str:
    """Returns current time in IST timezone (+05:30)."""
    ist = zoneinfo.ZoneInfo("Asia/Kolkata")
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")


# In-memory deduplication cache for incoming telemetry event IDs
PROCESSED_EVENT_IDS: set[str] = set()

# In-memory user cache for Slack user ID resolution (e.g. U08BXYZ123 -> "Adhish Aravind")
SLACK_USER_CACHE: dict[str, str] = {}

# In-memory channel cache for Slack channel ID resolution (e.g. C0BKV7U95CY -> "all-oip-org")
SLACK_CHANNEL_CACHE: dict[str, str] = {}


async def resolve_slack_channel_name(access_token: str | None, channel_id: str, config: dict | None = None) -> str:
    """
    Resolves Slack channel ID (e.g. C0BKV7U95CY) to channel name (e.g. "all-oip-org").
    Caches resolved names in memory.
    """
    if not channel_id:
        return "general"

    if channel_id in SLACK_CHANNEL_CACHE:
        return SLACK_CHANNEL_CACHE[channel_id]

    # Check integration config tracked_channels list first
    if config and config.get("tracked_channels"):
        for ch in config.get("tracked_channels", []):
            if isinstance(ch, dict) and ch.get("id") == channel_id:
                name = ch.get("name", channel_id)
                SLACK_CHANNEL_CACHE[channel_id] = name
                return name

    # Call Slack conversations.info API using existing channels:read / groups:read scopes
    if access_token:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"https://slack.com/api/conversations.info?channel={channel_id}",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                data = resp.json()
                if data.get("ok"):
                    ch_name = data.get("channel", {}).get("name")
                    if ch_name:
                        SLACK_CHANNEL_CACHE[channel_id] = ch_name
                        return ch_name
        except Exception:
            pass

    return channel_id


async def resolve_slack_user_name(access_token: str | None, user_id: str) -> str:
    """
    Resolves Slack user ID (e.g. U08BXYZ123) to real name using Slack users.info API.
    Caches resolved names in memory.
    """
    if not user_id or not user_id.startswith("U"):
        return user_id or "Slack User"

    if user_id in SLACK_USER_CACHE:
        return SLACK_USER_CACHE[user_id]

    if not access_token:
        return user_id

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://slack.com/api/users.info?user={user_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            data = resp.json()
            if data.get("ok"):
                user_obj = data.get("user", {})
                profile = user_obj.get("profile", {})
                real_name = profile.get("real_name") or profile.get("display_name") or user_obj.get("name")
                if real_name:
                    display = f"{real_name} ({user_id})"
                    SLACK_USER_CACHE[user_id] = display
                    return display
    except Exception:
        pass

async def classify_slack_signal(text: str, channel_name: str = "") -> dict[str, Any]:
    """
    LLM-powered signal intelligence for Slack using GPT-4o-mini.
    Returns structured dict:
    {
      "signal_type": "incident" | "debugging" | "status_update" | "discussion" | "noise",
      "urgency": "critical" | "high" | "medium" | "low" | "none",
      "entities": ["list of service names, systems, error codes, or components mentioned"],
      "reasoning": "brief 1-sentence reason"
    }
    Falls back to heuristic classification if OPENAI_API_KEY is not set or request fails.
    """
    if not text or not text.strip():
        return {"signal_type": "noise", "urgency": "none", "entities": [], "reasoning": "Empty text"}

    if settings.OPENAI_API_KEY:
        try:
            prompt = (
                "You are an operational intelligence classifier for an engineering team's Slack messages.\n"
                "Analyze the Slack message and classify it into JSON format:\n"
                "{\n"
                '  "signal_type": "incident" | "debugging" | "status_update" | "discussion" | "noise",\n'
                '  "urgency": "critical" | "high" | "medium" | "low" | "none",\n'
                '  "entities": ["list of service names, systems, error codes, or components mentioned"],\n'
                '  "reasoning": "brief 1-sentence reason"\n'
                "}\n\n"
                "Definitions:\n"
                "- incident: active outage, severe error, or system failure\n"
                "- debugging: active troubleshooting, investigating logs/metrics, or checking issues\n"
                "- status_update: progress, hotfix deploy, rollback, or resolution update\n"
                "- discussion: technical conversation or architectural talk, non-urgent\n"
                "- noise: casual greetings (hey, hi, good morning, thanks, lunch), social chatter, or administrative logs\n\n"
                f"Channel: #{channel_name}\n"
                f'Message: "{text[:500]}"'
            )
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.1,
                        "max_tokens": 150
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    import json
                    parsed_llm = json.loads(content)
                    if isinstance(parsed_llm, dict) and "signal_type" in parsed_llm:
                        return parsed_llm
        except Exception:
            pass

    # Fallback heuristic classification
    lower_text = text.lower()
    
    # Check social noise
    social_greetings = {"hey", "hi", "hello", "thanks", "thank you", "good morning", "good night", "lunch", "brb", "lol", "haha", "ok", "okay", "sure", "👍"}
    words = lower_text.strip().split()
    if lower_text.strip() in social_greetings or (len(words) <= 2 and not any("-" in w for w in words)):
        return {"signal_type": "noise", "urgency": "none", "entities": [], "reasoning": "Heuristic social noise"}

    # Extract entities via regex
    entities_dict = IngestService.extract_entities(text)
    entities = list(entities_dict["services"].union(entities_dict["errors"]).union(entities_dict["alert_ids"]))

    incident_kw = {"down", "broken", "outage", "crashed", "unresponsive", "502", "503", "504", "oom", "killed", "failed", "panic", "critical"}
    debugging_kw = {"checking", "investigating", "logs", "metrics", "seeing errors", "spike", "latency", "timeout", "bug"}
    status_kw = {"deploying", "rolled back", "reverted", "monitoring", "fixed", "resolved", "root cause", "hotfix"}

    if any(kw in lower_text for kw in incident_kw):
        return {"signal_type": "incident", "urgency": "high", "entities": entities, "reasoning": "Heuristic incident match"}
    elif any(kw in lower_text for kw in status_kw):
        return {"signal_type": "status_update", "urgency": "low", "entities": entities, "reasoning": "Heuristic status match"}
    elif any(kw in lower_text for kw in debugging_kw):
        return {"signal_type": "debugging", "urgency": "medium", "entities": entities, "reasoning": "Heuristic debugging match"}

    return {"signal_type": "discussion", "urgency": "low", "entities": entities, "reasoning": "Heuristic discussion match"}


async def correlate_slack_thread(
    mongo_db: AsyncIOMotorDatabase,
    thread_ts: str | None,
    channel_id: str | None
) -> str | None:
    """
    Thread-based deterministic correlation for Slack messages.
    If a message is a thread reply, find the parent message's evidence record in MongoDB
    and return its investigation_id.
    """
    if not thread_ts:
        return None

    query = {"type": "slack", "metadata.ts": thread_ts}
    if channel_id:
        query["metadata.channel_id"] = channel_id

    parent_evidence = await mongo_db.evidence.find_one(query)
    if parent_evidence and parent_evidence.get("investigation_id"):
        return parent_evidence["investigation_id"]

    return None


async def handle_slack_edit(
    mongo_db: AsyncIOMotorDatabase,
    channel_id: str | None,
    original_ts: str | None,
    new_text: str,
    previous_text: str | None
) -> str | None:
    """Update existing evidence when a message is edited."""
    if not original_ts:
        return None

    existing = await mongo_db.evidence.find_one({
        "type": "slack",
        "metadata.ts": original_ts,
        "metadata.channel_id": channel_id
    })
    if existing:
        doc_id = existing["_id"]
        await mongo_db.evidence.update_one(
            {"_id": doc_id},
            {"$set": {
                "metadata.text": new_text,
                "metadata.body": new_text,
                "metadata.edited": True,
                "metadata.previous_text": previous_text,
                "summary": f"{new_text[:100]} [edited]"
            }}
        )
        return str(doc_id)
    return None


async def handle_slack_delete(
    mongo_db: AsyncIOMotorDatabase,
    channel_id: str | None,
    deleted_ts: str | None
) -> str | None:
    """Mark existing evidence as retracted when message is deleted."""
    if not deleted_ts:
        return None

    existing = await mongo_db.evidence.find_one({
        "type": "slack",
        "metadata.ts": deleted_ts,
        "metadata.channel_id": channel_id
    })
    if existing:
        doc_id = existing["_id"]
        old_summary = existing.get("summary", "")
        await mongo_db.evidence.update_one(
            {"_id": doc_id},
            {"$set": {
                "metadata.retracted": True,
                "summary": f"{old_summary} [RETRACTED]"
            }}
        )
        return str(doc_id)
    return None


async def correlate_jira_issue_key(
    mongo_db: AsyncIOMotorDatabase,
    issue_key: str | None
) -> str | None:
    """
    Issue-key based deterministic correlation for Jira events.
    If an event references an issue key (e.g. KAN-3), find any existing evidence record
    in MongoDB with the same issue_key that has a non-null investigation_id.
    """
    if not issue_key:
        return None

    query = {
        "type": "jira",
        "metadata.issue_key": issue_key,
        "investigation_id": {"$ne": None},
        "metadata.retracted": {"$ne": True}
    }

    existing_evidence = await mongo_db.evidence.find_one(query)
    if existing_evidence and existing_evidence.get("investigation_id"):
        return existing_evidence["investigation_id"]

    return None


def extract_jira_keys_from_text(text: str | None) -> set[str]:
    """
    Scans arbitrary text for Jira issue key patterns (e.g. KAN-100, PROD-42, SEC-9).
    Filters out common uppercase non-issue tokens.
    """
    if not text:
        return set()

    matches = re.findall(r'\b([A-Z][A-Z0-9]+-\d+)\b', text)
    ignore_prefixes = {"HTTP", "ISO", "UTF", "TLS", "SSL", "SHA", "MD"}
    valid_keys = set()
    for m in matches:
        prefix = m.split('-')[0]
        if prefix not in ignore_prefixes:
            valid_keys.add(m)
    return valid_keys


async def correlate_cross_platform_keys(
    mongo_db: AsyncIOMotorDatabase,
    text: str | None
) -> str | None:
    """
    Cross-platform deterministic correlation via Jira issue keys referenced in text.
    Works for Slack messages, GitHub PR titles/branches, Gmail subjects, alert text.
    If any referenced issue key (e.g. KAN-3) matches an active evidence item linked
    to an investigation container in MongoDB, returns that investigation_id.
    """
    keys = extract_jira_keys_from_text(text)
    for key in keys:
        inv_id = await correlate_jira_issue_key(mongo_db, key)
        if inv_id:
            return inv_id
    return None


async def handle_jira_comment_edit(
    mongo_db: AsyncIOMotorDatabase,
    issue_key: str | None,
    comment_id: str | None,
    new_body: str,
    author_name: str
) -> str | None:
    """Update existing comment evidence in-place when a Jira comment is edited."""
    if not issue_key or not comment_id:
        return None

    existing = await mongo_db.evidence.find_one({
        "type": "jira",
        "metadata.issue_key": issue_key,
        "metadata.comment_id": comment_id
    })
    if existing:
        doc_id = existing["_id"]
        await mongo_db.evidence.update_one(
            {"_id": doc_id},
            {"$set": {
                "metadata.comment": new_body,
                "metadata.edited": True,
                "summary": f"Jira [{issue_key}] [COMMENT EDITED] by {author_name}: {new_body[:80]}"
            }}
        )
        return str(doc_id)
    return None


async def handle_jira_comment_delete(
    mongo_db: AsyncIOMotorDatabase,
    issue_key: str | None,
    comment_id: str | None
) -> str | None:
    """Mark existing comment evidence as retracted when a Jira comment is deleted."""
    if not issue_key or not comment_id:
        return None

    existing = await mongo_db.evidence.find_one({
        "type": "jira",
        "metadata.issue_key": issue_key,
        "metadata.comment_id": comment_id
    })
    if existing:
        doc_id = existing["_id"]
        old_summary = existing.get("summary", "")
        await mongo_db.evidence.update_one(
            {"_id": doc_id},
            {"$set": {
                "metadata.retracted": True,
                "summary": f"{old_summary} [RETRACTED]"
            }}
        )
        return str(doc_id)
    return None


async def handle_jira_issue_delete(
    mongo_db: AsyncIOMotorDatabase,
    issue_key: str | None
) -> list[str]:
    """Mark ALL evidence records for an issue key as retracted when a Jira issue is deleted."""
    if not issue_key:
        return []

    cursor = mongo_db.evidence.find({
        "type": "jira",
        "metadata.issue_key": issue_key
    })
    retracted_ids = []
    async for existing in cursor:
        doc_id = existing["_id"]
        old_summary = existing.get("summary", "")
        if not old_summary.endswith("[RETRACTED]"):
            await mongo_db.evidence.update_one(
                {"_id": doc_id},
                {"$set": {
                    "metadata.retracted": True,
                    "summary": f"{old_summary} [RETRACTED]"
                }}
            )
            retracted_ids.append(str(doc_id))

    return retracted_ids


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
            tracked_channels = config.get("tracked_channels", [])

            if tracked_channels:
                allowed_ids = [c.get("id") if isinstance(c, dict) else str(c) for c in tracked_channels]
                if channel_id and channel_id not in allowed_ids:
                    return False, f"Slack event channel '{channel_id}' is not in the tracked channels list."
            elif configured_channel_id and channel_id and channel_id != configured_channel_id:
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

        if platform == "github":
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

        elif platform == "slack":
            event = payload.get("event", {})
            event_type = event.get("type", "message")
            subtype = event.get("subtype")

            user = event.get("user") or payload.get("user_id") or "Slack User"
            channel = event.get("channel") or payload.get("channel_id") or "general"
            ts = event.get("ts", "")
            previous_text = None
            files_meta = []

            if subtype == "message_changed":
                msg = event.get("message", {})
                text = msg.get("text", "")
                user = msg.get("user") or user
                ts = msg.get("ts") or ts
                prev_msg = event.get("previous_message", {})
                previous_text = prev_msg.get("text", "")
                summary_prefix = f"Slack [edited message] in #{channel}"
            elif subtype == "message_deleted":
                prev_msg = event.get("previous_message", {})
                text = prev_msg.get("text", "")
                user = prev_msg.get("user") or user
                ts = event.get("deleted_ts") or ts
                summary_prefix = f"Slack [deleted message] in #{channel}"
            elif subtype == "channel_topic":
                topic = event.get("topic", "")
                text = f"Channel topic updated: {topic}"
                summary_prefix = f"Slack [topic change] in #{channel}"
            elif subtype == "channel_purpose":
                purpose = event.get("purpose", "")
                text = f"Channel purpose updated: {purpose}"
                summary_prefix = f"Slack [purpose change] in #{channel}"
            elif subtype == "file_share":
                text = event.get("text", "Shared a file")
                files = event.get("files", [])
                files_meta = [
                    {
                        "id": f.get("id"),
                        "name": f.get("name"),
                        "title": f.get("title"),
                        "filetype": f.get("filetype"),
                        "size": f.get("size")
                    }
                    for f in files if isinstance(f, dict)
                ]
                summary_prefix = f"Slack [file shared] in #{channel}"
            elif event_type == "reaction_added":
                reaction = event.get("reaction", "")
                item = event.get("item", {})
                item_ts = item.get("ts", "")
                item_channel = item.get("channel") or channel
                user = event.get("user") or user
                ts = event.get("event_ts") or ts
                text = f":{reaction}: reaction added to message"
                channel = item_channel
                summary_prefix = f"Slack [reaction :{reaction}:] in #{channel}"
            else:
                text = event.get("text") or payload.get("text") or "No message text"
                summary_prefix = f"Slack [{event_type}] in #{channel}"

            # Construct clickable Slack permalink: https://slack.com/archives/{channel}/p{ts_without_dot}
            source_url = None
            if channel and ts:
                clean_ts = str(ts).replace(".", "")
                source_url = f"https://slack.com/archives/{channel}/p{clean_ts}"

            summary = f"{summary_prefix}: {text[:80]}"
            author_name = user
            metadata = {
                "event_type": event_type,
                "subtype": subtype,
                "channel_id": channel,
                "text": text,
                "body": text,
                "ts": ts,
                "thread_ts": event.get("thread_ts"),
                "event_id": payload.get("event_id"),
                "client_msg_id": event.get("client_msg_id"),
                "team_id": payload.get("team_id"),
                "previous_text": previous_text,
                "files": files_meta,
                "reaction": event.get("reaction") if event_type == "reaction_added" else None,
                "item_ts": event.get("item", {}).get("ts") if event_type == "reaction_added" else None,
                "item_user": event.get("item_user") if event_type == "reaction_added" else None
            }

        elif platform == "jira":
            issue = payload.get("issue", {})
            webhook_event = payload.get("webhookEvent", "jira:issue_updated")
            comment = payload.get("comment", {})
            attachment = payload.get("attachment", {})
            worklog = payload.get("worklog", {})

            if issue:
                key = issue.get("key", "JIRA-KEY")
                fields = issue.get("fields", {})
                title = fields.get("summary", "No Summary")
                issue_type = fields.get("issuetype", {}).get("name", "Issue")
                priority = fields.get("priority", {}).get("name", "Medium")
                status_name = fields.get("status", {}).get("name", "Open")
                project = fields.get("project", {})
                project_key = project.get("key", "")
                project_name = project.get("name", "")

                creator = fields.get("creator", {}).get("displayName") or fields.get("reporter", {}).get("displayName") or "Jira User"
                user = payload.get("user", {}).get("displayName") or creator
                author_name = user

                # Construct clickable Jira permalink: https://site.atlassian.net/browse/{key}
                self_url = issue.get("self", "")
                domain = ""
                if "atlassian.net" in self_url:
                    domain = self_url.split("/rest/api")[0]
                if domain:
                    source_url = f"{domain}/browse/{key}"
                else:
                    source_url = f"https://atlassian.net/browse/{key}"

                # 1. Comment events author & summary resolution
                if "comment" in webhook_event or comment:
                    comment_author = comment.get("author", {}).get("displayName") or comment.get("updateAuthor", {}).get("displayName")
                    if comment_author:
                        author_name = comment_author

                    comment_body = str(comment.get("body", ""))
                    if webhook_event == "comment_updated":
                        summary = f"Jira [{key}] [COMMENT EDITED] by {author_name}: {comment_body[:80]}"
                    elif webhook_event == "comment_deleted":
                        summary = f"Jira [{key}] [COMMENT DELETED] by {author_name}"
                    else:
                        summary = f"Jira [{key}] [NEW COMMENT] by {author_name}: {comment_body[:80]}"

                # 2. Attachment events resolution
                elif webhook_event == "attachment_created" or attachment:
                    att_author = attachment.get("author", {}).get("displayName")
                    if att_author:
                        author_name = att_author
                    att_name = attachment.get("filename", "file")
                    att_size = attachment.get("size", 0)
                    summary = f"Jira [{key}] [ATTACHMENT]: {att_name} ({att_size} bytes) attached by {author_name}"

                # 3. Worklog events resolution
                elif webhook_event == "worklog_created" or worklog:
                    wl_author = worklog.get("author", {}).get("displayName") or worklog.get("updateAuthor", {}).get("displayName")
                    if wl_author:
                        author_name = wl_author
                    time_spent = worklog.get("timeSpent", "time")
                    summary = f"Jira [{key}] [WORKLOG]: {time_spent} logged by {author_name}"

                # 4. Issue Lifecycle events (Created, Updated, Deleted)
                elif webhook_event == "jira:issue_created":
                    summary = f"Jira [{key}] [CREATED] ({issue_type}/{status_name}): {title}"
                elif webhook_event == "jira:issue_deleted":
                    summary = f"Jira [{key}] [DELETED]: {title}"
                else:
                    summary = f"Jira [{key}] [UPDATED] ({issue_type}/{status_name}): {title}"

                metadata = {
                    "event_type": webhook_event,
                    "issue_key": key,
                    "issue_title": title,
                    "issue_type": issue_type,
                    "priority": priority,
                    "status": status_name,
                    "project_key": project_key,
                    "project_name": project_name,
                    "body": title,
                    "comment": comment.get("body") if comment else None,
                    "comment_id": str(comment.get("id")) if comment and comment.get("id") else None,
                    "attachment": {
                        "filename": attachment.get("filename"),
                        "size": attachment.get("size"),
                        "mimeType": attachment.get("mimeType"),
                        "content": attachment.get("content")
                    } if attachment else None,
                    "user": author_name
                }
                
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

        # Slack Noise Filtering: Filter administrative events (channel_join, channel_leave, channel_archive)
        if parsed.get("type") == "slack":
            subtype = metadata.get("subtype")
            if subtype in {"channel_join", "channel_leave", "channel_archive", "channel_unarchive"}:
                return False, f"Filtered Slack administrative event subtype: {subtype}"
            
            llm_class = metadata.get("llm_classification", {})
            signal_type = llm_class.get("signal_type")
            if signal_type == "noise":
                reasoning = llm_class.get("reasoning", "social noise")
                return False, f"Slack message classified as noise by signal intelligence ({reasoning})."
            return True, None

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

        # Slack Incident Routing Rules:
        # LLM signal_type (incident/debugging) with high/critical urgency spawns NEW SQL Investigations.
        # Edits, deletes, topic changes, reactions, and thread replies land in standalone evidence or thread correlation.
        if integration.platform == "slack":
            metadata = parsed.get("metadata") or {}
            subtype = metadata.get("subtype")
            event_type = metadata.get("event_type")

            if event_type == "reaction_added" or subtype in {"channel_topic", "channel_purpose", "message_changed", "message_deleted"}:
                return False

            if metadata.get("thread_ts"):
                return False

            llm_class = metadata.get("llm_classification", {})
            signal_type = llm_class.get("signal_type", "discussion")
            urgency = llm_class.get("urgency", "low")

            if signal_type in ("incident", "debugging") and urgency in ("critical", "high"):
                return True

            return False

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

        # Gmail Operational Routing Rules:
        # Genuine system monitoring alerts spawn NEW SQL Investigations.
        # Personal newsletters, bank alerts, and job updates go to standalone evidence.
        if integration.platform == "gmail":
            author = (parsed.get("author_name") or "").lower()
            subject = (parsed.get("summary") or "").lower()

            # Non-operational personal email senders -> standalone evidence (never spawn SQL investigation)
            personal_senders = [
                "bank", "credit", "card", "newsletter", "digest", "jobs", "job", "careers",
                "economist", "medium", "indeed", "linkedin", "hirist", "groww", "nse", "sbi",
                "paypal", "shoppersstop", "udemy", "anaconda", "wispr", "cred.club"
            ]
            if any(ps in author for ps in personal_senders):
                return False

            # Genuine operational monitoring prefixes
            op_prefixes = ["datadog", "sentry", "grafana", "kubernetes", "k8s", "pagerduty", "cloudwatch", "prometheus", "newrelic", "[alert]", "[error]", "[critical]", "incident"]
            if any(op in author or op in subject for op in op_prefixes):
                return True

            # If user has explicit triage rules configured, check them
            has_any_configured_rules = bool(
                config.get("allowed_senders") or config.get("required_keywords") or
                config.get("subject_contains") or config.get("subject_starts_with")
            )
            if has_any_configured_rules:
                required_keywords = [k.lower() for k in config.get("required_keywords", []) if k and k.strip()]
                if required_keywords and any(kw in full_text for kw in required_keywords):
                    return True
                subject_contains = [sc.lower() for sc in config.get("subject_contains", []) if sc and sc.strip()]
                if subject_contains and any(sc in summary for sc in subject_contains):
                    return True
                subject_starts_with = [ss.lower() for ss in config.get("subject_starts_with", []) if ss and ss.strip()]
                if subject_starts_with and any(summary.startswith(ss) for ss in subject_starts_with):
                    return True

            # Otherwise, un-configured personal/general emails land in Standalone Evidence
            return False

        # Jira Structured Incident Routing Rules:
        # High/Highest priority issues, bugs, or incident issue types spawn NEW SQL Investigations.
        # Comments, worklogs, attachments, deletions, or lower priority tasks land in standalone evidence or deterministic correlation.
        if integration.platform == "jira":
            metadata = parsed.get("metadata") or {}
            event_type = metadata.get("event_type")
            priority = str(metadata.get("priority") or "").lower()
            issue_type = str(metadata.get("issue_type") or "").lower()

            # Comment, worklog, attachment, or deletion events never spawn NEW SQL Investigations on their own
            if event_type in ("comment_created", "comment_updated", "comment_deleted", "attachment_created", "worklog_created", "jira:issue_deleted"):
                return False

            # High priority issues or Bug/Incident issue types -> incident-worthy
            if priority in ("highest", "high", "critical", "p0", "p1", "blocker"):
                return True

            if issue_type in ("bug", "incident", "security", "vulnerability"):
                return True

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
        ist_now = get_ist_time_str()
        platform = integration.platform.upper()

        # Step 0: Event Deduplication Check
        event_id = raw_payload.get("event_id") or raw_payload.get("event", {}).get("client_msg_id")
        if event_id:
            if event_id in PROCESSED_EVENT_IDS:
                print(f"[{ist_now}] 🔁 [{platform}] IGNORED (Duplicate Event ID: {event_id})")
                return {"status": "ignored", "reason": f"Duplicate event ID '{event_id}' suppressed."}
            
            if len(PROCESSED_EVENT_IDS) > 10000:
                PROCESSED_EVENT_IDS.clear()
            PROCESSED_EVENT_IDS.add(str(event_id))

        # Step 1: Platform Filter
        allowed, filter_reason = IngestService.platform_filter(integration, raw_payload)
        if not allowed:
            print(f"[{ist_now}] 🚫 [{platform}] IGNORED (Platform Filter): {filter_reason}")
            return {"status": "ignored", "reason": filter_reason}

        # Step 2: Normalize Payload
        parsed = IngestService.normalize_payload(integration.platform, raw_payload)

        # Slack Real Name, Channel Name & LLM Signal Intelligence Resolution
        if integration.platform == "slack":
            from app.core.security import decrypt_credentials
            try:
                creds = decrypt_credentials(integration.credentials_encrypted)
                access_token = creds.get("access_token")
                
                if parsed.get("author_name"):
                    parsed["author_name"] = await resolve_slack_user_name(access_token, parsed["author_name"])
                
                channel_id = parsed.get("metadata", {}).get("channel_id")
                ch_name = channel_id or "general"
                if channel_id:
                    ch_name = await resolve_slack_channel_name(access_token, channel_id, integration.config)
                    parsed["metadata"]["channel_name"] = ch_name
                    if f"in #{channel_id}" in parsed.get("summary", ""):
                        parsed["summary"] = parsed["summary"].replace(f"in #{channel_id}", f"in #{ch_name}")

                # Call LLM Signal Intelligence
                text_to_classify = parsed.get("metadata", {}).get("text", "")
                llm_class = await classify_slack_signal(text_to_classify, ch_name)
                parsed["metadata"]["llm_classification"] = llm_class
            except Exception:
                pass

        # Step 2.5: Slack Evidence Lifecycle (Edits, Deletions)
        if integration.platform == "slack":
            subtype = parsed.get("metadata", {}).get("subtype")
            channel_id = parsed.get("metadata", {}).get("channel_id")
            
            if subtype == "message_changed":
                orig_ts = parsed.get("metadata", {}).get("ts")
                new_text = parsed.get("metadata", {}).get("text", "")
                prev_text = parsed.get("metadata", {}).get("previous_text")
                edited_id = await handle_slack_edit(mongo_db, channel_id, orig_ts, new_text, prev_text)
                if edited_id:
                    print(f"[{ist_now}] ✏️ [SLACK] EVIDENCE UPDATED (Edit Event: {edited_id})")
                    return {"status": "updated", "evidence_id": edited_id}

            elif subtype == "message_deleted":
                del_ts = parsed.get("metadata", {}).get("ts")
                retracted_id = await handle_slack_delete(mongo_db, channel_id, del_ts)
                if retracted_id:
                    print(f"[{ist_now}] 🗑️ [SLACK] EVIDENCE RETRACTED (Delete Event: {retracted_id})")
                    return {"status": "retracted", "evidence_id": retracted_id}

        # Step 2.5: Jira Evidence Lifecycle (Comment Edits, Comment Deletions, Issue Deletions)
        if integration.platform == "jira":
            webhook_event = parsed.get("metadata", {}).get("event_type")
            issue_key = parsed.get("metadata", {}).get("issue_key")
            comment_id = parsed.get("metadata", {}).get("comment_id")

            if webhook_event == "comment_updated":
                new_body = parsed.get("metadata", {}).get("comment") or ""
                author_name = parsed.get("author_name") or "Jira User"
                edited_id = await handle_jira_comment_edit(mongo_db, issue_key, comment_id, new_body, author_name)
                if edited_id:
                    print(f"[{ist_now}] ✏️ [JIRA] EVIDENCE UPDATED (Comment Edit: {edited_id})")
                    return {"status": "updated", "evidence_id": edited_id}

            elif webhook_event == "comment_deleted":
                retracted_id = await handle_jira_comment_delete(mongo_db, issue_key, comment_id)
                if retracted_id:
                    print(f"[{ist_now}] 🗑️ [JIRA] EVIDENCE RETRACTED (Comment Delete: {retracted_id})")
                    return {"status": "retracted", "evidence_id": retracted_id}

            elif webhook_event == "jira:issue_deleted":
                retracted_ids = await handle_jira_issue_delete(mongo_db, issue_key)
                if retracted_ids:
                    print(f"[{ist_now}] 🗑️ [JIRA] EVIDENCE RETRACTED (Issue Delete: {len(retracted_ids)} items for {issue_key})")
                    return {"status": "retracted", "evidence_ids": retracted_ids}

        author = parsed.get("author_name") or "Unknown"
        summary = parsed.get("summary") or "No Summary"
        print(f"[{ist_now}] 📥 INCOMING TELEMETRY | Platform: {platform} | Author: {author[:30]} | Summary: {summary[:80]}")

        # Step 3: Signal / Noise Classification
        is_signal, noise_reason = IngestService.classify_signal(integration, parsed)
        if not is_signal:
            print(f"[{ist_now}] 🔇 [{platform}] IGNORED (Noise Filter): {noise_reason}")
            return {"status": "ignored", "reason": noise_reason}

        # Step 3.5: Slack Deterministic Thread Correlation
        if integration.platform == "slack":
            thread_ts = parsed.get("metadata", {}).get("thread_ts")
            channel_id = parsed.get("metadata", {}).get("channel_id")
            thread_inv_id = await correlate_slack_thread(mongo_db, thread_ts, channel_id)
            if thread_inv_id:
                evidence_in = EvidenceCreate(
                    type=parsed["type"],
                    summary=parsed["summary"],
                    author_name=parsed["author_name"],
                    source_url=parsed["source_url"],
                    metadata=parsed["metadata"]
                )
                evidence = await EvidenceService.create_evidence(mongo_db, uuid.UUID(thread_inv_id), evidence_in)
                print(f"[{ist_now}] 🧵 [SLACK] THREAD CORRELATED -> Linked to Investigation {thread_inv_id}")
                return {
                    "status": "correlated",
                    "investigation_id": uuid.UUID(thread_inv_id),
                    "evidence_id": evidence.id
                }

        # Step 3.5: Jira Deterministic Issue-Key Correlation
        if integration.platform == "jira":
            issue_key = parsed.get("metadata", {}).get("issue_key")
            jira_inv_id = await correlate_jira_issue_key(mongo_db, issue_key)
            if jira_inv_id:
                evidence_in = EvidenceCreate(
                    type=parsed["type"],
                    summary=parsed["summary"],
                    author_name=parsed["author_name"],
                    source_url=parsed["source_url"],
                    metadata=parsed["metadata"]
                )
                evidence = await EvidenceService.create_evidence(mongo_db, uuid.UUID(jira_inv_id), evidence_in)
                print(f"[{ist_now}] 🔗 [JIRA] ISSUE-KEY CORRELATED -> Linked to Investigation {jira_inv_id} ({issue_key})")
                return {
                    "status": "correlated",
                    "investigation_id": uuid.UUID(jira_inv_id),
                    "evidence_id": evidence.id
                }

        # Step 3.75: Cross-Platform Issue-Key Correlation (Slack, GitHub, Gmail referencing Jira keys like KAN-100)
        if integration.platform != "jira":
            full_incoming_text = f"{parsed.get('summary', '')} {str(parsed.get('metadata') or {})}"
            cross_inv_id = await correlate_cross_platform_keys(mongo_db, full_incoming_text)
            if cross_inv_id:
                evidence_in = EvidenceCreate(
                    type=parsed["type"],
                    summary=parsed["summary"],
                    author_name=parsed["author_name"],
                    source_url=parsed["source_url"],
                    metadata=parsed["metadata"]
                )
                evidence = await EvidenceService.create_evidence(mongo_db, uuid.UUID(cross_inv_id), evidence_in)
                print(f"[{ist_now}] 🌐 [{platform}] CROSS-PLATFORM CORRELATED -> Linked to Investigation {cross_inv_id} via Jira issue key match")
                return {
                    "status": "correlated",
                    "investigation_id": uuid.UUID(cross_inv_id),
                    "evidence_id": evidence.id
                }

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
            print(f"[{ist_now}] 🔗 [{platform}] CORRELATED -> Linked to Investigation {matched_inv.id} ({matched_inv.title[:50]})")
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
            print(f"[{ist_now}] 📦 [{platform}] STANDALONE EVIDENCE -> Stored in Mongo (investigation_id = None)")
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
        print(f"[{ist_now}] 🚨 [{platform}] NEW INVESTIGATION CREATED -> ID: {new_inv.id} | Severity: {severity.upper()}")

        return {
            "status": "created",
            "investigation_id": new_inv.id,
            "evidence_id": evidence.id
        }
