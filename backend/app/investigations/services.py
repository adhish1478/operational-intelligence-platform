import uuid
from typing import Sequence, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth.models import User
from app.investigations.models import Investigation, Diagnosis
from app.investigations.schemas import InvestigationCreate, InvestigationUpdate



class InvestigationService:
    @staticmethod
    async def get_investigation_by_id(db: AsyncSession, investigation_id: uuid.UUID) -> Investigation | None:
        statement = select(Investigation).where(Investigation.id == investigation_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_organization_investigations(db: AsyncSession, organization_id: uuid.UUID) -> Sequence[Investigation]:
        statement= select(Investigation).where(Investigation.organization_id == organization_id)
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def create_investigation(
        db: AsyncSession, organization_id: uuid.UUID, investigation_in: InvestigationCreate
    )-> Investigation:
        data = investigation_in.model_dump(exclude_unset=True)
        suggested_act = data.pop("suggested_action", None)
        if suggested_act and not data.get("suggestion_action"):
            data["suggestion_action"] = suggested_act

        investigation = Investigation(
            organization_id = organization_id,
            **data
        )
        db.add(investigation)

        await db.commit()
        await db.refresh(investigation)
        return investigation

    @staticmethod
    async def update_investigation(
        db: AsyncSession, db_obj: Investigation, obj_in: InvestigationUpdate
    ) -> Investigation:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class DiagnosisService:
    @staticmethod
    async def get_diagnosis_by_id(db: AsyncSession, diagnosis_id: uuid.UUID) -> Diagnosis | None:
        statement = select(Diagnosis).where(Diagnosis.id == diagnosis_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_investigation_diagnoses(db: AsyncSession, investigation_id: uuid.UUID) -> Sequence[Diagnosis]:
        statement = select(Diagnosis).where(Diagnosis.investigation_id == investigation_id)
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def generate_diagnosis_report(
        db: AsyncSession,
        mongo_db: Any,
        investigation: Investigation,
        triggered_by_id: uuid.UUID,
        event_callback: Any | None = None
    ) -> Diagnosis:
        from app.evidence.services import EvidenceService
        from app.investigations.multi_agent import MultiAgentOrchestrator

        # 1. Fetch all evidence for the investigation chronologically from MongoDB
        evidence_list = await EvidenceService.list_investigation_evidence(mongo_db, investigation.id)
        evidence_dicts = [
            {
                "id": str(ev.id),
                "type": ev.type,
                "author_name": ev.author_name,
                "summary": ev.summary,
                "source_url": ev.source_url,
                "metadata": ev.metadata,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            for ev in evidence_list
        ]

        # 2. Run Multi-Agent DAG Orchestrator
        orchestrator = MultiAgentOrchestrator()
        dag_output = await orchestrator.run_dag_analysis(
            investigation_title=investigation.title,
            investigation_description=investigation.description or "",
            severity=investigation.severity,
            evidence_items=evidence_dicts,
            event_callback=event_callback,
        )

        rca = dag_output.technical_rca
        impact = dag_output.business_impact
        remediation = dag_output.remediation_plan

        # 3. Format unified Markdown report summary for backwards compatibility (UI, Slack, Jira)
        report_summary = (
            f"### Incident Executive Summary\n"
            f"{dag_output.executive_summary}\n\n"
            f"### Technical Root Cause Analysis\n"
            f"{rca.root_cause_summary}\n\n"
            f"**Impacted Services:** {', '.join(rca.impacted_services) if rca.impacted_services else 'N/A'}\n"
            f"**Offending Commit:** `{rca.offending_commit.hash if rca.offending_commit else 'N/A'}` by {rca.offending_commit.author if rca.offending_commit else 'Unknown'}\n\n"
            f"### Business Impact & SLA Assessment\n"
            f"* **Financial Risk Level:** `{impact.financial_risk_level}` (${impact.estimated_downtime_cost_per_hour:,.2f}/hr exposure)\n"
            f"* **SLA Status:** `{impact.sla_breach_status}`\n"
            f"* **Cross-Functional Blast Radius:** {', '.join(impact.cross_functional_blast_radius)}\n\n"
            f"### Actionable Remediation & Hotfix\n"
        )
        for idx, step in enumerate(remediation.immediate_mitigation_steps, 1):
            report_summary += f"{step if step.startswith(str(idx)) else f'{idx}. {step}'}\n"

        report_summary += f"\n**Git Rollback Command:**\n```bash\n{remediation.git_rollback_command}\n```\n"

        # 4. Validate triggered_by_id user FK
        valid_user_id = None
        if triggered_by_id:
            user_check = await db.execute(select(User.id).where(User.id == triggered_by_id))
            if user_check.scalar_one_or_none():
                valid_user_id = triggered_by_id

        # Save Diagnosis to PostgreSQL with structured JSON columns
        diagnosis = Diagnosis(
            investigation_id=investigation.id,
            triggered_by_id=valid_user_id,
            report_summary=report_summary,
            technical_rca=rca.model_dump(),
            business_impact=impact.model_dump(),
            remediation_plan=remediation.model_dump(),
            orchestration_metadata={
                "triage_mode": dag_output.triage_mode,
                "evidence_count": len(evidence_list),
                "severity": investigation.severity,
            }
        )
        db.add(diagnosis)

        # 5. Update parent investigation status and suggestion
        investigation.status = "investigating"
        investigation.suggested_action = report_summary
        db.add(investigation)

        await db.commit()
        await db.refresh(diagnosis)
        await db.refresh(investigation)

        return diagnosis


