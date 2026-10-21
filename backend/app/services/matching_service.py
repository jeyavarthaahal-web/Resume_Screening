"""Authenticated RLS-preserving data orchestration for numerical matching."""
import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from app.ai.embedding_service import EmbeddingError, embedding_service
from app.ai.model_manager import ModelUnavailableError
from app.config import get_settings
from app.dependencies import CurrentUser
from app.matching.matching_engine import MatchingEngine, PreparedMatch
from app.schemas.matching import BulkMatchingResponse, MatchingCandidate, MatchingFailure, MatchingResult

logger = logging.getLogger(__name__)
MAX_BULK_CANDIDATES = 50


class MatchingPersistenceError(RuntimeError):
    pass


class MatchingService:
    def __init__(self, engine: MatchingEngine | None = None) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.supabase_url.rstrip("/")
        self.engine = engine or MatchingEngine(embedding_service)

    def _headers(self, user: CurrentUser, prefer: str | None = None) -> dict[str, str]:
        headers = {"apikey": self.settings.supabase_publishable_key, "Authorization": f"Bearer {user.access_token}", "Content-Type": "application/json"}
        if prefer: headers["Prefer"] = prefer
        return headers

    async def _client(self, user: CurrentUser) -> httpx.AsyncClient:
        if not self.base_url or not self.settings.supabase_publishable_key:
            raise HTTPException(status_code=503, detail="Matching data access is not configured on the server.")
        return httpx.AsyncClient(timeout=httpx.Timeout(25, connect=8), headers=self._headers(user))

    async def _require_role(self, client: httpx.AsyncClient, user: CurrentUser, role: str) -> None:
        try:
            response = await client.get(f"{self.base_url}/rest/v1/profiles", params={"select": "account_type", "id": f"eq.{user.id}"})
            if response.status_code == 401: raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
            if response.status_code != 200: raise HTTPException(status_code=502, detail="Your account permissions could not be verified.")
            rows = response.json()
            if not rows or rows[0].get("account_type") != role:
                raise HTTPException(status_code=403, detail="This action is not available to your account type.")
        except HTTPException: raise
        except (httpx.HTTPError, ValueError):
            raise HTTPException(status_code=503, detail="Your account permissions could not be verified.") from None

    async def _owned_job(self, client: httpx.AsyncClient, user: CurrentUser, job_id: UUID) -> dict[str, Any]:
        response = await client.get(f"{self.base_url}/rest/v1/jobs", params={
            "select": "id,recruiter_id,title,description,cleaned_description,summary,responsibilities,education_requirement,education_json,experience_min,experience_max,status",
            "id": f"eq.{job_id}", "recruiter_id": f"eq.{user.id}",
        })
        if response.status_code != 200: raise MatchingPersistenceError("The job could not be loaded.")
        rows = response.json()
        if not rows: raise HTTPException(status_code=404, detail="Job not found.")
        return rows[0]

    async def _requirements(self, client: httpx.AsyncClient, job_id: UUID) -> list[dict[str, Any]]:
        response = await client.get(f"{self.base_url}/rest/v1/job_requirements", params={
            "select": "skill_name,skill_type,importance", "job_id": f"eq.{job_id}", "order": "skill_type,skill_name",
        })
        if response.status_code != 200: raise MatchingPersistenceError("The job requirements could not be loaded.")
        return response.json()

    async def _candidate_rows(self, client: httpx.AsyncClient, job_id: UUID, resume_id: UUID | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"select": "job_id,candidate_id,resume_id,created_at", "job_id": f"eq.{job_id}", "order": "created_at.asc", "limit": MAX_BULK_CANDIDATES + 1}
        if resume_id: params["resume_id"] = f"eq.{resume_id}"
        response = await client.get(f"{self.base_url}/rest/v1/job_candidates", params=params)
        if response.status_code != 200: raise MatchingPersistenceError("Applied resumes could not be loaded.")
        rows = response.json()
        if len(rows) > MAX_BULK_CANDIDATES: raise HTTPException(status_code=413, detail="This job has more than 50 applications. Match smaller batches.")
        return rows

    async def _profiles(self, client: httpx.AsyncClient, applications: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        ids = list(dict.fromkeys(row["resume_id"] for row in applications))
        if not ids: return {}
        value_filter = "in.(" + ",".join(ids) + ")"
        resume_response = await client.get(f"{self.base_url}/rest/v1/resumes", params={
            "select": "id,candidate_id,status", "id": value_filter, "status": "eq.processed",
        })
        if resume_response.status_code != 200: raise MatchingPersistenceError("Applied resume status could not be checked.")
        processed_ids = {row["id"] for row in resume_response.json()}
        profile_response = await client.get(f"{self.base_url}/rest/v1/resume_profiles", params={
            "select": "resume_id,candidate_id,summary,years_experience,education_json,experience_json,skills_json,projects_json",
            "resume_id": value_filter,
        })
        if profile_response.status_code != 200: raise MatchingPersistenceError("Applied resume profiles could not be loaded.")
        profiles = {}
        for row in profile_response.json():
            if row.get("resume_id") in processed_ids and row.get("candidate_id"):
                profiles[row["resume_id"]] = row
        return profiles

    async def _save_results(self, client: httpx.AsyncClient, payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not payload: return []
        response = await client.post(f"{self.base_url}/rest/v1/screening_results", json=payload, headers={**client.headers, "Prefer": "return=representation"})
        if response.status_code not in (200, 201): raise MatchingPersistenceError("The matching results could not be saved.")
        return response.json()

    @staticmethod
    def _result_payload(job_id: UUID, resume_id: UUID, candidate_id: UUID, scores: dict[str, float]) -> dict[str, Any]:
        return {
            "job_id": str(job_id), "resume_id": str(resume_id), "candidate_id": str(candidate_id),
            "overall_score": scores["overall_score"], "semantic_score": scores["semantic_score"],
            "skills_score": scores["skill_score"], "experience_score": scores["experience_score"],
            "education_score": scores["education_score"], "projects_score": scores["project_score"],
        }

    @staticmethod
    def _as_result(row: dict[str, Any]) -> MatchingResult:
        return MatchingResult(
            job_id=row["job_id"], resume_id=row["resume_id"], candidate_id=row["candidate_id"],
            overall_score=row["overall_score"], semantic_score=row["semantic_score"],
            skill_score=row.get("skills_score", row.get("skill_score", 0)),
            experience_score=row["experience_score"], education_score=row["education_score"],
            project_score=row.get("projects_score", row.get("project_score", 0)), created_at=row.get("created_at"),
        )

    async def _load_context(self, client: httpx.AsyncClient, user: CurrentUser, job_id: UUID, resume_id: UUID | None = None):
        job = await self._owned_job(client, user, job_id)
        applications = await self._candidate_rows(client, job_id, resume_id)
        if resume_id and not applications: raise HTTPException(status_code=403, detail="This resume is not associated with the job.")
        requirements = await self._requirements(client, job_id)
        profiles = await self._profiles(client, applications)
        return job, requirements, applications, profiles

    async def list_candidates(self, user: CurrentUser, job_id: UUID) -> list[MatchingCandidate]:
        client = await self._client(user)
        try:
            await self._require_role(client, user, "recruiter")
            await self._owned_job(client, user, job_id)
            return [MatchingCandidate.model_validate(row) for row in await self._candidate_rows(client, job_id)]
        except HTTPException: raise
        except (httpx.HTTPError, MatchingPersistenceError, ValueError, KeyError):
            logger.exception("Matching candidate list failed for recruiter %s", user.id)
            raise HTTPException(status_code=502, detail="Applied resumes could not be loaded.") from None
        finally: await client.aclose()

    async def apply(self, user: CurrentUser, job_id: UUID, resume_id: UUID) -> MatchingCandidate:
        client = await self._client(user)
        try:
            await self._require_role(client, user, "job_seeker")
            job_response = await client.get(f"{self.base_url}/rest/v1/jobs", params={"select": "id,status", "id": f"eq.{job_id}", "status": "eq.published"})
            if job_response.status_code != 200: raise MatchingPersistenceError("The published job could not be checked.")
            if not job_response.json(): raise HTTPException(status_code=404, detail="Published job not found.")
            existing = await client.get(f"{self.base_url}/rest/v1/job_candidates", params={"select": "job_id,resume_id,candidate_id,created_at", "job_id": f"eq.{job_id}", "candidate_id": f"eq.{user.id}"})
            if existing.status_code != 200: raise MatchingPersistenceError("Your existing application could not be checked.")
            if existing.json():
                row = existing.json()[0]
                if row["resume_id"] != str(resume_id): raise HTTPException(status_code=409, detail="You have already applied to this job with another resume.")
                return MatchingCandidate.model_validate(row)
            resume_response = await client.get(f"{self.base_url}/rest/v1/resumes", params={"select": "id,candidate_id,status", "id": f"eq.{resume_id}", "candidate_id": f"eq.{user.id}", "status": "eq.processed"})
            if resume_response.status_code != 200: raise MatchingPersistenceError("Your resume could not be checked.")
            if not resume_response.json(): raise HTTPException(status_code=404, detail="Processed resume not found.")
            inserted = await client.post(f"{self.base_url}/rest/v1/job_candidates", json={"job_id": str(job_id), "candidate_id": str(user.id), "resume_id": str(resume_id)}, headers={**client.headers, "Prefer": "return=representation"})
            if inserted.status_code not in (200, 201) or not inserted.json(): raise MatchingPersistenceError("Your application could not be saved.")
            return MatchingCandidate.model_validate(inserted.json()[0])
        except HTTPException: raise
        except (httpx.HTTPError, MatchingPersistenceError, ValueError, KeyError):
            logger.exception("Job application association failed for candidate %s", user.id)
            raise HTTPException(status_code=502, detail="Your job application could not be saved. Please try again.") from None
        finally: await client.aclose()

    async def match_one(self, user: CurrentUser, job_id: UUID, resume_id: UUID) -> MatchingResult:
        client = await self._client(user)
        try:
            await self._require_role(client, user, "recruiter")
            job, requirements, applications, profiles = await self._load_context(client, user, job_id, resume_id)
            application = applications[0]
            profile = profiles.get(str(resume_id))
            if not profile: raise HTTPException(status_code=422, detail="The applied resume has no processed profile.")
            scores = await run_in_threadpool(self.engine.calculate, profile, job, requirements)
            rows = await self._save_results(client, [self._result_payload(job_id, resume_id, UUID(application["candidate_id"]), scores)])
            return self._as_result(rows[0])
        except HTTPException: raise
        except (ModelUnavailableError, EmbeddingError):
            logger.exception("Matching model failed for recruiter %s", user.id)
            raise HTTPException(status_code=503, detail="The matching model is unavailable. Check the model setup and retry.") from None
        except (httpx.HTTPError, MatchingPersistenceError, ValueError, KeyError, IndexError):
            logger.exception("Resume matching failed for recruiter %s", user.id)
            raise HTTPException(status_code=502, detail="This resume could not be matched. Please try again.") from None
        finally: await client.aclose()

    async def match_many(self, user: CurrentUser, job_id: UUID) -> BulkMatchingResponse:
        client = await self._client(user)
        try:
            await self._require_role(client, user, "recruiter")
            job, requirements, applications, profiles = await self._load_context(client, user, job_id)
            prepared: list[tuple[dict[str, Any], PreparedMatch]] = []
            failures: list[MatchingFailure] = []
            for application in applications:
                profile = profiles.get(str(application["resume_id"]))
                if not profile:
                    failures.append(MatchingFailure(resume_id=application["resume_id"], candidate_id=application["candidate_id"], message="The applied resume has no processed profile."))
                    continue
                prepared.append((application, self.engine.prepare(profile, job, requirements)))
            all_texts = [text for _, item in prepared for text in self.engine.embedding_texts(item)]
            await run_in_threadpool(self.engine.embeddings.encode_texts, all_texts)
            payload: list[dict[str, Any]] = []
            for application, item in prepared:
                try:
                    scores = await run_in_threadpool(self.engine.calculate_prepared, item)
                    payload.append(self._result_payload(job_id, UUID(application["resume_id"]), UUID(application["candidate_id"]), scores))
                except (ModelUnavailableError, EmbeddingError): raise
                except Exception:
                    logger.exception("One resume score failed in bulk for recruiter %s", user.id)
                    failures.append(MatchingFailure(resume_id=application["resume_id"], candidate_id=application["candidate_id"], message="This resume could not be scored."))
            rows = await self._save_results(client, payload)
            return BulkMatchingResponse(job_id=job_id, results=[self._as_result(row) for row in rows], failures=failures)
        except HTTPException: raise
        except (ModelUnavailableError, EmbeddingError):
            logger.exception("Bulk matching model failed for recruiter %s", user.id)
            raise HTTPException(status_code=503, detail="The matching model is unavailable. Check the model setup and retry.") from None
        except (httpx.HTTPError, MatchingPersistenceError, ValueError, KeyError):
            logger.exception("Bulk resume matching failed for recruiter %s", user.id)
            raise HTTPException(status_code=502, detail="Matching results could not be saved. Please try again.") from None
        finally: await client.aclose()

    async def get_result(self, user: CurrentUser, job_id: UUID, resume_id: UUID) -> MatchingResult:
        client = await self._client(user)
        try:
            await self._require_role(client, user, "recruiter")
            await self._owned_job(client, user, job_id)
            applications = await self._candidate_rows(client, job_id, resume_id)
            if not applications: raise HTTPException(status_code=403, detail="This resume is not associated with the job.")
            response = await client.get(f"{self.base_url}/rest/v1/screening_results", params={"select": "job_id,resume_id,candidate_id,overall_score,semantic_score,skills_score,experience_score,education_score,projects_score,created_at", "job_id": f"eq.{job_id}", "resume_id": f"eq.{resume_id}", "order": "created_at.desc", "limit": 1})
            if response.status_code != 200: raise MatchingPersistenceError("The saved matching result could not be loaded.")
            rows = response.json()
            if not rows: raise HTTPException(status_code=404, detail="No matching result has been saved yet.")
            return self._as_result(rows[0])
        except HTTPException: raise
        except (httpx.HTTPError, MatchingPersistenceError, ValueError, KeyError):
            logger.exception("Saved matching result load failed for recruiter %s", user.id)
            raise HTTPException(status_code=502, detail="The matching result could not be loaded.") from None
        finally: await client.aclose()

    async def list_results(self, user: CurrentUser, job_id: UUID) -> list[MatchingResult]:
        """Load latest saved scores in pages, without one request per applied resume."""
        client = await self._client(user)
        try:
            await self._require_role(client, user, "recruiter")
            await self._owned_job(client, user, job_id)
            latest: dict[str, MatchingResult] = {}
            offset, page_size = 0, 500
            while True:
                response = await client.get(
                    f"{self.base_url}/rest/v1/screening_results",
                    params={
                        "select": "job_id,resume_id,candidate_id,overall_score,semantic_score,skills_score,experience_score,education_score,projects_score,created_at",
                        "job_id": f"eq.{job_id}", "order": "created_at.desc", "limit": page_size,
                    },
                    headers={"Range": f"{offset}-{offset + page_size - 1}"},
                )
                if response.status_code != 200: raise MatchingPersistenceError("Saved matching results could not be loaded.")
                rows = response.json()
                for row in rows:
                    latest.setdefault(row["resume_id"], self._as_result(row))
                if len(rows) < page_size: break
                offset += page_size
            return list(latest.values())
        except HTTPException: raise
        except (httpx.HTTPError, MatchingPersistenceError, ValueError, KeyError):
            logger.exception("Saved matching results load failed for recruiter %s", user.id)
            raise HTTPException(status_code=502, detail="Matching results could not be loaded.") from None
        finally: await client.aclose()


matching_service = MatchingService()
