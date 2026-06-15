import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    # Core Identifiers
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    # Profile Fields
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Account Status Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Auditing Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # =========================================================================
    # TODO: FUTURE HOOKS (Phase 2 - Multi-Tenancy & RBAC Preparation)
    # =========================================================================
    #
    # 1. Organization Support (Multi-Tenancy):
    #    - One-to-Many or Many-to-Many relationship with Organization model.
    #    - Example:
    #      organization_id: Mapped[uuid.UUID | None] = mapped_column(
    #          ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    #      )
    #      organization: Mapped["Organization"] = relationship(back_populates="users")
    #
    # 2. Role Support (RBAC):
    #    - Field mapping a single Role enum or a Many-to-Many relationship with a Role model.
    #    - Example:
    #      role: Mapped[str] = mapped_column(
    #          String(50), default="viewer"  # e.g., admin, manager, viewer
    #      )
    #
    # =========================================================================

    def __repr__(self) -> str:
        return f"<User {self.email} (verified={self.is_verified})>"
