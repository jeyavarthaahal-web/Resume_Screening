# Database Schema

This reference reflects the SQL files under `supabase/migrations/`. It describes the schema in source; it does not prove that migrations have been applied to a live Supabase project. All listed application tables have RLS enabled in the initial migration. Resume files use the private `talentiq-resumes` Storage bucket, not a public table.

| Table | Purpose and important columns | Relationships | RLS / ownership |
|---|---|---|---|
| `profiles` | App profile keyed by `id`; `full_name`, `email`, `account_type`, company/contact fields, consent flags, timestamps | `id` references `auth.users.id`; referenced as candidate/recruiter/user by other tables | Users read/update their own profile. Recruiters may read limited identity fields of candidates who applied to one of their jobs. Role/identity fields are protected by grants/triggers. |
| `jobs` | Recruiter job record: `title`, `description`, `status`, location, employment type, experience range, education; later analysis fields include cleaned description, summary, responsibilities, certifications, benefits, work mode, and `analysis_status` | `recruiter_id` references `profiles.id`; parent of requirements, applications, scores, shortlist, notes, and comparisons | Recruiters manage only their own jobs. Published jobs are readable to anonymous/authenticated users; drafts/closed jobs are owner-only. |
| `job_requirements` | Normalized `skill_name`, `skill_type`, and `importance` | `job_id` references `jobs.id` with cascade delete | Readable only when the job is published or owned by the caller; writes require the owning recruiter. |
| `resumes` | Resume file metadata, private `file_path`, `file_type`, `file_size`, `raw_text`, processing `status` | `candidate_id` references `profiles.id`; composite `(id,candidate_id)` referenced by resume profiles/results/applications | Candidates manage their own records. A recruiter's read access is limited to a candidate who applied to that recruiter's job. |
| `resume_profiles` | Extracted profile: contact fields, summary, years experience, and JSON arrays for education, experience, skills, certifications, projects, languages, achievements | `resume_id` and `candidate_id` refer to the matching resume/candidate pair | Candidate can read/insert their own profile. Recruiters can read it only for an application to their job. |
| `job_candidates` | Candidate consent/application link: `job_id`, `candidate_id`, `resume_id`, `created_at` | Foreign keys to job, profile, and the candidate-owned resume; unique job/candidate and job/resume pairs | Candidate may apply only as self, using a processed self-owned resume, to a published job. The candidate and owning recruiter may read the link; candidate may withdraw their own application. |
| `screening_results` | Numerical `overall_score`, `semantic_score`, `skills_score`, `experience_score`, `education_score`, `projects_score`; later explanation fields include skill classifications, `score_breakdown`, `explanation`, `ranking_details`, `strengths`, `gaps`, and `evidence` | References job, resume, candidate; resume/candidate pair is constrained | Candidate reads their own result; owning recruiter reads results for applicants to their job. Recruiter writes are restricted to the matching applied candidate/job by RLS. |
| `shortlists` | Recruiter workflow status and notes for a candidate/job | References job, candidate, recruiter; unique job/candidate/recruiter | Only the recruiter who owns the job manages its shortlist rows. |
| `candidate_notes` | Recruiter-authored note scoped to candidate and job | References job, candidate, recruiter | Only the owning recruiter manages notes for that job. |
| `candidate_comparisons` | Stored comparison request: recruiter, job, candidate ID array, timestamp | References job and recruiter; candidate IDs must be associated with that job through service checks | Only the recruiter who owns the job can manage the comparison record. |
| `career_assistant_sessions` | Candidate-owned `title` and timestamps | `candidate_id` references `profiles.id`; parent of messages | The candidate manages only their own sessions. |
| `career_assistant_messages` | `session_id`, `candidate_id`, `role`, `content`, and timestamp | References session and candidate | Candidate reads messages in their own session. Client-scoped inserts are allowed only for `role = 'user'`; assistant/system rows cannot be inserted with a user's JWT. |
| `ai_analysis_logs` | Owner, entity/analysis type, optional model name, input/output metadata, timestamp | `user_id` references `profiles.id` | Owner can read their logs; client writes are not granted by these migrations. |

## Related database objects

- Enums: `account_type` (`job_seeker`, `recruiter`) and `job_status` (`draft`, `published`, `closed`).
- Functions/triggers create and synchronize profiles from Supabase Auth, lock account type after signup, and maintain `updated_at` timestamps.
- The private Storage bucket limits resume objects to PDF/DOCX and 10 MB. Candidate paths begin with the candidate UUID; recruiter reads require an application to a recruiter-owned job.
- `job_candidates` is introduced by `20260927000200_ai_matching_engine.sql`; job analysis columns, resume extraction fields, matching explanations, and recruiter access policies are introduced by the later migrations.

## Relationship summary

`auth.users` → `profiles` → candidate `resumes` → `resume_profiles`; candidate applications connect a processed resume to a published `jobs` row. That application scopes recruiter access to the candidate profile, resume object, and `screening_results`. Recruiter-owned jobs also parent `job_requirements`, `shortlists`, `candidate_notes`, and `candidate_comparisons`. Candidate profiles own assistant sessions and their messages.

RLS is an authorization boundary, not a compliance certification. See [README.md](README.md) for setup and the two-user verification procedure.
