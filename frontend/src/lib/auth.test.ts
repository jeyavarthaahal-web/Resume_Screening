import { describe, expect, it } from 'vitest'
import { routeForAccountType } from './auth'

describe('routeForAccountType', () => {
  it('starts recruiters in the recruiter workspace', () => {
    expect(routeForAccountType('recruiter')).toBe('/dashboard')
  })

  it('starts job seekers at resume upload and review', () => {
    expect(routeForAccountType('job_seeker')).toBe('/resumes/upload')
  })

  it('does not route accounts without a recognized role', () => {
    expect(routeForAccountType(null)).toBeNull()
  })
})