"""Database models for MailShieldAI Agent Backend - Single User Architecture."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import JSON, Column, Enum, Field, Relationship, SQLModel


class EmailStatus(str, enum.Enum):
    """Status of email analysis processing."""
    pending = "PENDING"
    processing = "PROCESSING"
    completed = "COMPLETED"
    failed = "FAILED"


class RiskTier(str, enum.Enum):
    """Risk classification tier for analyzed emails."""
    safe = "SAFE"
    cautious = "CAUTIOUS"
    threat = "THREAT"


class User(SQLModel, table=True):
    """User model - represents a single user of the application."""
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    google_id: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    name: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to emails
    email_events: list["EmailEvent"] = Relationship(back_populates="user")


class EmailEvent(SQLModel, table=True):
    """Email event model - represents an analyzed email."""
    __tablename__ = "email_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    sender: str
    recipient: str
    subject: str
    body_preview: Optional[str] = None
    status: EmailStatus = Field(
        default=EmailStatus.pending,
        sa_column=Column(
            Enum(EmailStatus, name="email_status_enum"),
            server_default="PENDING",
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

    # Relationship to user
    user: User = Relationship(back_populates="email_events")
