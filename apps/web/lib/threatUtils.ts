// Email threat types and helper utilities for Luffy chatbot

export type ThreatLevel = "critical" | "high" | "medium" | "low" | "safe"

export interface ThreatInfo {
    level: ThreatLevel
    label: string
    labelJa: string
    color: string
    bgColor: string
    description: string
    descriptionJa: string
}

export const threatLevels: Record<ThreatLevel, ThreatInfo> = {
    critical: {
        level: "critical",
        label: "Critical",
        labelJa: "危険",
        color: "#ef4444",
        bgColor: "rgba(239, 68, 68, 0.15)",
        description: "Immediate action required - confirmed malicious",
        descriptionJa: "即座の対応が必要 - 悪意が確認されました"
    },
    high: {
        level: "high",
        label: "High Risk",
        labelJa: "高リスク",
        color: "#f97316",
        bgColor: "rgba(249, 115, 22, 0.15)",
        description: "Likely phishing or malware attempt",
        descriptionJa: "フィッシングまたはマルウェアの可能性が高い"
    },
    medium: {
        level: "medium",
        label: "Suspicious",
        labelJa: "疑わしい",
        color: "#eab308",
        bgColor: "rgba(234, 179, 8, 0.15)",
        description: "Contains suspicious elements - review recommended",
        descriptionJa: "疑わしい要素を含む - 確認を推奨"
    },
    low: {
        level: "low",
        label: "Low Risk",
        labelJa: "低リスク",
        color: "#22d3ee",
        bgColor: "rgba(34, 211, 238, 0.15)",
        description: "Minor concerns but likely safe",
        descriptionJa: "軽微な懸念はあるが安全な可能性が高い"
    },
    safe: {
        level: "safe",
        label: "Safe",
        labelJa: "安全",
        color: "#10b981",
        bgColor: "rgba(16, 185, 129, 0.15)",
        description: "No threats detected",
        descriptionJa: "脅威は検出されませんでした"
    }
}

// Convert risk score (0-10) to threat level
export function riskScoreToLevel(score: number): ThreatLevel {
    if (score >= 9) return "critical"
    if (score >= 7) return "high"
    if (score >= 5) return "medium"
    if (score >= 2) return "low"
    return "safe"
}

// Format threat type for display
export function formatThreatType(type: string): { en: string; ja: string } {
    const types: Record<string, { en: string; ja: string }> = {
        "Phishing": { en: "Phishing", ja: "フィッシング" },
        "Malware": { en: "Malware", ja: "マルウェア" },
        "BEC": { en: "Business Email Compromise", ja: "ビジネスメール詐欺" },
        "Spam": { en: "Spam", ja: "スパム" },
        "Safe": { en: "Safe", ja: "安全" }
    }
    return types[type] || { en: type, ja: type }
}

// Quick action suggestions
export const quickActionSuggestions = [
    {
        id: "scan-24h",
        labelEn: "Scan last 24 hours",
        labelJa: "過去24時間をスキャン",
        query: "Show me any threats detected in the last 24 hours",
        icon: "clock"
    },
    {
        id: "dangerous",
        labelEn: "Most dangerous",
        labelJa: "最も危険なメール",
        query: "What are the most dangerous emails in my inbox?",
        icon: "alert"
    },
    {
        id: "phishing",
        labelEn: "Phishing check",
        labelJa: "フィッシング確認",
        query: "Did I receive any phishing emails recently?",
        icon: "fish"
    },
    {
        id: "summary",
        labelEn: "Security summary",
        labelJa: "セキュリティ概要",
        query: "Give me a complete summary of my email security status",
        icon: "shield"
    },
    {
        id: "vulnerabilities",
        labelEn: "Check vulnerabilities",
        labelJa: "脆弱性をチェック",
        query: "Are there any vulnerabilities in my inbox that I should be aware of?",
        icon: "bug"
    },
    {
        id: "week-review",
        labelEn: "Weekly review",
        labelJa: "週間レビュー",
        query: "Give me a security review of the emails from this week",
        icon: "calendar"
    }
]

// Common security phrases in Japanese
export const securityPhrases = {
    threatDetected: {
        en: "Threat Detected",
        ja: "脅威が検出されました"
    },
    noThreats: {
        en: "No Threats Found",
        ja: "脅威は見つかりませんでした"
    },
    analyzing: {
        en: "Analyzing...",
        ja: "分析中..."
    },
    recommendation: {
        en: "Recommendation",
        ja: "推奨"
    },
    warning: {
        en: "Warning",
        ja: "警告"
    },
    safeToOpen: {
        en: "Safe to open",
        ja: "開いても安全"
    },
    doNotClick: {
        en: "Do NOT click any links",
        ja: "リンクをクリックしないでください"
    },
    reportedBy: {
        en: "Reported by Luffy",
        ja: "ルフィより報告"
    }
}
