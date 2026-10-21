import { ArrowLeft, ArrowRight, Check, Sparkles } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthError, friendlyAuthError } from '../components/common/AuthError'
import { Brand } from '../components/common/Brand'
import { SocialAuthButtons } from '../components/common/SocialAuthButtons'
import { Checkbox } from '../components/ui/Checkbox'
import { Input } from '../components/ui/Input'
import { PasswordInput } from '../components/ui/PasswordInput'
import { useAuth } from '../hooks/useAuth'
import { routeForAccountType, type AccountType } from '../lib/auth'
import { getCurrentProfile } from '../services/profileService'

const companySizes = ['1-10', '11-50', '51-200', '201-500', '501-1000', '1000+']

export default function SignupPage() {
  const { signUp, user, configurationError } = useAuth()
  const navigate = useNavigate()
  const [accountType, setAccountType] = useState<AccountType | ''>('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [companySize, setCompanySize] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [gdprConsent, setGdprConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmation, setConfirmation] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (!accountType) return setError('Choose whether you are joining as a job seeker or recruiter.')
    if (password.length < 8) return setError('Your password must be at least 8 characters long.')
    if (password !== confirmPassword) return setError('Your passwords do not match.')
    if (accountType === 'recruiter' && (!companyName.trim() || !companySize)) return setError('Add your company name and company size to continue.')
    if (!termsAccepted) return setError('Please accept the Terms of Service and Privacy Policy to continue.')
    if (!gdprConsent) return setError('Please provide the requested consent to process your data.')

    setBusy(true)
    const result = await signUp(email.trim(), password, {
      account_type: accountType,
      full_name: fullName.trim(),
      company_name: accountType === 'recruiter' ? companyName.trim() : null,
      company_size: accountType === 'recruiter' ? companySize : null,
      terms_accepted: termsAccepted,
      gdpr_consent: gdprConsent,
    })
    setBusy(false)
    if (result.error) return setError(friendlyAuthError(result.error))
    if (result.needsEmailConfirmation) {
      setConfirmation(true)
      return
    }
    const authenticatedUser = result.user ?? user
    let destination: string | null = null
    if (result.hasSession && authenticatedUser) {
      try { destination = routeForAccountType((await getCurrentProfile()).account_type) }
      catch (profileError) {
        setError(profileError instanceof Error ? profileError.message : 'Your profile could not be loaded. Please try again.')
        return
      }
    }
    if (destination) navigate(destination, { replace: true })
    else setError('Supabase did not create a session. Check your email for a confirmation link or try signing in.')
  }

  function validateSocialSignup(): string | null {
    if (!accountType) return 'Choose an account type before continuing with a provider.'
    if (!fullName.trim()) return 'Enter your full name before continuing with a provider.'
    if (accountType === 'recruiter' && (!companyName.trim() || !companySize)) return 'Add your company name and size before continuing.'
    if (!termsAccepted) return 'Please accept the Terms of Service and Privacy Policy to continue.'
    if (!gdprConsent) return 'Please provide the requested data-processing consent to continue.'
    return null
  }

  const oauthMetadata = accountType ? {
    account_type: accountType,
    full_name: fullName.trim(),
    company_name: accountType === 'recruiter' ? companyName.trim() : null,
    company_size: accountType === 'recruiter' ? companySize : null,
    terms_accepted: termsAccepted,
    gdpr_consent: gdprConsent,
  } : undefined

  return <main className="auth-page"><div className="auth-top"><Brand/><Link to="/" className="back-link"><ArrowLeft size={15}/> Back to home</Link></div><div className="auth-card auth-card-expanded signup-card"><div className="auth-mark"><Sparkles size={20}/></div><div className="eyebrow">A MORE THOUGHTFUL WORKFLOW</div><h1>Create your account.</h1><p>Tell us a little about how you’ll use TalentIQ.</p>{confirmation ? <><AuthError kind="success" message="Check your inbox for a confirmation link. Your account will be ready after you confirm your email."/><div className="auth-foot"><Link to="/login">Return to sign in</Link></div></> : <><form onSubmit={event => void submit(event)}><fieldset className="account-types"><legend>Account type</legend><label className={accountType === 'job_seeker' ? 'account-choice selected' : 'account-choice'}><input type="radio" name="account-type" value="job_seeker" required checked={accountType === 'job_seeker'} onChange={() => setAccountType('job_seeker')}/><span><strong>Job Seeker</strong><small>Explore your next opportunity</small></span>{accountType === 'job_seeker' && <Check size={16}/>}</label><label className={accountType === 'recruiter' ? 'account-choice selected' : 'account-choice'}><input type="radio" name="account-type" value="recruiter" required checked={accountType === 'recruiter'} onChange={() => setAccountType('recruiter')}/><span><strong>Recruiter</strong><small>Find your next great hire</small></span>{accountType === 'recruiter' && <Check size={16}/>}</label></fieldset><Input id="signup-name" label="Full name" type="text" name="full_name" autoComplete="name" placeholder="Jordan Davis" required minLength={2} value={fullName} onChange={event => setFullName(event.target.value)}/><Input id="signup-email" label="Email" type="email" name="email" autoComplete="email" placeholder="you@company.com" required value={email} onChange={event => setEmail(event.target.value)}/>{accountType === 'recruiter' && <div className="company-fields"><Input id="company-name" label="Company name" name="company_name" autoComplete="organization" placeholder="Your company" required value={companyName} onChange={event => setCompanyName(event.target.value)}/><div className="field"><label htmlFor="company-size">Company size</label><select id="company-size" name="company_size" required value={companySize} onChange={event => setCompanySize(event.target.value)}><option value="" disabled>Select company size</option>{companySizes.map(size => <option value={size} key={size}>{size}</option>)}</select></div></div>}<PasswordInput id="signup-password" label="Password" name="new-password" autoComplete="new-password" placeholder="At least 8 characters" required minLength={8} value={password} onChange={event => setPassword(event.target.value)}/><PasswordInput id="signup-confirm" label="Confirm password" name="confirm-password" placeholder="Enter your password again" required minLength={8} value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)}/><div className="consent-list"><Checkbox id="terms-accepted" required checked={termsAccepted} onChange={event => setTermsAccepted(event.target.checked)}>I agree to TalentIQ’s Terms of Service and Privacy Policy.</Checkbox><Checkbox id="gdpr-consent" required checked={gdprConsent} onChange={event => setGdprConsent(event.target.checked)}>I consent to the processing of my personal data as described in the Privacy Policy.</Checkbox><small>Consent is recorded as account metadata; it does not by itself establish GDPR compliance.</small></div>{error && <AuthError message={error}/>} {configurationError && <AuthError message={configurationError}/>}<button className="button button-dark form-submit" type="submit" disabled={busy || Boolean(configurationError)}>{busy ? 'Creating account…' : 'Create account'} <ArrowRight size={17}/></button></form><SocialAuthButtons signupMetadata={oauthMetadata} validateSignup={validateSocialSignup}/><div className="auth-foot">Already have an account? <Link to="/login">Sign in</Link></div></>}</div><div className="auth-bottom">Thoughtful hiring starts here <span>✳</span></div></main>
}
