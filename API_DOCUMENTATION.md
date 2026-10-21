# API Documentation

Base URL for local development: `http://localhost:8000`. Interactive OpenAPI documentation is available at `/docs`; schemas there are the runtime contract. All routes below are registered by `backend/app/main.py`.

## Authentication and errors

Except `GET /api/health`, routes require `Authorization: Bearer <Supabase access token>`. The backend verifies the token with Supabase Auth. Role-specific routes also check the account type and resource ownership. Database and Storage calls use the same user token, preserving RLS.

Common errors are `401` missing/invalid/expired session, `403` wrong account type or forbidden resource, `404` missing or inaccessible resource, `413` file/size limit, `422` invalid request or unreadable input, `500` unexpected processing failure, `502` upstream Supabase operation failure, and `503` missing/unavailable Supabase configuration. A route may return only the subset relevant to its operation.

## Health

| Method | Path | Purpose | Authentication | Request | Response | Possible errors |
|---|---|---|---|---|---|---|
| GET | `/api/health` | API process health check | None | None | `{"status":"ok","service":"TalentIQ API"}` | None declared |

## Resume Intelligence

| Method | Path | Purpose | Authentication | Request | Response | Possible errors |
|---|---|---|---|---|---|---|
| POST | `/api/resumes/upload` | Validate, parse, extract, and save one resume | Job seeker | `multipart/form-data`, field `file`; PDF/DOCX, up to 10 MB | `ResumeUploadResponse`: processed resume record, extracted profile, parser metadata | 401, 403, 413, 422, 500, 502, 503 |

## Job Intelligence and jobs

| Method | Path | Purpose | Authentication | Request | Response | Possible errors |
|---|---|---|---|---|---|---|
| POST | `/api/jobs/analyze` | Analyze pasted job text or one uploaded PDF/DOCX without saving a job | Recruiter | Multipart `description` or `file`, exactly one; text must contain at least 40 characters | `JobAnalysisResponse` with extracted job fields and `analysis_status` | 401, 403, 413, 422, 500, 502, 503 |
| GET | `/api/jobs` | List the caller's recruiter-owned jobs | Recruiter | None | `JobResponse[]` | 401, 403, 502, 503 |
| POST | `/api/jobs` | Create a recruiter-owned job | Recruiter | JSON `JobCreateRequest`; includes title, description, optional role fields/profile, and `status` (`draft` by default or `published`) | `JobResponse` (201) | 401, 403, 422, 502, 503 |
| GET | `/api/jobs/{job_id}` | Read one recruiter-owned job | Recruiter | UUID path parameter | `JobResponse` | 401, 403, 404, 422, 502, 503 |
| PUT | `/api/jobs/{job_id}` | Update a recruiter-owned job | Recruiter | JSON partial `JobUpdateRequest` | `JobResponse` | 401, 403, 404, 422, 502, 503 |
| DELETE | `/api/jobs/{job_id}` | Delete a recruiter-owned job | Recruiter | UUID path parameter | Empty response (204) | 401, 403, 404, 422, 502, 503 |

## Candidate applications and matching

| Method | Path | Purpose | Authentication | Request | Response | Possible errors |
|---|---|---|---|---|---|---|
| POST | `/api/matching/jobs/{job_id}/apply` | Associate the job seeker's own processed resume with a published job | Job seeker | JSON `{ "resume_id": "<uuid>" }` | `MatchingCandidate` (201) | 401, 403, 404, 409, 422, 502, 503 |
| GET | `/api/matching/jobs/{job_id}/candidates` | List resumes applied to a recruiter's job | Owning recruiter | UUID path parameter | `MatchingCandidate[]` | 401, 403, 404, 422, 502, 503 |
| POST | `/api/matching/jobs/{job_id}/resumes/{resume_id}` | Calculate and save one numerical match | Owning recruiter | UUID path parameters | `MatchingResult` with overall and five component scores | 401, 403, 404, 422, 502, 503 |
| GET | `/api/matching/jobs/{job_id}/resumes/{resume_id}` | Read the latest saved numerical match | Owning recruiter | UUID path parameters | `MatchingResult` | 401, 403, 404, 422, 502, 503 |
| GET | `/api/matching/jobs/{job_id}/results` | Read saved match results for a job | Owning recruiter | UUID path parameter | `MatchingResult[]` | 401, 403, 404, 422, 502, 503 |
| POST | `/api/matching/jobs/{job_id}` | Match up to 50 applied resumes | Owning recruiter | UUID path parameter; no body | `BulkMatchingResponse` with `results` and per-resume `failures` | 401, 403, 404, 422, 502, 503 |

## Explainable Ranking

| Method | Path | Purpose | Authentication | Request | Response | Possible errors |
|---|---|---|---|---|---|---|
| GET | `/api/ranking/jobs/{job_id}/resumes/{resume_id}` | Retrieve or generate an explanation from a saved score | Owning recruiter | UUID path parameters | `RankingExplanation` | 401, 403, 404, 422, 502, 503 |
| POST | `/api/ranking/jobs/{job_id}/resumes/{resume_id}/explain` | Refresh and persist explanation from the saved score | Owning recruiter | UUID path parameters; no body | `RankingExplanation` | 401, 403, 404, 422, 502, 503 |
| POST | `/api/ranking/jobs/{job_id}/explain` | Explain saved results for up to 50 applied resumes | Owning recruiter | UUID path parameter; no body | `BulkRankingExplanation` with per-resume failures | 401, 403, 404, 422, 502, 503 |

