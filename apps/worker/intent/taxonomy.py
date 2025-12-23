from enum import Enum

class Intent(str, Enum):
    MEETING_REQUEST = "meeting_request"
    TASK_REQUEST = "task_request"
    FOLLOW_UP = "follow_up"
    INVOICE = "invoice"
    PAYMENT = "payment"
    SUPPORT = "support"
    SALES = "sales"
    NEWSLETTER = "newsletter"
    SPAM = "spam"
    PERSONAL = "personal"
    # Security Specific Intents
    PHISHING = "phishing"
    MALWARE = "malware"
    SOCIAL_ENGINEERING = "social_engineering"
    BEC_FRAUD = "bec_fraud"
    RECONNAISSANCE = "reconnaissance"
    UNKNOWN = "unknown"
