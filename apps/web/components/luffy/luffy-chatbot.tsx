"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Send, X, Shield, AlertTriangle } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import "@/styles/chatbot.css"

// Types
interface Message {
    id: string
    role: "user" | "assistant"
    content: string
    timestamp: Date
}

interface ThreatSummary {
    total: number
    phishing: number
    malware: number
    bec: number
    spam: number
    safe: number
    highRiskCount: number
    recentThreats: number
}

// Quick action chips data - Professional English labels
const quickActions = [
    { label: "Last 24 Hours", query: "Show me any threats detected in the last 24 hours" },
    { label: "High Risk Emails", query: "What are the most dangerous emails in my inbox?" },
    { label: "Phishing Check", query: "Did I receive any phishing emails recently?" },
    { label: "Security Summary", query: "Give me a summary of my email security status" },
]

// Welcome message - Professional and concise
const WELCOME_MESSAGE: Message = {
    id: "welcome",
    role: "assistant",
    content: `## 👋 Welcome to Luffy Security Assistant

I'm your **AI-powered email security guardian**. I can help you:

- 🔍 Analyze emails for **phishing** and **malware** threats
- 📊 Review your inbox **security status**
- ⚠️ Identify **high-risk** messages
- 💡 Provide **security recommendations**

**Try asking:**
- "Do I have any phishing emails?"
- "What's my security status?"
- "Show me dangerous emails"`,
    timestamp: new Date(),
}

