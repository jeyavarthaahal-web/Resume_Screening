import { ArrowLeft, ArrowRight, KeyRound } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AuthError, friendlyAuthError } from '../components/common/AuthError'
import { Brand } from '../components/common/Brand'
import { PasswordInput } from '../components/ui/PasswordInput'
import { useAuth } from '../hooks/useAuth'

export default function ResetPasswordPage() {
  const { session, updatePassword, configurationError } = useAuth()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (password.length < 8) return setError('Your password must be at least 8 characters long.')
    if (password !== confirm) return setError('Your passwords do not match.')
    setBusy(true)
    const result = await updatePassword(password)
    setBusy(false)
    if (result.error) setError(friendlyAuthError(result.error))
    else setDone(true)
  }

  return <main className="auth-page"><div className="auth-top"><Brand/><Link to="/login" className="back-link"><ArrowLeft size={15}/> Back to login</Link></div><div className="auth-card auth-card-expanded"><div className="auth-mark"><KeyRound size={19}/></div><div className="eyebrow">PASSWORD RESET</div><h1>{done ? 'Password updated.' : 'Choose a new password.'}</h1><p>{done ? 'Your password was updated with Supabase. You can now use it to sign in.' : 'Use at least 8 characters for your new password.'}</p>{done ? <div className="auth-foot"><Link to="/login">Continue to sign in</Link></div> : !session ? <><AuthError message={configurationError ?? 'This reset link is invalid or has expired. Request a new link to continue.'}/><div className="auth-foot"><Link to="/forgot-password">Request another reset link</Link></div></> : <form onSubmit={event => void submit(event)}><PasswordInput id="new-password" label="New password" name="new-password" placeholder="At least 8 characters" required minLength={8} value={password} onChange={event => setPassword(event.target.value)}/><PasswordInput id="confirm-new-password" label="Confirm new password" name="confirm-new-password" placeholder="Enter your new password again" required minLength={8} value={confirm} onChange={event => setConfirm(event.target.value)}/>{(error || configurationError) && <AuthError message={error ?? configurationError!}/>}<button className="button button-dark form-submit" type="submit" disabled={busy || Boolean(configurationError)}>{busy ? 'Updating password…' : 'Update password'} <ArrowRight size={17}/></button></form>}</div><div className="auth-bottom">Thoughtful hiring starts here <span>✳</span></div></main>
}
