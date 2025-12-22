"use client"

import { useEffect } from "react"
import Link from "next/link"
import { Shield, Mail, Search, Zap, Lock, Bot, CheckCircle, AlertTriangle, XCircle } from "lucide-react"
import gsap from "gsap"
import { ScrollToPlugin } from "gsap/ScrollToPlugin"

// Register GSAP plugin
if (typeof window !== "undefined") {
    gsap.registerPlugin(ScrollToPlugin)
}

// Hand-drawn style shield icon (Notion mascot style)
function ShieldIcon() {
    return (
        <svg
            width="64"
            height="64"
            viewBox="0 0 64 64"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="icon-hand-drawn"
        >
            <path
                d="M32 8L12 16V32C12 44 20 54 32 58C44 54 52 44 52 32V16L32 8Z"
                stroke="#000000"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
            />
            <path
                d="M24 32L30 38L42 26"
                stroke="#000000"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    )
}

// Testimonial data
const testimonials = [
    {
        name: "Sarah Chen",
        handle: "@sarahcodes",
        content: "MailShieldAI caught a phishing attempt that Gmail completely missed. The risk scoring is incredibly accurate.",
        avatar: "SC"
    },
    {
        name: "Alex Rivera",
        handle: "@alexrivera_",
        content: "Finally got rid of email anxiety. The AI detection is like having a security expert reviewing every email.",
        avatar: "AR"
    },
    {
        name: "Marcus Johnson",
        handle: "@marcusjdev",
        content: "The SPF/DKIM verification saves me so much time. I can instantly see if a sender is legitimate.",
        avatar: "MJ"
    },
    {
        name: "Emily Park",
        handle: "@emilypark",
        content: "Love how it sandboxes suspicious links before I click. Peace of mind in my inbox.",
        avatar: "EP"
    },
    {
        name: "David Kumar",
        handle: "@davidk_tech",
        content: "The color-coded threat levels make it so easy to prioritize which emails need attention.",
        avatar: "DK"
    },
    {
        name: "Lisa Zhang",
        handle: "@lisazhang",
        content: "Set it up in 2 minutes with my Gmail. The AI chatbot helps me understand security threats better.",
        avatar: "LZ"
    }
]

// Feature data
const features = [
    {
        icon: Zap,
        title: "AI Threat Detection",
        description: "Real-time analysis of every email using advanced machine learning models.",
    },
    {
        icon: Shield,
        title: "Risk Scoring",
        description: "0-100 score with color-coded threat levels: Safe, Cautious, or Threat.",
    },
    {
        icon: Lock,
        title: "SPF/DKIM/DMARC",
        description: "Automatic verification of sender authenticity and email integrity.",
    },
    {
        icon: Search,
        title: "URL Sandbox",
        description: "Links and attachments analyzed in isolation before you interact.",
    },
    {
        icon: Mail,
        title: "Gmail Integration",
        description: "One-click sync with your Gmail account. Setup takes under a minute.",
    },
    {
        icon: Bot,
        title: "AI Assistant",
        description: "Ask questions about email security and get instant, expert answers.",
    }
]

// Email mockup data
const mockEmails = [
    { sender: "Andrew, Jason", subject: "Q4 Report Review", risk: "safe", score: 12 },
    { sender: "support@paypai.com", subject: "Verify your account now", risk: "threat", score: 87 },
    { sender: "Jenny Williams", subject: "Meeting tomorrow?", risk: "safe", score: 8 },
    { sender: "notifications@dropbox.com", subject: "Someone shared a file", risk: "cautious", score: 45 },
    { sender: "IT Department", subject: "Password reset required", risk: "threat", score: 92 },
]