## Recruiter Workspace

| Method | Path | Purpose | Authentication | Request | Response | Possible errors |
|---|---|---|---|---|---|---|
| GET | `/api/recruiter/dashboard` | Recruiter-owned dashboard metrics and recent activity | Recruiter | None | Metrics object, jobs, and recent activity | 401, 403, 502, 503 |
| GET | `/api/recruiter/jobs` | Recruiter-owned jobs with requirements and applicant counts | Recruiter | None | Job objects | 401, 403, 502, 503 |
| GET | `/api/recruiter/jobs/{job_id}` | Read one owned job and its requirements | Recruiter | UUID path parameter | Job object | 401, 403, 404, 422, 502, 503 |
| GET | `/api/recruiter/jobs/{job_id}/candidates` | Search/filter/page applicants | Recruiter | Optional `page`, `page_size`, `q`, `score`, `shortlist`, `experience`, `skill`, `sort` query parameters | Page object with `items`, paging values, total, and required skills | 401, 403, 404, 422, 502, 503 |
| GET | `/api/recruiter/jobs/{job_id}/candidates/{candidate_id}` | Read one applied candidate profile, result, shortlist, and notes | Recruiter | UUID path parameters | Candidate workspace object | 401, 403, 404, 422, 502, 503 |
| GET | `/api/recruiter/jobs/{job_id}/candidates/{candidate_id}/resumes/{resume_id}/download` | Create a short-lived signed URL for the applied resume | Recruiter | UUID path parameters | `{ "file_name": string, "url": string }` | 401, 403, 404, 422, 502, 503 |
| GET | `/api/recruiter/jobs/{job_id}/shortlist` | List shortlisted applicants for the owned job | Recruiter | UUID path parameter | Candidate workspace objects | 401, 403, 404, 422, 502, 503 |
| POST | `/api/recruiter/jobs/{job_id}/shortlist/{candidate_id}` | Add an applied candidate to the shortlist | Recruiter | UUID path parameters | Shortlist record | 401, 403, 404, 422, 502, 503 |
| DELETE | `/api/recruiter/jobs/{job_id}/shortlist/{candidate_id}` | Remove an applied candidate from the shortlist | Recruiter | UUID path parameters | `{ "shortlisted": false }` | 401, 403, 404, 422, 502, 503 |
| POST | `/api/recruiter/candidates/{candidate_id}/notes` | Add a note for an applied candidate | Recruiter | JSON `{ "job_id": "<uuid>", "note": string }` | Note record | 401, 403, 404, 422, 502, 503 |
| PATCH | `/api/recruiter/notes/{note_id}` | Edit an owned note | Recruiter | JSON note update | Updated note | 401, 403, 404, 422, 502, 503 |
| DELETE | `/api/recruiter/notes/{note_id}` | Delete an owned note | Recruiter | UUID path parameter | Empty response (204) | 401, 403, 404, 422, 502, 503 |
| POST | `/api/recruiter/compare` | Compare candidates associated with an owned job | Recruiter | JSON `job_id` and `candidate_ids` | Candidate workspace objects in requested order | 401, 403, 404, 422, 502, 503 |

## Career Assistant

| Method | Path | Purpose | Authentication | Request | Response | Possible errors |
|---|---|---|---|---|---|---|
| POST | `/api/career-assistant/chat` | Return a templated response and store the user's message in a candidate-owned session | Job seeker | JSON `message` (1–4000 chars), optional `session_id`, `session_type`, `metadata` | `CareerAssistantResponse` with response and session/message IDs | 400, 401, 403, 422, 502, 503 |
| POST | `/api/career-assistant/resume-review` | Return rule-based resume improvement suggestions from the caller's profile | Job seeker | Optional `ResumeReviewRequest` | Resume review result categories | 401, 403, 502, 503 |
| POST | `/api/career-assistant/skill-gap` | Compare caller skills with a job, supplied description, or target role | Job seeker | Optional `job_id`, `job_description`, `target_role` | Matched, partial, missing skills and learning areas | 401, 403, 422, 502, 503 |
| POST | `/api/career-assistant/interview` | Prepare deterministic interview questions | Job seeker | Optional `interview_type`, `job_id`, `job_description`, `target_role` | Technical, behavioral, project, and follow-up question lists | 401, 403, 422, 502, 503 |
| GET | `/api/career-assistant/sessions` | List the caller's assistant sessions | Job seeker | None | Session array | 401, 403, 502, 503 |
| GET | `/api/career-assistant/sessions/{session_id}` | Read one caller-owned session and its persisted messages | Job seeker | UUID path parameter | Session and message objects | 401, 403, 404, 422, 502, 503 |

Career Assistant outputs are deterministic/template-based in the current implementation; the route names do not imply a generative model integration. RLS permits the client-scoped API to insert user-role chat messages; assistant replies are returned to the active chat but are not persisted as assistant-role database rows.
