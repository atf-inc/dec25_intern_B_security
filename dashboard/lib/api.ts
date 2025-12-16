const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

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
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED"
  risk_score?: number
  risk_tier?: "SAFE" | "CAUTIOUS" | "THREAT"
  analysis_result?: Record<string, unknown>
}

export async function fetchEmails(token: string): Promise<Email[]> {
  return request<Email[]>("/api/emails", { token })
}

export async function syncEmails(token: string, googleToken: string): Promise<{ status: string, new_messages: number }> {
  return request("/api/emails/sync", {
    token,
    headers: { "X-Google-Token": googleToken },
    method: "POST"
    // Fetch defaults to GET, so we might need to change request util or pass method?
    // Wait, the request util only does GET? Let's check.
  })
}
