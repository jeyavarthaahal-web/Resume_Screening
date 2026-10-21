# TalentIQ

TalentIQ is a resume intelligence and hiring workflow application. The current implementation includes authentication, profile-backed database security, PDF/DOCX resume and job-document intelligence, numerical matching, explainable results, recruiter workflows, and the AI Career Assistant. Live deployment still requires project-specific Supabase and hosting configuration.

## Architecture

- `frontend/`: React, TypeScript, and Vite single-page application.
- `backend/`: independently deployable FastAPI API, secure document intake, parsers, extraction, matching, explainability, and assistant services.
- `supabase/`: versioned PostgreSQL migrations, RLS policies, and private resume storage setup.

## Tech stack

React · TypeScript · Vite · Tailwind CSS · React Router · TanStack Query · Lucide React · Supabase JavaScript client · Python · FastAPI · Uvicorn

## Project structure

```text
frontend/src/       UI pages, reusable components, API and Supabase clients
backend/app/        FastAPI API, parsers, extraction, services, and response schemas
backend/tests/      Synthetic-fixture tests for resume intelligence
supabase/           PostgreSQL migrations, RLS policies, and seed data
```

## Prerequisites

- Node.js 20.19+ or 22.12+ (required by the current Vite release)
- Python 3.10+

## Frontend setup

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Vite prints the local URL (normally `http://localhost:5173`). Create a production bundle with `npm run build`.

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The health endpoint is `http://localhost:8000/api/health` and the interactive API docs are at `http://localhost:8000/docs`.

## Environment variables

