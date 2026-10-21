import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { AuthError, Provider, Session, User } from '@supabase/supabase-js'
import { getSupabaseClient, setRememberMe } from '../lib/supabase'

type AuthResult = { error: Error | null; hasSession?: boolean; needsEmailConfirmation?: boolean; user?: User | null }
type SignupMetadata = {
  account_type: 'recruiter' | 'job_seeker'
  full_name: string
  company_name: string | null
  company_size: string | null
  terms_accepted: boolean
  gdpr_consent: boolean
}
type AuthContextValue = {
  session: Session | null
  user: User | null
  loading: boolean
  configurationError: string | null
  signIn: (email: string, password: string, remember: boolean) => Promise<AuthResult>
  signUp: (email: string, password: string, metadata: SignupMetadata) => Promise<AuthResult>
  signOut: () => Promise<AuthResult>
  resetPassword: (email: string) => Promise<AuthResult>
  updatePassword: (password: string) => Promise<AuthResult>
  signInWithProvider: (provider: Provider, signupMetadata?: SignupMetadata, remember?: boolean) => Promise<AuthResult>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function errorFrom(error: unknown): Error | null {
  return error instanceof Error ? error : error ? new Error('Authentication failed. Please try again.') : null
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [clientReady, setClientReady] = useState(false)
  const [configurationError, setConfigurationError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    let unsubscribe: (() => void) | undefined
    try {
      const client = getSupabaseClient()
      setClientReady(true)
      const { data } = client.auth.onAuthStateChange((_event, nextSession) => {
        if (active) {
          setSession(nextSession)
          setLoading(false)
        }
      })
      unsubscribe = () => data.subscription.unsubscribe()
      void client.auth.getSession().then(({ data: result }) => {
        if (!active) return
        // A stale or expired session is an auth-state result, not a missing-config error.
        setSession(result.session)
        setLoading(false)
      }).catch(() => {
        if (active) {
          setLoading(false)
        }
      })
    } catch (error) {
      setConfigurationError(errorFrom(error)?.message ?? 'Supabase is not configured.')
      setLoading(false)
    }
    return () => {
      active = false
      unsubscribe?.()
    }
  }, [])

  const requireClient = useCallback(() => {
    if (clientReady) return getSupabaseClient()
    throw new Error(configurationError ?? 'Supabase is not configured. Set the frontend environment variables and restart Vite.')
  }, [clientReady, configurationError])

  const signIn = useCallback(async (email: string, password: string, remember: boolean): Promise<AuthResult> => {
    try {
      setRememberMe(remember)
      const { data, error } = await requireClient().auth.signInWithPassword({ email, password })
      if (error) return { error: error as AuthError }
      setSession(data.session as Session | null)
      return { error: null, hasSession: Boolean(data.session), user: data.user }
    } catch (error) { return { error: errorFrom(error) } }
  }, [requireClient])

  const signUp = useCallback(async (email: string, password: string, metadata: SignupMetadata): Promise<AuthResult> => {
    try {
      setRememberMe(true)
      const { data, error } = await requireClient().auth.signUp({
        email,
        password,
        options: { data: metadata, emailRedirectTo: `${window.location.origin}/auth/callback` },
      })
      if (error) return { error: error as AuthError }
      setSession(data.session as Session | null)
      return { error: null, hasSession: Boolean(data.session), needsEmailConfirmation: Boolean(data.user && !data.session), user: data.user }
    } catch (error) { return { error: errorFrom(error) } }
  }, [requireClient])

  const signOut = useCallback(async (): Promise<AuthResult> => {
    try {
      const { error } = await requireClient().auth.signOut()
      if (!error) {
        setRememberMe(true)
        setSession(null)
      }
      return { error: error as AuthError | null }
    } catch (error) { return { error: errorFrom(error) } }
  }, [requireClient])

  const resetPassword = useCallback(async (email: string): Promise<AuthResult> => {
    try {
      const { error } = await requireClient().auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      })
      return { error: error as AuthError | null }
    } catch (error) { return { error: errorFrom(error) } }
  }, [requireClient])

  const updatePassword = useCallback(async (password: string): Promise<AuthResult> => {
    try {
      const { error } = await requireClient().auth.updateUser({ password })
      return { error: error as AuthError | null }
    } catch (error) { return { error: errorFrom(error) } }
  }, [requireClient])

  const signInWithProvider = useCallback(async (provider: Provider, signupMetadata?: SignupMetadata, remember?: boolean): Promise<AuthResult> => {
    try {
      if (remember !== undefined) setRememberMe(remember)
      else if (signupMetadata) setRememberMe(true)
      if (signupMetadata) window.sessionStorage.setItem('talentiq.pending-signup-metadata', JSON.stringify(signupMetadata))
      else window.sessionStorage.removeItem('talentiq.pending-signup-metadata')
      const result = await requireClient().auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
          ...(provider === 'azure' ? { scopes: 'email' } : {}),
        },
      } as any)
      const { data, error } = result as { data?: { session?: Session | null; user?: User | null }; error?: AuthError | null }
      if (error) {
        window.sessionStorage.removeItem('talentiq.pending-signup-metadata')
        return { error: error as AuthError | null }
      }
      setSession((data?.session ?? null) as Session | null)
      return { error: null, hasSession: Boolean(data?.session), user: data?.user ?? null }
    } catch (error) {
      window.sessionStorage.removeItem('talentiq.pending-signup-metadata')
      return { error: errorFrom(error) }
    }
  }, [requireClient])

  const value = useMemo<AuthContextValue>(() => ({
    session,
    user: session?.user ?? null,
    loading,
    configurationError,
    signIn,
    signUp,
    signOut,
    resetPassword,
    updatePassword,
    signInWithProvider,
  }), [session, loading, configurationError, signIn, signUp, signOut, resetPassword, updatePassword, signInWithProvider])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider.')
  return context
}
