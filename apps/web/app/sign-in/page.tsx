import { signIn } from "@/auth"
import { Button } from "@/components/ui/button"

export default function SignIn() {
    return (
        <div className="flex h-screen items-center justify-center">
            <form
                action={async () => {
                    "use server"
                    await signIn("google", { redirectTo: "/" })
                }}
            >
                <Button type="submit">Sign in with Google</Button>
            </form>
        </div>
    )
}
