# Demo Checklist

## Before presenting

- [ ] Use a development/test Supabase project with the repository migrations applied; do not use production records for the demo.
- [ ] Configure the frontend Supabase URL/publishable key and API base URL; configure backend Supabase URL/publishable key and allowed frontend origin.
- [ ] Confirm `http://localhost:8000/api/health` returns `{"status":"ok","service":"TalentIQ API"}`.
- [ ] Create separate presenter-owned recruiter and job-seeker test accounts; do not share or commit credentials.
- [ ] Prepare a clearly fictional PDF/DOCX resume. The committed text fixture at `backend/tests/fixtures/sample_resume.txt` is synthetic test data, not a production seed and not an uploadable format by itself.
- [ ] Have the matching model available locally or allow the first model load to complete before the presentation.
- [ ] Ensure the recruiter publishes the demonstration job, then upload the fictional resume and submit an application from the job-seeker account.
- [ ] Keep each account in a separate browser profile/private window so the account boundary is clear.

## Walkthrough

- [ ] Landing page communicates TalentIQ and links to signup/login.
- [ ] Recruiter dashboard shows current database-backed metrics (empty values are valid when there is no data).
- [ ] Create and analyze a role; inspect requirements; publish it explicitly.
- [ ] Job seeker uploads a fictional resume, reviews extraction, and applies to the published role.
- [ ] Recruiter opens the applied candidate, runs matching, and reviews all score components.
- [ ] Inspect explainability evidence, shortlist, notes, and comparison using real applied test records only.
- [ ] Open `/career-assistant`; demonstrate review, skill gap, interview preparation, and a chat exchange.
- [ ] Explain that Career Assistant guidance/chat is deterministic/template-based in this version.
- [ ] Avoid presenting a match score as a hiring decision, quality guarantee, or candidate ranking.

## Safe demo data

No seeded user accounts or demo records exist. Create test records only in the development Supabase project through the normal authenticated app flow. Use invented candidate/job information and never insert sample auth users, bypass RLS, or reuse a real person's resume.
