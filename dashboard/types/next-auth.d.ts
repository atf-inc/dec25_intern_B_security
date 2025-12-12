import { DefaultSession, DefaultUser } from "next-auth"
import { JWT, DefaultJWT } from "next-auth/jwt"

declare module "next-auth" {
    interface Session extends DefaultSession {
        accessToken?: string
        refreshToken?: string
        expiresAt?: number
    }

    interface User extends DefaultUser {
        // Add custom user properties here if needed
    }
}

declare module "next-auth/jwt" {
    interface JWT extends DefaultJWT {
        accessToken?: string
        refreshToken?: string
        expiresAt?: number
    }
}
