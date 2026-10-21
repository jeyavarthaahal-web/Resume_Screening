import { ArrowLeft, ArrowRight, Sparkles } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AuthError, friendlyAuthError } from '../components/common/AuthError'
import { Brand } from '../components/common/Brand'
import { SocialAuthButtons } from '../components/common/SocialAuthButtons'
import { Checkbox } from '../components/ui/Checkbox'
import { Input } from '../components/ui/Input'
import { PasswordInput } from '../components/ui/PasswordInput'
import { useAuth } from '../hooks/useAuth'
import { routeForAccountType } from '../lib/auth'
import { getCurrentProfile } from '../services/profileService'

export default function LoginPage() {
  const { signIn, user, configurationError } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    const result = await signIn(email.trim(), password, remember)
    setBusy(false)
    if (result.error) {
      setError(friendlyAuthError(result.error))
      return
    }
    const authenticatedUser = result.user ?? user
    if (!result.hasSession || !authenticatedUser) {
      setError('Supabase did not return a session. Try signing in again.')
      return
    }
    let destination: string | null
    try {
      destination = routeForAccountType((await getCurrentProfile()).account_type)
    } catch (profileError) {
      setError(profileError instanceof Error ? profileError.message : 'Your profile could not be loaded. Please try again.')
      return
    }
    if (!destination) {
      setError('We couldn’t determine your account type. Please contact your workspace administrator.')
      return
    }
    const requested = (location.state as { from?: string } | null)?.from
    navigate(requested === destination ? requested : destination, { replace: true })
  }

  return <main className="auth-page"><div className="auth-top"><Brand/><Link to="/" className="back-link"><ArrowLeft size={15}/> Back to home</Link></div><div className="auth-card auth-card-expanded"><div className="auth-mark"><Sparkles size={20}/></div><div className="eyebrow">WELCOME BACK</div><h1>Good to see you.</h1><p>Sign in to pick up where your team left off.</p>{(error || configurationError) && <AuthError message={error ?? configurationError!}/>}<form onSubmit={submit}><Input id="login-email" label="Work email" type="email" name="email" autoComplete="email" placeholder="you@company.com" required value={email} onChange={event => setEmail(event.target.value)}/><PasswordInput id="login-password" label="Password" name="password" autoComplete="current-password" placeholder="Enter your password" required value={password} onChange={event => setPassword(event.target.value)}/><div className="form-between"><Checkbox id="remember-me" checked={remember} onChange={event => setRemember(event.target.checked)}>Remember me</Checkbox><Link to="/forgot-password">Forgot password?</Link></div><button className="button button-dark form-submit" type="submit" disabled={busy || Boolean(configurationError)}>{busy ? 'Signing in…' : 'Sign in'} <ArrowRight size={17}/></button></form><SocialAuthButtons remember={remember}/><div className="auth-foot">New to TalentIQ? <Link to="/signup">Create an account</Link></div></div><div className="auth-bottom">Thoughtful hiring starts here <span>✳</span></div></main>
}
