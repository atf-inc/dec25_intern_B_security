const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

type FetchOptions = {
  token?: string
} & RequestInit

async function request<T>(path: string, { token, ...options }: FetchOptions = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    cache: options.cache || "no-store",
  })

  if (!res.ok) {
    let errorMessage = `API request failed (${res.status})`
    if (process.env.NODE_ENV === "development") {
      try {
        const body = await res.text()
        errorMessage += `: ${body}`
      } catch {
        // Ignore parsing errors
      }
    }
    throw new Error(errorMessage)
  }

  return res.json() as Promise<T>
}

export type Email = {
  id: string
  sender: string
  recipient: string
  subject: string
  body_preview?: string
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED"
  risk_score?: number
  risk_tier?: "SAFE" | "CAUTIOUS" | "THREAT"
  analysis_result?: Record<string, unknown>
}

export async function fetchEmails(token: string): Promise<Email[]> {
  return request<Email[]>("/api/emails", { token })
}

export async function fetchGmailEmails(accessToken: string): Promise<Email[]> {
  const response = await request<{ emails: Email[] }>("/api/v1/emails/fetch", {
    method: "POST",
    token: accessToken, // Sending for Backend Auth (Clerk)
    body: JSON.stringify({ access_token: accessToken }), // Sending for Gmail Service
  })
  return response.emails || []
}
