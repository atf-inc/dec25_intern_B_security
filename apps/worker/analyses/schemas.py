from pydantic import BaseModel
from typing import Optional, List, Literal


class AttachmentMetadata(BaseModel):
    filename: str
    mime_type: str
    size: int
    attachment_id: Optional[str] = None


class StructuredEmailPayload(BaseModel):
    message_id: str
    sender: str
    subject: str
    extracted_urls: List[str]
    attachment_metadata: List[AttachmentMetadata]


class SandboxResult(BaseModel):
    verdict: Literal['malicious', 'suspicious', 'clean', 'unknown']
    score: int
    family: Optional[str] = None
    confidence: float = 0.0


class DecisionMetadata(BaseModel):
    provider: str
    timed_out: bool = False
    reason: Optional[str] = None


class UnifiedDecisionPayload(BaseModel):
    message_id: str
    static_risk_score: int
    sandboxed: bool
    sandbox_result: Optional[SandboxResult] = None
    decision_metadata: DecisionMetadata
