"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { useSession } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { X, Send, Shield, Mail, AlertTriangle, Lock, Sparkles, MessageCircle, RefreshCw } from "lucide-react"
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
    recentThreats: number
}

// Quick action chips data
const quickActions = [
    { 
        icon: Mail,
        label: "Phishing emails", 
        query: "Do I have any phishing emails?" 
    },
    { 
        icon: AlertTriangle,
        label: "Security status", 
        query: "What's my security status?" 
    },
    { 
        icon: Shield,
        label: "Dangerous emails", 
        query: "Show me dangerous emails" 
    },
]

// Welcome message
const WELCOME_MESSAGE: Message = {
    id: "welcome",
    role: "assistant",
    content: `**Luffy Security Assistant**

I am your AI-powered email security guardian. My capabilities include:

• Analyzing emails for phishing and malware
• Reviewing your inbox security status
• Identifying high-risk messages
• Providing security recommendations`,
    timestamp: new Date(),
}

export function LuffyChatbot() {
    const { data: session } = useSession()
    
    // State
    const [isOpen, setIsOpen] = useState(false)
    const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE])
    const [inputValue, setInputValue] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [threatSummary, setThreatSummary] = useState<ThreatSummary | null>(null)
    const [hasAlert, setHasAlert] = useState(false)

    // Refs
    const scrollAreaRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        if (scrollAreaRef.current) {
            scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
        }
    }, [messages, isLoading])

    // Fetch initial threat summary
    useEffect(() => {
        async function fetchStatus() {
            try {
                const res = await fetch("/api/luffy")
                if (res.ok) {
                    const data = await res.json()
                    if (data.threatSummary) {
                        setThreatSummary(data.threatSummary)
                        setHasAlert(data.threatSummary.recentThreats > 0)
                    }
                }
            } catch (error) {
                console.error("Failed to fetch Luffy status:", error)
            }
        }
        fetchStatus()
    }, [])

    // Focus input when chat opens
    useEffect(() => {
        if (isOpen) {
            setTimeout(() => inputRef.current?.focus(), 100)
        }
    }, [isOpen])

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
            // Build conversation history (excluding welcome message to save context)
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
                content: `⚠️ Sorry, I encountered an error. Please try again.`,
                timestamp: new Date(),
            }
            setMessages((prev) => [...prev, errorMessage])
        } finally {
            setIsLoading(false)
        }
    }

    // Handle form submit
    const handleSubmit = (e?: React.FormEvent) => {
        if (e) e.preventDefault()
        sendMessage(inputValue)
    }

    const handleQuickAction = (query: string) => {
        setInputValue(query)
        // Small delay to allow visual feedback
        setTimeout(() => sendMessage(query), 100)
    }

    if (!session) return null

    if (!isOpen) {
        return (
            <Button
                onClick={() => setIsOpen(true)}
                size="icon"
                className="fixed bottom-6 right-6 h-16 w-16 rounded-full bg-black shadow-lg hover:bg-neutral-900 transition-all duration-300 hover:scale-105 z-50 text-3xl border border-white/10"
            >
                <div className="relative flex items-center justify-center w-full h-full p-3">
                    <Avatar className="h-full w-full bg-transparent">
                        <AvatarImage src="https://github.com/evilrabbit.png" alt="Luffy" className="object-contain" />
                        <AvatarFallback>LS</AvatarFallback>
                    </Avatar>
                    {hasAlert && (
                        <div className="absolute -top-1 -right-1 h-3.5 w-3.5 bg-red-500 rounded-full border-2 border-blue-700 animate-pulse" />
                    )}
                </div>
                <span className="sr-only">Open security assistant</span>
            </Button>
        )
    }

    return (
        <Card className="fixed bottom-24 right-6 w-[380px] h-[600px] max-h-[calc(100vh-120px)] shadow-2xl border-border/50 bg-card/95 backdrop-blur-xl z-50 flex flex-col overflow-hidden animate-in slide-in-from-bottom-8 duration-300">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border/50 bg-black/95">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <div className="h-10 w-10 rounded-full bg-black border border-white/10 flex items-center justify-center overflow-hidden p-1.5">
                             <Avatar className="h-full w-full">
                                <AvatarImage src="https://github.com/evilrabbit.png" alt="Luffy" className="object-contain" />
                                <AvatarFallback>LS</AvatarFallback>
                            </Avatar>
                        </div>
                        <div className={`absolute -bottom-1 -right-1 h-3 w-3 rounded-full border-2 border-black ${hasAlert ? "bg-red-500 animate-pulse" : "bg-green-500"}`} />
                    </div>
                    <div>
                        <h3 className="font-semibold text-foreground flex items-center gap-2">
                            Luffy Security
                            <Sparkles className="h-3.5 w-3.5 text-blue-500" />
                        </h3>
                        <p className="text-xs text-muted-foreground">
                            {threatSummary ? `AI-powered • ${threatSummary.total} emails scanned` : "AI-powered Security"}
                        </p>
                    </div>
                </div>
                <Button
                    onClick={() => setIsOpen(false)}
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-accent/50"
                >
                    <X className="h-4 w-4" />
                </Button>
            </div>

            {/* Messages Area - Using div with overflow-y-auto as ScrollArea replacement */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-secondary scrollbar-track-transparent" ref={scrollAreaRef}>
                 {messages.map((message) => (
                    <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div
                            className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                                message.role === "user"
                                    ? "bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-md shadow-blue-500/20"
                                    : "bg-secondary/80 text-foreground border border-border/50"
                            }`}
                        >
                            <div className={`text-sm leading-relaxed prose dark:prose-invert prose-p:my-1 prose-pre:my-1 ${message.role === "user" ? "text-white" : ""}`}>
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {message.content}
                                </ReactMarkdown>
                            </div>
                            <span
                                className={`text-[10px] mt-1.5 block ${
                                    message.role === "user" ? "text-blue-200" : "text-muted-foreground"
                                }`}
                            >
                                {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </span>
                        </div>
                    </div>
                ))}

                {/* Loading Indicator */}
                {isLoading && (
                    <div className="flex justify-start">
                         <div className="bg-secondary/80 text-foreground border border-border/50 rounded-2xl px-4 py-3 flex items-center gap-1.5">
                            <span className="w-2 h-2 bg-blue-500/50 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                            <span className="w-2 h-2 bg-blue-500/50 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                            <span className="w-2 h-2 bg-blue-500/50 rounded-full animate-bounce"></span>
                        </div>
                    </div>
                )}
            </div>

            {/* Quick Actions */}
            {!isLoading && messages.length <= 2 && (
                <div className="px-4 pb-3 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <p className="text-xs text-muted-foreground mb-2 font-medium">Try asking:</p>
                    <div className="flex flex-wrap gap-2">
                        {quickActions.map((action, index) => (
                            <Button
                                key={index}
                                onClick={() => handleQuickAction(action.query)}
                                variant="outline"
                                size="sm"
                                className="text-xs h-8 bg-secondary/50 hover:bg-secondary border-border/50 hover:border-blue-500/50 hover:text-blue-500 transition-all"
                            >
                                <action.icon className="h-3 w-3 mr-1.5" />
                                {action.label}
                            </Button>
                        ))}
                    </div>
                </div>
            )}

            {/* Input Area */}
            <div className="p-4 border-t border-border/50 bg-background/50 backdrop-blur-sm">
                <form 
                    className="flex items-end gap-2"
                    onSubmit={handleSubmit}
                    autoComplete="off"
                >
                    {/* Hack to prevent browser autofill */}
                    <input type="text" name="email" style={{ display: 'none' }} tabIndex={-1} autoComplete="off" />
                    <input type="password" name="password" style={{ display: 'none' }} tabIndex={-1} autoComplete="off" />

                    <div className="flex-1 relative">
                        <Input
                            ref={inputRef}
                            name="luffy-chat-message"
                            id="luffy-chat-message"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            // onKeyDown handled by Input by default for Enter, but form handles submit
                            placeholder="Ask about email security..."
                            className="pr-10 bg-secondary/50 border-border/50 focus-visible:border-blue-500/50 focus-visible:ring-blue-500/20"
                            disabled={isLoading}
                            autoComplete="off"
                            data-form-type="other"
                            data-lpignore="true"
                        />
                        <Lock className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/50" />
                    </div>
                    <Button
                        type="submit"
                        size="icon"
                        disabled={!inputValue.trim() || isLoading}
                        className="h-10 w-10 bg-gradient-to-br from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 transition-all disabled:opacity-50"
                    >
                        <Send className="h-4 w-4" />
                    </Button>
                </form>
                <p className="text-[10px] text-muted-foreground mt-2 text-center flex items-center justify-center gap-1.5">
                    <Shield className="h-3 w-3" /> Encrypted and secure conversation
                </p>
            </div>
        </Card>
    )
}

