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
        # Find all words with length >= 3
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        stop_words = {
            "the", "and", "for", "from", "with", "this", "that", "alert", 
            "error", "sentry", "github", "slack", "jira", "gmail", "message", 
            "commit", "issue", "incident", "outage", "broken", "failed"
        }
        return {word for word in words if word not in stop_words}

    @staticmethod
    def parse_webhook_payload(platform: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Parse raw webhook payload depending on the integration platform.
        Extracts summary, author, source_url, and structured metadata.
        """
        summary = "Unrecognized webhook alert payload"
        author_name = None
        source_url = None
        metadata = payload

        if platform == "slack":
            event = payload.get("event", {})
            text = event.get("text", "")
            summary = f"Slack Alert: {text[:100]}..." if len(text) > 100 else f"Slack Alert: {text}"
            author_name = event.get("user")
            
        elif platform == "github":
            # GitHub Push webhook payload structure
            commit = payload.get("head_commit", {})
            if commit:
                msg = commit.get("message", "")
                summary = f"GitHub Commit: {msg[:100]}..." if len(msg) > 100 else f"GitHub Commit: {msg}"
                author_name = commit.get("author", {}).get("username") or commit.get("author", {}).get("name")
                source_url = commit.get("url")
            else:
                repo_name = payload.get("repository", {}).get("full_name", "Unknown Repo")
                summary = f"GitHub Event on repository: {repo_name}"

        elif platform == "jira":
            # Jira webhook payload structure
            issue = payload.get("issue", {})
            if issue:
                key = issue.get("key", "JIRA-KEY")
                fields = issue.get("fields", {})
                title = fields.get("summary", "No Summary")
                summary = f"Jira Issue {key}: {title}"
                author_name = fields.get("creator", {}).get("displayName")
                
        elif platform == "gmail":
            # Gmail inbox alert structure
            email = payload.get("email", {})
            if email:
                subject = email.get("subject", "No Subject")
                summary = f"Gmail Alert: {subject}"
                author_name = email.get("from")

        return {
            "type": platform,
            "summary": summary,
            "author_name": author_name,
            "source_url": source_url,
            "metadata": metadata
        }

    @staticmethod
    async def correlate_and_process(
        db: AsyncSession,
        mongo_db: AsyncIOMotorDatabase,
        integration: Integration,
        raw_payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Process the raw payload, correlate it against active investigations,
        and append it to MongoDB. Auto-creates a new SQL Investigation container if no match exists.
        """
        # 0. Enforce tracking configurations
        if integration.platform == "github":
            repo_name = raw_payload.get("repository", {}).get("full_name")
            tracked_repos = integration.config.get("tracked_repos", [])
            if repo_name and repo_name not in tracked_repos:
                return {
                    "status": "ignored",
                    "reason": f"Repository '{repo_name}' is not in the tracked repositories list."
                }
        elif integration.platform == "slack":
            event = raw_payload.get("event", {})
            channel_id = event.get("channel")
            configured_channel_id = integration.config.get("channel_id")
            if channel_id and channel_id != configured_channel_id:
                return {
                    "status": "ignored",
                    "reason": f"Slack event channel '{channel_id}' does not match configured triage channel."
                }

        # 1. Parse platform-specific payload fields
        parsed = IngestService.parse_webhook_payload(integration.platform, raw_payload)
        
        # 2. Extract keywords from parsed summary
        incoming_keywords = IngestService.extract_keywords(parsed["summary"])
        
        # 3. Fetch active investigations for this tenant
        statement = select(Investigation).where(
            Investigation.organization_id == integration.organization_id,
            Investigation.status.in_(["open", "investigating"])
        )
        result = await db.execute(statement)
        active_investigations = result.scalars().all()
        
        matched_investigation = None
        
        # 4. Check keyword overlap for correlation
        for inv in active_investigations:
            inv_keywords = IngestService.extract_keywords(inv.title)
            # Find common keywords
            overlap = inv_keywords.intersection(incoming_keywords)
            if len(overlap) > 0:
                matched_investigation = inv
                break
                
        # 5. Route to Database
        if matched_investigation is not None:
            # Match found -> Appends evidence directly to matched investigation
            evidence_in = EvidenceCreate(
                type=parsed["type"],
                summary=parsed["summary"],
                author_name=parsed["author_name"],
                source_url=parsed["source_url"],
                metadata=parsed["metadata"]
            )
            evidence = await EvidenceService.create_evidence(mongo_db, matched_investigation.id, evidence_in)
            return {
                "status": "correlated",
                "investigation_id": matched_investigation.id,
                "evidence_id": evidence.id
            }
        else:
            # No match found -> Auto-creates a new SQL investigation
            severity = "medium"
            lower_summary = parsed["summary"].lower()
            if "critical" in lower_summary or "outage" in lower_summary or "severity 1" in lower_summary:
                severity = "critical"
            elif "error" in lower_summary or "failed" in lower_summary or "spiked" in lower_summary or "leak" in lower_summary:
                severity = "high"

                
            new_inv = Investigation(
                organization_id=integration.organization_id,
                title=parsed["summary"],
                description=f"Auto-created from incoming {integration.platform} webhook payload.",
                severity=severity,
                status="open"
            )
            db.add(new_inv)
            await db.commit()
            await db.refresh(new_inv)
            
            # Save payload as the first evidence of this new investigation container
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
