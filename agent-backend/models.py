from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import JSON, Column, Enum, Field, Relationship, SQLModel


class UserRole(str, enum.Enum):
    admin = "admin"
    member = "member"


class EmailStatus(str, enum.Enum):
    pending = "PENDING"
    processing = "PROCESSING"
    completed = "COMPLETED"
    failed = "FAILED"


class RiskTier(str, enum.Enum):
    safe = "SAFE"
    cautious = "CAUTIOUS"
    threat = "THREAT"


class Organisation(SQLModel, table=True):
    __tablename__ = "organisations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str
    domain: str
    api_key_hash: str = Field(index=True, unique=True)  # Store hashed value only
    api_key_prefix: str = Field(max_length=8)  # For identification in UI (e.g., "pg_abc123")

    users: list["User"] = Relationship(back_populates="organisation")
    email_events: list["EmailEvent"] = Relationship(back_populates="organisation")


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    org_id: uuid.UUID = Field(foreign_key="organisations.id", index=True)
    clerk_id: str = Field(index=True)
    email: str = Field(index=True)
    role: UserRole = Field(sa_column=Column(Enum(UserRole, name="user_role_enum")))

    organisation: Organisation = Relationship(back_populates="users")


class EmailEvent(SQLModel, table=True):
    __tablename__ = "email_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    org_id: uuid.UUID = Field(foreign_key="organisations.id", index=True)
    sender: str
    recipient: str
    subject: str
    body_preview: Optional[str] = None
    status: EmailStatus = Field(
        default=EmailStatus.pending,
        sa_column=Column(
            Enum(EmailStatus, name="email_status_enum"),
            server_default="PENDING",  # DB-side default for inserts bypassing ORM
        ),
    )
    risk_score: Optional[int] = Field(default=None)
    risk_tier: Optional[RiskTier] = Field(
        default=None, sa_column=Column(Enum(RiskTier, name="risk_tier_enum"))
    )
    analysis_result: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    organisation: Organisation = Relationship(back_populates="email_events")