Frontend values are documented in `frontend/.env.example` (set them in the frontend host's build environment for production):

- `VITE_API_BASE_URL` — deployed FastAPI origin (use `http://localhost:8000` locally).
- `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` — your Supabase project URL and publishable key. The auth client is initialized lazily and reports a clear error if missing.

Backend settings are documented in `backend/.env.example`. The API uses `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` to verify callers and make JWT-scoped Storage/PostgREST requests; `FRONTEND_ORIGINS` controls production CORS, `ENVIRONMENT` selects development or production behavior, `EMBEDDING_MODEL` optionally selects the matching model, and `PORT` is read by the deployment start command. The implementation does not use a service-role key or an external generative AI key. No real credentials are included.

## Implemented Scope: Tasks 1–10

The application includes the authentication and profile foundation, resume and job intelligence, consent-based candidate applications, numerical matching, explanations of saved results, recruiter workspace, and the Career Assistant. Database authorization is enforced by Supabase RLS and server-side ownership checks, not frontend routes. Matching scores and explanations are decision-support signals, not hiring decisions.

## Security and generated files

Copy the example environment files for local development, then keep actual `.env` files private. `.env.example` files are intentionally tracked. Dependencies, build output, virtual environments, and Python caches are ignored by Git.

## Supabase authentication setup (Task 2)

1. Create a Supabase project and copy its **Project URL** and **publishable key** (the public client key) from the project API settings.
2. Copy `frontend/.env.example` to `frontend/.env.local`, set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`, then restart Vite. Never put a service-role key in the frontend.
3. In Supabase Authentication → Providers, enable Email and choose whether email confirmation is required. Configure the project's email sender and templates for a usable production flow.
4. Set the Supabase Auth **Site URL** to the deployed frontend origin. Add the local callback URLs to the redirect URL allowlist: `http://localhost:5173/auth/callback` and `http://localhost:5173/reset-password`; also allow the corresponding production URLs, such as `https://your-frontend.example/auth/callback` and `https://your-frontend.example/reset-password`. The app builds redirects from `window.location.origin`, so no production hostname is hardcoded in the client.
5. To enable Google, LinkedIn OIDC, or Microsoft, configure each provider in the Supabase dashboard and supply that provider's own client ID/secret there. For the provider's redirect/callback URL, use the Supabase callback shown in the dashboard (typically `https://<project-ref>.supabase.co/auth/v1/callback`). No provider credentials are included in this repository.
6. Microsoft uses the `azure` provider with the `email` scope. LinkedIn uses Supabase's `linkedin_oidc` provider.

OAuth and password recovery cannot complete until the project URL/key, provider settings (where applicable), and redirect allowlist are configured. Signup captures the requested consent booleans as user metadata; this checkbox is not a claim of GDPR compliance. The actual Terms of Service and Privacy Policy text still needs to be supplied before launch.

## Task 3 — Supabase Database Setup

The Task 3 schema is in `supabase/migrations/20260926000100_initial_talentiq_schema.sql`. It creates `profiles`, `jobs`, `job_requirements`, `resumes`, `resume_profiles`, `screening_results`, `shortlists`, `candidate_notes`, `candidate_comparisons`, `career_assistant_sessions`, `career_assistant_messages`, and `ai_analysis_logs`, with account/job status enums, foreign keys, checks, indexes, updated-at triggers, and RLS policies. There is no production seed data; do not insert fake records into `auth.users`.

### Apply the migration

Use either supported method:

1. In the Supabase Dashboard, open **SQL Editor**, paste the complete migration file, and run it against the intended project.
2. With the Supabase CLI linked to the project, run `supabase db push` from the repository root. This applies pending files in `supabase/migrations/`.

For a new local Supabase stack, run `supabase start` and `supabase db reset` from the repository root. Review the CLI's target project before applying a migration. This migration is a one-time initial schema migration; do not run it a second time after successful application.

### Profile creation and roles

An `AFTER INSERT` trigger on `auth.users` maps the signup metadata (`full_name`, `account_type`, company fields, and consent booleans) into `public.profiles`; the email comes from `auth.users.email`. Missing or invalid role metadata defaults to the least-privileged `job_seeker` role with an internal role lock left open only for the Task 2 OAuth callback. That callback writes the saved signup metadata after OAuth returns; a database trigger accepts a valid role once and locks it. Later edits to editable `user_metadata` cannot change the profile role. Auth email changes are synchronized to the profile. Passwords and auth tokens are not copied into application tables.

The frontend uses the existing Supabase client and auth-state listener. `useProfile()` loads profile data on demand; `getCurrentProfile()` and `updateCurrentProfile()` are in the profile service. Profile id, email, role, and the internal role lock cannot be updated through the client profile service. Role-based UI routing reads `profiles.account_type`; RLS checks that same database role.

### RLS overview

RLS is enabled for every application table. Users can read/update only their own profile, with column grants preventing changes to identity and role fields. Recruiters can manage only their own jobs and related requirements, shortlists, notes, and comparisons. Published jobs and their requirements are readable publicly; draft/closed jobs remain recruiter-private. Candidates can manage only their own resume records; extracted profiles are readable by their owner and accept owner-scoped inserts, while screening records are read-only to the client. Screening results are visible only to their candidate and the recruiter who owns the related job. Career sessions/messages are candidate-owned; clients can add only user-role messages, leaving assistant/system messages to a future trusted server workflow. AI logs are owner-readable and not client-writable. These policies are access controls, not a compliance certification.

### RLS verification procedure

Use two test users created through Supabase Auth (one recruiter and one job seeker), and apply the migration first. Do not use the SQL Editor's default owner session to judge RLS: database owners bypass row policies. Verify through the frontend with each user's authenticated session, Supabase client, or a SQL session explicitly set to role `authenticated` with a valid test JWT:

1. Sign up each user and confirm a `profiles` row exists with matching id, email, mapped name/role/company/consents. For OAuth signup, confirm the callback metadata sync completes and locks the selected role.
2. Read each user's own profile. Attempt to select and update the other user's profile; the select should return no row and the update should affect zero rows. Attempt to update `account_type`, `email`, or `id`; PostgREST should reject updates to columns the role cannot update.
3. As Recruiter A, create and edit a draft job. As Recruiter B, try reading/updating that draft (it should be invisible/unchanged). As the job seeker, try inserting or editing a job (it should fail). Publish a test job as its owner and confirm anonymous/authenticated reads see only published jobs.
4. As each of two job seekers, create a resume record with an isolated test file path. Confirm each can read/edit/delete only their own row. A candidate cannot read another candidate's resume or extracted profile.
5. Create a screening row using a trusted SQL/service-role fixture only in a disposable development project. Confirm the candidate and owning recruiter can read it, while another candidate and unrelated recruiter cannot. The client has no insert/update grant for screening results.
6. Create candidate-owned career sessions and user messages. Confirm another account cannot read them, and client inserts with `assistant`/`system` roles are rejected.
7. Check a user's AI logs are invisible to another user and client writes are denied.

SQL Editor owner queries can confirm that tables, indexes, triggers, and policies exist, but do not count as an RLS test. No live project credentials are present in this workspace, so the authenticated two-user checks must be run against your Supabase project after applying the migration.

### Environment and security

The browser uses only `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` from `frontend/.env.local`. Never add a Supabase service-role key, database password, OAuth client secret, or private API key to a `VITE_` variable. Use a trusted backend for future privileged writes. The consent fields only store the user's choices and do not by themselves establish GDPR compliance; provide the actual terms and privacy text before launch.

If port 5173 is occupied, Vite automatically selects another port. In that case, add the callback and reset URLs for the exact local origin Vite prints (for example, port 5174) to Supabase's redirect URL allowlist.

### Session persistence

“Remember me” on uses the browser's persistent local storage through Supabase's storage adapter. When off, Supabase writes its session to session storage, which is scoped to the current browser tab/session and is normally cleared when that tab session ends. Browser session-restore features may restore tabs and their session storage, and private browsing or browser storage restrictions can affect persistence. The app does not read, parse, or manually save access or refresh tokens. OAuth signup details are briefly held in session storage to survive the provider redirect, then removed by the callback.

## Task 4 — Resume Intelligence

Task 4 adds an authenticated `POST /api/resumes/upload` endpoint and the job seeker page at `/resumes/upload`. The workflow accepts exactly one `.pdf` or `.docx` file up to 10 MB, validates its content signature and structure, extracts text, normalizes whitespace, detects common sections, and returns a typed candidate profile. A synthetic resume is in `backend/tests/fixtures/sample_resume.txt`; tests generate small PDF and DOCX fixtures in memory, so no private resumes are committed.

### Local setup and run

Install backend runtime and test dependencies, then configure the server:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` in `backend/.env`. Set the same project URL and publishable key in `frontend/.env.local`, plus `VITE_API_BASE_URL=http://localhost:8000`. Start Vite from `frontend/` using `npm run dev`. The upload page is protected and accepts only job seeker accounts. FastAPI documents the request and response at `http://localhost:8000/docs`; health is at `http://localhost:8000/api/health`. For a deployed frontend, set its exact origin in the comma-separated backend `FRONTEND_ORIGINS` setting.

### Storage and database

After Task 3, apply `supabase/migrations/20260926000200_resume_intelligence_storage.sql`. It creates a private `talentiq-resumes` Storage bucket, limits it to PDF/DOCX and 10 MB, scopes Storage writes/deletes to the authenticated user's folder, allows an owner-scoped extracted-profile insert, and permits grouped skill JSON plus achievement data. Do not edit the already-applied Task 3 migration.

The backend verifies the bearer access token against Supabase Auth. It derives the candidate UUID from that verified identity, checks the user's profile role, and sends the same JWT with Storage and PostgREST requests. No service-role key is used, so database and Storage RLS remain active. The source file is stored under `<candidate UUID>/<resume UUID>/<sanitized filename>` in the private bucket; `resumes.file_path` stores that private object key. The `resumes` row stores file metadata, raw extracted text, and status. The `resume_profiles` row stores personal fields, approximate experience, and structured JSON for education, experience, grouped skills, certifications, projects, languages, and achievements. Processing and database writes are rolled back best-effort on failure; successful records become `processed` only after both rows are saved.

### Parser and extraction behavior

- `backend/app/parsers/` contains a shared interface plus PDF and DOCX parsers. PDF pages are processed individually; corrupt and password-protected files get clear errors. DOCX paragraphs and tables are collected in document order.
- `backend/app/nlp/resume_cleaner.py` applies Unicode/whitespace cleanup while preserving technical forms such as `C++`, `C#`, `.NET`, and `Node.js`; repeated short page headers/footers are dropped when they occur at least three times.
- `backend/app/nlp/resume_extractor.py` recognizes common summary, education, experience, skills, projects, certification, achievement, and language headings with deterministic patterns. It normalizes a small explicit skill alias list (for example `Postgres` to `PostgreSQL`, `K8s` to `Kubernetes`, and `Sklearn` to `Scikit-learn`).
- Approximate experience is the union of dated work intervals, so overlapping jobs are not double-counted. Year-only ranges use calendar-year differences and same-year entries are estimated as six months; undated entries do not contribute. Missing or weakly supported fields remain empty.

OCR is not implemented. This parser is heuristic: formats vary, and users should review extracted results. Image-only PDFs return an unsupported message rather than pretending OCR ran.

### Tests

Run the backend suite from `backend/`:

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```

The tests cover file validation, PDF text and multi-page extraction, corrupt/encrypted/image-only PDF handling, DOCX paragraphs/tables/corruption, text cleanup, section extraction, fields, skills, certifications, languages, achievements, experience-date merging, the unauthenticated API response, and OpenAPI registration. Build the frontend from `frontend/` with `npm run build`.

## Task 5 — Job Intelligence

Recruiters can manage their job postings at `/jobs`, create a role at `/jobs/new`, and view saved job intelligence at `/jobs/:jobId`. The create flow accepts pasted description text or one PDF/DOCX (10 MB maximum), analyzes it locally with deterministic rules, presents editable role fields and separated required/preferred skills, then saves a draft. The recruiter may select published status through the API; the initial UI saves drafts. Analysis is a separate status from the job lifecycle status.

The backend provides authenticated recruiter-only `POST /api/jobs/analyze`, `POST /api/jobs`, `GET /api/jobs`, `GET /api/jobs/{job_id}`, `PUT /api/jobs/{job_id}`, and `DELETE /api/jobs/{job_id}` endpoints. It verifies the JWT with Supabase Auth (shared Task 4 dependency), checks `profiles.account_type` using that user's bearer token, derives `recruiter_id` from the verified identity, and performs PostgREST reads/writes with that same token. No service-role key is used. Task 3 ownership RLS remains active. `job_requirements.skill_type` stores required/preferred and the existing smallint importance is set to 4/2 respectively; requirements stay normalized in that table.

Apply `supabase/migrations/20260927000100_job_intelligence.sql` after the Task 3 and Task 4 migrations. It uses the existing `jobs.description` for source text and adds cleaned description, summary, responsibilities, education/certifications/benefits JSON, work mode, and a separate analysis status to `jobs`. Apply it through the Supabase Dashboard SQL Editor or your linked Supabase CLI. The workspace has no live database connection, so the migration must be applied to the intended Supabase project before running the new write endpoints.

The parser reuses Task 4's bounded PDF/DOCX parsers and does not perform OCR. The section detector tolerates known heading variants and order differences. Skill mentions in explicit required/preferred sections or labeled sentences follow that label; if found only in an unlabelled skills list, they default to preferred so the parser does not overstate requirements. Experience, education, benefits, certifications, and categories are extracted only from explicit textual clues; uncertain values remain empty. Review extracted fields before saving. No matching, ranking, embedding, scoring, or career assistant work is included.

Run Task 5 backend tests from `backend/` with `python -m pytest tests -q`. They exercise text normalization, heading detection, structured extraction, required/preferred classification, experience ranges, DOCX parsing, invalid/encrypted PDFs, validation, schema constraints, and auth/role guards. Run `npm run build` from `frontend/` to type-check and build the recruiter pages.

## Task 6 — AI Matching Engine

Task 6 provides authenticated numerical matching for processed resumes that a job seeker explicitly associates with a published job. Candidates create that association with `POST /api/matching/jobs/{job_id}/apply`; the recruiter who owns the job can list candidates, score one resume, score up to 50 associated resumes in a batch, and read a saved result through the other `/api/matching/jobs/...` endpoints. The frontend exposes the recruiter workflow from the job detail page at `/jobs/:jobId/matching`. Candidate-owned application links gate recruiter access to resume data and score rows.

The backend uses a lazy, process-wide CPU `SentenceTransformer` loader configured by `EMBEDDING_MODEL`, defaulting to `sentence-transformers/all-MiniLM-L6-v2`. Embeddings are normalized and cached in a bounded process-local cache; bulk matching embeds texts in batches. Install `backend/requirements.txt` (or `requirements-dev.txt`, which includes it) and allow the first run to download the model. The [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) describes this model and its Sentence Transformers usage. If loading or inference fails, the API returns a retryable service error and does not persist invented scores.

Matching score components are bounded from 0 to 100 and persisted numerically in `screening_results`: semantic similarity, normalized required/preferred skill coverage, experience threshold fit, education compatibility, and project relevance. Semantic scoring is `max(0, cosine similarity) × 100`; no unrelated transformation is applied. Skill coverage is matched normalized skills divided by requested skills, with required coverage weighted 70% and preferred coverage 30%; when only one group exists it supplies the whole component, and no listed skills yields a neutral 50. Experience below a minimum scores candidate years divided by minimum years; meeting or exceeding the minimum scores 100, maximum experience does not penalize, no requirement scores 100, and unknown candidate experience scores 50. Education uses a small degree-level hierarchy and related-field groups; unknown candidate education or unrecognized requirements score 50. Project relevance combines normalized technology coverage (60%) with semantic relevance (40%) when both are available, using the best-scoring project; absent projects score 50. The weighted overall score is 40% semantic, 25% skills, 15% experience, 10% education, and 10% projects. These are heuristic decision-support signals, not a ranking or hiring decision.

Authenticated API endpoints:

- `POST /api/matching/jobs/{job_id}/apply` — job seeker associates their own processed resume with a published job.
- `GET /api/matching/jobs/{job_id}/candidates` — owning recruiter lists associated resumes.
- `POST /api/matching/jobs/{job_id}/resumes/{resume_id}` — calculate and persist one score.
- `GET /api/matching/jobs/{job_id}/resumes/{resume_id}` — read its latest saved score.
- `GET /api/matching/jobs/{job_id}/results` — read latest saved scores for the job in a paged query.
- `POST /api/matching/jobs/{job_id}` — batch match up to 50 associated resumes.

Apply `supabase/migrations/20260927000200_ai_matching_engine.sql` after the earlier schema and Task 5 migrations. It creates `job_candidates`, adds candidate-authorized resume access for the associated job's recruiter, and scopes result reads/writes with RLS. The migration is source code only until applied to your Supabase project. This workspace has no configured live Supabase URL or publishable key, so the migration and live RLS behavior have not been applied or verified here.

Run the backend suite from `backend/` with `python -m pytest tests -q`; matching unit tests use a deterministic local embedding stand-in so they do not download model files. Build the frontend from `frontend/` with `npm run build`. The real model has been loaded on CPU and smoke-tested locally. Live Supabase scoring/persistence and two-account RLS checks require the intended Supabase project configuration and applied migration.

Known limitations: Task 6 provides numerical scores only; Task 7 adds explanations but does not order candidates. The engine is deterministic but heuristic, depends on Task 4/5 extraction quality, and is not a hiring decision. It does not include OCR, custom model training, or the AI Career Assistant.

## Task 7 — Explainable Ranking

Task 7 explains saved Task 6 scores deterministically from the persisted component values and Task 4/5 structured source fields. It does not run the matching engine again or change its weights. The five weighted contributions use the established 40% semantic, 25% skills, 15% experience, 10% education, and 10% project weights. The API verifies that rounded contributions reconcile with the saved overall score; inconsistent legacy rows return a clear error instead of silently creating a different overall score.

Skill explanations reuse Task 6 normalization. Exact normalized aliases (such as Postgres/PostgreSQL, ReactJS/React, NodeJS/Node.js, and Sklearn/Scikit-learn) are matches. A small explicit relation list classifies selected close alternatives such as React/Angular, AWS/Azure, and PostgreSQL/MySQL as partial; other unmatched job skills are identified as missing with required/preferred importance. Explanations contain short snippets and structured references to resume and job source fields. Strengths and gaps are generated only when source fields support their statements; absent extraction is labeled “not identified.” The data-quality label counts populated resume summary, skills, experience, education, and projects and describes extraction completeness, not candidate quality.

Recruiter-only API endpoints:

- `GET /api/ranking/jobs/{job_id}/resumes/{resume_id}` — retrieve a saved explanation or generate it from the existing Task 6 result.
- `POST /api/ranking/jobs/{job_id}/resumes/{resume_id}/explain` — regenerate and persist the explanation for the same saved score.
- `POST /api/ranking/jobs/{job_id}/explain` — explain existing results for up to 50 associated resumes; individual missing profiles/results are returned as failures.

The page at `/jobs/:jobId/resumes/:resumeId/explanation` is linked from the recruiter matching view. The new migration `supabase/migrations/20260927000300_explainable_ranking.sql` converts the existing skill-name arrays to JSONB so each entry can retain its status and required/preferred importance, and adds the score breakdown, explanation text, and context details. Existing RLS and the recruiter-owned job/application checks remain in force; database calls use the recruiter's JWT. Candidate ordering is handled by the recruiter workspace; explanations use no external LLM.

Run `python -m pytest tests -q` from `backend/`, `npm test` from `frontend/` for the explanation page states, and `npm run build` from `frontend/`. Apply the migration after Task 6 to use explanation persistence; live Supabase RLS behavior requires verification against the configured project.

## Production Deployment (Task 11)

The frontend and API are independent deployables. The frontend is a Vite static site; the backend is a Python ASGI service. Keep production credentials in each hosting provider's environment-variable settings, not in this repository. `.env`, `.env.local`, and other `.env.*` files are ignored; the tracked `.env.example` files contain names only.

### Frontend: Netlify

The root `netlify.toml` uses `frontend/` as the build base, runs `npm run build`, publishes `dist/`, and rewrites unknown paths to `index.html` with HTTP 200. This SPA fallback is required for refreshes on routes such as `/recruiter`, `/recruiter/jobs`, `/career-assistant`, and `/recruiter/compare`.

Set these values in Netlify's build environment. Vite variables are public and compiled into browser assets, so never put secrets in them:

- `VITE_SUPABASE_URL` — Supabase project URL.
- `VITE_SUPABASE_PUBLISHABLE_KEY` — Supabase publishable key only.
- `VITE_API_BASE_URL` — deployed API origin, with no path suffix.

Build locally with `cd frontend` followed by `npm ci`, `npm run build`, and optionally `npm run preview`. The output is `frontend/dist/`, which is ignored by Git and should be generated by the deployment build, not committed.

### Backend: ASGI host

Deploy `backend/` as an independent Python service. Install from `requirements.txt`; start with `uvicorn app.main:app --host 0.0.0.0 --port $PORT` on hosts that provide `PORT`. The included `backend/Procfile` uses the platform `PORT` and defaults to 8000. For local development, from `backend/`, `uvicorn app.main:app --reload` continues to use port 8000; the explicit production command is `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

Configure these backend variables in the host dashboard:

- `ENVIRONMENT=production` to disable development-only localhost CORS allowances.
- `FRONTEND_ORIGINS` as a comma-separated list of exact deployed frontend origins, for example `https://talentiq.example` (no wildcard, path, or trailing slash).
- `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` for authenticated, caller-JWT-scoped Supabase requests.
- `EMBEDDING_MODEL` only when selecting a model other than the configured default.
- `PORT` is normally supplied by the host; do not set a conflicting port.

The API rejects wildcard CORS configuration. Development keeps localhost support; production only permits explicitly configured origins. Verify deployment with `GET https://<api-host>/api/health`, which should return `{"status":"ok","service":"TalentIQ API"}`. Do not expose a service-role key or external AI API key in frontend settings. The current implementation does not require either one.

### Supabase release checklist

1. Apply the six existing migrations in timestamp order from `supabase/migrations/`; do not re-run already-applied migrations. They create the application tables, `job_candidates`, private resume storage, indexes, constraints, ownership policies, and RLS policies. RLS is enabled for the application tables; do not disable it. No live Supabase project is configured in this workspace, so the migration state and cross-account RLS behavior must be checked in the target project.
2. In Authentication settings, set **Site URL** to the production frontend origin. Add production `/auth/callback` and `/reset-password` URLs to the redirect allowlist, alongside local development callback URLs. OAuth provider credentials, if enabled, belong only in the Supabase dashboard; do not invent or commit credentials.
3. After deployment, test signup/sign-in, password recovery, OAuth callbacks when configured, protected-role routing, resume/job document uploads, and ownership boundaries with separate recruiter and job-seeker test accounts.

Uploads remain limited to PDF and DOCX, at most 10 MB. The API checks extensions and file signatures/OOXML structure, sanitizes filenames, parses in memory, closes each request upload, rejects parse errors, and does not provide OCR. No temporary upload files are created by the current parser flow.

### Final checks

From `frontend/`, run `npm ci`, `npm test`, and `npm run build`. From `backend/`, install `requirements-dev.txt` and run `python -m pytest -q`. The production frontend bundle contains only public Vite configuration. Deployment is not complete until the host environment variables, Supabase migrations, redirect allowlist, and live RLS checks have been verified for the actual projects.

## Demo Walkthrough (Task 12)

Start the backend and frontend with the setup steps above, and configure the local Supabase project and redirect allowlist first. Create separate recruiter and job-seeker accounts through the signup page; the repository does not provide demo credentials or production seed records.

- **Job seeker:** Sign in to open resume upload, submit a PDF or DOCX you are authorized to use, review the extracted profile, detected skills, and fields to review, then open the Career Assistant.
- **Recruiter:** Sign in to open the recruiter workspace, create a role, and use the candidate, shortlist, comparison, matching, and explanation views with applicants associated to that role.
- **Release demo:** Use disposable test accounts and consented test documents in a non-production Supabase project. Never use real candidate data in a public demo, and do not present heuristic scores or extracted fields as hiring decisions or guaranteed outcomes.
