import { getSupabaseClient } from '../lib/supabase'
import { apiRequest } from './api'
import type { JobCreateInput, JobProfile, JobRecord } from '../types/job'

export async function authenticatedHeaders(): Promise<HeadersInit> {
  const { data, error } = await getSupabaseClient().auth.getSession()
  if (error || !data.session?.access_token) throw new Error('Your session has expired. Sign in again to manage jobs.')
  return { Authorization: `Bearer ${data.session.access_token}` }
}

export async function analyzeJobDescription(description: string, file?: File): Promise<JobProfile> {
  const form = new FormData()
  if (file) form.append('file', file)
  else form.append('description', description)
  return apiRequest<JobProfile>('/api/jobs/analyze', { method: 'POST', headers: await authenticatedHeaders(), body: form })
}

export async function createJob(input: JobCreateInput): Promise<JobRecord> {
  return apiRequest<JobRecord>('/api/jobs', { method: 'POST', headers: { ...(await authenticatedHeaders()), 'Content-Type': 'application/json' }, body: JSON.stringify(input) })
}

export async function getJobs(): Promise<JobRecord[]> { return apiRequest('/api/jobs', { headers: await authenticatedHeaders() }) }
export async function getJob(jobId: string): Promise<JobRecord> { return apiRequest(`/api/jobs/${encodeURIComponent(jobId)}`, { headers: await authenticatedHeaders() }) }
export async function updateJob(jobId: string, changes: Partial<JobCreateInput>): Promise<JobRecord> {
  return apiRequest(`/api/jobs/${encodeURIComponent(jobId)}`, { method: 'PUT', headers: { ...(await authenticatedHeaders()), 'Content-Type': 'application/json' }, body: JSON.stringify(changes) })
}
export async function deleteJob(jobId: string): Promise<void> {
  const headers = await authenticatedHeaders()
  await apiRequest<void>(`/api/jobs/${encodeURIComponent(jobId)}`, { method: 'DELETE', headers })
}
