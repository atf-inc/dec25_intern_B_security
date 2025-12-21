import enum

class EmailStatus(str, enum.Enum):
    """Status of email analysis processing."""
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RiskTier(str, enum.Enum):
    """Risk classification tier for analyzed emails."""
    SAFE = "SAFE"
    CAUTIOUS = "CAUTIOUS"
    THREAT = "THREAT"


class ThreatCategory(str, enum.Enum):
    """Category of detected threat."""
    NONE = "NONE"
    PHISHING = "PHISHING"
    MALWARE = "MALWARE"
    SPAM = "SPAM"
    BEC = "BEC"  # Business Email Compromise
    SPOOFING = "SPOOFING"
    SUSPICIOUS = "SUSPICIOUS"
