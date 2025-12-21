from pydantic import BaseModel, Field
from typing import Optional


class AttachmentMetadata(BaseModel):
    """
    Metadata for an email attachment (content is NOT downloaded for security).

    Attributes:
        filename: Original filename of the attachment
        mime_type: MIME type (e.g., "application/pdf", "image/png")
        size: Size in bytes
        attachment_id: Gmail's internal attachment ID (for later retrieval if needed)
    """

    filename: str
    mime_type: str
    size: int
    attachment_id: Optional[str] = None


class EmailAuthenticationStatus(BaseModel):
    """
    Email authentication results from SPF, DKIM, and DMARC checks.

    These are critical for detecting spoofed/phishing emails:
    - SPF: Sender Policy Framework (validates sender IP is authorized)
    - DKIM: DomainKeys Identified Mail (validates email wasn't modified)
    - DMARC: Domain-based Message Auth (policy for handling SPF/DKIM failures)

    Possible values: "PASS", "FAIL", "NEUTRAL", "NONE", or None if not present
    """

    spf: Optional[str] = None
    dkim: Optional[str] = None
    dmarc: Optional[str] = None


class StructuredEmail(BaseModel):
    """
    Complete structured representation of a Gmail message.

    This is the unified output format that combines all extracted data
    needed for security analysis and display.
    """

    # Core identifiers
    message_id: str = Field(description="Gmail's unique message ID")

    # Envelope information
    sender: str = Field(description='From header value')
    recipient: str = Field(description='To header value')
    subject: str = Field(description='Email subject line')

    # Body content
    body_preview: str = Field(description='Gmail snippet (first ~100 chars)')
    body_text: Optional[str] = Field(default=None, description='Full text/plain body')
    body_html: Optional[str] = Field(default=None, description='Full text/html body')

    # Timestamps
    received_at: Optional[datetime] = Field(default=None, description='Parsed Date header')

    # Security analysis fields
    auth_status: EmailAuthenticationStatus = Field(
        default_factory=EmailAuthenticationStatus, description='SPF/DKIM/DMARC results'
    )
    sender_ip: Optional[str] = Field(default=None, description='Originating IP from Received headers')

    # Content analysis
    extracted_urls: list[str] = Field(default_factory=list, description='URLs found in body')
    attachments: list[AttachmentMetadata] = Field(default_factory=list, description='Attachment metadata')

    # Classification
    status: EmailStatus = Field(default=EmailStatus.PROCESSING, description='Email status (PENDING, SPAM, etc.)')
    gmail_labels: list[str] = Field(default_factory=list, description='Gmail label IDs')

    # Legacy compatibility fields (for backwards compatibility with existing code)
    @property
    def spf_status(self) -> Optional[str]:
        return self.auth_status.spf

    @property
    def dkim_status(self) -> Optional[str]:
        return self.auth_status.dkim

    @property
    def dmarc_status(self) -> Optional[str]:
        return self.auth_status.dmarc

    @property
    def attachment_info(self) -> Optional[str]:
        """Comma-separated attachment filenames for legacy compatibility."""
        if not self.attachments:
            return None
        return ', '.join(att.filename for att in self.attachments)


class WatchInfo(BaseModel):
    """
    Information about a Gmail watch subscription.

    Returned by the Gmail API when calling users().watch().
    Must be stored in database to track watch expiration.
    """

    history_id: int = Field(description='Starting historyId for incremental sync')
    expiration: int = Field(description='Unix timestamp (ms) when watch expires (~7 days)')

    @property
    def expiration_datetime(self) -> datetime:
        """Convert expiration to datetime for easier comparison."""
        return datetime.fromtimestamp(self.expiration / 1000, tz=timezone.utc)

    @property
    def is_expired(self) -> bool:
        """Check if the watch has expired."""
        return datetime.now(timezone.utc) >= self.expiration_datetime

    @property
    def expires_soon(self) -> bool:
        """Check if watch expires within 24 hours (should renew)."""
        from datetime import timedelta

        return datetime.now(timezone.utc) >= (self.expiration_datetime - timedelta(hours=24))


class BackgroundSyncRequest(BaseModel):
    email_address: str
    history_id: int
