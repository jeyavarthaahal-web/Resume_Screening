import { ArrowLeft, ArrowRight, Mail } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AuthError, friendlyAuthError } from '../components/common/AuthError'
import { Brand } from '../components/common/Brand'
import { Input } from '../components/ui/Input'
import { useAuth } from '../hooks/useAuth'

export default function ForgotPasswordPage() {
  const { resetPassword, configurationError } = useAuth()
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    const result = await resetPassword(email.trim())
    setBusy(false)
    if (result.error && /user not found|email not found|no user/i.test(result.error.message)) setSent(true)
    else if (result.error) setError(friendlyAuthError(result.error))
    else setSent(true)
  }

  return <main className="auth-page"><div className="auth-top"><Brand/><Link to="/login" className="back-link"><ArrowLeft size={15}/> Back to login</Link></div><div className="auth-card auth-card-expanded"><div className="auth-mark"><Mail size={19}/></div><div className="eyebrow">ACCOUNT RECOVERY</div><h1>{sent ? 'Check your inbox.' : 'Forgot your password?'}</h1><p>{sent ? 'If an account matches that email, a reset link is on its way. Follow the link to choose a new password.' : 'Enter the email you use for TalentIQ and we’ll send you a reset link.'}</p>{!sent && <><form onSubmit={event => void submit(event)}><Input id="recovery-email" label="Work email" type="email" name="email" autoComplete="email" placeholder="you@company.com" required value={email} onChange={event => setEmail(event.target.value)}/>{(error || configurationError) && <AuthError message={error ?? configurationError!}/>}<button className="button button-dark form-submit" type="submit" disabled={busy || Boolean(configurationError)}>{busy ? 'Sending link…' : 'Send reset link'} <ArrowRight size={17}/></button></form></>}<div className="auth-foot"><Link to="/login">Return to sign in</Link></div></div><div className="auth-bottom">Thoughtful hiring starts here <span>✳</span></div></main>
}
