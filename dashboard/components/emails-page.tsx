"use client"

import { useEffect, useState, useCallback } from "react"
import { useSession } from "next-auth/react"
import { fetchEmails } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Search, Filter, AlertTriangle, Mail, CheckCircle2, XCircle, RefreshCw } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

interface Email {
  id: string
  subject: string
  sender: string
  date: string
  snippet: string
  status: string
  threat: string | null
  folder: string
}

export function EmailsPage() {
  const { data: session } = useSession()
  const [emails, setEmails] = useState<Email[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadEmails = useCallback(async () => {
    if (!session?.accessToken) {
      setEmails([])
      return
    }

    setLoading(true)
    setError(null)

    try {
      const data = await fetchEmails(session.accessToken)
      setEmails(data.emails || [])
    } catch (err) {
      setError("Failed to fetch emails. Please try again.")
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [session?.accessToken])

  useEffect(() => {
    loadEmails()
  }, [loadEmails])

  // Calculate stats
  const totalScanned = emails.length
  const cleanCount = emails.filter(e => e.status === "clean").length
  const unscannedCount = emails.filter(e => e.status === "Unscanned").length
  const threatsCount = emails.filter(e => e.status === "blocked").length
  const manualCount = emails.filter(e => e.status === "Pending").length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Email Logs</h1>
          <p className="text-muted-foreground">Real-time history from your Gmail Inbox</p>
        </div>
        <Button onClick={loadEmails} disabled={loading} variant="outline" className="gap-2">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {session ? (
        <>
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Scanned</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-foreground">{totalScanned}</div>
                <p className="text-xs text-muted-foreground mt-1">From recent inbox</p>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Clean</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-500">{cleanCount}</div>
                <p className="text-xs text-muted-foreground mt-1">Safe emails</p>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Unscanned</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-500">{unscannedCount}</div>
                <p className="text-xs text-muted-foreground mt-1">Pending analysis</p>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Threats Blocked</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-destructive">{threatsCount}</div>
                <p className="text-xs text-muted-foreground mt-1">Detected threats</p>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Under Review</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-chart-3">{manualCount}</div>
                <p className="text-xs text-muted-foreground mt-1">Pending scan</p>
              </CardContent>
            </Card>
          </div>

          {/* Email Logs Table */}
          <Card className="border-border">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-foreground">Email Activity Log</CardTitle>
                  <CardDescription>Recent emails from your inbox</CardDescription>
                </div>
                {/* ... Filters ... */}
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email ID</TableHead>
                    <TableHead>Sender</TableHead>
                    <TableHead>Subject</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8">
                        Loading emails...
                      </TableCell>
                    </TableRow>
                  ) : error ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8 text-destructive">
                        {error}
                      </TableCell>
                    </TableRow>
                  ) : emails.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                        No emails found.
                      </TableCell>
                    </TableRow>
                  ) : (
                    emails.map((email) => (
                      <TableRow key={email.id} className="cursor-pointer hover:bg-accent/50">
                        <TableCell>
                          <code className="text-xs font-mono text-muted-foreground">{email.id.substring(0, 8)}</code>
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
                          <span className="text-xs text-muted-foreground">{email.date}</span>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card className="bg-muted/50 border-dashed">
          <CardContent className="pt-6 text-center text-muted-foreground">
            Please sign in to view your emails.
          </CardContent>
        </Card>
      )}
    </div>
  )
}
