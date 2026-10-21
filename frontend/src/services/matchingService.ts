import { apiRequest } from './api'
import { authenticatedHeaders } from './jobService'
import { getSupabaseClient } from '../lib/supabase'
import type { BulkMatchingResponse, MatchingCandidate, MatchingResult, PublishedJobSummary } from '../types/matching'

export async function getPublishedJobs(): Promise<PublishedJobSummary[]> {
  const { data, error } = await getSupabaseClient()
    .from('jobs')
    .select('id,title,department,location,employment_type')
    .eq('status', 'published')
    .order('created_at', { ascending: false })
  if (error) throw new Error('Published jobs could not be loaded. Please try again.')
  return data ?? []
}

export async function applyResumeToJob(jobId: string, resumeId: string): Promise<MatchingCandidate> {
  return apiRequest<MatchingCandidate>(`/api/matching/jobs/${encodeURIComponent(jobId)}/apply`, {
    method: 'POST',
    headers: { ...(await authenticatedHeaders()), 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume_id: resumeId }),
  })
}

export async function matchResumeToJob(jobId: string, resumeId: string): Promise<MatchingResult> {
  return apiRequest<MatchingResult>(`/api/matching/jobs/${encodeURIComponent(jobId)}/resumes/${encodeURIComponent(resumeId)}`, { method: 'POST', headers: await authenticatedHeaders() })
}

export async function matchCandidatesToJob(jobId: string): Promise<BulkMatchingResponse> {
  return apiRequest<BulkMatchingResponse>(`/api/matching/jobs/${encodeURIComponent(jobId)}`, { method: 'POST', headers: await authenticatedHeaders() })
}

export async function getMatchingResult(jobId: string, resumeId: string): Promise<MatchingResult> {
  return apiRequest<MatchingResult>(`/api/matching/jobs/${encodeURIComponent(jobId)}/resumes/${encodeURIComponent(resumeId)}`, { headers: await authenticatedHeaders() })
}

export async function getMatchingResults(jobId: string): Promise<MatchingResult[]> {
  return apiRequest<MatchingResult[]>(`/api/matching/jobs/${encodeURIComponent(jobId)}/results`, { headers: await authenticatedHeaders() })
}

export async function getMatchingCandidates(jobId: string): Promise<MatchingCandidate[]> {
  return apiRequest<MatchingCandidate[]>(`/api/matching/jobs/${encodeURIComponent(jobId)}/candidates`, { headers: await authenticatedHeaders() })
}
