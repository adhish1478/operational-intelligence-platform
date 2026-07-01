import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.investigations.models import Investigation
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

