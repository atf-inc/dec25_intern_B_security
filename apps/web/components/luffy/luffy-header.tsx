"use client"

import { motion } from "framer-motion"
import { X, Minimize2, Maximize2, Settings } from "lucide-react"
import { LuffyAvatar } from "@/components/ui/luffy-avatar"

interface ChatHeaderProps {
    hasAlert?: boolean
    totalEmails?: number
    recentThreats?: number
    onClose: () => void
    onMinimize?: () => void
    onSettings?: () => void
    isMinimized?: boolean
}

export function ChatHeader({
    hasAlert = false,
    totalEmails,
    recentThreats,
    onClose,
    onMinimize,
    onSettings,
    isMinimized = false
}: ChatHeaderProps) {
    const statusText = totalEmails !== undefined
        ? `${totalEmails} emails • ${recentThreats || 0} recent threats`
        : "AI Security Guardian"

    return (
        <div className="luffy-chat-header">
            <div className="luffy-header-info">
                <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                >
                    <LuffyAvatar size="md" hasAlert={hasAlert} animated={false} />
                </motion.div>
                <div className="luffy-header-text">
                    <h3>
                        Luffy ルフィ
                        <span
                            className={`luffy-status-indicator ${hasAlert ? "alert" : "safe"}`}
                            aria-label={hasAlert ? "Threats detected" : "All clear"}
                            role="status"
                        />
                    </h3>
                    <p className="flex items-center gap-1">
                        <span>{statusText}</span>
                    </p>
                </div>
            </div>

            <div className="flex items-center gap-1">
                {onSettings && (
                    <button
                        className="luffy-header-btn"
                        onClick={onSettings}
                        aria-label="Settings"
                    >
                        <Settings size={16} />
                    </button>
                )}

                {onMinimize && (
                    <button
                        className="luffy-header-btn"
                        onClick={onMinimize}
                        aria-label={isMinimized ? "Maximize" : "Minimize"}
                    >
                        {isMinimized ? <Maximize2 size={16} /> : <Minimize2 size={16} />}
                    </button>
                )}

                <button
                    className="luffy-close-btn"
                    onClick={onClose}
                    aria-label="Close chat"
                >
                    <X size={18} />
                </button>
            </div>
        </div>
    )
}

// Compact header for minimized state
export function CompactHeader({
    hasAlert,
    onExpand
}: {
    hasAlert?: boolean
    onExpand: () => void
}) {
    return (
        <motion.button
            onClick={onExpand}
            className="luffy-compact-header"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
        >
            <LuffyAvatar size="sm" hasAlert={hasAlert} animated={false} />
            <span className="text-sm font-medium text-white">Luffy ルフィ</span>
            <span
                className={`luffy-status-indicator ${hasAlert ? "alert" : "safe"}`}
            />
        </motion.button>
    )
}
