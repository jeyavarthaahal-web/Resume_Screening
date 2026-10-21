import { useEffect, useState } from 'react'
import { useAuth } from './useAuth'
import { getCurrentProfile } from '../services/profileService'
import type { Profile } from '../types/profile'

/** Loads database profile data from the existing auth context; it does not subscribe to auth again. */
export function useProfile() {
  const { user, loading: authLoading } = useAuth()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [profileLoading, setProfileLoading] = useState(true)
  const [profileError, setProfileError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    if (authLoading) {
      setProfileLoading(true)
      return () => { active = false }
    }
    if (!user) {
      setProfile(null)
      setProfileError(null)
      setProfileLoading(false)
      return () => { active = false }
    }

    setProfile(null)
    setProfileError(null)
    setProfileLoading(true)
    void getCurrentProfile().then(nextProfile => {
      if (active) setProfile(nextProfile)
    }).catch(error => {
      if (active) setProfileError(error instanceof Error ? error.message : 'Could not load your profile.')
    }).finally(() => {
      if (active) setProfileLoading(false)
    })
    return () => { active = false }
  }, [authLoading, user?.id])

  return { profile, accountType: profile?.account_type ?? null, loading: authLoading || profileLoading, error: profileError }
}
