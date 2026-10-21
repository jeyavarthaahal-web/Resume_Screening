import { getSupabaseClient } from '../lib/supabase'
import type { Profile, ProfileUpdate } from '../types/profile'

const profileColumns = 'id,full_name,email,account_type,company_name,company_size,avatar_url,phone,location,bio,terms_accepted,gdpr_consent,created_at,updated_at'

export async function getCurrentProfile(): Promise<Profile> {
  const client = getSupabaseClient()
  const { data: authData, error: authError } = await client.auth.getUser()
  if (authError) throw authError
  if (!authData.user) throw new Error('You need to be signed in to load your profile.')

  const { data, error } = await client
    .from('profiles')
    .select(profileColumns)
    .eq('id', authData.user.id)
    .maybeSingle()
  if (error) throw error
  if (!data) throw new Error('Your profile is not available yet. Try again shortly or contact support.')
  return data as Profile
}

export async function updateCurrentProfile(updates: ProfileUpdate): Promise<Profile> {
  const client = getSupabaseClient()
  const { data: authData, error: authError } = await client.auth.getUser()
  if (authError) throw authError
  if (!authData.user) throw new Error('You need to be signed in to update your profile.')

  const { data, error } = await client
    .from('profiles')
    .update(updates)
    .eq('id', authData.user.id)
    .select(profileColumns)
    .single()
  if (error) throw error
  return data as Profile
}
