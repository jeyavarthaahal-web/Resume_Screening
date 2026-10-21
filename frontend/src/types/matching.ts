export interface MatchingResult {
  job_id: string
  resume_id: string
  candidate_id: string
  overall_score: number
  semantic_score: number
  skill_score: number
  experience_score: number
  education_score: number
  project_score: number
  created_at?: string | null
}

export interface MatchingCandidate {
  job_id: string
  resume_id: string
  candidate_id: string
  created_at?: string | null
}

export interface PublishedJobSummary {
  id: string
  title: string
  department: string | null
  location: string | null
  employment_type: string | null
}

export interface MatchingFailure {
  resume_id: string
  candidate_id: string
  message: string
}

export interface BulkMatchingResponse {
  job_id: string
  results: MatchingResult[]
  failures: MatchingFailure[]
}
