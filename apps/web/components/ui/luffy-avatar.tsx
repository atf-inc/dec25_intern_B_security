"use client"

import { motion } from "framer-motion"
import { Shield, ShieldAlert, ShieldCheck, Zap } from "lucide-react"

interface LuffyAvatarProps {
    size?: "sm" | "md" | "lg"
    hasAlert?: boolean
    animated?: boolean
}

const sizeClasses = {
    sm: "w-8 h-8 text-sm",
    md: "w-11 h-11 text-lg",
    lg: "w-16 h-16 text-2xl",
}

export function LuffyAvatar({ size = "md", hasAlert = false, animated = true }: LuffyAvatarProps) {
    const sizeClass = sizeClasses[size]

    const content = (
        <div
            className={`
        ${sizeClass}
        rounded-full
        flex items-center justify-center
        font-bold text-white
        relative overflow-hidden
      `}
            style={{
                background: hasAlert
                    ? "linear-gradient(135deg, #ff4b4b 0%, #ff6b35 100%)"
                    : "linear-gradient(135deg, oklch(0.75 0.15 195) 0%, oklch(0.60 0.18 250) 50%, oklch(0.55 0.22 280) 100%)",
                boxShadow: hasAlert
                    ? "0 0 20px rgba(255, 75, 75, 0.5)"
                    : "0 0 20px rgba(0, 200, 255, 0.4)",
                border: "2px solid rgba(255, 255, 255, 0.2)",
            }}
        >
            {/* Cyber pattern overlay */}
            <div
                className="absolute inset-0 opacity-20"
                style={{
                    backgroundImage: `
            linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.1) 50%, transparent 60%),
            linear-gradient(-45deg, transparent 40%, rgba(255,255,255,0.1) 50%, transparent 60%)
          `,
                    backgroundSize: "6px 6px",
                }}
            />

            {/* Icon */}
            {hasAlert ? (
                <ShieldAlert className="relative z-10" style={{ width: "60%", height: "60%" }} />
            ) : (
                <ShieldCheck className="relative z-10" style={{ width: "60%", height: "60%" }} />
            )}

            {/* Glow effect */}
            <div
                className="absolute inset-0 rounded-full"
                style={{
                    background: hasAlert
                        ? "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.3) 0%, transparent 60%)"
                        : "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.3) 0%, transparent 60%)",
                }}
            />
        </div>
    )

    if (animated) {
        return (
            <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                whileHover={{ scale: 1.1 }}
                transition={{ type: "spring", damping: 15 }}
            >
                {content}
            </motion.div>
        )
    }

    return content
}

// Stylized L icon for the FAB
export function LuffyIcon({ className = "" }: { className?: string }) {
    return (
        <div className={`relative ${className}`}>
            <span
                className="font-bold"
                style={{
                    fontSize: "inherit",
                    textShadow: "0 0 10px rgba(255, 255, 255, 0.5)",
                    fontFamily: "'Geist', system-ui, sans-serif",
                }}
            >
                L
            </span>
            <Zap
                className="absolute -right-1 -bottom-0.5"
                style={{
                    width: "40%",
                    height: "40%",
                    filter: "drop-shadow(0 0 4px rgba(0, 200, 255, 0.8))"
                }}
            />
        </div>
    )
}

// Shield with security status
export function SecurityShield({ status }: { status: "safe" | "warning" | "danger" }) {
    const colors = {
        safe: {
            bg: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
            glow: "rgba(16, 185, 129, 0.5)",
        },
        warning: {
            bg: "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
            glow: "rgba(245, 158, 11, 0.5)",
        },
        danger: {
            bg: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
            glow: "rgba(239, 68, 68, 0.5)",
        },
    }

    const { bg, glow } = colors[status]

    return (
        <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="w-12 h-12 rounded-full flex items-center justify-center"
            style={{
                background: bg,
                boxShadow: `0 0 20px ${glow}`,
            }}
        >
            <Shield className="w-6 h-6 text-white" />
        </motion.div>
    )
}
