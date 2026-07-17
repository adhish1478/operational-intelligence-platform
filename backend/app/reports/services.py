import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.investigations.models import Investigation
from app.reports.schemas import (
    ReportDigest,
    SeverityDistribution,
    CategoryDistribution
)

class ReportService:
    @staticmethod
    async def generate_weekly_digest(db: AsyncSession, organization_id: uuid.UUID) -> ReportDigest:
        """
        Aggregate active/resolved investigation metrics, SLA warning/breach counts,
        severity weights, and title-keyword categories for the organization.
        """
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        # Retrieve all investigations belonging to this tenant organization
        statement = select(Investigation).where(Investigation.organization_id == organization_id)
        result = await db.execute(statement)
        investigations = result.scalars().all()

        total_created_last_7_days = 0
        total_resolved_last_7_days = 0
        total_active = 0
        sla_warnings = 0
        sla_breaches = 0

        # Severity counts for active incidents
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0

        # Category counts for active incidents
        db_count = 0
        api_count = 0
        infra_count = 0
        other_count = 0

        for inv in investigations:
            # Enforce timezone safety
            detected_at = inv.detected_at
            if detected_at.tzinfo is None:
                detected_at = detected_at.replace(tzinfo=timezone.utc)
            else:
                detected_at = detected_at.astimezone(timezone.utc)

            # Check creation stats (created in last 7 days)
            if detected_at >= seven_days_ago:
                total_created_last_7_days += 1

            # Check resolution stats
            if inv.status == "resolved":
                # Assuming resolution within the digest window if detected within 7 days
                if detected_at >= seven_days_ago:
                    total_resolved_last_7_days += 1
            else:
                # Incident is active (open or investigating)
                total_active += 1

                # 1. Update severity counts
                severity = inv.severity.lower()
                if severity == "critical":
                    critical_count += 1
                elif severity == "high":
                    high_count += 1
                elif severity == "medium":
                    medium_count += 1
                else:
                    low_count += 1

                # 2. Update category counts via title keyword check
                title_lower = inv.title.lower()
                if any(k in title_lower for k in ["database", "db", "sql", "mongo"]):
                    db_count += 1
                elif any(k in title_lower for k in ["api", "http", "checkout", "router", "endpoint"]):
                    api_count += 1
                elif any(k in title_lower for k in ["kubernetes", "k8s", "server", "memory", "cpu", "leak"]):
                    infra_count += 1
                else:
                    other_count += 1

                # 3. Calculate SLA states
                # SLA hours: critical = 4h, high = 12h, medium = 24h, low = 48h
                if severity == "critical":
                    sla_limit = timedelta(hours=4)
                elif severity == "high":
                    sla_limit = timedelta(hours=12)
                elif severity == "medium":
                    sla_limit = timedelta(hours=24)
                else:
                    sla_limit = timedelta(hours=48)

                elapsed = now - detected_at
                
                # Check breach
                if elapsed > sla_limit:
                    sla_breaches += 1
                # Check warning (within 80% to 100% of SLA time limit)
                elif elapsed > (sla_limit * 0.8):
                    sla_warnings += 1

        return ReportDigest(
            organization_id=organization_id,
            total_created_last_7_days=total_created_last_7_days,
            total_resolved_last_7_days=total_resolved_last_7_days,
            total_active=total_active,
            sla_warnings=sla_warnings,
            sla_breaches=sla_breaches,
            severity_distribution=SeverityDistribution(
                critical=critical_count,
                high=high_count,
                medium=medium_count,
                low=low_count
            ),
            category_distribution=CategoryDistribution(
                database=db_count,
                api=api_count,
                infrastructure=infra_count,
                other=other_count
            ),
            generated_at=now
        )
