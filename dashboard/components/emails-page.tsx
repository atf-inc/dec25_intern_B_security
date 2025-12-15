"use client"

import { useEffect, useMemo, useState } from "react"

import { useAuth } from "@clerk/nextjs"
import { Filter, Mail, Search } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { fetchEmails, type Email } from "@/lib/api"

const tierColor: Record<string, string> = {
  SAFE: "text-green-500 bg-green-500/10",
  CAUTIOUS: "text-yellow-600 bg-yellow-500/10",
  THREAT: "text-destructive bg-destructive/10",
}

export function EmailsPage() {
  const { getToken } = useAuth()
  const [emails, setEmails] = useState<Email[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>("all")

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const token = await getToken()
        if (!token) {
          throw new Error("Not authenticated")
        }
        const data = await fetchEmails(token)
        if (active) {
          setEmails(data)
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to fetch emails")
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void load()
    return () => {
      active = false
    }
  }, [getToken])

  const filteredEmails = useMemo(() => {
    if (statusFilter === "all") return emails
    return emails.filter((email) => email.status === statusFilter)
  }, [emails, statusFilter])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Email Logs</h1>
        <p className="text-muted-foreground">Complete history of scanned emails and threat detection</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Scanned</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">{emails.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Current dataset</p>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Safe</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {emails.filter((e) => e.risk_tier === "SAFE").length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Marked as low risk</p>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Cautious</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-500">
              {emails.filter((e) => e.risk_tier === "CAUTIOUS").length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Review recommended</p>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Threat</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {emails.filter((e) => e.risk_tier === "THREAT").length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">High risk detected</p>
          </CardContent>
        </Card>
      </div>

      {/* Email Logs Table */}
      <Card className="border-border">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-foreground">Email Activity Log</CardTitle>
              <CardDescription>Real-time email scanning and threat detection results</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative w-64">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input placeholder="Search emails..." className="pl-8" />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="PENDING">Pending</SelectItem>
                  <SelectItem value="PROCESSING">Processing</SelectItem>
                  <SelectItem value="COMPLETED">Completed</SelectItem>
                  <SelectItem value="FAILED">Failed</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon">
                <Filter className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error && <p className="text-sm text-destructive mb-4">Error: {error}</p>}
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading emails...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email ID</TableHead>
                  <TableHead>Recipient</TableHead>
                  <TableHead>Sender</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Score</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEmails.map((email) => (
                  <TableRow key={email.id} className="cursor-pointer hover:bg-accent/50">
                    <TableCell>
                      <code className="text-xs font-mono text-muted-foreground">{email.id}</code>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Mail className="h-3 w-3 text-muted-foreground" />
                        <span className="text-sm text-foreground">{email.recipient}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-foreground">{email.sender}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-foreground max-w-xs truncate block">{email.subject}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {email.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {email.risk_tier ? (
                          <>
                            <div className={`h-2 w-2 rounded-full ${tierColor[email.risk_tier] ?? "bg-muted"}`} />
                            <span className={`text-xs font-medium ${tierColor[email.risk_tier] ?? "text-muted-foreground"}`}>
                              {email.risk_tier}
                            </span>
                          </>
                        ) : (
                          <span className="text-xs text-muted-foreground">Pending</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground">
                        {email.risk_score !== undefined ? email.risk_score : "-"}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
                {!filteredEmails.length && !loading && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-sm text-muted-foreground">
                      No emails found for this filter.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
