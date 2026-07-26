import uuid
from typing import Sequence, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
        investigation = Investigation(
            organization_id = organization_id,
            **investigation_in.model_dump()
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
        triggered_by_id: uuid.UUID
    ) -> Diagnosis:
        from openai import AsyncOpenAI
        from app.core.config import settings
        from app.evidence.services import EvidenceService

        # 1. Fetch all evidence for the investigation chronologically from MongoDB
        evidence_list = await EvidenceService.list_investigation_evidence(mongo_db, investigation.id)
        
        # Compile the timeline context
        timeline = ""
        for idx, ev in enumerate(evidence_list, 1):
            timeline += f"{idx}. [{ev.created_at.isoformat()}] Platform: {ev.type} | Author: {ev.author_name} | Summary: {ev.summary}\n"
            if ev.source_url:
                timeline += f"   URL: {ev.source_url}\n"
            timeline += f"   Raw Details: {ev.metadata}\n\n"

            
        system_prompt = (
            "You are Antigravity AI, an expert Lead Site Reliability Engineer and Forensic Incident Analyst.\n"
            "Analyze the provided chronological timeline of evidence logs for an operational incident investigation.\n"
            "Generate a structured, highly professional Markdown diagnosis report with the following exact section headers:\n\n"
            "### 🚨 Incident Overview\n"
            "A concise 2-sentence summary of the active incident.\n\n"
            "### 🔍 Estimated Root Cause\n"
            "Direct technical explanation of the likely root cause based on telemetry evidence.\n\n"
            "### ⏱️ Key Telemetry Timeline\n"
            "Bullet list of critical events across platforms with timestamps and platform names.\n\n"
            "### ⚡ Actionable Remediation & Hotfix\n"
            "Numbered step-by-step hotfix/mitigation instructions for engineering on-call.\n\n"
            "Keep the report under 350 words. Be direct, technical, and precise."
        )
        
        user_content = (
            f"Investigation Title: {investigation.title}\n"
            f"Investigation Description: {investigation.description}\n\n"
            f"Chronological Evidence Timeline:\n{timeline}"
        )
        
        report_summary = ""
        if settings.OPENAI_API_KEY:
            try:
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                completion = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    max_tokens=500,
                    temperature=0.2
                )
                report_summary = completion.choices[0].message.content or ""
            except Exception as e:
                # Fallback to local detailed summary in case of API connection error
                report_summary = f"[AI Engine Exception, fallback report generated]\nRoot Cause: {investigation.title}. Details: {str(e)}"
        
        if not report_summary:
            # Fallback mock report generation if OpenAI key is not present or failed
            report_summary = (
                f"--- DIAGNOSIS REPORT FOR: {investigation.title} ---\n"
                f"Root Cause: Multiple system failure alerts detected.\n"
                f"Evidence Summary: Found {len(evidence_list)} logs spanning platforms.\n"
                f"Recommendation: Review error logs and trace resource exhaustion bottlenecks."
            )

        # 2. Save Diagnosis to PostgreSQL
        diagnosis = Diagnosis(
            investigation_id=investigation.id,
            triggered_by_id=triggered_by_id,
            report_summary=report_summary
        )
        db.add(diagnosis)
        
        # 3. Update the investigation status to "investigating" and save suggestions
        investigation.status = "investigating"
        investigation.suggestion_action = report_summary
        db.add(investigation)
        
        await db.commit()
        await db.refresh(diagnosis)
        await db.refresh(investigation)
        
        return diagnosis


