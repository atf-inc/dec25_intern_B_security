"use client"

import { forwardRef, useState, useCallback } from "react"
import { motion } from "framer-motion"
import { Send, Mic, Sparkles } from "lucide-react"

interface ChatInputProps {
    value: string
    onChange: (value: string) => void
    onSubmit: () => void
    disabled?: boolean
    placeholder?: string
    showVoice?: boolean
    showAI?: boolean
}

export const ChatInput = forwardRef<HTMLInputElement, ChatInputProps>(
    function ChatInput(
        {
            value,
            onChange,
            onSubmit,
            disabled = false,
            placeholder = "Ask about email security... / メールセキュリティについて質問...",
            showVoice = false,
            showAI = false
        },
        ref
    ) {
        const [isFocused, setIsFocused] = useState(false)

        const handleSubmit = useCallback((e: React.FormEvent) => {
            e.preventDefault()
            if (value.trim() && !disabled) {
                onSubmit()
            }
        }, [value, disabled, onSubmit])

        const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
            }
        }, [handleSubmit])

        return (
            <form className="luffy-input-area" onSubmit={handleSubmit}>
                <div className={`luffy-input-wrapper ${isFocused ? 'focused' : ''}`}>
                    {showAI && (
                        <motion.span
                            initial={{ opacity: 0, scale: 0 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="absolute left-3 top-1/2 -translate-y-1/2"
                        >
                            <Sparkles size={16} className="text-cyan-400" />
                        </motion.span>
                    )}

                    <input
                        ref={ref}
                        type="text"
                        className={`luffy-input ${showAI ? 'pl-10' : ''}`}
                        placeholder={placeholder}
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        onKeyDown={handleKeyDown}
                        onFocus={() => setIsFocused(true)}
                        onBlur={() => setIsFocused(false)}
                        disabled={disabled}
                        aria-label="Chat message input"
                    />
                </div>

                {showVoice && (
                    <button
                        type="button"
                        className="luffy-voice-btn"
                        disabled={disabled}
                        aria-label="Voice input"
                    >
                        <Mic size={20} />
                    </button>
                )}

                <motion.button
                    type="submit"
                    className="luffy-send-btn"
                    disabled={!value.trim() || disabled}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    aria-label="Send message"
                >
                    <Send size={20} />
                </motion.button>
            </form>
        )
    }
)

// Suggested prompts component
interface SuggestedPromptsProps {
    prompts: string[]
    onPromptClick: (prompt: string) => void
    disabled?: boolean
}

export function SuggestedPrompts({
    prompts,
    onPromptClick,
    disabled = false
}: SuggestedPromptsProps) {
    return (
        <div className="flex flex-wrap gap-2 p-3">
            {prompts.map((prompt, index) => (
                <motion.button
                    key={prompt}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    onClick={() => onPromptClick(prompt)}
                    disabled={disabled}
                    className="text-xs px-3 py-1.5 rounded-full bg-white/5 border border-white/10 
                     text-white/60 hover:bg-white/10 hover:text-white/80 
                     transition-colors disabled:opacity-50"
                >
                    {prompt}
                </motion.button>
            ))}
        </div>
    )
}

// Default suggested prompts
export const defaultPrompts = [
    "Check my inbox security",
    "Show recent threats",
    "Any phishing emails?",
    "セキュリティ状況"
]
