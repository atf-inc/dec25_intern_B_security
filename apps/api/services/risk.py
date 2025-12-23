import logging
import os
from packages.shared.types import StructuredEmail

logger = logging.getLogger(__name__)


# --- Risk Gate Logic (Pure, Deterministic) ---
RISKY_EXTENSIONS = {".exe", ".scr", ".vbs", ".js", ".bat", ".iso", ".dll", ".ps1"}


def evaluate_static_risk(payload: StructuredEmail) -> tuple[bool, str, int]:
    """
    Evaluates static indicators to decide if sandboxing is needed.
    Returns: (should_sandbox, reason, static_risk_score)
    """
    score = 0
    reasons = []
    should_sandbox = False

    # 1. Attachment Check
    for att in payload.attachments:
        ext = os.path.splitext(att.filename)[1].lower()
        if ext in RISKY_EXTENSIONS:
            score += 70
            reasons.append(f"Risky extension {ext}")
            should_sandbox = True
        elif att.mime_type == "application/zip":
            score += 30
            reasons.append("Archive attachment")
            should_sandbox = True  # Inspecting zips is standard

    # 2. URL Check (Basic heuristics for Phase 2A)
    if len(payload.extracted_urls) > 0:
        score += 5  # Presence of URLs
        if len(payload.extracted_urls) > 3:
            score += 20
            reasons.append("Many URLs")
            should_sandbox = True

    # Normalize score
    score = min(score, 100)
    reason_str = "; ".join(reasons) if reasons else "Low static risk"

    # Fail-safe
    if score > 50:
        should_sandbox = True
    
    logger.info(
        'Risk evaluation: should_sandbox=%s, score=%d, reasons=%s',
        should_sandbox, score, reason_str
    )

    return should_sandbox, reason_str, score
