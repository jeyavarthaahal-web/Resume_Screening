export type AccountType = 'job_seeker' | 'recruiter'

/** Mirrors the client-visible columns in public.profiles. The internal account_type_locked
 * column is deliberately omitted because the browser must never control that lock. */
export type Profile = {
  id: string
  full_name: string
  email: string | null
  account_type: AccountType
  company_name: string | null
  company_size: string | null
  avatar_url: string | null
  phone: string | null
  location: string | null
  bio: string | null
  terms_accepted: boolean
  gdpr_consent: boolean
  created_at: string
  updated_at: string
}

/** Identity, email, role, and creation metadata are server managed. */
export type ProfileUpdate = Partial<Pick<Profile,
  'full_name' | 'company_name' | 'company_size' | 'avatar_url' | 'phone' | 'location' | 'bio' | 'terms_accepted' | 'gdpr_consent'
>>
