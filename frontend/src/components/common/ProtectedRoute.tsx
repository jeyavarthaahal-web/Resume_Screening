import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { useProfile } from '../../hooks/useProfile'
import { LoadingScreen } from './LoadingScreen'
import { routeForAccountType, type AccountType } from '../../lib/auth'

export function ProtectedRoute({ children, requiredRole }: { children: ReactNode; requiredRole: AccountType }) {
  const { session, user, loading: authLoading } = useAuth()
  const { accountType, loading: profileLoading, error } = useProfile()
  const location = useLocation()
  if (authLoading) return <LoadingScreen/>
  if (!session || !user) return <Navigate to="/login" replace state={{ from: location.pathname }}/>
  if (profileLoading) return <LoadingScreen label="Loading your profile…"/>
  if (error) return <ProfileUnavailable message={error}/>
  const role = accountType
  if (!role) return <UnresolvedRole/>
  if (role !== requiredRole) return <Navigate to={routeForAccountType(role)!} replace/>
  return children
}

export function GuestOnly({ children }: { children: ReactNode }) {
  const { session, user, loading: authLoading } = useAuth()
  const { accountType, loading: profileLoading, error } = useProfile()
  if (authLoading) return <LoadingScreen/>
  if (session && user && profileLoading) return <LoadingScreen label="Loading your profile…"/>
  if (session && user) {
    if (error) return <ProfileUnavailable message={error}/>
    const destination = routeForAccountType(accountType)
    if (destination) return <Navigate to={destination} replace/>
    return <UnresolvedRole/>
  }
  return children
}

function UnresolvedRole() {
  const { signOut } = useAuth()
  return <main className="auth-page"><section className="auth-card"><div className="eyebrow">ACCOUNT SETUP</div><h1>We couldn’t identify your account type.</h1><p>Your Supabase profile does not yet contain a supported account type. Sign out and contact your workspace administrator.</p><button className="button button-dark form-submit" onClick={() => void signOut()}>Sign out</button></section></main>
}

function ProfileUnavailable({ message }: { message: string }) {
  const { signOut } = useAuth()
  return <main className="auth-page"><section className="auth-card"><div className="eyebrow">PROFILE UNAVAILABLE</div><h1>We couldn’t load your profile.</h1><p>{message}</p><button className="button button-dark form-submit" onClick={() => void signOut()}>Sign out</button></section></main>
}
