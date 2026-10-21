export type EducationItem = {
  degree: string | null
  field_of_study: string | null
  institution: string | null
  location: string | null
  start_date: string | null
  end_date: string | null
}

export type ExperienceItem = {
  job_title: string | null
  company: string | null
  location: string | null
  start_date: string | null
  end_date: string | null
  description: string | null
}

export type ResumeSkills = {
  technical: string[]
  soft: string[]
  tools: string[]
  frameworks: string[]
  databases: string[]
  cloud: string[]
  programming_languages: string[]
}

export type ProjectItem = {
  project_name: string | null
  description: string | null
  technologies: string[]
  role: string | null
  url: string | null
}

export type CertificationItem = {
  certification_name: string
  issuer: string | null
  date: string | null
  credential_id: string | null
}

export type AchievementItem = { title: string; description: string | null }
export type LanguageItem = { name: string; proficiency: string | null }

export type DetectedSections = {
  summary: boolean
  education: boolean
  experience: boolean
  skills: boolean
  projects: boolean
  certifications: boolean
  achievements: boolean
  languages: boolean
  other: string[]
}

export type ResumeProfile = {
  full_name: string | null
  email: string | null
  phone: string | null
  location: string | null
  summary: string | null
  years_experience: number | null
  education: EducationItem[]
  experience: ExperienceItem[]
  skills: ResumeSkills
  projects: ProjectItem[]
  certifications: CertificationItem[]
  achievements: AchievementItem[]
  languages: LanguageItem[]
  sections: DetectedSections
}

export type ResumeRecord = {
  id: string
  candidate_id: string
  file_name: string
  file_type: string
  file_size: number
  status: 'processed'
  created_at: string
}

export type ResumeUploadResponse = {
  status: 'processed'
  resume: ResumeRecord
  profile: ResumeProfile
  parser: {
    page_count: number | null
    document_metadata: Record<string, string | number | null>
  }
}
