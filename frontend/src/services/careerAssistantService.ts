import { getSupabaseClient } from '../lib/supabase'
import { apiRequest } from './api'
import type { CareerAssistantChatRequest, CareerAssistantResponse, CareerAssistantSession, InterviewResult, ResumeReviewResult, SkillGapResult } from '../types/careerAssistant'

export async function authenticatedHeaders(): Promise<HeadersInit> {
  const { data, error } = await getSupabaseClient().auth.getSession()
  if (error || !data.session?.access_token) throw new Error('Your session has expired. Sign in again to continue.')
  return { Authorization: `Bearer ${data.session.access_token}` }
}

export async function getCareerAssistantSessions(): Promise<CareerAssistantSession[]> {
  return apiRequest<CareerAssistantSession[]>('/api/career-assistant/sessions', { headers: await authenticatedHeaders() })
}

export async function getCareerAssistantSession(sessionId: string): Promise<{ session: CareerAssistantSession; messages: Array<{ id: string; role: string; content: string; created_at: string }> }> {
  return apiRequest(`/api/career-assistant/sessions/${encodeURIComponent(sessionId)}`, { headers: await authenticatedHeaders() })
}

export async function sendAssistantMessage(input: CareerAssistantChatRequest): Promise<CareerAssistantResponse> {
  return apiRequest<CareerAssistantResponse>('/api/career-assistant/chat', {
    method: 'POST',
    headers: { ...(await authenticatedHeaders()), 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export async function reviewResume(): Promise<ResumeReviewResult> {
  return apiRequest<ResumeReviewResult>('/api/career-assistant/resume-review', {
    method: 'POST',
    headers: { ...(await authenticatedHeaders()), 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
}

export async function analyzeSkillGap(input?: { job_id?: string; job_description?: string; target_role?: string }): Promise<SkillGapResult> {
  return apiRequest<SkillGapResult>('/api/career-assistant/skill-gap', {
    method: 'POST',
    headers: { ...(await authenticatedHeaders()), 'Content-Type': 'application/json' },
    body: JSON.stringify(input ?? {}),
  })
}

export async function prepareInterview(input?: { interview_type?: string; job_id?: string; job_description?: string; target_role?: string }): Promise<InterviewResult> {
  return apiRequest<InterviewResult>('/api/career-assistant/interview', {
    method: 'POST',
    headers: { ...(await authenticatedHeaders()), 'Content-Type': 'application/json' },
    body: JSON.stringify(input ?? { interview_type: 'general' }),
  })
}
