from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.dependencies import CurrentUser


class CareerAssistantService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.supabase_url.rstrip('/')

    def _headers(self, user: CurrentUser, content_type: str | None = None, prefer: str | None = None) -> dict[str, str]:
        headers = {
            'apikey': self.settings.supabase_publishable_key,
            'Authorization': f'Bearer {user.access_token}',
        }
        if content_type:
            headers['Content-Type'] = content_type
        if prefer:
            headers['Prefer'] = prefer
        return headers

    def _normalize(self, value: str | None) -> str:
        return re.sub(r'[^a-z0-9]+', '', (value or '').lower())

    def _flatten_skills(self, profile: dict[str, Any] | None) -> list[str]:
        if not profile:
            return []
        skills_json = profile.get('skills_json') or {}
        items: list[str] = []
        for section in (skills_json.get('technical') or [], skills_json.get('soft') or [], skills_json.get('tools') or [], skills_json.get('frameworks') or [], skills_json.get('programming_languages') or [], skills_json.get('databases') or [], skills_json.get('cloud') or []):
            if isinstance(section, list):
                items.extend(str(item).strip() for item in section if str(item).strip())
        values = profile.get('skills') or []
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str):
                    items.append(item)
        return sorted({skill for skill in items if skill})

    def _extract_job_skills(self, payload: dict[str, Any] | None) -> list[str]:
        if not payload:
            return []
        items: list[str] = []
        for key in ('required_skills', 'preferred_skills', 'technical_skills', 'tools', 'frameworks', 'databases', 'programming_languages', 'cloud_platforms'):
            value = payload.get(key) or []
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        name = item.get('name') or item.get('skill_name') or item.get('original_name')
                        if name:
                            items.append(str(name))
                    elif isinstance(item, str):
                        items.append(item)
        if not items and isinstance(payload.get('description'), str):
            text = payload['description']
            matches = re.findall(r"[A-Za-z][A-Za-z0-9+/.-]*", text)
            items = matches
        return sorted({skill.strip() for skill in items if skill and skill.strip()})

    async def _read_profile(self, user: CurrentUser) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f'{self.base_url}/rest/v1/resume_profiles',
                params={'select': '*', 'candidate_id': f'eq.{user.id}', 'order': 'updated_at.desc'},
                headers=self._headers(user),
            )
            if response.status_code == 404:
                return None
            if response.status_code >= 400:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Your resume profile could not be loaded.')
            rows = response.json()
            return rows[0] if rows else None

    async def _read_jobs(self, user: CurrentUser) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f'{self.base_url}/rest/v1/jobs',
                params={'select': 'id,title,description,summary,requirements,profile', 'status': 'eq.published', 'order': 'created_at.desc'},
                headers=self._headers(user),
            )
            if response.status_code >= 400:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Job data could not be loaded.')
            rows = response.json() or []
            return rows

    async def _read_job_requirements(self, job_id: UUID, user: CurrentUser) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f'{self.base_url}/rest/v1/job_requirements',
                params={'select': 'skill_name,skill_type,importance', 'job_id': f'eq.{job_id}', 'order': 'skill_type,skill_name'},
                headers=self._headers(user),
            )
            if response.status_code >= 400:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Job requirements could not be loaded.')
            return response.json() or []

    async def _read_session(self, user: CurrentUser, session_id: UUID) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f'{self.base_url}/rest/v1/career_assistant_sessions',
                params={'select': '*', 'id': f'eq.{session_id}', 'candidate_id': f'eq.{user.id}'},
                headers=self._headers(user),
            )
            if response.status_code >= 400:
                return None
            rows = response.json() or []
            return rows[0] if rows else None

    async def _read_session_messages(self, user: CurrentUser, session_id: UUID) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f'{self.base_url}/rest/v1/career_assistant_messages',
                params={'select': '*', 'session_id': f'eq.{session_id}', 'candidate_id': f'eq.{user.id}', 'order': 'created_at.asc'},
                headers=self._headers(user),
            )
            if response.status_code >= 400:
                return []
            return response.json() or []

    async def _write_message(self, user: CurrentUser, session_id: UUID, role: str, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            'id': str(uuid4()),
            'session_id': str(session_id),
            'candidate_id': str(user.id),
            'role': role,
            'content': content,
        }
        if metadata is not None:
            payload['metadata'] = metadata
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f'{self.base_url}/rest/v1/career_assistant_messages',
                json=payload,
                headers=self._headers(user, content_type='application/json', prefer='return=representation'),
            )
            if response.status_code not in (200, 201):
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Your message could not be saved.')
            rows = response.json() or []
            return rows[0] if rows else payload

    async def _ensure_session(self, user: CurrentUser, title: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f'{self.base_url}/rest/v1/career_assistant_sessions',
                params={'select': '*', 'candidate_id': f'eq.{user.id}', 'order': 'updated_at.desc', 'limit': '10'},
                headers=self._headers(user),
            )
            if response.status_code >= 400:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Your career assistant history could not be accessed.')
            sessions = response.json() or []
            if sessions:
                first = sessions[0]
                if title and first.get('title') == title:
                    return first
            payload = {'candidate_id': str(user.id), 'title': title}
            create = await client.post(
                f'{self.base_url}/rest/v1/career_assistant_sessions',
                json=payload,
                headers=self._headers(user, content_type='application/json', prefer='return=representation'),
            )
            if create.status_code not in (200, 201):
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Could not open a new career assistant session.')
            rows = create.json() or []
            if rows:
                return rows[0]
            return payload

    def _skill_overlap(self, requested: list[str], available: list[str]) -> tuple[list[str], list[str], list[str]]:
        normalized_available = {self._normalize(skill): skill for skill in available if skill}
        matches: list[str] = []
        missing: list[str] = []
        partial: list[str] = []
        for skill in requested:
            raw = str(skill).strip()
            if not raw:
                continue
            key = self._normalize(raw)
            if key in normalized_available:
                matches.append(raw)
                continue
            if any(key in self._normalize(v) or self._normalize(v) in key for v in normalized_available):
                partial.append(raw)
            else:
                missing.append(raw)
        return sorted(set(matches)), sorted(set(partial)), sorted(set(missing))

    def _build_learning_areas(self, missing: list[str]) -> list[str]:
        learning_areas = {
            'sql': ['SELECT queries', 'JOINs', 'GROUP BY', 'Subqueries', 'Window functions'],
            'python': ['Core syntax and data structures', 'Functions and modules', 'Testing basics', 'Async patterns'],
            'java': ['Classes and inheritance', 'Collections and streams', 'Exception handling', 'Testing strategies'],
            'javascript': ['Async/await', 'DOM or event handling', 'Modules and tooling', 'Testing'],
            'react': ['Components and props', 'State and effects', 'Hooks and data fetching', 'Accessibility'],
            'docker': ['Container basics', 'Dockerfile patterns', 'Compose workflows', 'Image optimization'],
            'aws': ['Core services', 'IAM and security', 'Deployments', 'Monitoring'],
            'fastapi': ['Route design', 'Dependency injection', 'Validation', 'API testing'],
            'postgresql': ['Schema design', 'Indexes', 'Transactions', 'Query tuning'],
            'excel': ['Formulas', 'Pivot tables', 'VLOOKUP/XLOOKUP', 'Data cleaning'],
            'machine learning': ['Model evaluation', 'Feature engineering', 'Bias and validation', 'Deployment basics'],
        }
        suggestions: list[str] = []
        for skill in missing:
            key = self._normalize(skill)
            for candidate, areas in learning_areas.items():
                if key in candidate or candidate in key:
                    suggestions.extend(areas)
                    break
            if not any(key in self._normalize(item) or self._normalize(item) in key for item in learning_areas):
                suggestions.append(f'Review core concepts for {skill}')
        return sorted(set(suggestions))[:8]

    def _build_skill_gap(self, candidate_skills: list[str], required_skills: list[str], preferred_skills: list[str] | None = None) -> dict[str, Any]:
        all_required = list(required_skills or []) + list(preferred_skills or [])
        matched, partial, missing = self._skill_overlap(all_required, candidate_skills)
        return {
            'matched_skills': matched,
            'missing_skills': missing,
            'partial_skills': partial,
            'suggested_learning_areas': self._build_learning_areas(missing + partial),
            'job_requirements_total': len(all_required),
        }

    def _build_resume_review(self, profile: dict[str, Any] | None) -> dict[str, Any]:
        if not profile:
            return {
                'summary_improvements': [{'current_issue': 'No resume profile was found.', 'suggested_improvement': 'Upload a resume to unlock personalized suggestions.', 'example_wording': 'Upload a resume to unlock personalized suggestions.'}],
                'experience_improvements': [],
                'skills_improvements': [],
                'project_improvements': [],
                'formatting_suggestions': [],
                'missing_information': ['Upload a resume to unlock personalized suggestions.'],
            }

        summary = profile.get('summary') or ''
        summary_improvements: list[dict[str, str]] = []
        if not summary or len(summary.strip()) < 40:
            summary_improvements.append({
                'current_issue': 'The summary is missing or too short to explain the candidate clearly.',
                'suggested_improvement': 'Add a concise summary that mentions the strongest role fit, core skills, and years of experience from the resume.',
                'example_wording': 'Product-minded software engineer with 4+ years of experience building reliable web applications and APIs using Python, SQL, and React.'
            })
        experience_items = profile.get('experience_json') or []
        experience_improvements: list[dict[str, str]] = []
        for item in experience_items:
            description = (item.get('description') or '').strip()
            title = (item.get('job_title') or 'Experience').strip()
            if not description:
                experience_improvements.append({
                    'current_issue': f'{title} does not include a clear impact statement.',
                    'suggested_improvement': 'Add 2–4 impact-focused bullets that explain what was delivered, how it was measured, and which tools were used.',
                    'example_wording': 'Built and shipped internal tooling that reduced manual reporting time and improved reliability for the team.'
                })

        skills = self._flatten_skills(profile)
        skills_improvements: list[dict[str, str]] = []
        if not skills:
            skills_improvements.append({
                'current_issue': 'No skills section was detected.',
                'suggested_improvement': 'List the candidate’s technical and transferable skills in a clean, scannable format that mirrors their strongest tools and workflows.',
                'example_wording': 'Technical Skills: Python, SQL, FastAPI, React, PostgreSQL'
            })

        projects = profile.get('projects_json') or []
        project_improvements: list[dict[str, str]] = []
        for item in projects:
            if not (item.get('description') or '').strip():
                project_improvements.append({
                    'current_issue': 'One or more project entries may be too brief to show impact.',
                    'suggested_improvement': 'Add a brief summary of the problem, the solution, the tools used, and the measurable outcome.',
                    'example_wording': 'Developed a dashboard to track onboarding metrics and reduced manual reporting time by 35%.'
                })

        formatting_suggestions = [
            'Keep the top section focused on the target role with a short summary, key skills, and recent experience.',
            'Use consistent date formats and keep bullet points concise and measurable when possible.',
            'Prioritize the most relevant technical skills near the top of the resume and match them to the target role.'
        ]

        missing_information = []
        for field in ('full_name', 'email', 'phone', 'location'):
            value = profile.get(field)
            if not value:
                missing_information.append(f'{field.replace("_", " ").title()} is missing or incomplete.')
        if not experience_items:
            missing_information.append('No experience entries were detected. Add role history with dates, company names, and scope.')
        if not (profile.get('education_json') or []):
            missing_information.append('Education details are missing. Add degree, institution, and date information if relevant.')

        return {
            'summary_improvements': summary_improvements,
            'experience_improvements': experience_improvements,
            'skills_improvements': skills_improvements,
            'project_improvements': project_improvements,
            'formatting_suggestions': formatting_suggestions,
            'missing_information': missing_information,
        }

    async def generate_resume_review(self, user: CurrentUser) -> dict[str, Any]:
        profile = await self._read_profile(user)
        return self._build_resume_review(profile)

    async def generate_skill_gap(self, user: CurrentUser, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        profile = await self._read_profile(user)
        candidate_skills = self._flatten_skills(profile)
        job_id = payload.get('job_id') if payload else None
        description = payload.get('job_description') if payload else None
        target_role = payload.get('target_role') if payload else None
        required = []
        preferred = []
        if job_id:
            requirements = await self._read_job_requirements(UUID(job_id), user)
            for row in requirements:
                skill_name = row.get('skill_name') or row.get('name')
                if not skill_name:
                    continue
                if row.get('skill_type') == 'preferred':
                    preferred.append(str(skill_name))
                else:
                    required.append(str(skill_name))
        if not required and description:
            text = description
            required = [token for token in re.findall(r"[A-Za-z][A-Za-z0-9+/.-]*", text) if token.lower() not in {'the', 'and', 'for', 'with', 'experience', 'work', 'role', 'job', 'skills', 'required', 'preferred'}][:20]
        if not required and target_role:
            required = [target_role]
        result = self._build_skill_gap(candidate_skills, required, preferred)
        return result

    async def generate_interview(self, user: CurrentUser, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        profile = await self._read_profile(user)
        interview_type = (payload or {}).get('interview_type', 'general')
        job_id = (payload or {}).get('job_id')
        description = (payload or {}).get('job_description') or ''
        requirements = []
        if job_id:
            requirements = [str(row.get('skill_name') or row.get('name') or '') for row in await self._read_job_requirements(UUID(job_id), user) if row.get('skill_name') or row.get('name')]
        skills = self._flatten_skills(profile)
        projects = profile.get('projects_json') or [] if profile else []
        project_names = [str(item.get('project_name') or 'Project') for item in projects if item.get('project_name')]

        technical = [
            'Describe a technical challenge you solved and how you validated the result.',
            'What trade-offs did you consider when choosing the tools or architecture for your recent work?',
            'Walk me through a project where you improved performance or reliability.'
        ] if interview_type in {'general', 'technical', 'job_specific'} else []
        behavioral = [
            'Tell me about yourself.',
            'Describe a difficult problem you solved.',
            'Tell me about a time you worked in a team.',
            'What do you do when priorities change unexpectedly?'
        ] if interview_type in {'general', 'behavioral', 'job_specific'} else []
        project_questions = [
            f"Tell me more about the {name} project and your role in it." for name in project_names[:3]
        ]
        skill_questions = [
            f"How have you used {skill} in your recent work?" for skill in skills[:5]
        ]
        requirement_questions = [
            f"How would you apply {skill} to this role?" for skill in requirements[:5]
        ]
        return {
            'interview_type': interview_type,
            'technical_questions': technical + skill_questions + requirement_questions,
            'behavioral_questions': behavioral,
            'project_questions': project_questions,
            'follow_up_questions': [
                'What was the problem you were solving?',
                'What decisions did you make and why?',
                'How did you measure whether the work was successful?',
                'What would you do differently next time?'
            ],
            'job_context': description[:400] if description else None,
        }

    async def chat(self, user: CurrentUser, message: str, session_id: UUID | None = None, session_type: str | None = None) -> dict[str, Any]:
        title = 'Career Assistant'
        if session_id:
            existing = await self._read_session(user, session_id)
            if existing:
                title = existing.get('title') or title
            else:
                session_id = None
        if session_id is None:
            session = await self._ensure_session(user, title or 'Career Assistant')
            session_id = UUID(str(session['id'])) if isinstance(session, dict) and session.get('id') else uuid4()
        stored_message = await self._write_message(user, session_id, 'user', message)
        assistant_response = self._build_chat_response(user, message)
        return {'session_id': str(session_id), 'message': stored_message, 'response': assistant_response}

    def _build_chat_response(self, user: CurrentUser, message: str) -> str:
        lowered = message.lower()
        if 'resume' in lowered and ('improve' in lowered or 'review' in lowered):
            return 'I can help you sharpen the resume summary, strengthen impact statements, and highlight the experience most relevant to your target role.'
        if 'skill' in lowered and ('gap' in lowered or 'missing' in lowered):
            return 'A skill-gap review is most useful when you compare your existing profile to a target job or job description. I can highlight matched skills, missing requirements, and neutral learning priorities.'
        if 'interview' in lowered:
            return 'I can prepare technical, behavioral, and project-specific questions, plus follow-up prompts based on your background and the role you are targeting.'
        if 'career' in lowered or 'guidance' in lowered:
            return 'Career guidance works best when we align your experience with your next role, identify the skills to develop, and define a realistic plan for interviews and applications.'
        return 'I can help you improve your resume, compare your profile to a target role, and prepare for interviews. Tell me which workflow you want to use.'

    async def list_sessions(self, user: CurrentUser) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f'{self.base_url}/rest/v1/career_assistant_sessions',
                params={'select': '*', 'candidate_id': f'eq.{user.id}', 'order': 'updated_at.desc'},
                headers=self._headers(user),
            )
            if response.status_code >= 400:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Career assistant sessions could not be loaded.')
            return response.json() or []

    async def get_session(self, user: CurrentUser, session_id: UUID) -> dict[str, Any]:
        session = await self._read_session(user, session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Session not found.')
        messages = await self._read_session_messages(user, session_id)
        return {'session': session, 'messages': messages}
