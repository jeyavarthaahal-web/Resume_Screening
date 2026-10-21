import { useState } from 'react'
import type { Provider } from '@supabase/supabase-js'
import { AuthError, friendlyAuthError } from './AuthError'
import { useAuth } from '../../hooks/useAuth'
import type { AccountType } from '../../lib/auth'

type SignupMetadata = { account_type: AccountType; full_name: string; company_name: string | null; company_size: string | null; terms_accepted: boolean; gdpr_consent: boolean }

const providers: { id: Provider; label: string; mark: string; className: string }[] = [
  { id: 'google', label: 'Google', mark: 'G', className: 'google-mark' },
  { id: 'linkedin_oidc', label: 'LinkedIn', mark: 'in', className: 'linkedin-mark' },
  { id: 'azure', label: 'Microsoft', mark: '▦', className: 'microsoft-mark' },
]

export function SocialAuthButtons({ signupMetadata, validateSignup, remember }: { signupMetadata?: SignupMetadata; validateSignup?: () => string | null; remember?: boolean }) {
  const { signInWithProvider, configurationError } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<Provider | null>(null)

  async function start(provider: Provider) {
    setError(null)
    const validationError = validateSignup?.()
    if (validationError) return setError(validationError)
    setBusy(provider)
    const result = await signInWithProvider(provider, signupMetadata, remember)
    setBusy(null)
    if (result.error) setError(friendlyAuthError(result.error))
  }

  return <div className="social-auth"><div className="auth-divider"><span>or continue with</span></div><div className="social-auth-grid">{providers.map(provider => <button className="social-auth-button" type="button" key={provider.id} onClick={() => void start(provider.id)} disabled={Boolean(busy) || Boolean(configurationError)}><span className={provider.className} aria-hidden="true">{provider.mark}</span>{busy === provider.id ? 'Connecting…' : provider.label}</button>)}</div>{error && <AuthError message={error}/>}</div>
}
