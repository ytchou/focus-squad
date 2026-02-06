/**
 * Simple module-level token cache to avoid race conditions with Supabase session recovery.
 *
 * Problem: When onAuthStateChange fires with INITIAL_SESSION, the session is available
 * in the callback parameter. However, if we immediately call getSession() separately
 * (e.g., in ApiClient), it may return null because Supabase hasn't finished
 * recovering the session from storage.
 *
 * Solution: Cache the token when we receive it in onAuthStateChange, and have ApiClient
 * read from this cache first.
 */

let cachedToken: string | null = null;

export function setAuthToken(token: string | null): void {
  cachedToken = token;
}

export function getAuthToken(): string | null {
  return cachedToken;
}

export function clearAuthToken(): void {
  cachedToken = null;
}
