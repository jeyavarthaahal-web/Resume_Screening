# TalentIQ Project Overview

TalentIQ is a two-sided resume screening and career-intelligence application. Recruiters create and analyze job profiles, review candidates who have applied, calculate role-specific match scores, inspect supporting evidence, and manage shortlists, notes, and comparisons. Job seekers upload resumes, review extracted profiles, apply to published roles, and use career guidance tools.

## Core capabilities

- **Resume Intelligence:** authenticated PDF/DOCX upload, text extraction, section detection, and structured profile storage.
- **Job Intelligence:** recruiter-owned job analysis with editable role details and separated required/preferred skills.
- **AI Matching Engine:** CPU Sentence Transformer semantic similarity combined with deterministic skill, experience, education, and project signals.
- **Explainable Ranking:** factual matched/partial/missing skills, score contributions, evidence, strengths, and gaps; it does not make hiring decisions.
- **Recruiter Workspace:** dashboard, job and candidate views, shortlist management, notes, and candidate comparison.
- **Career Assistant:** resume review, skill-gap analysis, interview question preparation, and chat. Current guidance is deterministic/rule-based; it does not call a generative AI service.

## Technology

- Frontend: React 19, TypeScript, Vite, React Router, Supabase JavaScript client, Lucide React.
- Backend: Python, FastAPI, Pydantic, PDF/DOCX parsers, Sentence Transformers.
- Data and identity: Supabase Auth, PostgreSQL/PostgREST, RLS, and a private Supabase Storage bucket for resumes.

## Local run

Configure the environment variables described in [README.md](README.md), then run the API and frontend in separate terminals:

```powershell
cd backend
uvicorn app.main:app --reload
```

```powershell
cd frontend
npm install
npm run dev
```

The API health route is `http://localhost:8000/api/health`; the API reference is `http://localhost:8000/docs`. The frontend runs at the Vite URL printed in its terminal.

## Demo safety and limitations

There are no demo accounts or production seed records. Use presenter-created test accounts in a development Supabase project and clearly fictional resume content. Recruiters can publish a role; job seekers can apply with an uploaded processed resume. Ownership checks and RLS remain enabled.

Resume and job extraction are heuristic and do not use OCR. Matching is decision support, not a hiring recommendation. The Career Assistant currently produces deterministic suggestions and templated chat responses rather than generative model output. Live authentication, storage, database, and cross-account behavior require a configured Supabase project.

See [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md), [DEMO_SCRIPT.md](DEMO_SCRIPT.md), [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md), [API_DOCUMENTATION.md](API_DOCUMENTATION.md), [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md), and [VIVA_NOTES.md](VIVA_NOTES.md) before presenting.
