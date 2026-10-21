import type { AccountType } from '../types/profile'

export type { AccountType } from '../types/profile'

export function routeForAccountType(role: AccountType | null): string | null {
  if (role === 'recruiter') return '/dashboard'
  if (role === 'job_seeker') return '/resumes/upload'
  return null
}
