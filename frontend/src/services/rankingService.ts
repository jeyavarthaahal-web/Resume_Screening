import { apiRequest } from './api'
import { authenticatedHeaders } from './jobService'
import type { BulkRankingExplanation, RankingExplanation } from '../types/ranking'

export async function getRankingExplanation(jobId: string, resumeId: string): Promise<RankingExplanation> {
  return apiRequest<RankingExplanation>(`/api/ranking/jobs/${encodeURIComponent(jobId)}/resumes/${encodeURIComponent(resumeId)}`, { headers: await authenticatedHeaders() })
}

export async function generateRankingExplanation(jobId: string, resumeId: string): Promise<RankingExplanation> {
  return apiRequest<RankingExplanation>(`/api/ranking/jobs/${encodeURIComponent(jobId)}/resumes/${encodeURIComponent(resumeId)}/explain`, { method: 'POST', headers: await authenticatedHeaders() })
}

export async function generateJobExplanations(jobId: string): Promise<BulkRankingExplanation> {
  return apiRequest<BulkRankingExplanation>(`/api/ranking/jobs/${encodeURIComponent(jobId)}/explain`, { method: 'POST', headers: await authenticatedHeaders() })
}
