# Viva Notes

### What is TalentIQ?
A resume-screening and career-intelligence application that structures resumes and job descriptions, provides explainable matching signals, and supports recruiter and job-seeker workflows.

### What problem does it solve?
It reduces repetitive document review and gives users a consistent way to inspect role requirements, candidate evidence, and skill gaps.

### Why is traditional resume screening difficult?
Resumes use inconsistent layouts and terminology, while manual review is time-consuming and can apply criteria inconsistently.

### What is Resume Intelligence?
The authenticated PDF/DOCX pipeline that extracts text, detects sections, and stores a structured candidate profile for review.

### What is Job Intelligence?
The job-description pipeline that extracts role details, responsibilities, qualifications, and separate required/preferred skills.

### How does AI matching work?
It compares a resume profile with a job using semantic similarity plus deterministic skill, experience, education, and project components.

### Why use semantic similarity?
It can recognize related meaning when a resume and job description use different wording; it supplements rather than replaces explicit requirement checks.

### What is Sentence Transformer?
A model family that maps text into vectors intended for semantic comparison, commonly using cosine similarity.

### Why use `all-MiniLM-L6-v2`?
It is a compact sentence-embedding model suitable for local CPU inference and short-text semantic comparison. It is not trained specifically to make hiring decisions.

### How is the match score calculated?
`overall = semantic × 0.40 + skills × 0.25 + experience × 0.15 + education × 0.10 + projects × 0.10`. Each component is bounded from 0 to 100. These weights are fixed in the existing matching engine.

### What is explainable AI?
It means showing relevant inputs and evidence behind an output. TalentIQ exposes score components, skill classifications, evidence, strengths, and gaps so a person can inspect them.

### How does the system identify missing skills?
It normalizes known aliases, compares extracted candidate skills with required/preferred job skills, and labels exact matches, selected related alternatives, and unmatched requirements. It is rule-based and depends on extraction quality.

### What is the Recruiter Workspace?
A recruiter-owned dashboard for jobs and applied candidates, with candidate details, matching, explanations, shortlists, notes, and comparisons.

### What is the Career Assistant?
A job-seeker workspace for deterministic resume suggestions, skill-gap comparison, interview question templates, and chat responses. This version does not call a generative AI service.

### Why use React?
React provides reusable UI components and state-driven views for the multi-step recruiter and job-seeker workflows.

### Why use FastAPI?
FastAPI provides typed request/response validation, async API handlers, dependency-based authentication, and generated OpenAPI documentation.

### Why use Supabase?
Supabase supplies managed authentication, PostgreSQL/PostgREST, row-level security, and private file storage behind one user-scoped integration.

### How is authentication handled?
Supabase Auth handles signup/login and issues access tokens. FastAPI verifies bearer tokens against Supabase Auth before protected operations.

### How is user data protected?
The backend forwards the caller's JWT to PostgREST/Storage, database RLS restricts rows, ownership checks guard recruiter operations, and resume files live in a private bucket. No service-role key is used by the app.

### What is RLS?
Row-level security is PostgreSQL policy enforcement that controls which rows an authenticated or anonymous database role can read or change.

### How are resumes processed?
The API checks type, content, and size, parses PDF/DOCX text, normalizes it, detects sections, extracts structured fields, and saves the file/profile under the candidate's identity.

### What happens if a resume cannot be parsed?
The API returns a validation/parser error and does not present an invented profile as successful extraction. Image-only PDFs are unsupported because OCR is not implemented.

### What are the limitations of the current system?
Extraction is heuristic and format-sensitive; OCR is absent; matching is rule-based decision support; explanations inherit extraction limitations; Career Assistant responses are deterministic/templates, not generative; live Supabase/RLS behavior requires project configuration and verification.

### What are possible future improvements?
Add OCR with reviewable provenance, broaden extraction tests, evaluate matching on consented representative data, improve assistant quality with a trusted model integration, add candidate application history, and perform security/accessibility/usability review before production.
