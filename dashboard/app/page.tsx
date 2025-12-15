"use client"

import { useUser, SignIn } from "@clerk/nextjs"
import { DashboardLayout } from "@/components/dashboard-layout"
import { OverviewPage } from "@/components/overview-page"

export default function Home() {
  const { isLoaded, isSignedIn } = useUser()

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    )
  }

  if (!isSignedIn) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <SignIn />
      </div>
    )
  }

  return (
    <DashboardLayout>
      <OverviewPage />
    </DashboardLayout>
  )
}
