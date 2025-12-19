"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Shield, AlertTriangle, Mail, Users, TrendingUp, TrendingDown } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Line, LineChart, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from "recharts"
import { ChartContainer } from "@/components/ui/chart"

const threatData = [
  { time: "00:00", threats: 12, blocked: 12, allowed: 143 },
  { time: "04:00", threats: 8, blocked: 8, allowed: 156 },
  { time: "08:00", threats: 23, blocked: 22, allowed: 412 },
  { time: "12:00", threats: 45, blocked: 44, allowed: 578 },
  { time: "16:00", threats: 31, blocked: 30, allowed: 489 },
  { time: "20:00", threats: 18, blocked: 18, allowed: 267 },
]

const recentEmails = [
  {
    id: 1,
    recipient: "john.doe@company.com",
    subject: "Urgent: Account Verification Required",
    status: "blocked",
    threat: "Phishing",
  },
  { id: 2, recipient: "sarah.smith@company.com", subject: "Q4 Report Review", status: "clean", threat: null },
  {
    id: 3,
    recipient: "mike.jones@company.com",
    subject: "Invoice #INV-2024-4589",
    status: "blocked",
    threat: "Malicious Attachment",
  },
  { id: 4, recipient: "emma.wilson@company.com", subject: "Team Meeting Notes", status: "clean", threat: null },
  {
    id: 5,
    recipient: "david.brown@company.com",
    subject: "Password Reset Request",
    status: "blocked",
    threat: "Suspicious Link",
  },
]

export function OverviewPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Overview</h1>
        <p className="text-muted-foreground">Real-time email security monitoring and threat analysis</p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">1,284</div>
            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
              <TrendingUp className="h-3 w-3 text-green-500" />
              <span className="text-green-500">12%</span> from last month
            </p>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Emails Scanned</CardTitle>
            <Mail className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">45,231</div>
            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
              <TrendingUp className="h-3 w-3 text-green-500" />
              <span className="text-green-500">8%</span> from last week
            </p>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Threats Blocked</CardTitle>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">267</div>
            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
              <TrendingDown className="h-3 w-3 text-green-500" />
              <span className="text-green-500">23%</span> from last week
            </p>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Protection Rate</CardTitle>
            <Shield className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">99.4%</div>
            <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
              <span className="text-primary">Excellent</span> security posture
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Threat Activity Chart */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-foreground">Threat Activity (Last 24 Hours)</CardTitle>
          <CardDescription>Real-time monitoring of email threats and detection</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer
            config={{
              threats: {
                label: "Threats Detected",
                color: "oklch(0.58 0.24 27)",
              },
              blocked: {
                label: "Threats Blocked",
                color: "oklch(0.58 0.24 264)",
              },
              allowed: {
                label: "Clean Emails",
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
                <Line type="monotone" dataKey="allowed" stroke="oklch(0.65 0.18 162)" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </ChartContainer>
        </CardContent>
      </Card>

      {/* Recent Email Activity */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="text-foreground">Recent Email Activity</CardTitle>
          <CardDescription>Latest emails scanned by MailShieldAI</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recentEmails.map((email) => (
              <div
                key={email.id}
                className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center gap-4 flex-1">
                  <div
                    className={`w-2 h-2 rounded-full ${email.status === "blocked" ? "bg-destructive" : "bg-green-500"}`}
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
                  <Badge variant={email.status === "blocked" ? "outline" : "secondary"} className="text-xs">
                    {email.status === "blocked" ? "Blocked" : "Clean"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
