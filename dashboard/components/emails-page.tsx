"use client"

import * as React from "react"
import { useEffect, useMemo, useRef, useState } from "react"

import { useSession } from "next-auth/react"
import { AlertTriangle, CheckCircle, Paperclip, Search, XCircle, RefreshCw } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { type Email, fetchEmails, syncEmails } from "@/lib/api"

const tierColor: Record<string, string> = {
  SAFE: "text-green-500 bg-green-500/10",
  CAUTIOUS: "text-yellow-600 bg-yellow-500/10",
  THREAT: "text-destructive bg-destructive/10",
}

const threatCategoryColor: Record<string, string> = {
  NONE: "text-green-500",
  PHISHING: "text-red-500",
  MALWARE: "text-red-600",
  SPAM: "text-yellow-500",
  BEC: "text-orange-500",
  SPOOFING: "text-red-400",
  SUSPICIOUS: "text-yellow-600",
}

const authStatusIcon = (status: string | undefined) => {
  if (!status) return <span className="text-muted-foreground text-xs">-</span>
  if (status === "PASS") return <CheckCircle className="h-3 w-3 text-green-500" />
  if (status === "FAIL") return <XCircle className="h-3 w-3 text-red-500" />
  return <AlertTriangle className="h-3 w-3 text-yellow-500" />
}

const formatDate = (dateStr: string | undefined) => {
  if (!dateStr) return "-"
  const date = new Date(dateStr)
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function EmailsPage() {
  const { data: session } = useSession()
  const [emails, setEmails] = useState<Email[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>("all")

  // Track sync state to avoid redundant syncs
  const syncedRef = useRef(false)
  const lastTokenRef = useRef<string | null>(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      // If the token hasn't changed, don't re-fetch to avoid flicker on tab switch
      if (session?.idToken && lastTokenRef.current === session.idToken) {
        return
      }
      
      // Only show loading state if we have no data to avoid flash
      if (emails.length === 0) {
        setLoading(true)
      }
      
      setError(null)
      try {
        if (!session?.idToken) {
          // Wait for session to load or redirect handled by middleware
          if (session === null) throw new Error("Not authenticated")
          return
        }

        // Trigger sync only once per session mount
        if (session.accessToken && !syncedRef.current) {
          syncedRef.current = true
          // Fire and forget sync, don't block UI
          syncEmails(session.idToken, session.accessToken).catch(console.error)
        }

        // Fetch emails (uses cache if available)
        const data = await fetchEmails(session.idToken)
        if (active) {
          setEmails(data)
          lastTokenRef.current = session.idToken
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
  }, [session, emails.length])

  // Manual refresh function
  const handleRefresh = async () => {
    if (!session?.idToken || !session?.accessToken) return
    
    setRefreshing(true)
    try {
      // Clear cache and sync fresh data
      await syncEmails(session.idToken, session.accessToken)
      const data = await fetchEmails(session.idToken)
      setEmails(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh emails")
    } finally {
      setRefreshing(false)
    }
  }

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
                  <SelectItem value="SPAM">Spam</SelectItem>
                </SelectContent>
              </Select>
              <Button 
                variant="outline" 
                size="icon"
                onClick={handleRefresh}
                disabled={refreshing}
                title="Refresh emails"
              >
                <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
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
                  <TableHead className="w-[100px]">Time</TableHead>
                  <TableHead>Sender</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Threat</TableHead>
                  <TableHead className="text-center">Score</TableHead>
                  <TableHead className="text-center">Auth</TableHead>
                  <TableHead>Attachments</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEmails.map((email) => (
                  <TableRow key={email.id} className="cursor-pointer hover:bg-accent/50">
                    <TableCell>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDate(email.received_at)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="text-sm text-foreground truncate max-w-[200px]" title={email.sender}>
                          {email.sender}
                        </span>
                        {email.sender_ip && (
                          <span className="text-xs text-muted-foreground font-mono">{email.sender_ip}</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col max-w-[250px]">
                        <span className="text-sm text-foreground truncate" title={email.subject}>
                          {email.subject}
                        </span>
                        {email.detection_reason && (
                          <span className="text-xs text-muted-foreground truncate" title={email.detection_reason}>
                            {email.detection_reason}
                          </span>
                        )}
                      </div>
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
                        ) : email.threat_category && email.threat_category !== "NONE" ? (
                          <span className={`text-xs font-medium ${threatCategoryColor[email.threat_category] ?? "text-muted-foreground"}`}>
                            {email.threat_category}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      {email.risk_score !== undefined && email.risk_score !== null ? (
                        <span className={`text-xs font-medium ${
                          email.risk_score >= 70 ? "text-red-500" :
                          email.risk_score >= 40 ? "text-yellow-500" :
                          "text-green-500"
                        }`}>
                          {email.risk_score}
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-center gap-1" title={`SPF: ${email.spf_status || "N/A"} | DKIM: ${email.dkim_status || "N/A"} | DMARC: ${email.dmarc_status || "N/A"}`}>
                        <span className="flex items-center gap-0.5">
                          <span className="text-[10px] text-muted-foreground">S</span>
                          {authStatusIcon(email.spf_status)}
                        </span>
                        <span className="flex items-center gap-0.5">
                          <span className="text-[10px] text-muted-foreground">D</span>
                          {authStatusIcon(email.dkim_status)}
                        </span>
                        <span className="flex items-center gap-0.5">
                          <span className="text-[10px] text-muted-foreground">M</span>
                          {authStatusIcon(email.dmarc_status)}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {email.attachment_info ? (
                        <div className="flex items-center gap-1" title={email.attachment_info}>
                          <Paperclip className="h-3 w-3 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground truncate max-w-[80px]">
                            {email.attachment_info}
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {email.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
                {!filteredEmails.length && !loading && (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-sm text-muted-foreground">
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
