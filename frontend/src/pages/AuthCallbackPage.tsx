import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { AuthError } from '../components/common/AuthError'
import { LoadingScreen } from '../components/common/LoadingScreen'
import { useAuth } from '../hooks/useAuth'
import { routeForAccountType } from '../lib/auth'
import { getSupabaseClient } from '../lib/supabase'
import { getCurrentProfile } from '../services/profileService'
import type { Profile } from '../types/profile'

export default function AuthCallbackPage() {
  const { session, user, loading, configurationError } = useAuth()
  const location = useLocation()
  const [callbackError, setCallbackError] = useState<string | null>(null)
  const [callbackProfile, setCallbackProfile] = useState<Profile | null>(null)
  const metadataProcessed = useRef(false)

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const description = params.get('error_description') ?? params.get('error')
    if (description) setCallbackError('The identity provider could not complete sign-in. Check that it is enabled and that its callback URL is configured in Supabase.')
  }, [location.search])

  useEffect(() => {
    if (!loading && !session) window.sessionStorage.removeItem('talentiq.pending-signup-metadata')
  }, [loading, session])

  useEffect(() => {
    if (loading || !session || !user || metadataProcessed.current) return
    metadataProcessed.current = true
    const pending = window.sessionStorage.getItem('talentiq.pending-signup-metadata')
    void (async () => {
      try {
        if (pending) {
          const metadata = JSON.parse(pending) as {
          account_type: 'recruiter' | 'job_seeker'
          full_name: string
          company_name: string | null
          company_size: string | null
          terms_accepted: boolean
          gdpr_consent: boolean
          }
          if (!metadata || !['recruiter', 'job_seeker'].includes(metadata.account_type)) throw new Error('Invalid signup details.')
          const { error } = await getSupabaseClient().auth.updateUser({ data: metadata })
          window.sessionStorage.removeItem('talentiq.pending-signup-metadata')
          if (error) throw new Error('Your provider signed you in, but TalentIQ could not save your signup details. Please contact support.')
        }
        setCallbackProfile(await getCurrentProfile())
      } catch {
        window.sessionStorage.removeItem('talentiq.pending-signup-metadata')
        setCallbackError('We could not complete account setup after provider sign-in. Please try again or contact support.')
      }
    })()
  }, [loading, session, user])

  if (loading) return <LoadingScreen label="Completing secure sign-in…"/>
  if (session && user && callbackProfile) {
    const destination = routeForAccountType(callbackProfile.account_type)
    if (destination) return <Navigate to={destination} replace/>
    return <main className="auth-page"><section className="auth-card"><AuthError message="Your profile does not contain a supported account type. Please contact support."/><div className="auth-foot"><Link to="/login">Return to sign in</Link></div></section></main>
  }
  if (session && !callbackError) return <LoadingScreen label="Preparing your TalentIQ account…"/>
  return <main className="auth-page"><section className="auth-card"><div className="eyebrow">SIGN-IN NOT COMPLETED</div><h1>We couldn’t finish signing you in.</h1><p>{callbackError ?? configurationError ?? 'No authenticated Supabase session was received. Confirm the provider setup and try again.'}</p><div className="auth-foot"><Link to="/login">Return to sign in</Link></div></section></main>
}
