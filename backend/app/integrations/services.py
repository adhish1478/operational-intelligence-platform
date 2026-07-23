import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.integrations.models import Integration
from app.integrations.schemas import IntegrationCreate, IntegrationUpdate
from app.core.security import encrypt_credentials, decrypt_credentials

class IntegrationService:
    @staticmethod
    async def get_integration_by_id(db: AsyncSession, integration_id: uuid.UUID) -> Integration | None:
        statement = select(Integration).where(Integration.id == integration_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_organization_integrations(db: AsyncSession, organization_id: uuid.UUID) -> Sequence[Integration]:
        statement = select(Integration).where(Integration.organization_id == organization_id)
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def create_integration(
        db: AsyncSession, organization_id: uuid.UUID, integration_in: IntegrationCreate
    ) -> Integration:
        # Prevent duplicate integration rows for the same platform in an organization
        statement = select(Integration).where(
            Integration.organization_id == organization_id,
            Integration.platform == integration_in.platform
        )
        existing = (await db.execute(statement)).scalar_one_or_none()

        encrypted_creds = encrypt_credentials(integration_in.credentials)

        if existing:
            existing.credentials_encrypted = encrypted_creds
            existing.status = integration_in.status
            db.add(existing)
            await db.commit()
            await db.refresh(existing)
            return existing

        integration = Integration(
            organization_id=organization_id,
            platform=integration_in.platform,
            credentials_encrypted=encrypted_creds,
            config={},
            status=integration_in.status
        )
        db.add(integration)
        await db.commit()
        await db.refresh(integration)
        return integration

    @staticmethod
    async def update_integration(
        db: AsyncSession, db_obj: Integration, obj_in: IntegrationUpdate
    ) -> Integration:
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # If user is updating credentials, encrypt them first
        if "credentials" in update_data and update_data["credentials"] is not None:
            encrypted_creds = encrypt_credentials(update_data.pop("credentials"))
            db_obj.credentials_encrypted = encrypted_creds
            
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        if "config" in update_data:
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(db_obj, "config")

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def delete_integration(db: AsyncSession, db_obj: Integration) -> None:
        await db.delete(db_obj)
        await db.commit()

    @staticmethod
    def get_decrypted_credentials(db_obj: Integration) -> dict:
        """
        Helper method to decrypt credentials for system ingestion worker logic.
        """
        return decrypt_credentials(db_obj.credentials_encrypted)
