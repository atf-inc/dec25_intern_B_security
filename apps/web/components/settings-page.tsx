"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Shield, Bell, Database, User } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useSession } from "next-auth/react"

export function SettingsPage() {
  const { data: session } = useSession()
  const user = session?.user

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground">Manage your account and security preferences</p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="grid w-full max-w-md grid-cols-3">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="space-y-4">
          <Card className="border-border">
            <CardHeader>
              <div className="flex items-center gap-2">
                <User className="h-5 w-5 text-primary" />
                <CardTitle className="text-foreground">Profile Information</CardTitle>
              </div>
              <CardDescription>Your account details from Google</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="user-name">Name</Label>
                <Input id="user-name" defaultValue={user?.name || ""} disabled />
              </div>
              <div className="space-y-2">
                <Label htmlFor="user-email">Email</Label>
                <Input id="user-email" type="email" defaultValue={user?.email || ""} disabled />
              </div>
              <p className="text-xs text-muted-foreground">
                Profile information is managed through your Google account.
              </p>
            </CardContent>
          </Card>

          <Card className="border-border">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-primary" />
                <CardTitle className="text-foreground">Data & Privacy</CardTitle>
              </div>
              <CardDescription>Control data retention and privacy settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="retention">Email Log Retention Period</Label>
                <Input id="retention" defaultValue="90 days" />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">Anonymous Analytics</div>
                  <div className="text-xs text-muted-foreground">Share anonymized threat data to improve detection</div>
                </div>
                <Switch />
              </div>
              <Button>Save Changes</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-4">
          <Card className="border-border">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                <CardTitle className="text-foreground">Security Settings</CardTitle>
              </div>
              <CardDescription>Configure email protection and threat detection</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">Advanced Phishing Detection</div>
                  <div className="text-xs text-muted-foreground">Use AI to detect sophisticated phishing attempts</div>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">Attachment Scanning</div>
                  <div className="text-xs text-muted-foreground">Scan all email attachments for malware</div>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">URL Analysis</div>
                  <div className="text-xs text-muted-foreground">Check links for suspicious destinations</div>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">DMARC Verification</div>
                  <div className="text-xs text-muted-foreground">Verify sender identity using DMARC</div>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">Quarantine Suspicious Emails</div>
                  <div className="text-xs text-muted-foreground">Automatically quarantine detected threats</div>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications" className="space-y-4">
          <Card className="border-border">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bell className="h-5 w-5 text-primary" />
                <CardTitle className="text-foreground">Notification Preferences</CardTitle>
              </div>
              <CardDescription>Choose when and how you receive alerts</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">Threat Alerts</div>
                  <div className="text-xs text-muted-foreground">Get notified when threats are detected</div>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">Weekly Reports</div>
                  <div className="text-xs text-muted-foreground">Receive weekly security summary</div>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <div className="space-y-0.5">
                  <div className="text-sm font-medium text-foreground">System Updates</div>
                  <div className="text-xs text-muted-foreground">Updates about new features and improvements</div>
                </div>
                <Switch />
              </div>
              <Separator />
              <div className="space-y-2">
                <Label htmlFor="email-notif">Notification Email</Label>
                <Input id="email-notif" type="email" defaultValue={user?.email || ""} />
              </div>
              <Button>Save Preferences</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
