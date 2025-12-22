import { signIn } from "@/auth"
import { Shield, Mail, Lock, CheckCircle } from "lucide-react"
import Link from "next/link"
import "@/styles/landing.css"

export default function SignIn() {
    return (
        <div className="landing min-h-screen flex">
            {/* Left Panel - Branding */}
            <div className="hidden lg:flex lg:w-1/2 bg-gray-50 flex-col justify-between p-12">
                <div>
                    <Link href="/" className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-lg bg-black flex items-center justify-center">
                            <Shield className="h-6 w-6 text-white" />
                        </div>
                        <span className="text-xl font-semibold text-black">MailShieldAI</span>
                    </Link>
                </div>

                <div className="max-w-md">
                    <h1 className="landing-headline text-4xl mb-6">
                        Protect your inbox<br />with AI-powered security
                    </h1>
                    <ul className="space-y-4 text-gray-600">
                        <li className="flex items-center gap-3">
                            <CheckCircle className="h-5 w-5 text-green-600" />
                            <span>Real-time threat detection</span>
                        </li>
                        <li className="flex items-center gap-3">
                            <CheckCircle className="h-5 w-5 text-green-600" />
                            <span>SPF/DKIM/DMARC verification</span>
                        </li>
                        <li className="flex items-center gap-3">
                            <CheckCircle className="h-5 w-5 text-green-600" />
                            <span>URL sandbox analysis</span>
                        </li>
                        <li className="flex items-center gap-3">
                            <CheckCircle className="h-5 w-5 text-green-600" />
                            <span>Color-coded risk scores</span>
                        </li>
                    </ul>
                </div>

                <div className="text-sm text-gray-500">
                    © {new Date().getFullYear()} MailShieldAI
                </div>
            </div>

            {/* Right Panel - Sign In */}
            <div className="flex-1 flex items-center justify-center p-8">
                <div className="w-full max-w-md">
                    {/* Mobile Logo */}
                    <div className="lg:hidden mb-8 flex justify-center">
                        <Link href="/" className="flex items-center gap-2">
                            <div className="w-10 h-10 rounded-lg bg-black flex items-center justify-center">
                                <Shield className="h-6 w-6 text-white" />
                            </div>
                            <span className="text-xl font-semibold text-black">MailShieldAI</span>
                        </Link>
                    </div>

                    <div className="text-center mb-8">
                        <h2 className="landing-headline text-2xl mb-2">Welcome back</h2>
                        <p className="text-gray-600 text-sm">Sign in to access your protected inbox</p>
                    </div>

                    <form
                        action={async () => {
                            "use server"
                            await signIn("google", { redirectTo: "/dashboard" })
                        }}
                        className="space-y-4"
                    >
                        <button
                            type="submit"
                            className="w-full flex items-center justify-center gap-3 px-6 py-3 bg-white border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 hover:border-gray-400 transition-all"
                        >
                            <svg className="w-5 h-5" viewBox="0 0 24 24">
                                <path
                                    fill="#4285F4"
                                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                                />
                                <path
                                    fill="#34A853"
                                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                                />
                                <path
                                    fill="#FBBC05"
                                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                                />
                                <path
                                    fill="#EA4335"
                                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                                />
                            </svg>
                            Continue with Google
                        </button>
                    </form>

                    <div className="mt-6 text-center">
                        <p className="text-xs text-gray-500">
                            We'll request permission to read and manage your Gmail<br />to provide AI-powered email security
                        </p>
                    </div>

                    <div className="mt-8 pt-6 border-t border-gray-200 flex items-center justify-center gap-6 text-sm text-gray-500">
                        <div className="flex items-center gap-2">
                            <Lock className="h-4 w-4" />
                            <span>Secure</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Mail className="h-4 w-4" />
                            <span>Gmail Only</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
