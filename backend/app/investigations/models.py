from app.organizations.models import Organization
from sqlalchemy.orm.dependency import ManyToOneDP
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Investigation(Base):
    __tablename__ = 'investigations'

    id: Mapped[uuid.UUID] = mapped_column(primary_key= True, default= uuid.uuid4, index= True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete= "CASCADE"), nullable= False, index= True
        )
    title: Mapped[str] = mapped_column(String(255), nullable= False)
    description: Mapped[str | None] = mapped_column(Text, nullable= True)

    # severity: critical, high, medium, low
    severity: Mapped[str] = mapped_column(String(50), nullable= False)
    # status: open, investigating, resolved
    status: Mapped[str] = mapped_column(String(50), default='open', nullable= False)

    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable= True, index= False
    )
    suggestion_action: Mapped[str | None] = mapped_column(Text, nullable= True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default= func.now(), nullable= False
    )
    

    # Relations
    # Note: we import models locally or dynamically using strings to prevent circular imports
    organization= relationship("Organization")
    assigned_to = relationship('User')


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    triggered_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=False
    )
    report_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    investigation = relationship("Investigation")
    triggered_by = relationship("User")