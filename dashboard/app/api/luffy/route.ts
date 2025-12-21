import { GoogleGenerativeAI } from "@google/generative-ai"
import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/auth"

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
        const session = await auth()
        if (!session || !session.accessToken) {
            return NextResponse.json(
                { error: "Unauthorized" },
                { status: 401 }
            )
        }

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

        // Fetch real data from backend
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
        
        // Backend expects ID Token for authentication, not Access Token
        const token = session.idToken || session.accessToken
        
        console.log(`[Luffy] Using token type: ${session.idToken ? 'ID Token' : 'Access Token'} (Length: ${token?.length})`)

        const headers = { 
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        }

        let emailContext = ""
        let threatSummary = null

        try {
            // Parallel fetch for speed
            const [emailsRes, statsRes] = await Promise.all([
                fetch(`${backendUrl}/api/emails?limit=20`, { headers }),
                fetch(`${backendUrl}/api/stats`, { headers })
            ])
            
            if (!emailsRes.ok) console.error(`[Luffy] Emails fetch failed: ${emailsRes.status} ${emailsRes.statusText}`)
            if (!statsRes.ok) console.error(`[Luffy] Stats fetch failed: ${statsRes.status} ${statsRes.statusText}`)

            const emails = emailsRes.ok ? await emailsRes.json() : []
            const stats = statsRes.ok ? await statsRes.json() : {}

            threatSummary = {
                total: stats.total_emails || 0,
                phishing: 0, // Backend stats might not break this down yet, infer from emails?
                malware: 0,
                bec: 0,
                spam: 0,
                safe: stats.safe || 0,
                highRiskCount: stats.threat || 0,
                recentThreats: stats.threat || 0 // Approximate
            }

             emailContext = `
## Current Email Security Data

### Summary
- Total emails analyzed: ${stats.total_emails || 0}
- Safe: ${stats.safe || 0}
- Cautious: ${stats.cautious || 0}
- Threats/High Risk: ${stats.threat || 0}

### Recent Emails (Last 20)
${JSON.stringify(emails, null, 2)}
`
        } catch (fetchError) {
            console.error("Failed to fetch backend data:", fetchError)
            emailContext = "\nNote: Unable to fetch real-time email data. Please ask General security questions."
        }

        // Build conversation for Gemini
        const model = genAI.getGenerativeModel({
            model: "gemini-3-flash-preview", 
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
        console.error("Luffy API Critical Error:", error)
        return NextResponse.json(
            {
                error: "Failed to get response from Luffy",
                details: error instanceof Error ? error.message : "Unknown error",
                stack: error instanceof Error ? error.stack : undefined
            },
            { status: 500 }
        )
    }
}

// Health check and status endpoint
export async function GET() {
    const hasApiKey = !!process.env.GOOGLE_GEMINI_API_KEY
    
    // Attempt to fetch stats if user is authenticated
    let threatSummary = null
    try {
        const session = await auth()
        if (session && (session.idToken || session.accessToken)) {
             const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
             const headers = { 
                "Authorization": `Bearer ${session.idToken || session.accessToken}`,
                "Content-Type": "application/json"
            }
            
            const statsRes = await fetch(`${backendUrl}/api/stats`, { headers })
            if (statsRes.ok) {
                const stats = await statsRes.json()
                threatSummary = {
                    total: stats.total_emails || 0,
                    phishing: 0, 
                    malware: 0,
                    bec: 0,
                    spam: 0,
                    safe: stats.safe || 0,
                    highRiskCount: stats.threat || 0,
                    recentThreats: stats.threat || 0 
                }
            }
        }
    } catch (e) {
        console.error("Failed to fetch stats for GET:", e)
    }

    return NextResponse.json({
        status: "ok",
        assistant: "Luffy (ルフィ)",
        apiKeyConfigured: hasApiKey,
        mode: "connected_to_backend",
        threatSummary: threatSummary || {
            // Fallback empty summary to prevent frontend crash
            total: 0, phishing: 0, malware: 0, bec: 0, spam: 0, safe: 0, highRiskCount: 0, recentThreats: 0
        }
    })
}
