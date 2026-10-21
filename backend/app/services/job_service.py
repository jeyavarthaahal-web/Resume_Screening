"""Supabase PostgREST job persistence using the recruiter's JWT, preserving RLS."""
import logging
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.dependencies import CurrentUser
from app.nlp.job_extractor import SKILLS, extract_job_profile
from app.schemas.job import JobCreateRequest, JobResponse, JobStructuredProfile

logger = logging.getLogger(__name__)

class JobPersistenceError(RuntimeError): pass

class JobService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.supabase_url.rstrip("/")

    def _headers(self, user: CurrentUser, prefer: str | None = None) -> dict[str, str]:
        headers = {"apikey": self.settings.supabase_publishable_key, "Authorization": f"Bearer {user.access_token}", "Content-Type": "application/json"}
        if prefer: headers["Prefer"] = prefer
        return headers

    async def _client(self, user: CurrentUser) -> httpx.AsyncClient:
        if not self.base_url or not self.settings.supabase_publishable_key:
            raise HTTPException(status_code=503, detail="Job storage is not configured on the server.")
        return httpx.AsyncClient(timeout=httpx.Timeout(20, connect=8), headers=self._headers(user))

    async def _ensure_recruiter(self, client: httpx.AsyncClient, user: CurrentUser) -> None:
        try:
            response = await client.get(f"{self.base_url}/rest/v1/profiles", params={"select": "account_type", "id": f"eq.{user.id}"})
        except (httpx.HTTPError, ValueError):
            raise HTTPException(status_code=503, detail="Could not verify recruiter access.") from None
        if response.status_code == 401: raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
        if response.status_code != 200: raise HTTPException(status_code=502, detail="Recruiter profile could not be verified.")
        rows = response.json()
        if not rows or rows[0].get("account_type") != "recruiter": raise HTTPException(status_code=403, detail="Job management is available to recruiter accounts.")

    async def _requirements(self, client: httpx.AsyncClient, job_id: str) -> list[dict]:
        response = await client.get(f"{self.base_url}/rest/v1/job_requirements", params={"select": "skill_name,skill_type", "job_id": f"eq.{job_id}", "order": "skill_type,skill_name"})
        if response.status_code != 200: raise JobPersistenceError("Job requirements could not be loaded.")
        return [{"name": r["skill_name"], "category": SKILLS.get(r["skill_name"], (None,))[0], "importance": "preferred" if r["skill_type"] in ("preferred", "nice_to_have") else "required"} for r in response.json()]

    async def _hydrate(self, client: httpx.AsyncClient, row: dict) -> JobResponse:
        values = dict(row)
        values["requirements"] = await self._requirements(client, str(row["id"]))
        return JobResponse.model_validate(values)

    async def list_jobs(self, user: CurrentUser) -> list[JobResponse]:
        client = await self._client(user)
        try:
            await self._ensure_recruiter(client, user)
            response = await client.get(f"{self.base_url}/rest/v1/jobs", params={"select": "*", "recruiter_id": f"eq.{user.id}", "order": "created_at.desc"})
            if response.status_code != 200: raise JobPersistenceError("Jobs could not be loaded.")
            return [await self._hydrate(client, row) for row in response.json()]
        except HTTPException: raise
        except (httpx.HTTPError, JobPersistenceError, ValueError, KeyError):
            logger.exception("Recruiter job list request failed for %s", user.id)
            raise HTTPException(status_code=502, detail="Jobs could not be loaded. Please try again.") from None
        finally: await client.aclose()


    async def get_job(self, user: CurrentUser, job_id: str) -> JobResponse:
        client = await self._client(user)
        try:
            await self._ensure_recruiter(client, user)
            response = await client.get(f"{self.base_url}/rest/v1/jobs", params={"select": "*", "id": f"eq.{job_id}", "recruiter_id": f"eq.{user.id}"})
            if response.status_code != 200: raise JobPersistenceError("Job could not be loaded.")
            rows = response.json()
            if not rows: raise HTTPException(status_code=404, detail="Job not found.")
            return await self._hydrate(client, rows[0])
        except HTTPException: raise
        except (httpx.HTTPError, JobPersistenceError, ValueError, KeyError):
            logger.exception("Recruiter job detail request failed for %s", user.id)
            raise HTTPException(status_code=502, detail="Job could not be loaded. Please try again.") from None
        finally: await client.aclose()


    async def create_job(self, user: CurrentUser, request: JobCreateRequest) -> JobResponse:
        client = await self._client(user)
        job_id = str(uuid4())
        try:
            await self._ensure_recruiter(client, user)
            extracted = request.profile or JobStructuredProfile.model_validate(extract_job_profile(request.description))
            min_exp = request.experience_min if request.experience_min is not None else extracted.minimum_experience
            max_exp = request.experience_max if request.experience_max is not None else extracted.maximum_experience
            education = extracted.education_requirement.model_dump(mode="json") if extracted.education_requirement else None
            payload = {"id": job_id, "recruiter_id": str(user.id), "title": request.title, "department": request.department or extracted.department,
                "description": request.description, "cleaned_description": extracted.cleaned_description or request.description,
                "location": request.location or extracted.location, "employment_type": request.employment_type or extracted.employment_type,
                "work_mode": request.work_mode or extracted.work_mode, "experience_min": min_exp, "experience_max": max_exp,
                "education_requirement": request.education_requirement or ", ".join((education or {}).get("degrees", [])) or None,
                "summary": extracted.summary, "responsibilities": extracted.responsibilities, "education_json": education,
                "certifications_json": extracted.certifications, "benefits_json": extracted.benefits, "analysis_status": "analyzed", "status": request.status}
            inserted = await client.post(f"{self.base_url}/rest/v1/jobs", json=payload, headers={**self._headers(user), "Prefer": "return=representation"})
            if inserted.status_code not in (200, 201) or not inserted.json(): raise JobPersistenceError("Job could not be saved.")
            skills: dict[str, str] = {}
            for skill in extracted.required_skills: skills[skill.name] = "required"
            for skill in extracted.preferred_skills: skills.setdefault(skill.name, "preferred")
            if skills:
                req_payload = [{"job_id": job_id, "skill_name": name, "skill_type": importance, "importance": 4 if importance == "required" else 2} for name, importance in skills.items()]
                saved = await client.post(f"{self.base_url}/rest/v1/job_requirements", json=req_payload, headers={**self._headers(user), "Prefer": "return=minimal"})
                if saved.status_code not in (200, 201, 204):
                    await client.delete(f"{self.base_url}/rest/v1/jobs", params={"id": f"eq.{job_id}", "recruiter_id": f"eq.{user.id}"})
                    raise JobPersistenceError("Job requirements could not be saved.")
            return await self._hydrate(client, inserted.json()[0])
        except HTTPException: raise
        except (httpx.HTTPError, JobPersistenceError, ValueError, KeyError):
            logger.exception("Recruiter job creation failed for %s", user.id)
            raise HTTPException(status_code=502, detail="The job could not be saved. Please try again.") from None
        finally: await client.aclose()

    async def update_job(self, user: CurrentUser, job_id: str, changes: dict) -> JobResponse:
        client = await self._client(user)
        try:
            await self._ensure_recruiter(client, user)
            response = await client.patch(f"{self.base_url}/rest/v1/jobs", params={"id": f"eq.{job_id}", "recruiter_id": f"eq.{user.id}"}, json=changes, headers={**self._headers(user), "Prefer": "return=representation"})
            if response.status_code not in (200, 204): raise JobPersistenceError("Job could not be updated.")
            if not response.json(): raise HTTPException(status_code=404, detail="Job not found.")
            return await self._hydrate(client, response.json()[0])
        except HTTPException: raise
        except (httpx.HTTPError, JobPersistenceError, ValueError, KeyError):
            logger.exception("Recruiter job update failed for %s", user.id)
            raise HTTPException(status_code=502, detail="The job could not be updated. Please try again.") from None
        finally: await client.aclose()

    async def delete_job(self, user: CurrentUser, job_id: str) -> None:
        client = await self._client(user)
        try:
            await self._ensure_recruiter(client, user)
            response = await client.delete(f"{self.base_url}/rest/v1/jobs", params={"id": f"eq.{job_id}", "recruiter_id": f"eq.{user.id}"}, headers={**self._headers(user), "Prefer": "return=representation"})
            if response.status_code not in (200, 204): raise JobPersistenceError("Job could not be deleted.")
            if not response.content or not response.json(): raise HTTPException(status_code=404, detail="Job not found.")
        except HTTPException: raise
        except (httpx.HTTPError, JobPersistenceError, ValueError):
            logger.exception("Recruiter job deletion failed for %s", user.id)
            raise HTTPException(status_code=502, detail="The job could not be deleted. Please try again.") from None
        finally: await client.aclose()


job_service = JobService()
