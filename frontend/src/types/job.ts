export type JobImportance = 'required' | 'preferred'
export type EmploymentType = 'full_time' | 'part_time' | 'contract' | 'temporary' | 'internship' | 'other'

export interface JobRequirement {
  name: string
  original_name?: string | null
  category?: string | null
  importance: JobImportance
}

export interface EducationRequirement {
  degree_level?: string | null
  degrees: string[]
  fields: string[]
}

export interface JobProfile {
  job_title?: string | null
  department?: string | null
  location?: string | null
  employment_type?: EmploymentType | null
  work_mode?: 'Remote' | 'Hybrid' | 'On-site' | null
  summary?: string | null
  responsibilities: string[]
  required_skills: JobRequirement[]
  preferred_skills: JobRequirement[]
  technical_skills: string[]
  soft_skills: string[]
  tools: string[]
  frameworks: string[]
  programming_languages: string[]
  databases: string[]
  cloud_platforms: string[]
  minimum_experience?: number | null
  maximum_experience?: number | null
  education_requirement?: EducationRequirement | null
  certifications: Array<{ name: string; importance: JobImportance }>
  benefits: string[]
  raw_description?: string | null
  cleaned_description?: string | null
  classification_note?: string | null
  analysis_status?: 'analyzed'
}

export interface JobRecord {
  id: string
  recruiter_id: string
  title: string
  department?: string | null
  description: string
  location?: string | null
  employment_type?: EmploymentType | null
  work_mode?: string | null
  experience_min?: number | null
  experience_max?: number | null
  education_requirement?: string | null
  summary?: string | null
  responsibilities: string[]
  education_json?: EducationRequirement | null
  certifications_json: Array<{ name: string; importance: JobImportance }>
  benefits_json: string[]
  analysis_status: string
  status: 'draft' | 'published' | 'closed'
  requirements: JobRequirement[]
  created_at?: string | null
  updated_at?: string | null
}

export interface JobCreateInput {
  title: string
  department?: string | null
  description: string
  location?: string | null
  employment_type?: EmploymentType | null
  work_mode?: string | null
  experience_min?: number | null
  experience_max?: number | null
  education_requirement?: string | null
  status?: 'draft' | 'published'
  profile?: JobProfile
}
