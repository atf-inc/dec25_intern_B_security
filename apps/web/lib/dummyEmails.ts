/**
 * Dummy Email Data for Luffy AI Security Guardian
 * 
 * This module provides simulated email threat data for demonstration purposes.
 * Each email includes detailed analysis information that Luffy uses to explain
 * why emails are suspicious or dangerous.
 * 
 * Threat Types:
 * - Phishing: Attempts to steal credentials via fake login pages
 * - Malware: Contains malicious attachments or links
 * - BEC: Business Email Compromise targeting financial transactions
 * - Spam: Unsolicited commercial/scam emails
 * - Safe: Legitimate verified emails
 * 
 * @module dummyEmails
 */

export interface EmailThreatData {
    id: string
    sender: string
    sender_domain: string
    subject: string
    timestamp: string
    received_hours_ago: number
    risk_score: number // 0-10 scale
    threat_type: "Phishing" | "Malware" | "Spam" | "BEC" | "Safe"
    body_preview: string
    analysis_details: {
        suspicious_indicators: string[]
        malicious_urls?: string[]
        impersonation_target?: string
        recommendation: string
    }
}

export const dummyEmails: EmailThreatData[] = [
    // PHISHING EMAILS
    {
        id: "email_001",
        sender: "security@paypa1-secure.com",
        sender_domain: "paypa1-secure.com",
        subject: "Urgent: Your PayPal Account Has Been Limited",
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 2,
        risk_score: 9,
        threat_type: "Phishing",
        body_preview: "We've noticed unusual activity in your account. Click here to verify your identity immediately or your account will be suspended...",
        analysis_details: {
            suspicious_indicators: [
                "Sender domain 'paypa1-secure.com' uses number '1' instead of letter 'l' (typosquatting)",
                "Urgent language designed to create panic",
                "Generic greeting instead of your actual name",
                "Request for immediate action with threats of account suspension"
            ],
            malicious_urls: ["hxxp://paypa1-secure.com/verify-now"],
            impersonation_target: "PayPal",
            recommendation: "Do NOT click any links. This is a classic phishing attempt impersonating PayPal."
        }
    },
    {
        id: "email_002",
        sender: "support@arnazon-orders.net",
        sender_domain: "arnazon-orders.net",
        subject: "Your Amazon Order #112-4567890 Has Been Shipped",
        timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 5,
        risk_score: 8,
        threat_type: "Phishing",
        body_preview: "Track your package or update delivery preferences. If you didn't place this order, click here to cancel and secure your account...",
        analysis_details: {
            suspicious_indicators: [
                "Domain 'arnazon-orders.net' misspells 'Amazon' as 'Arnazon'",
                "Uses fake order number to create urgency",
                "Links point to credential harvesting site",
                "Sender email doesn't match official Amazon domains"
            ],
            malicious_urls: ["hxxp://arnazon-orders.net/track-package"],
            impersonation_target: "Amazon",
            recommendation: "Phishing attempt. Verify orders directly on amazon.com, never through email links."
        }
    },
    {
        id: "email_003",
        sender: "it-helpdesk@company-secure.xyz",
        sender_domain: "company-secure.xyz",
        subject: "Password Expiration Notice - Action Required",
        timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 8,
        risk_score: 10,
        threat_type: "Phishing",
        body_preview: "Your email password will expire in 24 hours. Click below to update your credentials and maintain access to your account...",
        analysis_details: {
            suspicious_indicators: [
                "External domain pretending to be internal IT",
                "Password expiration scam is a common phishing tactic",
                "Links to credential harvesting page",
                "Creates false urgency with 24-hour deadline"
            ],
            malicious_urls: ["hxxp://company-secure.xyz/password-reset"],
            impersonation_target: "Internal IT Department",
            recommendation: "CRITICAL: Never enter credentials from email links. Contact IT directly if unsure."
        }
    },

    // MALWARE EMAILS
    {
        id: "email_004",
        sender: "invoice@quickbooks-billing.com",
        sender_domain: "quickbooks-billing.com",
        subject: "Invoice #INV-2024-0892 Attached",
        timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 12,
        risk_score: 9,
        threat_type: "Malware",
        body_preview: "Please find attached invoice for your recent purchase. Open the PDF to view payment details and due date...",
        analysis_details: {
            suspicious_indicators: [
                "Attachment contains malicious macro code",
                "Fake QuickBooks domain not associated with Intuit",
                "PDF file is actually a disguised executable",
                "No prior business relationship with sender"
            ],
            malicious_urls: [],
            recommendation: "DO NOT open attachment. Contains malware disguised as an invoice PDF."
        }
    },
    {
        id: "email_005",
        sender: "hr@job-application-portal.com",
        sender_domain: "job-application-portal.com",
        subject: "Your Resume Has Been Viewed - Interview Invitation",
        timestamp: new Date(Date.now() - 18 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 18,
        risk_score: 7,
        threat_type: "Malware",
        body_preview: "Congratulations! A hiring manager has reviewed your profile. Download the attached job description to prepare for your interview...",
        analysis_details: {
            suspicious_indicators: [
                "Attachment contains trojan downloader",
                "Generic job portal domain, not a real company",
                "Exploits job seekers' desire for employment",
                "Word document contains malicious VBA macros"
            ],
            malicious_urls: [],
            recommendation: "Delete immediately. Attachment contains malware targeting job seekers."
        }
    },

    // BEC (Business Email Compromise)
    {
        id: "email_006",
        sender: "ceo@company-executive.com",
        sender_domain: "company-executive.com",
        subject: "Urgent Wire Transfer Needed",
        timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 3,
        risk_score: 10,
        threat_type: "BEC",
        body_preview: "I need you to process a wire transfer of $47,500 to a new vendor immediately. I'm in meetings all day and can't call. Please handle this urgently...",
        analysis_details: {
            suspicious_indicators: [
                "Sender impersonating company CEO",
                "External domain designed to look internal",
                "Urgent request for large wire transfer",
                "Specifically asks not to call for verification",
                "Classic Business Email Compromise attack pattern"
            ],
            impersonation_target: "Company CEO",
            recommendation: "CRITICAL BEC ATTACK: Always verify wire transfer requests by phone. Never trust email alone."
        }
    },

    // SPAM
    {
        id: "email_007",
        sender: "deals@mega-savings-outlet.com",
        sender_domain: "mega-savings-outlet.com",
        subject: "🎉 You've Won a $500 Gift Card! Claim Now!",
        timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 24,
        risk_score: 5,
        threat_type: "Spam",
        body_preview: "Congratulations! You've been selected to receive a $500 gift card. Click here to claim your prize before it expires...",
        analysis_details: {
            suspicious_indicators: [
                "Unsolicited prize notification",
                "Unknown sender with suspicious domain",
                "Uses emojis to bypass spam filters",
                "Creates urgency with expiration claim"
            ],
            recommendation: "Spam email. Mark as junk and delete. Do not click any links."
        }
    },
    {
        id: "email_008",
        sender: "newsletter@crypto-signals-pro.io",
        sender_domain: "crypto-signals-pro.io",
        subject: "Make $10,000/week with our SECRET crypto strategy!",
        timestamp: new Date(Date.now() - 36 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 36,
        risk_score: 6,
        threat_type: "Spam",
        body_preview: "Join thousands of successful traders who are making consistent profits with our guaranteed trading signals...",
        analysis_details: {
            suspicious_indicators: [
                "Unrealistic financial promises",
                "\"Guaranteed\" returns is a red flag for scams",
                "No unsubscribe option",
                "Likely a pump-and-dump or advance fee scam"
            ],
            recommendation: "Financial scam spam. Delete and block sender."
        }
    },

    // SAFE EMAILS
    {
        id: "email_009",
        sender: "noreply@github.com",
        sender_domain: "github.com",
        subject: "[GitHub] A new sign-in to your account",
        timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 1,
        risk_score: 1,
        threat_type: "Safe",
        body_preview: "Hey there! We noticed a new sign-in to your GitHub account from Chrome on macOS. If this was you, you can safely ignore this email...",
        analysis_details: {
            suspicious_indicators: [],
            recommendation: "Legitimate security notification from GitHub. Verify if the sign-in was yours."
        }
    },
    {
        id: "email_010",
        sender: "no-reply@accounts.google.com",
        sender_domain: "accounts.google.com",
        subject: "Security alert: New sign-in on Windows",
        timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 4,
        risk_score: 0,
        threat_type: "Safe",
        body_preview: "We noticed a new sign-in to your Google Account on a Windows device. If this was you, you don't need to do anything...",
        analysis_details: {
            suspicious_indicators: [],
            recommendation: "Authentic Google security alert. Verify if you recognize the sign-in activity."
        }
    },
    {
        id: "email_011",
        sender: "receipts@uber.com",
        sender_domain: "uber.com",
        subject: "Your trip with Uber - Receipt",
        timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 6,
        risk_score: 0,
        threat_type: "Safe",
        body_preview: "Thanks for riding with Uber! Here's your receipt for your recent trip from Downtown to Airport...",
        analysis_details: {
            suspicious_indicators: [],
            recommendation: "Legitimate Uber receipt. Safe to open and review."
        }
    },
    {
        id: "email_012",
        sender: "team@slack.com",
        sender_domain: "slack.com",
        subject: "New message in #general",
        timestamp: new Date(Date.now() - 0.5 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 0.5,
        risk_score: 0,
        threat_type: "Safe",
        body_preview: "You have a new message in the #general channel: 'Team meeting moved to 3pm today'...",
        analysis_details: {
            suspicious_indicators: [],
            recommendation: "Authentic Slack notification. Safe to view."
        }
    },
    {
        id: "email_013",
        sender: "notifications@linkedin.com",
        sender_domain: "linkedin.com",
        subject: "You appeared in 12 searches this week",
        timestamp: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 48,
        risk_score: 1,
        threat_type: "Safe",
        body_preview: "Good news! Your profile appeared in 12 search results this week. See who's looking for professionals like you...",
        analysis_details: {
            suspicious_indicators: [],
            recommendation: "Legitimate LinkedIn engagement notification."
        }
    },

    // MORE PHISHING (for variety)
    {
        id: "email_014",
        sender: "service@netfl1x-billing.com",
        sender_domain: "netfl1x-billing.com",
        subject: "Netflix: Payment Failed - Update Required",
        timestamp: new Date(Date.now() - 10 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 10,
        risk_score: 9,
        threat_type: "Phishing",
        body_preview: "We were unable to process your payment. Update your billing information within 48 hours to avoid service interruption...",
        analysis_details: {
            suspicious_indicators: [
                "Domain 'netfl1x-billing.com' uses '1' instead of 'i'",
                "Creates urgency with 48-hour deadline",
                "Requests payment information update",
                "Link leads to credential harvesting site"
            ],
            malicious_urls: ["hxxp://netfl1x-billing.com/update-payment"],
            impersonation_target: "Netflix",
            recommendation: "Phishing attempt. Log in directly at netflix.com to check account status."
        }
    },
    {
        id: "email_015",
        sender: "admin@microsoft365-verify.com",
        sender_domain: "microsoft365-verify.com",
        subject: "Action Required: Verify Your Microsoft Account",
        timestamp: new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString(),
        received_hours_ago: 72,
        risk_score: 8,
        threat_type: "Phishing",
        body_preview: "Your Microsoft 365 subscription needs verification. Click the secure link below to confirm your account details...",
        analysis_details: {
            suspicious_indicators: [
                "Unofficial Microsoft domain",
                "Requests account verification via email link",
                "Uses 'secure' language to build false trust",
                "Designed to steal Microsoft credentials"
            ],
            malicious_urls: ["hxxp://microsoft365-verify.com/secure-login"],
            impersonation_target: "Microsoft",
            recommendation: "Do not click. Verify account status at account.microsoft.com directly."
        }
    }
]

// Helper function to get threat summary
export function getThreatSummary(emails: EmailThreatData[]): {
    total: number
    phishing: number
    malware: number
    bec: number
    spam: number
    safe: number
    highRiskCount: number
    recentThreats: number
} {
    const phishing = emails.filter(e => e.threat_type === "Phishing").length
    const malware = emails.filter(e => e.threat_type === "Malware").length
    const bec = emails.filter(e => e.threat_type === "BEC").length
    const spam = emails.filter(e => e.threat_type === "Spam").length
    const safe = emails.filter(e => e.threat_type === "Safe").length
    const highRiskCount = emails.filter(e => e.risk_score >= 8).length
    const recentThreats = emails.filter(e =>
        e.received_hours_ago <= 24 && e.threat_type !== "Safe"
    ).length

    return {
        total: emails.length,
        phishing,
        malware,
        bec,
        spam,
        safe,
        highRiskCount,
        recentThreats
    }
}

// Get emails from specific time period
export function getEmailsFromPeriod(
    emails: EmailThreatData[],
    hours: number
): EmailThreatData[] {
    return emails.filter(e => e.received_hours_ago <= hours)
}

// Get most dangerous emails
export function getMostDangerousEmails(
    emails: EmailThreatData[],
    limit: number = 5
): EmailThreatData[] {
    return [...emails]
        .sort((a, b) => b.risk_score - a.risk_score)
        .slice(0, limit)
}
