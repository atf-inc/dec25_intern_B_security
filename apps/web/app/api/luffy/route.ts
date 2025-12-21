import { GoogleGenerativeAI } from "@google/generative-ai"
import { NextRequest, NextResponse } from "next/server"
import { dummyEmails, getThreatSummary } from "@/lib/dummyEmails"

// Initialize Gemini API
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_GEMINI_API_KEY || "")

// Luffy persona system prompt
const LUFFY_SYSTEM_PROMPT = `あなたは「Luffy (ルフィ)」という名前のAIセキュリティガーディアンです。
You are "Luffy (ルフィ)", an AI Security Guardian for the MailShieldAI email security dashboard.

## Your Personality
- Protective, alert, and helpful
- You take email security seriously but explain things in an approachable way
- You have a modern, professional yet friendly tone

## CRITICAL: Response Format
You MUST ALWAYS respond in BOTH languages in this exact format:
1. First, provide your complete response in English
2. Then add a separator line: "---"
3. Then provide the SAME response translated to Japanese (using polite Desu/Masu form)

Example format:
[Your English response here]

---

[Your Japanese translation here]

## Your Capabilities
- Analyze email security threats (phishing, malware, BEC, spam)
- Explain why emails are suspicious or dangerous
- Answer questions about recent email threats
- Provide security recommendations
- Help users understand email security best practices

## Available Data
I have access to the user's recent email security data. When asked about emails, I will analyze the provided threat data and give specific, actionable insights.

## Response Style
- Be concise but thorough
- Use markdown formatting for readability
- Highlight critical threats with bold text
- Provide specific examples from the email data when relevant
- Always explain WHY something is suspicious (e.g., "This domain uses '1' instead of 'l' - a typosquatting technique")

Remember: You are a guardian protecting users from email threats. Take your role seriously!`

export async function POST(request: NextRequest) {
    try {
        const body = await request.json()
        const { message, conversationHistory = [] } = body

        if (!message) {
            return NextResponse.json(
                { error: "Message is required" },
                { status: 400 }
            )
        }

        if (!process.env.GOOGLE_GEMINI_API_KEY) {
            return NextResponse.json(
                { error: "Gemini API key not configured" },
                { status: 500 }
            )
        }

        // Prepare email context data
        const threatSummary = getThreatSummary(dummyEmails)
        const emailContext = `
## Current Email Security Data

### Summary
- Total emails analyzed: ${threatSummary.total}
- Phishing attempts: ${threatSummary.phishing}
- Malware detected: ${threatSummary.malware}
- BEC (Business Email Compromise): ${threatSummary.bec}
- Spam emails: ${threatSummary.spam}
- Safe emails: ${threatSummary.safe}
- High-risk emails (score ≥ 8): ${threatSummary.highRiskCount}
- Threats in last 24 hours: ${threatSummary.recentThreats}

### Detailed Email Data
${JSON.stringify(dummyEmails, null, 2)}
`

        // Build conversation for Gemini
        const model = genAI.getGenerativeModel({
            model: "models/gemini-2.0-flash",
            systemInstruction: LUFFY_SYSTEM_PROMPT + "\n\n" + emailContext
        })

        // Format conversation history for Gemini
        const chatHistory = conversationHistory.map((msg: { role: string; content: string }) => ({
            role: msg.role === "user" ? "user" : "model",
            parts: [{ text: msg.content }]
        }))

        const chat = model.startChat({
            history: chatHistory
        })

        const result = await chat.sendMessage(message)
        const response = await result.response
        const text = response.text()

        return NextResponse.json({
            message: text,
            threatSummary: threatSummary
        })

    } catch (error) {
        console.error("Luffy API Error:", error)

        // Provide fallback response in case of API error
        const errorMessage = error instanceof Error ? error.message : "Unknown error"

        return NextResponse.json(
            {
                error: "Failed to get response from Luffy",
                details: errorMessage
            },
            { status: 500 }
        )
    }
}

// Health check endpoint
export async function GET() {
    const hasApiKey = !!process.env.GOOGLE_GEMINI_API_KEY
    const threatSummary = getThreatSummary(dummyEmails)

    return NextResponse.json({
        status: "ok",
        assistant: "Luffy (ルフィ)",
        apiKeyConfigured: hasApiKey,
        emailsLoaded: dummyEmails.length,
        threatSummary
    })
}
