"use client"

import { memo } from "react"
import { motion } from "framer-motion"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { LuffyAvatar } from "@/components/ui/luffy-avatar"
import { User } from "lucide-react"

export interface Message {
    id: string
    role: "user" | "assistant"
    content: string
    timestamp: Date
    isError?: boolean
}

interface MessageBubbleProps {
    message: Message
    showAvatar?: boolean
}

// Memoized message bubble for performance
export const MessageBubble = memo(function MessageBubble({
    message,
    showAvatar = false
}: MessageBubbleProps) {
    const isAssistant = message.role === "assistant"
    const isError = message.isError

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className={`luffy-message ${message.role} ${isError ? 'error' : ''}`}
        >
            <div className="flex gap-2 items-end">
                {showAvatar && isAssistant && (
                    <LuffyAvatar size="sm" hasAlert={isError} animated={false} />
                )}
                <div
                    className={`luffy-message-bubble ${isError ? 'luffy-message-error' : ''}`}
                    role="article"
                    aria-label={`Message from ${isAssistant ? 'Luffy' : 'you'}`}
                >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                    </ReactMarkdown>
                </div>
                {showAvatar && !isAssistant && (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                        <User size={16} className="text-white" />
                    </div>
                )}
            </div>
        </motion.div>
    )
})

// Time stamp component
interface TimestampProps {
    date: Date
    showTime?: boolean
}

export function MessageTimestamp({ date, showTime = true }: TimestampProps) {
    const formatTime = (d: Date) => {
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    const formatDate = (d: Date) => {
        const now = new Date()
        const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24))

        if (diffDays === 0) return 'Today'
        if (diffDays === 1) return 'Yesterday'
        return d.toLocaleDateString()
    }

    return (
        <span className="text-xs text-white/40">
            {showTime ? formatTime(date) : formatDate(date)}
        </span>
    )
}

// Typing indicator component
export function TypingIndicator() {
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="luffy-message assistant"
        >
            <div className="flex gap-2 items-end">
                <LuffyAvatar size="sm" animated={false} />
                <div className="luffy-typing-indicator" aria-label="Luffy is typing">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </motion.div>
    )
}

// Error message component
export function ErrorMessage({ error }: { error: string }) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="luffy-message assistant"
        >
            <div className="luffy-message-bubble luffy-message-error">
                <div className="flex items-center gap-2 text-red-400 mb-2">
                    <span className="font-semibold">⚠️ Error</span>
                </div>
                <p className="text-sm">{error}</p>
                <hr className="my-3 border-red-500/30" />
                <p className="text-sm text-white/60">
                    ⚠️ エラー: {error}
                </p>
            </div>
        </motion.div>
    )
}

// Message group component for date separators
interface MessageGroupProps {
    date: string
    messages: Message[]
}

export function MessageGroup({ date, messages }: MessageGroupProps) {
    return (
        <div className="space-y-4">
            <div className="flex justify-center">
                <span className="px-3 py-1 text-xs bg-white/5 rounded-full text-white/40">
                    {date}
                </span>
            </div>
            {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} showAvatar />
            ))}
        </div>
    )
}
