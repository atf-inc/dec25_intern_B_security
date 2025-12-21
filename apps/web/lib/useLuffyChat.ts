"use client"

import { useState, useCallback, useRef, useEffect } from "react"

export interface ChatMessage {
    id: string
    role: "user" | "assistant"
    content: string
    timestamp: Date
    isError?: boolean
}

export interface ChatState {
    messages: ChatMessage[]
    isLoading: boolean
    error: string | null
}

interface UseLuffyChatOptions {
    onMessageSent?: (message: string) => void
    onResponseReceived?: (response: string) => void
    onError?: (error: Error) => void
}

export function useLuffyChat(options: UseLuffyChatOptions = {}) {
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const abortControllerRef = useRef<AbortController | null>(null)

    // Cancel any pending request on unmount
    useEffect(() => {
        return () => {
            abortControllerRef.current?.abort()
        }
    }, [])

    const sendMessage = useCallback(async (content: string) => {
        if (!content.trim() || isLoading) return

        // Cancel any existing request
        abortControllerRef.current?.abort()
        abortControllerRef.current = new AbortController()

        // Add user message immediately
        const userMessage: ChatMessage = {
            id: `user-${Date.now()}`,
            role: "user",
            content: content.trim(),
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMessage])
        setIsLoading(true)
        setError(null)
        options.onMessageSent?.(content)

        try {
            // Build conversation history
            const conversationHistory = messages.map(m => ({
                role: m.role,
                content: m.content
            }))

            const response = await fetch("/api/luffy", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: content,
                    conversationHistory
                }),
                signal: abortControllerRef.current.signal
            })

            if (!response.ok) {
                throw new Error(`Failed to get response: ${response.status}`)
            }

            const data = await response.json()

            const assistantMessage: ChatMessage = {
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: data.message,
                timestamp: new Date()
            }

            setMessages(prev => [...prev, assistantMessage])
            options.onResponseReceived?.(data.message)

        } catch (err) {
            if (err instanceof Error && err.name === "AbortError") {
                // Request was cancelled, ignore
                return
            }

            const errorMessage = err instanceof Error ? err.message : "Unknown error"
            setError(errorMessage)
            options.onError?.(err instanceof Error ? err : new Error(errorMessage))

            // Add error message to chat
            const errorChatMessage: ChatMessage = {
                id: `error-${Date.now()}`,
                role: "assistant",
                content: `⚠️ Error: ${errorMessage}\n\n---\n\n⚠️ エラー: ${errorMessage}`,
                timestamp: new Date(),
                isError: true
            }
            setMessages(prev => [...prev, errorChatMessage])

        } finally {
            setIsLoading(false)
        }
    }, [isLoading, messages, options])

    const clearMessages = useCallback(() => {
        setMessages([])
        setError(null)
    }, [])

    const cancelRequest = useCallback(() => {
        abortControllerRef.current?.abort()
        setIsLoading(false)
    }, [])

    return {
        messages,
        isLoading,
        error,
        sendMessage,
        clearMessages,
        cancelRequest
    }
}

// Hook for managing chat input
export function useChatInput() {
    const [value, setValue] = useState("")
    const inputRef = useRef<HTMLInputElement>(null)

    const focus = useCallback(() => {
        inputRef.current?.focus()
    }, [])

    const clear = useCallback(() => {
        setValue("")
    }, [])

    const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setValue(e.target.value)
    }, [])

    return {
        value,
        setValue,
        inputRef,
        focus,
        clear,
        handleChange
    }
}
