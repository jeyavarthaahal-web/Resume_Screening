import type { JobRecord } from './job'

export interface RecruiterMetrics {
  profile: { full_name?: string; company_name?: string }
  total_jobs: number
  active_jobs: number
  total_candidates: number
  screened_candidates: number
  shortlisted_candidates: number
  average_match_score: number | null
  jobs: JobRecord[]
  recent_activity: Array<{ kind: string; title: string; created_at: string | null; job_id: string }>
}

export interface WorkspaceCandidate {
  job_id: string
  candidate_id: string
  resume_id: string
  applied_at: string | null
  candidate: { full_name?: string | null; email?: string | null; phone?: string | null; location?: string | null }
  resume?: { file_name?: string }
  profile: {
    summary?: string | null; years_experience?: number | null; skills_json?: unknown
    experience_json?: unknown[]; education_json?: unknown[]; projects_json?: unknown[]
    certifications_json?: unknown[]; languages_json?: unknown[]; updated_at?: string
  }
  result: null | {
    overall_score: number | null; semantic_score: number | null; skills_score: number | null
    experience_score: number | null; education_score: number | null; projects_score: number | null
    matched_skills?: unknown[]; partial_skills?: unknown[]; missing_skills?: unknown[]
    strengths?: unknown[]; gaps?: unknown[]; evidence?: unknown[]; score_breakdown?: Record<string, unknown>
  }
  shortlist: null | { id: string; status: string; created_at: string }
  notes?: Array<{ id: string; note: string; created_at: string; updated_at: string }>
}

export interface CandidatePage {
  items: WorkspaceCandidate[]; page: number; page_size: number; total: number; required_skills: string[]
}
