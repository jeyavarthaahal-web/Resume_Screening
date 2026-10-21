"""Authorization-preserving persistence and retrieval for explainability data."""
import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.dependencies import CurrentUser
from app.ranking.explainability_engine import build_explanation
from app.schemas.ranking import BulkRankingExplanation, RankingExplanation, RankingFailure
from app.services.matching_service import MatchingPersistenceError, matching_service

logger = logging.getLogger(__name__)
_RESULT_SELECT = "id,job_id,resume_id,candidate_id,overall_score,semantic_score,skills_score,experience_score,education_score,projects_score,matched_skills,partial_skills,missing_skills,strengths,gaps,evidence,score_breakdown,explanation,ranking_details,created_at"
MAX_BULK_RESULT_HISTORY = 5000


class RankingService:
    def __init__(self) -> None:
        self.matching = matching_service

    async def _result_rows(self, client: httpx.AsyncClient, job_id: UUID, resume_ids: list[str] | None = None) -> list[dict[str, Any]]:
        single_resume = resume_ids is not None and len(resume_ids) == 1
        page_size = 1 if single_resume else 500
        params: dict[str, Any] = {
            "select": _RESULT_SELECT, "job_id": f"eq.{job_id}",
            "order": "created_at.desc,id.desc", "limit": page_size,
        }
        if resume_ids is not None:
            if not resume_ids:
                return []
            params["resume_id"] = "in.(" + ",".join(resume_ids) + ")"
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = await client.get(
                f"{self.matching.base_url}/rest/v1/screening_results", params=params,
                headers={"Range": f"{offset}-{offset + page_size - 1}"},
            )
            if response.status_code != 200:
                raise MatchingPersistenceError("Saved matching results could not be loaded.")
            page = response.json()
            rows.extend(page)
            if len(page) < page_size or single_resume:
                return rows
            if offset + len(page) >= MAX_BULK_RESULT_HISTORY:
                probe = await client.get(
                    f"{self.matching.base_url}/rest/v1/screening_results",
                    params={**params, "limit": 1},
                    headers={"Range": f"{MAX_BULK_RESULT_HISTORY}-{MAX_BULK_RESULT_HISTORY}"},
                )
                if probe.status_code != 200:
                    raise MatchingPersistenceError("Saved matching results could not be loaded.")
                if probe.json():
                    raise HTTPException(status_code=413, detail="There is too much score history to explain safely in one batch.")
                return rows
            offset += page_size

    async def _associated_context(self, client: httpx.AsyncClient, user: CurrentUser, job_id: UUID, resume_id: UUID | None = None):
        await self.matching._require_role(client, user, "recruiter")
        job = await self.matching._owned_job(client, user, job_id)
        applications = await self.matching._candidate_rows(client, job_id, resume_id)
        if resume_id and not applications:
            raise HTTPException(status_code=403, detail="This resume is not associated with the job.")
        return job, applications

    @staticmethod
    def _cached(row: dict[str, Any]) -> RankingExplanation | None:
        details = row.get("ranking_details")
        if not row.get("explanation") or not isinstance(details, dict) or not details:
            return None
        try:
            return RankingExplanation.model_validate({
                **row, **details,
                "score_breakdown": row.get("score_breakdown") or {},
                "matched_skills": row.get("matched_skills") or [],
                "partial_skills": row.get("partial_skills") or [],
                "missing_skills": row.get("missing_skills") or [],
                "strengths": row.get("strengths") or [], "gaps": row.get("gaps") or [],
                "evidence": row.get("evidence") or [],
            })
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _payload(explanation: RankingExplanation) -> dict[str, Any]:
        value = explanation.model_dump(mode="json")
        return {
            "matched_skills": value["matched_skills"], "partial_skills": value["partial_skills"],
            "missing_skills": value["missing_skills"], "strengths": value["strengths"],
            "gaps": value["gaps"], "evidence": value["evidence"],
            "score_breakdown": value["score_breakdown"], "explanation": value["explanation"],
            "ranking_details": {key: value[key] for key in (
                "experience_context", "education_context", "relevant_projects", "data_quality", "data_quality_note", "generated_at",
            )},
        }

    async def _persist(self, client: httpx.AsyncClient, row: dict[str, Any], explanation: RankingExplanation) -> None:
        response = await client.patch(
            f"{self.matching.base_url}/rest/v1/screening_results",
            params={"id": f"eq.{row['id']}"}, json=self._payload(explanation),
            headers={**client.headers, "Prefer": "return=minimal"},
        )
        if response.status_code not in (200, 204):
            raise MatchingPersistenceError("The explanation could not be saved.")

    async def _generate(self, client: httpx.AsyncClient, row: dict[str, Any], profile: dict[str, Any], job: dict[str, Any], requirements: list[dict[str, Any]]) -> RankingExplanation:
        expected_candidate = str(row.get("candidate_id"))
        if not all(row.get(key) is not None for key in ("overall_score", "semantic_score", "skills_score", "experience_score", "education_score", "projects_score")):
            raise HTTPException(status_code=422, detail="The saved matching result is incomplete and cannot be explained.")
        try:
            explanation = build_explanation(row, profile, job, requirements)
        except (KeyError, TypeError, ValueError):
            logger.exception("Could not explain result %s for candidate %s", row.get("id"), expected_candidate)
            raise HTTPException(status_code=422, detail="The saved result or extracted profile is incomplete.") from None
        await self._persist(client, row, explanation)
        return explanation

    async def get_explanation(self, user: CurrentUser, job_id: UUID, resume_id: UUID, refresh: bool = False) -> RankingExplanation:
        client = await self.matching._client(user)
        try:
            job, applications = await self._associated_context(client, user, job_id, resume_id)
            results = await self._result_rows(client, job_id, [str(resume_id)])
            row = next((item for item in results if item.get("resume_id") == str(resume_id)), None)
            if not row:
                raise HTTPException(status_code=404, detail="No Task 6 matching result exists for this resume and job.")
            application = next(item for item in applications if item["resume_id"] == str(resume_id))
            if row.get("candidate_id") != application.get("candidate_id"):
                raise HTTPException(status_code=403, detail="The saved result does not match the job application.")
            cached = None if refresh else self._cached(row)
            if cached:
                return cached
            profiles = await self.matching._profiles(client, applications)
            profile = profiles.get(str(resume_id))
            if not profile or profile.get("candidate_id") != application.get("candidate_id"):
                raise HTTPException(status_code=422, detail="The applied resume has no authorized processed profile.")
            requirements = await self.matching._requirements(client, job_id)
            return await self._generate(client, row, profile, job, requirements)
        except HTTPException:
            raise
        except (httpx.HTTPError, MatchingPersistenceError, ValueError, KeyError, StopIteration):
            logger.exception("Ranking explanation load failed for recruiter %s", user.id)
            raise HTTPException(status_code=502, detail="The explanation could not be loaded.") from None
        finally:
            await client.aclose()

    async def explain_job(self, user: CurrentUser, job_id: UUID) -> BulkRankingExplanation:
        client = await self.matching._client(user)
        try:
            job, applications = await self._associated_context(client, user, job_id)
            requirements = await self.matching._requirements(client, job_id)
            profiles = await self.matching._profiles(client, applications)
            application_by_resume = {str(item["resume_id"]): item for item in applications}
            results = await self._result_rows(client, job_id, list(application_by_resume))
            latest_by_resume: dict[str, dict[str, Any]] = {}
            for row in results:
                latest_by_resume.setdefault(str(row.get("resume_id")), row)
            explanations: list[RankingExplanation] = []
            failures: list[RankingFailure] = []
            for resume_id, application in application_by_resume.items():
                row = latest_by_resume.get(resume_id)
                profile = profiles.get(resume_id)
                if not row:
                    failures.append(RankingFailure(resume_id=resume_id, candidate_id=application["candidate_id"], message="No Task 6 matching result exists for this resume."))
                    continue
                if row.get("candidate_id") != application.get("candidate_id") or not profile or profile.get("candidate_id") != application.get("candidate_id"):
                    failures.append(RankingFailure(resume_id=resume_id, candidate_id=application["candidate_id"], message="The authorized processed resume profile is unavailable."))
                    continue
                try:
                    explanations.append(await self._generate(client, row, profile, job, requirements))
                except HTTPException as exc:
                    failures.append(RankingFailure(resume_id=resume_id, candidate_id=application["candidate_id"], message=exc.detail))
                except (httpx.HTTPError, MatchingPersistenceError, ValueError, KeyError, TypeError):
                    logger.exception("Bulk explainability failed for resume %s", resume_id)
                    failures.append(RankingFailure(resume_id=resume_id, candidate_id=application["candidate_id"], message="This result could not be explained."))
            return BulkRankingExplanation(job_id=job_id, results=explanations, failures=failures)
        except HTTPException:
            raise
        except (httpx.HTTPError, MatchingPersistenceError, ValueError, KeyError):
            logger.exception("Bulk ranking explanation failed for recruiter %s", user.id)
            raise HTTPException(status_code=502, detail="Ranking explanations could not be generated.") from None
        finally:
            await client.aclose()


ranking_service = RankingService()
