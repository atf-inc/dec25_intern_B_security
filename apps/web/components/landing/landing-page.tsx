"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Shield, Mail, Search, Zap, Lock, Bot, CheckCircle, AlertTriangle, XCircle, Globe } from "lucide-react"
import gsap from "gsap"
import { ScrollToPlugin } from "gsap/ScrollToPlugin"

// Register GSAP plugin
if (typeof window !== "undefined") {
    gsap.registerPlugin(ScrollToPlugin)
}

// Translations
const translations = {
    en: {
        nav: {
            product: "Product",
            security: "Security",
            reviews: "Reviews",
            docs: "Docs",
            cta: "Get MailShieldAI Free",
        },
        hero: {
            headline: "The inbox that\ndefends itself.",
            subheadline: "Meet MailShieldAI: The security layer that organizes threats, verifies senders, and sandboxes links before you even click.",
            learnMore: "Learn more",
        },
        testimonials: {
            badge: "Loved by Teams",
            headline: "Trusted by security-conscious teams",
            subheadline: "See what people are saying about MailShieldAI",
            items: [
                { name: "Sarah Chen", handle: "@sarahcodes", content: "MailShieldAI caught a phishing attempt that Gmail completely missed. The risk scoring is incredibly accurate.", avatar: "SC" },
                { name: "Alex Rivera", handle: "@alexrivera_", content: "Finally got rid of email anxiety. The AI detection is like having a security expert reviewing every email.", avatar: "AR" },
                { name: "Marcus Johnson", handle: "@marcusjdev", content: "The SPF/DKIM verification saves me so much time. I can instantly see if a sender is legitimate.", avatar: "MJ" },
                { name: "Emily Park", handle: "@emilypark", content: "Love how it sandboxes suspicious links before I click. Peace of mind in my inbox.", avatar: "EP" },
                { name: "David Kumar", handle: "@davidk_tech", content: "The color-coded threat levels make it so easy to prioritize which emails need attention.", avatar: "DK" },
                { name: "Lisa Zhang", handle: "@lisazhang", content: "Set it up in 2 minutes with my Gmail. The AI chatbot helps me understand security threats better.", avatar: "LZ" },
            ],
        },
        features: {
            headline: "Everything you need to stay protected",
            subheadline: "Powerful security features, beautifully simple",
            items: [
                { icon: Zap, title: "AI Threat Detection", description: "Real-time analysis of every email using advanced machine learning models." },
                { icon: Shield, title: "Risk Scoring", description: "0-100 score with color-coded threat levels: Safe, Cautious, or Threat." },
                { icon: Lock, title: "SPF/DKIM/DMARC", description: "Automatic verification of sender authenticity and email integrity." },
                { icon: Search, title: "URL Sandbox", description: "Links and attachments analyzed in isolation before you interact." },
                { icon: Mail, title: "Gmail Integration", description: "One-click sync with your Gmail account. Setup takes under a minute." },
                { icon: Bot, title: "AI Assistant", description: "Ask questions about email security and get instant, expert answers." },
            ],
        },
        cta: {
            headline: "Ready to shield your inbox?",
            subheadline: "Join thousands of users who trust MailShieldAI to keep their inbox safe.",
            button: "Get Started",
        },
        footer: {
            copyright: "MailShieldAI. All rights reserved.",
        },
        mockup: {
            protected: "Protected",
            inbox: "Inbox",
            safe: "Safe",
            cautious: "Cautious",
            threats: "Threats",
            aiProtected: "AI Protected",
        },
        pills: {
            safe: "Safe",
            cautious: "Cautious",
            threat: "Threat",
        },
    },
    ja: {
        nav: {
            product: "製品",
            security: "セキュリティ",
            reviews: "レビュー",
            docs: "ドキュメント",
            cta: "無料で始める",
        },
        hero: {
            headline: "自ら守る\n受信トレイ。",
            subheadline: "MailShieldAI: 脅威を整理し、送信者を検証し、クリック前にリンクをサンドボックスでチェックするセキュリティレイヤー。",
            learnMore: "詳しく見る",
        },
        testimonials: {
            badge: "チームに愛されています",
            headline: "セキュリティ意識の高いチームに信頼されています",
            subheadline: "MailShieldAIについての声をご覧ください",
            items: [
                { name: "田中 さくら", handle: "@sakura_codes", content: "Gmailが見逃したフィッシング攻撃をMailShieldAIが検出しました。リスクスコアリングは驚くほど正確です。", avatar: "田" },
                { name: "山田 太郎", handle: "@taro_dev", content: "メールの不安から解放されました。AI検出はまるでセキュリティ専門家がすべてのメールをレビューしているようです。", avatar: "山" },
                { name: "佐藤 花子", handle: "@hanako_tech", content: "SPF/DKIM検証で時間を大幅に節約できます。送信者が正当かどうか即座にわかります。", avatar: "佐" },
                { name: "鈴木 健太", handle: "@kenta_suzuki", content: "不審なリンクをクリック前にサンドボックスでチェックしてくれるのが最高です。安心感があります。", avatar: "鈴" },
                { name: "高橋 美咲", handle: "@misaki_t", content: "色分けされた脅威レベルで、どのメールに注意が必要かすぐにわかります。", avatar: "高" },
                { name: "伊藤 翔", handle: "@sho_ito", content: "Gmailとの連携が2分で完了。AIチャットボットでセキュリティ脅威をよりよく理解できます。", avatar: "伊" },
            ],
        },
        features: {
            headline: "保護に必要なすべてが揃っています",
            subheadline: "強力なセキュリティ機能をシンプルに",
            items: [
                { icon: Zap, title: "AI脅威検出", description: "高度な機械学習モデルを使用して、すべてのメールをリアルタイムで分析します。" },
                { icon: Shield, title: "リスクスコアリング", description: "0-100のスコアと色分けされた脅威レベル：安全、注意、脅威。" },
                { icon: Lock, title: "SPF/DKIM/DMARC", description: "送信者の信頼性とメールの整合性を自動検証します。" },
                { icon: Search, title: "URLサンドボックス", description: "リンクと添付ファイルを操作前に隔離環境で分析します。" },
                { icon: Mail, title: "Gmail連携", description: "ワンクリックでGmailアカウントと同期。設定は1分以内で完了。" },
                { icon: Bot, title: "AIアシスタント", description: "メールセキュリティについて質問すると、即座に専門的な回答を得られます。" },
            ],
        },
        cta: {
            headline: "受信トレイを守る準備はできましたか？",
            subheadline: "MailShieldAIを信頼して受信トレイを安全に保つ何千人ものユーザーに参加しましょう。",
            button: "始める",
        },
        footer: {
            copyright: "MailShieldAI. All rights reserved.",
        },
        mockup: {
            protected: "保護済み",
            inbox: "受信トレイ",
            safe: "安全",
            cautious: "注意",
            threats: "脅威",
            aiProtected: "AI保護",
        },
        pills: {
            safe: "安全",
            cautious: "注意",
            threat: "脅威",
        },
    },
}

