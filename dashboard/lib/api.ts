const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

// Cache configuration removed


type FetchOptions = {
  token?: string
  headers?: Record<string, string>
  method?: "GET" | "POST" | "PUT" | "DELETE"
  body?: unknown
}

async function request<T>(path: string, { token, headers, method = "GET", body }: FetchOptions = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
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
  received_at?: string
  
  // Threat Intelligence
  threat_category?: "NONE" | "PHISHING" | "MALWARE" | "SPAM" | "BEC" | "SPOOFING" | "SUSPICIOUS"
  detection_reason?: string
  
  // Security Metadata
  spf_status?: string
  dkim_status?: string
  dmarc_status?: string
  sender_ip?: string
  attachment_info?: string
  
  // Processing
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | "SPAM"
  risk_score?: number
  risk_tier?: "SAFE" | "CAUTIOUS" | "THREAT"
  analysis_result?: Record<string, unknown>
}

export async function fetchEmails(token: string): Promise<Email[]> {
  // Fetch from API (limit to 20 most recent)
  // We removed localStorage caching to prevent data leakage between users (Issue #121)
  const emails = await request<Email[]>("/api/emails?limit=20", { token })
  return emails
}



export async function syncEmails(token: string, googleToken: string): Promise<{ status: string, new_messages: number }> {
  return request("/api/emails/sync", {
    token,
    headers: { "X-Google-Token": googleToken },
    method: "POST"
  })
}
