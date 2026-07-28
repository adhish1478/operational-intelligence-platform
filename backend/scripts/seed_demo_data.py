import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.mongo import get_mongo_db
from app.auth.models import User
from app.organizations.models import Organization, Membership
from app.investigations.models import Investigation
from app.evidence.schemas import EvidenceCreate
from app.evidence.services import EvidenceService
from app.core.security import hash_password


async def seed_data():
    print("🌱 Seeding realistic incident investigations and evidence telemetry...")
    async with AsyncSessionLocal() as db:
        mongo_db = get_mongo_db()

        # 1. Ensure Default User & Organization
        user_stmt = select(User).where(User.email == "admin@example.com")
        res = await db.execute(user_stmt)
        user = res.scalar_one_or_none()

        if not user:
            user = User(
                email="admin@example.com",
                password_hash=hash_password("password123"),
                full_name="Lead SRE Admin"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        org_stmt = select(Organization).where(Organization.slug == "demo-org")
        res = await db.execute(org_stmt)
        org = res.scalar_one_or_none()

        if not org:
            org = Organization(
                name="Acme Platform Engineering",
                slug="demo-org"
            )
            db.add(org)
            await db.flush()

            db.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
            await db.commit()
            await db.refresh(org)

        # 2. Create Realistic Incident Investigations
        inv1 = Investigation(
            organization_id=org.id,
            title="Database Connection Pool Exhaustion on API Gateway",
            description="Severe 504 Gateway Timeouts and latency spikes (>4500ms) on /checkout and /payments endpoints.",
            severity="critical",
            status="open",
            assigned_to_id=user.id
        )

        inv2 = Investigation(
            organization_id=org.id,
            title="Auth Service JWT Verification Failure Spike",
            description="Elevated HTTP 401 Unauthorized errors affecting Enterprise Tier 1 single sign-on users.",
            severity="high",
            status="open",
            assigned_to_id=user.id
        )

        db.add(inv1)
        db.add(inv2)
        await db.commit()
        await db.refresh(inv1)
        await db.refresh(inv2)

        print(f"✅ Created Investigation 1: '{inv1.title}' (ID: {inv1.id})")
        print(f"✅ Created Investigation 2: '{inv2.title}' (ID: {inv2.id})")

        # 3. Create Rich Evidence Items for Investigation 1 (Database Exhaustion)
        ev_items_1 = [
            EvidenceCreate(
                type="github",
                summary="GitHub Commit #a8f912e: Reduced default DB pool max_overflow parameter",
                author_name="dev-alice",
                source_url="https://github.com/acme/api-gateway/commit/a8f912e",
                metadata={
                    "commit_hash": "a8f912e38c92a1b",
                    "author": "Alice S. <alice@acme.com>",
                    "message": "perf: optimize pool overflow defaults for staging",
                    "diff_summary": "- max_overflow = 50\n+ max_overflow = 5"
                }
            ),
            EvidenceCreate(
                type="alert",
                summary="Sentry Alert: DB_CONNECTION_TIMEOUT in sqlalchemy/pool.py line 248",
                author_name="Alertmanager",
                source_url="https://sentry.io/organizations/acme/issues/84912/",
                metadata={
                    "error_signature": "TimeoutError: QueuePool limit of size 10 overflow 5 reached",
                    "impacted_service": "api-gateway-service",
                    "environment": "production"
                }
            ),
            EvidenceCreate(
                type="slack",
                summary="#incident-checkout: Customers reporting payment hanging at 99%. 42 support tickets logged in 15 mins.",
                author_name="sre-oncall",
                source_url="https://acme.slack.com/archives/C012345/p16723223",
                metadata={
                    "channel": "#incident-checkout",
                    "affected_customers": ["Enterprise-Acme", "Growth-Tier-Corp"],
                    "symptom": "Payment gateway handshake timeout"
                }
            ),
            EvidenceCreate(
                type="jira",
                summary="Jira Ticket PLAT-482: [URGENT] Database connection limits hit on Prod-US-West-1",
                author_name="jira-bot",
                source_url="https://acme.atlassian.net/browse/PLAT-482",
                metadata={
                    "issue_key": "PLAT-482",
                    "priority": "Highest",
                    "reporter": "Lead SRE"
                }
            ),
            EvidenceCreate(
                type="gmail",
                summary="Email Escalation: Enterprise Tier 1 Account VP Escalation - Checkout API Errors",
                author_name="enterprise-support@acme.com",
                source_url=None,
                metadata={
                    "customer_tier": "Enterprise Tier 1",
                    "sla_status": "AT_RISK",
                    "financial_impact_est": "$18,500/hr"
                }
            ),
        ]

        for ev in ev_items_1:
            await EvidenceService.create_evidence(mongo_db, inv1.id, ev)

        print(f"✅ Seeded {len(ev_items_1)} evidence items for Investigation 1.")

        # 4. Create Evidence Items for Investigation 2 (JWT Failure Spike)
        ev_items_2 = [
            EvidenceCreate(
                type="github",
                summary="GitHub PR #182: Refactored JWT token signing key rotation algorithm",
                author_name="dev-bob",
                source_url="https://github.com/acme/auth-service/pull/182",
                metadata={
                    "commit_hash": "b7194c201a",
                    "author": "Bob T. <bob@acme.com>",
                    "diff_summary": "Rotated RSA 2048 key without fallback grace period"
                }
            ),
            EvidenceCreate(
                type="slack",
                summary="#auth-alerts: SSO login errors spiked to 14.2% across Okta SAML integrations",
                author_name="datadog-bot",
                source_url=None,
                metadata={
                    "metric": "sso.auth.failure_rate",
                    "threshold": "> 2.0%"
                }
            )
        ]

        for ev in ev_items_2:
            await EvidenceService.create_evidence(mongo_db, inv2.id, ev)

        print(f"✅ Seeded {len(ev_items_2)} evidence items for Investigation 2.")
        print("🎉 Demo data population complete!")


if __name__ == "__main__":
    asyncio.run(seed_data())
