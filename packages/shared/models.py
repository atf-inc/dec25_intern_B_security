"""Database models for MailShieldAI - Single User Architecture."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import JSON, Column, Enum, Field, SQLModel


from .constants import EmailStatus, RiskTier, ThreatCategory


def utc_now() -> datetime:
    """Return current UTC time as a naive datetime (for PostgreSQL TIMESTAMP WITHOUT TIME ZONE)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(SQLModel, table=True):
    """User model - represents a single user of the application."""

    __tablename__ = 'users'

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    google_id: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    name: Optional[str] = None
    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
    )
    refresh_token: Optional[str] = None


class EmailEvent(SQLModel, table=True):
    """Email event model - represents an analyzed email."""

    __tablename__ = 'email_events'

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key='users.id', index=True)

    # Essential Identification Fields
    sender: str
    recipient: str
    subject: str
    message_id: Optional[str] = Field(default=None, index=True)
    body_preview: Optional[str] = None
    received_at: Optional[datetime] = Field(default=None)  # Email timestamp from headers

    # Threat Intelligence Fields
    threat_category: Optional[ThreatCategory] = Field(
        default=None, sa_column=Column(Enum(ThreatCategory, name='threat_category_enum', create_type=False))
    )
    detection_reason: Optional[str] = Field(default=None)  # Brief explanation of detection

    # Security Metadata Fields
    spf_status: Optional[str] = Field(default=None)  # PASS, FAIL, NEUTRAL, etc.
    dkim_status: Optional[str] = Field(default=None)
    dmarc_status: Optional[str] = Field(default=None)
    sender_ip: Optional[str] = Field(default=None)

    # Processing Fields
    status: EmailStatus = Field(
        default=EmailStatus.PROCESSING,
        sa_column=Column(
            Enum(EmailStatus, name='email_status_enum', create_type=False),
            server_default='PENDING',
        ),
    )
    risk_score: Optional[int] = Field(default=None)  # 0-100
    risk_tier: Optional[RiskTier] = Field(
        default=None, sa_column=Column(Enum(RiskTier, name='risk_tier_enum', create_type=False))
    )
    analysis_result: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Intent Classification Fields
    intent: Optional[str] = Field(default=None)
    intent_confidence: Optional[float] = Field(default=None)
    intent_processed_at: Optional[datetime] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False),
    )


class EmailRead(SQLModel):
    """Schema for reading an email event."""

    id: uuid.UUID
    sender: str
    recipient: str
    subject: str
    body_preview: Optional[str]
    received_at: Optional[datetime] = None

    # Threat Intelligence
    threat_category: Optional[ThreatCategory] = None
    detection_reason: Optional[str] = None

    # Security Metadata
    spf_status: Optional[str] = None
    dkim_status: Optional[str] = None
    dmarc_status: Optional[str] = None
    sender_ip: Optional[str] = None

    # Processing
    status: EmailStatus
    risk_score: Optional[int] = None
    risk_tier: Optional[RiskTier] = None
    analysis_result: Optional[dict] = None

    # Intent Classification
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    intent_processed_at: Optional[datetime] = None


class UserRead(SQLModel):
    """Schema for reading user info."""

    id: uuid.UUID
    email: str
    name: Optional[str]
