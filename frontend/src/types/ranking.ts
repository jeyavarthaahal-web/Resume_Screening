export type SkillImportance = 'required' | 'preferred'
export type SkillStatus = 'matched' | 'partial' | 'missing'
export type EvidenceType = 'skill' | 'experience' | 'education' | 'project' | 'summary' | 'responsibility'

export interface Evidence {
  type: EvidenceType
  source: 'resume' | 'job'
  text: string
  related_requirement?: string | null
}

export interface SkillClassification {
  name: string
  importance: SkillImportance
  status: SkillStatus
  resume_skill?: string | null
}

export interface ScoreComponent {
  score: number
  weight: number
  weighted_contribution: number
}

export interface Strength {
  title: string
  description: string
  evidence: Evidence[]
}

export interface Gap {
  title: string
  description: string
  severity: 'required' | 'preferred' | 'informational'
  status: 'missing' | 'partial' | 'below_requirement' | 'not_identified'
  evidence: Evidence[]
}

export interface ExperienceContext {
  candidate_years: number | null
  minimum_years: number | null
  maximum_years: number | null
  status: 'matched' | 'below_requirement' | 'maximum_only' | 'not_specified' | 'not_identified'
}

export interface EducationContext {
  candidate: string[]
  requirement: string[]
  status: 'matched' | 'partial' | 'not_specified' | 'not_identified'
}

export interface RelevantProject {
  project_name: string
  relevant_technologies: string[]
  related_job_requirements: string[]
  evidence: Evidence
}

export interface RankingExplanation {
  job_id: string
  resume_id: string
  candidate_id: string
  overall_score: number
  score_breakdown: Record<'semantic' | 'skills' | 'experience' | 'education' | 'projects', ScoreComponent>
  matched_skills: SkillClassification[]
  partial_skills: SkillClassification[]
  missing_skills: SkillClassification[]
  strengths: Strength[]
  gaps: Gap[]
  evidence: Evidence[]
  explanation: string
  experience_context: ExperienceContext
  education_context: EducationContext
  relevant_projects: RelevantProject[]
  data_quality: 'complete' | 'partially_complete' | 'limited'
  data_quality_note: string
  generated_at?: string | null
}

export interface RankingFailure {
  resume_id: string
  candidate_id: string
  message: string
}

export interface BulkRankingExplanation {
  job_id: string
  results: RankingExplanation[]
  failures: RankingFailure[]
}