export function LandingPage() {
    // GSAP smooth scroll for anchor links
    useEffect(() => {
        const handleAnchorClick = (e: MouseEvent) => {
            const target = e.target as HTMLElement
            const anchor = target.closest('a[href^="#"]')
            if (anchor) {
                e.preventDefault()
                const targetId = anchor.getAttribute('href')
                if (targetId && targetId !== '#') {
                    const targetElement = document.querySelector(targetId)
                    if (targetElement) {
                        gsap.to(window, {
                            duration: 1,
                            scrollTo: { y: targetElement, offsetY: 80 },
                            ease: "power3.inOut"
                        })
                    }
                }
            }
        }

        document.addEventListener('click', handleAnchorClick)
        return () => document.removeEventListener('click', handleAnchorClick)
    }, [])

    return (
        <div className="landing">
            {/* Navigation */}
            <nav className="landing-nav fixed top-0 left-0 right-0 z-50 px-6 py-4">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-black flex items-center justify-center">
                            <Shield className="h-5 w-5 text-white" />
                        </div>
                        <span className="text-lg font-semibold text-black">MailShieldAI</span>
                    </Link>

                    {/* Nav Links */}
                    <div className="hidden md:flex items-center gap-8">
                        <Link href="#features" className="landing-nav-link">Product</Link>
                        <Link href="#security" className="landing-nav-link">Security</Link>
                        <Link href="#testimonials" className="landing-nav-link">Reviews</Link>
                        <Link
                            href="https://deepwiki.com/atf-inc/dec25_intern_B_security/1-overview"
                            className="landing-nav-link"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            Docs
                        </Link>
                    </div>

                    {/* CTA */}
                    <Link href="/sign-in" className="landing-cta-primary">
                        Get MailShieldAI Free
                    </Link>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="pt-32 pb-24 px-6 relative overflow-hidden">
                {/* Subtle gradient background */}
                <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-transparent pointer-events-none" />

                <div className="max-w-4xl mx-auto text-center relative z-10">
                    {/* Hand-drawn Icon */}
                    <div className="flex justify-center mb-10 animate-fade-in-up">
                        <div className="p-4 rounded-2xl bg-gray-50 border border-gray-100">
                            <ShieldIcon />
                        </div>
                    </div>

                    {/* Headline */}
                    <h1 className="landing-headline text-5xl md:text-6xl lg:text-7xl mb-8 animate-fade-in-up animation-delay-100 leading-tight">
                        The inbox that<br />defends itself.
                    </h1>

                    {/* Subheadline */}
                    <p className="landing-subheadline text-lg md:text-xl max-w-2xl mx-auto mb-12 animate-fade-in-up animation-delay-200 leading-relaxed">
                        Meet MailShieldAI: The security layer that organizes threats, verifies senders, and sandboxes links before you even click.
                    </p>

                    {/* CTA Buttons */}
                    <div className="animate-fade-in-up animation-delay-300 flex flex-col sm:flex-row gap-4 justify-center items-center">
                        <Link href="/sign-in" className="landing-cta-primary inline-block text-base px-8 py-3.5 rounded-lg font-medium">
                            Get MailShieldAI Free
                        </Link>
                        <Link href="#features" className="text-gray-600 hover:text-gray-900 font-medium text-sm flex items-center gap-2 transition-colors">
                            Learn more
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </Link>
                    </div>
                </div>

                {/* Email Mockup */}
                <div className="max-w-5xl mx-auto mt-16 relative">
                    <div className="email-mockup overflow-hidden">
                        {/* Mockup Header */}
                        <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100">
                            <div className="flex gap-1.5">
                                <div className="w-3 h-3 rounded-full bg-red-400"></div>
                                <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                                <div className="w-3 h-3 rounded-full bg-green-400"></div>
                            </div>
                            <span className="text-xs text-gray-400 ml-2">mail.google.com</span>
                        </div>

                        {/* Mockup Content */}
                        <div className="flex">
                            {/* Sidebar */}
                            <div className="w-48 border-r border-gray-100 p-4 hidden md:block">
                                <div className="flex items-center gap-2 mb-6">
                                    <Shield className="h-4 w-4" />
                                    <span className="text-sm font-medium">Protected</span>
                                </div>
                                <div className="space-y-2 text-sm text-gray-600">
                                    <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
                                        <Mail className="h-4 w-4" />
                                        <span>Inbox</span>
                                    </div>
                                    <div className="flex items-center gap-2 px-3 py-2">
                                        <span className="w-4 h-4 text-center text-green-600">✓</span>
                                        <span>Safe</span>
                                    </div>
                                    <div className="flex items-center gap-2 px-3 py-2">
                                        <span className="w-4 h-4 text-center text-yellow-600">!</span>
                                        <span>Cautious</span>
                                    </div>
                                    <div className="flex items-center gap-2 px-3 py-2">
                                        <span className="w-4 h-4 text-center text-red-600">✕</span>
                                        <span>Threats</span>
                                    </div>
                                </div>
                            </div>

                            {/* Email List */}
                            <div className="flex-1 p-4">
                                <div className="flex items-center justify-between mb-4">
                                    <span className="text-sm font-medium text-gray-700">Inbox</span>
                                    <span className="feature-badge">AI Protected</span>
                                </div>
                                <div className="space-y-1">
                                    {mockEmails.map((email, index) => (
                                        <div
                                            key={index}
                                            className="flex items-center justify-between py-3 px-3 rounded-lg hover:bg-gray-50 transition-colors"
                                        >
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-3">
                                                    <span className="text-sm font-medium text-gray-900 truncate">{email.sender}</span>
                                                    <span className="text-sm text-gray-500 truncate hidden sm:block">{email.subject}</span>
                                                </div>
                                            </div>
                                            <div className="ml-4 flex-shrink-0">
                                                <span className={`pill ${email.risk === 'safe' ? 'pill-safe' : email.risk === 'cautious' ? 'pill-cautious' : 'pill-threat'}`}>
                                                    {email.risk === 'safe' && <CheckCircle className="h-3 w-3" />}
                                                    {email.risk === 'cautious' && <AlertTriangle className="h-3 w-3" />}
                                                    {email.risk === 'threat' && <XCircle className="h-3 w-3" />}
                                                    {email.score}/100
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Social Proof / Testimonials */}
            <section id="testimonials" className="py-24 px-6 bg-gradient-to-b from-gray-50 to-white">
                <div className="max-w-6xl mx-auto">
                    <div className="text-center mb-16">
                        <span className="inline-block px-4 py-1.5 bg-gray-100 text-gray-700 text-xs font-medium rounded-full mb-4">
                            Loved by Teams
                        </span>
                        <h2 className="landing-headline text-3xl md:text-4xl mb-4">Trusted by security-conscious teams</h2>
                        <p className="landing-subheadline max-w-lg mx-auto">See what people are saying about MailShieldAI</p>
                    </div>

                    {/* Masonry Grid */}
                    <div className="columns-1 md:columns-2 lg:columns-3 gap-5 space-y-5">
                        {testimonials.map((testimonial, index) => (
                            <div key={index} className="testimonial-card break-inside-avoid group">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-11 h-11 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center text-sm font-semibold text-gray-700">
                                            {testimonial.avatar}
                                        </div>
                                        <div>
                                            <div className="text-sm font-semibold text-gray-900">{testimonial.name}</div>
                                            <div className="text-xs text-gray-500">{testimonial.handle}</div>
                                        </div>
                                    </div>
                                    {/* X (Twitter) icon */}
                                    <svg className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                                    </svg>
                                </div>
                                <p className="text-sm text-gray-700 leading-relaxed">{testimonial.content}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Features Bento Grid */}
            <section id="features" className="py-20 px-6">
                <div className="max-w-6xl mx-auto">
                    <div className="text-center mb-12">
                        <h2 className="landing-headline text-3xl md:text-4xl mb-4">Everything you need to stay protected</h2>
                        <p className="landing-subheadline">Powerful security features, beautifully simple</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {features.map((feature, index) => (
                            <div key={index} className="feature-card">
                                <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center mb-4">
                                    <feature.icon className="h-5 w-5 text-gray-700" />
                                </div>
                                <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                                <p className="text-sm text-gray-600 leading-relaxed">{feature.description}</p>

                                {/* Feature-specific UI snippet */}
                                {feature.title === "Risk Scoring" && (
                                    <div className="mt-4 flex gap-2">
                                        <span className="pill pill-safe text-xs">Safe</span>
                                        <span className="pill pill-cautious text-xs">Cautious</span>
                                        <span className="pill pill-threat text-xs">Threat</span>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Final CTA */}
            <section className="py-24 px-6 bg-gray-50">
                <div className="max-w-2xl mx-auto text-center">
                    <h2 className="landing-headline text-3xl md:text-4xl mb-6">Ready to shield your inbox?</h2>
                    <p className="landing-subheadline mb-8">
                        Join thousands of users who trust MailShieldAI to keep their inbox safe.
                    </p>
                    <Link href="/sign-in" className="landing-cta-primary inline-block text-base px-10 py-4">
                        Get Started
                    </Link>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-8 px-6 border-t border-gray-200">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                        <Shield className="h-5 w-5" />
                        <span className="text-sm font-medium">MailShieldAI</span>
                    </div>
                    <div className="text-sm text-gray-500">
                        © {new Date().getFullYear()} MailShieldAI. All rights reserved.
                    </div>
                </div>
            </footer>
        </div>
    )
}
