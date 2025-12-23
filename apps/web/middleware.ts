import { auth } from "@/auth"

export default auth((req) => {
  const isLandingPage = req.nextUrl.pathname === "/"
  const isSignIn = req.nextUrl.pathname === "/sign-in"
  const isApiRoute = req.nextUrl.pathname.startsWith("/api")
  const isPublicAsset = req.nextUrl.pathname.startsWith("/_next") ||
    req.nextUrl.pathname.startsWith("/favicon") ||
    /\.[^/]+$/.test(req.nextUrl.pathname)

  // Public routes - allow access (including API routes for auth)
  if (isLandingPage || isSignIn || isApiRoute || isPublicAsset) {
    // If authenticated and trying to access sign-in, redirect to dashboard
    if (req.auth && isSignIn) {
      const newUrl = new URL("/dashboard", req.nextUrl.origin)
      return Response.redirect(newUrl)
    }
    return
  }

  // Protected routes - require authentication
  if (!req.auth) {
    const newUrl = new URL("/sign-in", req.nextUrl.origin)
    return Response.redirect(newUrl)
  }
})

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
}
