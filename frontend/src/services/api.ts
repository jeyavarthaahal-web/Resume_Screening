const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path.startsWith('/') ? path : `/${path}`}`, {
    ...init,
    headers: { Accept: 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let message = `Request failed (${response.status}). Please try again.`
    try { const body = await response.json() as { detail?: unknown }; if (typeof body.detail === 'string') message = body.detail } catch { /* keep the safe fallback */ }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = { get: <T>(path: string) => apiRequest<T>(path) }
