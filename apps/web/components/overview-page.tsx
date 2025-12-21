"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Shield, AlertTriangle, Mail, TrendingUp, TrendingDown, CheckCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Line, LineChart, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from "recharts"
import { ChartContainer } from "@/components/ui/chart"
import { fetchEmails, type Email } from "@/lib/api"

// Sample chart data - in production this would come from API
const threatData = [
  { time: "00:00", threats: 2, blocked: 2, safe: 14 },
  { time: "04:00", threats: 1, blocked: 1, safe: 16 },
  { time: "08:00", threats: 3, blocked: 3, safe: 42 },
  { time: "12:00", threats: 5, blocked: 5, safe: 58 },
  { time: "16:00", threats: 3, blocked: 3, safe: 49 },
  { time: "20:00", threats: 2, blocked: 2, safe: 27 },
]

export function OverviewPage() {
  const { data: session } = useSession()
  const [emails, setEmails] = useState<Email[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadEmails = async () => {
      if (!session?.idToken) return
      try {
        const data = await fetchEmails(session.idToken)
        setEmails(data)
      } catch (error) {
        console.error("Failed to fetch emails:", error)
      } finally {
        setLoading(false)
      }
    }
    loadEmails()
  }, [session])

  // Calculate stats from emails
  const totalEmails = emails.length
  const safeEmails = emails.filter(e => e.risk_tier === "SAFE").length
  const cautiousEmails = emails.filter(e => e.risk_tier === "CAUTIOUS").length
  const threatEmails = emails.filter(e => e.risk_tier === "THREAT").length
  const analyzedEmails = safeEmails + cautiousEmails + threatEmails
  const protectionRate = analyzedEmails > 0 
    ? ((safeEmails / analyzedEmails) * 100).toFixed(1)
    : "100.0"

  // Recent emails for display
  const recentEmails = emails.slice(0, 5).map(email => ({
    id: email.id,
    recipient: email.recipient,
    subject: email.subject,
    status: email.risk_tier === "THREAT" ? "blocked" : email.risk_tier === "SAFE" ? "clean" : "review",
    threat: email.risk_tier === "THREAT" ? "Potential Threat" : null,
  }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Overview</h1>
        <p className="text-muted-foreground">Your email security dashboard</p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Emails Scanned</CardTitle>
            <Mail className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "..." : totalEmails}
            </div>
            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
              <TrendingUp className="h-3 w-3 text-green-500" />
              All time total
            </p>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Safe Emails</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {loading ? "..." : safeEmails}
            </div>
            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
              Verified as safe
            </p>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Threats Detected</CardTitle>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {loading ? "..." : threatEmails}
            </div>
            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
              <TrendingDown className="h-3 w-3 text-green-500" />
              Blocked automatically
            </p>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Protection Rate</CardTitle>
            <Shield className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">{protectionRate}%</div>
            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
              <span className="text-primary">Excellent</span> security
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Threat Activity Chart */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-foreground">Email Activity (Last 24 Hours)</CardTitle>
          <CardDescription>Real-time monitoring of your email security</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer
            id="email-activity-chart"
            config={{
              threats: {
                label: "Threats Detected",
                color: "oklch(0.58 0.24 27)",
              },
              blocked: {
                label: "Threats Blocked",
                color: "oklch(0.58 0.24 264)",
              },
              safe: {
                label: "Safe Emails",
                color: "oklch(0.65 0.18 162)",
              },
            }}
            className="h-[300px]"
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={threatData}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.22 0 0)" />
                <XAxis dataKey="time" stroke="oklch(0.65 0 0)" />
                <YAxis stroke="oklch(0.65 0 0)" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "oklch(0.16 0 0)",
                    border: "1px solid oklch(0.22 0 0)",
                    borderRadius: "8px",
                  }}
                />
                <Line type="monotone" dataKey="threats" stroke="oklch(0.58 0.24 27)" strokeWidth={2} />
                <Line type="monotone" dataKey="blocked" stroke="oklch(0.58 0.24 264)" strokeWidth={2} />
                <Line type="monotone" dataKey="safe" stroke="oklch(0.65 0.18 162)" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        </CardContent>
      </Card>

      {/* Recent Email Activity */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-foreground">Recent Email Activity</CardTitle>
          <CardDescription>Latest emails analyzed by MailShieldAI</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading emails...</p>
          ) : recentEmails.length === 0 ? (
            <p className="text-sm text-muted-foreground">No emails scanned yet. Sync your Gmail to get started.</p>
          ) : (
            <div className="space-y-3">
              {recentEmails.map((email) => (
                <div
                  key={email.id}
                  className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        email.status === "blocked" ? "bg-destructive" : 
                        email.status === "review" ? "bg-yellow-500" : "bg-green-500"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">{email.subject}</p>
                      <p className="text-xs text-muted-foreground">{email.recipient}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {email.status === "blocked" && email.threat && (
                      <Badge variant="destructive" className="text-xs">
                        {email.threat}
                      </Badge>
                    )}
                    <Badge 
                      variant={email.status === "blocked" ? "outline" : email.status === "review" ? "secondary" : "secondary"} 
                      className="text-xs"
                    >
                      {email.status === "blocked" ? "Blocked" : email.status === "review" ? "Review" : "Safe"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
