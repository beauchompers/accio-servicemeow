import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { ReactNode } from 'react'
import type { User, TokenResponse } from '@/types'
import {
  apiClient,
  setTokens,
  clearTokens,
  getAccessToken,
  setAuthFailureHandler,
} from '@/api/client'

// ─── Types ──────────────────────────────────────────────────────────────────

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

// ─── Context ────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// ─── Provider ───────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = useCallback(() => {
    // Call server-side logout to clear the httpOnly refresh cookie.
    fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'same-origin' }).finally(() => {
      clearTokens()
      setUser(null)
      window.location.href = '/login'
    })
  }, [])

  // Register the auth-failure handler so the API client can trigger logout
  // when token refresh fails.
  useEffect(() => {
    setAuthFailureHandler(() => logout())
  }, [logout])

  // On mount, attempt to restore the session. If no access token is in memory
  // (e.g. after a page refresh), try the refresh endpoint — the httpOnly
  // cookie will be sent automatically by the browser.
  useEffect(() => {
    async function init() {
      let token = getAccessToken()

      // No in-memory token — try to obtain one via the refresh cookie.
      if (!token) {
        try {
          const res = await fetch('/api/v1/auth/refresh', {
            method: 'POST',
            credentials: 'same-origin',
          })
          if (res.ok) {
            const data = await res.json()
            setTokens(data.access_token)
            token = data.access_token
          }
        } catch {
          // Refresh failed — user needs to log in.
        }
      }

      if (token) {
        try {
          const me = await apiClient<User>('/api/v1/users/me')
          setUser(me)
        } catch {
          // Token is invalid or expired and refresh also failed — start fresh.
          clearTokens()
        }
      }
      setIsLoading(false)
    }
    init()
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const tokenResponse = await apiClient<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })

    setTokens(tokenResponse.access_token)

    const me = await apiClient<User>('/api/v1/users/me')
    setUser(me)
  }, [])

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// ─── Hook ───────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
