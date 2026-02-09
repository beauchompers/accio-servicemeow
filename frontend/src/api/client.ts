// ─── Token state ─────────────────────────────────────────────────────────────
//
// Only the access token is stored in memory. The refresh token lives as an
// httpOnly cookie set by the backend — the browser sends it automatically.

let accessToken: string | null = null
let onAuthFailure: (() => void) | null = null

/**
 * Store the access token (typically after login or token refresh).
 * The refresh token is managed as an httpOnly cookie by the backend.
 */
export function setTokens(access: string): void {
  accessToken = access
}

/**
 * Clear the stored access token (typically on logout or auth failure).
 */
export function clearTokens(): void {
  accessToken = null
}

/**
 * Return the current access token, or null if not authenticated.
 */
export function getAccessToken(): string | null {
  return accessToken
}

/**
 * Register a callback invoked when authentication cannot be recovered
 * (e.g. refresh token is also expired). Typically used to redirect to login.
 */
export function setAuthFailureHandler(handler: () => void): void {
  onAuthFailure = handler
}

// ─── Token refresh ───────────────────────────────────────────────────────────

async function refreshAccessToken(): Promise<boolean> {
  try {
    // The refresh token is sent automatically as an httpOnly cookie.
    const res = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      credentials: 'same-origin',
    })

    if (!res.ok) {
      return false
    }

    const data = await res.json()
    setTokens(data.access_token)
    return true
  } catch {
    return false
  }
}

// ─── Public API client ───────────────────────────────────────────────────────

export interface ApiError {
  status: number
  detail: string
}

/**
 * Generic fetch wrapper with automatic JWT injection and token refresh.
 *
 * 1. Attaches `Authorization: Bearer <token>` when a token is available.
 * 2. Sets `Content-Type: application/json` unless the body is FormData.
 * 3. On a 401 response, attempts a single token refresh and retries.
 * 4. If the retry also fails with 401, clears tokens and invokes the
 *    registered auth-failure handler before throwing.
 * 5. Non-ok responses are thrown as `ApiError` with status and detail.
 * 6. 204 No Content responses return `undefined` cast to `T`.
 * 7. All other responses are parsed as JSON and returned as `T`.
 */
export async function apiClient<T>(
  url: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)

  // Attach bearer token
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  // Set JSON content-type unless the body is FormData (let the browser set
  // the multipart boundary automatically).
  if (!(options.body instanceof FormData)) {
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }
  }

  let res = await fetch(url, { ...options, headers })

  // On 401, attempt a single token refresh then retry
  if (res.status === 401) {
    const refreshed = await refreshAccessToken()

    if (refreshed) {
      headers.set('Authorization', `Bearer ${accessToken}`)
      res = await fetch(url, { ...options, headers })
    }

    if (!refreshed || res.status === 401) {
      clearTokens()
      onAuthFailure?.()

      const error: ApiError = { status: 401, detail: 'Authentication failed' }
      throw error
    }
  }

  // Handle non-ok responses
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') {
        detail = body.detail
      } else if (Array.isArray(body.detail)) {
        detail = body.detail.map((e: { msg?: string }) => e.msg ?? '').join('; ')
      }
    } catch {
      // body was not JSON; keep statusText
    }

    const error: ApiError = { status: res.status, detail }
    throw error
  }

  // 204 No Content
  if (res.status === 204) {
    return undefined as T
  }

  return res.json() as Promise<T>
}
