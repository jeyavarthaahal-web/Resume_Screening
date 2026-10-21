export type CareerAssistantWorkflow = 'resume' | 'skills' | 'interview' | 'guidance'

export type CareerAssistantRole = 'user' | 'assistant' | 'system'

export interface CareerAssistantSession {
  id: string
  candidate_id: string
  title: string | null
  session_type: string | null
  metadata?: Record<string, unknown> | null
  created_at: string
  updated_at?: string | null
}

export interface CareerAssistantMessage {
  id: string
  session_id: string
  candidate_id: string
  role: CareerAssistantRole
  content: string
  metadata?: Record<string, unknown> | null
  created_at: string
}

export interface CareerAssistantChatRequest {
  session_id?: string | null
  message: string
  session_type?: string | null
  metadata?: Record<string, unknown>
}

export interface CareerAssistantResponse {
  response: string
  session_id: string
  message_id: string
}

export interface ResumeReviewResult {
  summary_improvements: Array<{ current_issue: string; suggested_improvement: string; example_wording?: string }>
  experience_improvements: Array<{ current_issue: string; suggested_improvement: string; example_wording?: string }>
  skills_improvements: Array<{ current_issue: string; suggested_improvement: string; example_wording?: string }>
  project_improvements: Array<{ current_issue: string; suggested_improvement: string; example_wording?: string }>
  formatting_suggestions: string[]
  missing_information: string[]
}

export interface SkillGapResult {
  matched_skills: string[]
  missing_skills: string[]
  partial_skills: string[]
  suggested_learning_areas: string[]
  job_requirements_total: number
}

export interface InterviewResult {
  interview_type: string
  technical_questions: string[]
  behavioral_questions: string[]
  project_questions: string[]
  follow_up_questions: string[]
  job_context?: string | null
}
