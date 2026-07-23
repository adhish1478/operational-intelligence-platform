import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.evidence.schemas import EvidenceCreate, EvidenceRead

class EvidenceService:
    @staticmethod
    async def list_investigation_evidence(
        mongo_db: AsyncIOMotorDatabase, investigation_id: uuid.UUID
    ) -> list[EvidenceRead]:
        """
        List all evidence associated with a specific investigation in chronological order.
        """
        cursor = mongo_db.evidence.find({"investigation_id": str(investigation_id)}).sort("created_at", 1)
        documents = await cursor.to_list(length=1000)
        
        evidence_list = []
        for doc in documents:
            doc_id = doc.pop("_id")
            raw_inv_id = doc.get("investigation_id")
            inv_id = uuid.UUID(raw_inv_id) if raw_inv_id else None
            evidence_list.append(
                EvidenceRead(
                    id=uuid.UUID(doc_id),
                    investigation_id=inv_id,
                    created_at=doc["created_at"].replace(tzinfo=timezone.utc),
                    **{k: v for k, v in doc.items() if k not in ("id", "investigation_id", "created_at")}
                )
            )
        return evidence_list

    @staticmethod
    async def create_evidence(
        mongo_db: AsyncIOMotorDatabase, investigation_id: uuid.UUID | None, evidence_in: EvidenceCreate
    ) -> EvidenceRead:
        """
        Insert a new evidence record into the MongoDB collection.
        Supports standalone evidence (investigation_id = None) or evidence linked to an Investigation container.
        """
        evidence_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        
        doc = {
            "_id": str(evidence_id),
            "investigation_id": str(investigation_id) if investigation_id else None,
            "type": evidence_in.type,
            "summary": evidence_in.summary,
            "author_name": evidence_in.author_name,
            "source_url": evidence_in.source_url,
            "metadata": evidence_in.metadata,
            "created_at": now
        }
        
        await mongo_db.evidence.insert_one(doc)
        
        return EvidenceRead(
            id=evidence_id,
            investigation_id=investigation_id,
            created_at=now,
            type=evidence_in.type,
            summary=evidence_in.summary,
            author_name=evidence_in.author_name,
            source_url=evidence_in.source_url,
            metadata=evidence_in.metadata
        )