// Email mockup data
const mockEmails = [
    { sender: "Andrew, Jason", subject: "Q4 Report Review", subjectJa: "Q4レポートレビュー", risk: "safe", score: 12 },
    { sender: "support@definitely-not-paypal.com", subject: "Verify your account now", subjectJa: "今すぐアカウントを確認", risk: "threat", score: 87 },
    { sender: "Jenny Williams", subject: "Meeting tomorrow?", subjectJa: "明日の会議は？", risk: "safe", score: 8 },
    { sender: "notifications@dropbox.com", subject: "Someone shared a file", subjectJa: "ファイルが共有されました", risk: "cautious", score: 45 },
    { sender: "IT Department", subject: "Password reset required", subjectJa: "パスワードリセットが必要です", risk: "threat", score: 92 },
]

type Language = "en" | "ja"

// Hand-drawn style shield icon
function ShieldIcon() {
    return (
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="icon-hand-drawn" aria-hidden="true">
            <path d="M32 8L12 16V32C12 44 20 54 32 58C44 54 52 44 52 32V16L32 8Z" stroke="#000000" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            <path d="M24 32L30 38L42 26" stroke="#000000" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    )
}

export function LandingPage() {
    const [lang, setLang] = useState<Language>("en")
    const t = translations[lang]

    const toggleLanguage = () => setLang(lang === "en" ? "ja" : "en")

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
                        <Link href="#features" className="landing-nav-link">{t.nav.product}</Link>
                        <Link href="#security" className="landing-nav-link">{t.nav.security}</Link>
                        <Link href="#testimonials" className="landing-nav-link">{t.nav.reviews}</Link>
                        <Link
                            href="https://deepwiki.com/atf-inc/dec25_intern_B_security/1-overview"
                            className="landing-nav-link"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            {t.nav.docs}
                        </Link>
                    </div>

                    {/* Right side: Language toggle + CTA */}
                    <div className="flex items-center gap-3">
                        {/* Language Toggle */}
                        <button
                            onClick={toggleLanguage}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all text-sm font-medium text-gray-600"
                            title={lang === "en" ? "Switch to Japanese" : "英語に切り替え"}
                        >
                            <Globe className="h-4 w-4" />
                            <span>{lang === "en" ? "日本語" : "EN"}</span>
                        </button>

                        {/* CTA */}
                        <Link href="/sign-in" className="landing-cta-primary hidden sm:inline-block">
                            {t.nav.cta}
                        </Link>
                    </div>
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
                    <h1 className="landing-headline text-5xl md:text-6xl lg:text-7xl mb-8 animate-fade-in-up animation-delay-100 leading-tight whitespace-pre-line">
                        {t.hero.headline}
                    </h1>

                    {/* Subheadline */}
                    <p className="landing-subheadline text-lg md:text-xl max-w-2xl mx-auto mb-12 animate-fade-in-up animation-delay-200 leading-relaxed">
                        {t.hero.subheadline}
                    </p>

                    {/* CTA Buttons */}
                    <div className="animate-fade-in-up animation-delay-300 flex flex-col sm:flex-row gap-4 justify-center items-center">
                        <Link href="/sign-in" className="landing-cta-primary inline-block text-base px-8 py-3.5 rounded-lg font-medium">
                            {t.nav.cta}
                        </Link>
                        <Link href="#features" className="text-gray-600 hover:text-gray-900 font-medium text-sm flex items-center gap-2 transition-colors">
                            {t.hero.learnMore}
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
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
                            <div className="flex gap-1.5" aria-hidden="true">
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
                                    <span className="text-sm font-medium">{t.mockup.protected}</span>
                                </div>
                                <div className="space-y-2 text-sm text-gray-600">
                                    <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
                                        <Mail className="h-4 w-4" />
                                        <span>{t.mockup.inbox}</span>
                                    </div>
                                    <div className="flex items-center gap-2 px-3 py-2">
                                        <span className="w-4 h-4 text-center text-green-600">✓</span>
                                        <span>{t.mockup.safe}</span>
                                    </div>
                                    <div className="flex items-center gap-2 px-3 py-2">
                                        <span className="w-4 h-4 text-center text-yellow-600">!</span>
                                        <span>{t.mockup.cautious}</span>
                                    </div>
                                    <div className="flex items-center gap-2 px-3 py-2">
                                        <span className="w-4 h-4 text-center text-red-600">✕</span>
                                        <span>{t.mockup.threats}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Email List */}
                            <div className="flex-1 p-4">
                                <div className="flex items-center justify-between mb-4">
                                    <span className="text-sm font-medium text-gray-700">{t.mockup.inbox}</span>
                                    <span className="feature-badge">{t.mockup.aiProtected}</span>
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
                                                    <span className="text-sm text-gray-500 truncate hidden sm:block">{lang === "ja" ? email.subjectJa : email.subject}</span>
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
                            {t.testimonials.badge}
                        </span>
                        <h2 className="landing-headline text-3xl md:text-4xl mb-4">{t.testimonials.headline}</h2>
                        <p className="landing-subheadline max-w-lg mx-auto">{t.testimonials.subheadline}</p>
                    </div>

                    {/* Masonry Grid */}
                    <div className="columns-1 md:columns-2 lg:columns-3 gap-5 space-y-5">
                        {t.testimonials.items.map((testimonial: { name: string; handle: string; content: string; avatar: string }, index: number) => (
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
                                    <svg className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
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
                        <h2 className="landing-headline text-3xl md:text-4xl mb-4">{t.features.headline}</h2>
                        <p className="landing-subheadline">{t.features.subheadline}</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {t.features.items.map((feature: { icon: React.ElementType; title: string; description: string }, index: number) => (
                            <div key={index} className="feature-card">
                                <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center mb-4">
                                    <feature.icon className="h-5 w-5 text-gray-700" />
                                </div>
                                <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                                <p className="text-sm text-gray-600 leading-relaxed">{feature.description}</p>

                                {/* Feature-specific UI snippet */}
                                {(feature.title === "Risk Scoring" || feature.title === "リスクスコアリング") && (
                                    <div className="mt-4 flex gap-2">
                                        <span className="pill pill-safe text-xs">{t.pills.safe}</span>
                                        <span className="pill pill-cautious text-xs">{t.pills.cautious}</span>
                                        <span className="pill pill-threat text-xs">{t.pills.threat}</span>
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
                    <h2 className="landing-headline text-3xl md:text-4xl mb-6">{t.cta.headline}</h2>
                    <p className="landing-subheadline mb-8">
                        {t.cta.subheadline}
                    </p>
                    <Link href="/sign-in" className="landing-cta-primary inline-block text-base px-10 py-4">
                        {t.cta.button}
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
