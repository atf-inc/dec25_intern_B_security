const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

type FetchOptions = {
  token?: string
}

async function request<T>(path: string, { token }: FetchOptions = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
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
