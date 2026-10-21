import { apiRequest } from './api'
import { authenticatedHeaders } from './jobService'
import type { CandidatePage, RecruiterMetrics, WorkspaceCandidate } from '../types/recruiter'
import type { JobRecord } from '../types/job'

export async function getRecruiterDashboard() { return apiRequest<RecruiterMetrics>('/api/recruiter/dashboard', { headers: await authenticatedHeaders() }) }
export async function getRecruiterJobs() { return apiRequest<JobRecord[]>('/api/recruiter/jobs', { headers: await authenticatedHeaders() }) }
export async function getRecruiterJob(jobId: string) { return apiRequest<JobRecord>(`/api/recruiter/jobs/${encodeURIComponent(jobId)}`, { headers: await authenticatedHeaders() }) }
export async function getCandidates(jobId: string, params: Record<string, string | number>) {
  const query = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]))
  return apiRequest<CandidatePage>(`/api/recruiter/jobs/${encodeURIComponent(jobId)}/candidates?${query}`, { headers: await authenticatedHeaders() })
}
export async function getCandidate(jobId: string, candidateId: string) { return apiRequest<WorkspaceCandidate>(`/api/recruiter/jobs/${encodeURIComponent(jobId)}/candidates/${encodeURIComponent(candidateId)}`, { headers: await authenticatedHeaders() }) }
export async function getResumeDownload(jobId: string, candidateId: string, resumeId: string) { return apiRequest<{ file_name: string; url: string }>(`/api/recruiter/jobs/${encodeURIComponent(jobId)}/candidates/${encodeURIComponent(candidateId)}/resumes/${encodeURIComponent(resumeId)}/download`, { headers: await authenticatedHeaders() }) }
export async function getShortlist(jobId: string) { return apiRequest<WorkspaceCandidate[]>(`/api/recruiter/jobs/${encodeURIComponent(jobId)}/shortlist`, { headers: await authenticatedHeaders() }) }
export async function updateShortlist(jobId: string, candidateId: string, add: boolean) {
  return apiRequest(`/api/recruiter/jobs/${encodeURIComponent(jobId)}/shortlist/${encodeURIComponent(candidateId)}`, { method: add ? 'POST' : 'DELETE', headers: await authenticatedHeaders() })
}
export async function saveNote(candidateId: string, jobId: string, note: string) { return apiRequest('/api/recruiter/candidates/' + encodeURIComponent(candidateId) + '/notes', { method: 'POST', headers: { ...(await authenticatedHeaders()), 'Content-Type': 'application/json' }, body: JSON.stringify({ job_id: jobId, note }) }) }
export async function editNote(noteId: string, note: string) { return apiRequest(`/api/recruiter/notes/${encodeURIComponent(noteId)}`, { method: 'PATCH', headers: { ...(await authenticatedHeaders()), 'Content-Type': 'application/json' }, body: JSON.stringify({ note }) }) }
export async function deleteNote(noteId: string) { return apiRequest<void>(`/api/recruiter/notes/${encodeURIComponent(noteId)}`, { method: 'DELETE', headers: await authenticatedHeaders() }) }
export async function compareCandidates(jobId: string, candidateIds: string[]) { return apiRequest<WorkspaceCandidate[]>('/api/recruiter/compare', { method: 'POST', headers: { ...(await authenticatedHeaders()), 'Content-Type': 'application/json' }, body: JSON.stringify({ job_id: jobId, candidate_ids: candidateIds }) }) }