export function LuffyChatbot() {
    // State
    const [isOpen, setIsOpen] = useState(false)
    const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE])
    const [inputValue, setInputValue] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [threatSummary, setThreatSummary] = useState<ThreatSummary | null>(null)
    const [hasAlert, setHasAlert] = useState(false)

    // Refs
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    // Auto-scroll to bottom when messages change
    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [])

    useEffect(() => {
        scrollToBottom()
    }, [messages, scrollToBottom])

    // Focus input when chat opens
    useEffect(() => {
        if (isOpen) {
            setTimeout(() => inputRef.current?.focus(), 100)
        }
    }, [isOpen])

    // Fetch initial threat summary
    useEffect(() => {
        async function fetchStatus() {
            try {
                const res = await fetch("/api/luffy")
                if (res.ok) {
                    const data = await res.json()
                    setThreatSummary(data.threatSummary)
                    setHasAlert(data.threatSummary.recentThreats > 0)
                }
            } catch (error) {
                console.error("Failed to fetch Luffy status:", error)
            }
        }
        fetchStatus()
    }, [])

    // Send message to Luffy API
    const sendMessage = async (content: string) => {
        if (!content.trim() || isLoading) return

        // Add user message
        const userMessage: Message = {
            id: `user-${Date.now()}`,
            role: "user",
            content: content.trim(),
            timestamp: new Date(),
        }
        setMessages((prev) => [...prev, userMessage])
        setInputValue("")
        setIsLoading(true)

        try {
            // Build conversation history (excluding welcome message)
            const conversationHistory = messages
                .filter((m) => m.id !== "welcome")
                .map((m) => ({
                    role: m.role,
                    content: m.content,
                }))

            const response = await fetch("/api/luffy", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: content,
                    conversationHistory,
                }),
            })

            if (!response.ok) {
                throw new Error("Failed to get response")
            }

            const data = await response.json()

            // Add assistant message
            const assistantMessage: Message = {
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: data.message,
                timestamp: new Date(),
            }
            setMessages((prev) => [...prev, assistantMessage])

            // Update threat summary if provided
            if (data.threatSummary) {
                setThreatSummary(data.threatSummary)
                setHasAlert(data.threatSummary.recentThreats > 0)
            }
        } catch (error) {
            console.error("Error sending message:", error)
            const errorMessage: Message = {
                id: `error-${Date.now()}`,
                role: "assistant",
                content: `⚠️ Sorry, I encountered an error. Please try again.

---

⚠️ 申し訳ありませんが、エラーが発生しました。もう一度お試しください。`,
                timestamp: new Date(),
            }
            setMessages((prev) => [...prev, errorMessage])
        } finally {
            setIsLoading(false)
        }
    }

    // Handle form submit
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        sendMessage(inputValue)
    }

    // Handle quick action click
    const handleQuickAction = (query: string) => {
        sendMessage(query)
    }

    // Handle keyboard shortcut (Escape to close)
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape" && isOpen) {
                setIsOpen(false)
            }
        }
        window.addEventListener("keydown", handleKeyDown)
        return () => window.removeEventListener("keydown", handleKeyDown)
    }, [isOpen])

    return (
        <div className="luffy-chatbot-container">
            <AnimatePresence mode="wait">
                {isOpen ? (
                    // Chat Window
                    <motion.div
                        key="chat-window"
                        initial={{ opacity: 0, scale: 0.8, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.8, y: 20 }}
                        transition={{ type: "spring", damping: 25, stiffness: 300 }}
                        className="luffy-chat-window"
                    >
                        {/* Header */}
                        <div className="luffy-chat-header">
                            <div className="luffy-header-info">
                                <img
                                    src="/assets/luffy-avatar.png"
                                    alt="Luffy"
                                    className="luffy-avatar-img"
                                />
                                <div className="luffy-header-text">
                                    <h3>
                                        Luffy Security
                                        <span className={`luffy-status-indicator ${hasAlert ? "alert" : "safe"}`} />
                                    </h3>
                                    <p>
                                        {threatSummary
                                            ? `${threatSummary.total} emails analyzed • ${threatSummary.recentThreats} threats`
                                            : "AI Security Assistant"}
                                    </p>
                                </div>
                            </div>
                            <button
                                className="luffy-close-btn"
                                onClick={() => setIsOpen(false)}
                                aria-label="Close chat"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        {/* Messages */}
                        <div className="luffy-messages">
                            {messages.map((message) => (
                                <motion.div
                                    key={message.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.3 }}
                                    className={`luffy-message ${message.role}`}
                                >
                                    <div className="luffy-message-bubble">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {message.content}
                                        </ReactMarkdown>
                                    </div>
                                </motion.div>
                            ))}

                            {/* Typing indicator */}
                            {isLoading && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="luffy-message assistant"
                                >
                                    <div className="luffy-typing-indicator">
                                        <span></span>
                                        <span></span>
                                        <span></span>
                                    </div>
                                </motion.div>
                            )}

                            <div ref={messagesEndRef} />
                        </div>

                        {/* Quick Actions */}
                        {messages.length <= 2 && (
                            <div className="luffy-quick-actions">
                                {quickActions.map((action) => (
                                    <button
                                        key={action.label}
                                        className="luffy-chip"
                                        onClick={() => handleQuickAction(action.query)}
                                        disabled={isLoading}
                                    >
                                        {action.label}
                                    </button>
                                ))}
                            </div>
                        )}

                        {/* Input Area */}
                        <form className="luffy-input-area" onSubmit={handleSubmit}>
                            <div className="luffy-input-wrapper">
                                <input
                                    ref={inputRef}
                                    type="text"
                                    className="luffy-input"
                                    placeholder="Ask about email security..."
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    disabled={isLoading}
                                />
                            </div>
                            <button
                                type="submit"
                                className="luffy-send-btn"
                                disabled={!inputValue.trim() || isLoading}
                                aria-label="Send message"
                            >
                                <Send size={20} />
                            </button>
                        </form>
                    </motion.div>
                ) : (
                    // FAB with tooltip
                    <div className="relative">
                        {/* Tooltip popup */}
                        <motion.div
                            initial={{ opacity: 0, x: 10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 1, duration: 0.3 }}
                            className="luffy-tooltip"
                        >
                            <div className="luffy-tooltip-content">
                                <p>🛡️ <strong>Scan your emails for threats</strong></p>
                                <span>Click to chat with your inbox</span>
                            </div>
                            <div className="luffy-tooltip-arrow" />
                        </motion.div>

                        {/* FAB Button */}
                        <motion.button
                            key="fab"
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            exit={{ scale: 0 }}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.95 }}
                            transition={{ type: "spring", damping: 20, stiffness: 300 }}
                            className="luffy-fab"
                            onClick={() => setIsOpen(true)}
                            aria-label="Open Luffy chatbot"
                        >
                            <img
                                src="/assets/luffy-avatar.png"
                                alt="Luffy"
                                className="luffy-fab-img"
                            />
                            {hasAlert && (
                                <motion.span
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-xs font-bold text-white"
                                >
                                    !
                                </motion.span>
                            )}
                        </motion.button>
                    </div>
                )}
            </AnimatePresence>
        </div>
    )
}

