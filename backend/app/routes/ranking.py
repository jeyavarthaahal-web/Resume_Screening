"""Recruiter-only deterministic explanations for saved matching results."""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, require_current_user
from app.schemas.ranking import BulkRankingExplanation, RankingExplanation
from app.services.ranking_service import ranking_service

router = APIRouter(prefix="/api/ranking", tags=["ranking"])


@router.get("/jobs/{job_id}/resumes/{resume_id}", response_model=RankingExplanation, summary="Retrieve or generate a persisted match explanation")
async def get_explanation(job_id: UUID, resume_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await ranking_service.get_explanation(user, job_id, resume_id)


@router.post("/jobs/{job_id}/resumes/{resume_id}/explain", response_model=RankingExplanation, summary="Refresh an explanation from the saved Task 6 score")
async def refresh_explanation(job_id: UUID, resume_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await ranking_service.get_explanation(user, job_id, resume_id, refresh=True)


@router.post("/jobs/{job_id}/explain", response_model=BulkRankingExplanation, summary="Explain saved results for up to 50 applied resumes")
async def explain_job_results(job_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await ranking_service.explain_job(user, job_id)
