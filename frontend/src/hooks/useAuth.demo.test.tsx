import '@testing-library/jest-dom/vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from './useAuth'

describe('auth fallback demo mode', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.stubEnv('VITE_SUPABASE_URL', '')
    vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', '')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('creates a working local account when Supabase is not configured', async () => {
    const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let signupResult: Awaited<ReturnType<typeof result.current.signUp>> | undefined

    await act(async () => {
      signupResult = await result.current.signUp('demo@example.com', 'Password123', {
        account_type: 'job_seeker',
        full_name: 'Demo User',
        company_name: null,
        company_size: null,
        terms_accepted: true,
        gdpr_consent: true,
      })
    })

    expect(signupResult?.error).toBeNull()
    expect(signupResult?.hasSession).toBe(true)
    expect(signupResult?.user).not.toBeNull()
    expect(result.current.session).not.toBeNull()
  })
})
