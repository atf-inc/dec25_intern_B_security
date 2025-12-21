"use client"

import { motion } from "framer-motion"
import {
    Clock,
    AlertTriangle,
    Fish,
    Shield,
    Bug,
    Calendar,
    Mail,
    Search,
    Zap
} from "lucide-react"

export interface QuickActionChip {
    id: string
    labelEn: string
    labelJa: string
    query: string
    icon: React.ReactNode
}

const iconProps = { size: 14, className: "flex-shrink-0" }

export const defaultQuickActions: QuickActionChip[] = [
    {
        id: "scan-24h",
        labelEn: "Last 24h",
        labelJa: "過去24時間",
        query: "Show me any threats detected in the last 24 hours",
        icon: <Clock {...iconProps} />
    },
    {
        id: "dangerous",
        labelEn: "Dangerous",
        labelJa: "危険なメール",
        query: "What are the most dangerous emails in my inbox?",
        icon: <AlertTriangle {...iconProps} />
    },
    {
        id: "phishing",
        labelEn: "Phishing",
        labelJa: "フィッシング",
        query: "Did I receive any phishing emails recently?",
        icon: <Fish {...iconProps} />
    },
    {
        id: "summary",
        labelEn: "Summary",
        labelJa: "概要",
        query: "Give me a complete summary of my email security status",
        icon: <Shield {...iconProps} />
    }
]

export const extendedQuickActions: QuickActionChip[] = [
    ...defaultQuickActions,
    {
        id: "vulnerabilities",
        labelEn: "Vulnerabilities",
        labelJa: "脆弱性",
        query: "Are there any vulnerabilities in my inbox that I should be aware of?",
        icon: <Bug {...iconProps} />
    },
    {
        id: "week-review",
        labelEn: "This Week",
        labelJa: "今週",
        query: "Give me a security review of the emails from this week",
        icon: <Calendar {...iconProps} />
    },
    {
        id: "malware",
        labelEn: "Malware",
        labelJa: "マルウェア",
        query: "Have I received any emails with malware attachments?",
        icon: <Mail {...iconProps} />
    },
    {
        id: "bec",
        labelEn: "BEC Check",
        labelJa: "BEC確認",
        query: "Check for any Business Email Compromise attempts",
        icon: <Search {...iconProps} />
    }
]

interface QuickActionChipsProps {
    actions?: QuickActionChip[]
    onActionClick: (query: string) => void
    disabled?: boolean
    showExtended?: boolean
}

export function QuickActionChips({
    actions,
    onActionClick,
    disabled = false,
    showExtended = false
}: QuickActionChipsProps) {
    const chips = actions || (showExtended ? extendedQuickActions : defaultQuickActions)

    return (
        <div className="luffy-quick-actions">
            {chips.map((action, index) => (
                <motion.button
                    key={action.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="luffy-chip flex items-center gap-2"
                    onClick={() => onActionClick(action.query)}
                    disabled={disabled}
                    title={action.labelEn}
                    aria-label={`${action.labelEn}: ${action.query}`}
                >
                    {action.icon}
                    <span>{action.labelJa}</span>
                </motion.button>
            ))}
        </div>
    )
}

// Standalone chip component for reuse
interface SingleChipProps {
    label: string
    icon?: React.ReactNode
    onClick: () => void
    disabled?: boolean
    variant?: "default" | "highlight" | "danger"
}

export function Chip({
    label,
    icon,
    onClick,
    disabled = false,
    variant = "default"
}: SingleChipProps) {
    const variantStyles = {
        default: "",
        highlight: "luffy-chip-highlight",
        danger: "luffy-chip-danger"
    }

    return (
        <button
            className={`luffy-chip flex items-center gap-2 ${variantStyles[variant]}`}
            onClick={onClick}
            disabled={disabled}
        >
            {icon}
            <span>{label}</span>
            {variant === "highlight" && <Zap size={12} className="text-yellow-400" />}
        </button>
    )
}
