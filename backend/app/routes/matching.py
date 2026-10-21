"""Recruiter matching endpoints and the candidate-owned application link."""
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import CurrentUser, require_current_user
from app.schemas.matching import BulkMatchingResponse, MatchApplicationRequest, MatchingCandidate, MatchingResult
from app.services.matching_service import matching_service

router = APIRouter(prefix="/api/matching", tags=["matching"])


@router.post("/jobs/{job_id}/apply", response_model=MatchingCandidate, status_code=status.HTTP_201_CREATED,
             summary="Associate a processed resume with a published job")
async def apply_resume(job_id: UUID, request: MatchApplicationRequest, user: CurrentUser = Depends(require_current_user)):
    """The verified job-seeker identity, not a client candidate UUID, owns the application."""
    return await matching_service.apply(user, job_id, request.resume_id)


@router.get("/jobs/{job_id}/candidates", response_model=list[MatchingCandidate], summary="List resumes associated with the recruiter's job")
async def list_matching_candidates(job_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await matching_service.list_candidates(user, job_id)


@router.post("/jobs/{job_id}/resumes/{resume_id}", response_model=MatchingResult, summary="Calculate and save a match score")
async def match_resume_to_job(job_id: UUID, resume_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await matching_service.match_one(user, job_id, resume_id)


@router.get("/jobs/{job_id}/resumes/{resume_id}", response_model=MatchingResult, summary="Load the latest saved numerical match")
async def get_matching_result(job_id: UUID, resume_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await matching_service.get_result(user, job_id, resume_id)


@router.get("/jobs/{job_id}/results", response_model=list[MatchingResult], summary="Load latest saved numerical matches for a job")
async def list_matching_results(job_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await matching_service.list_results(user, job_id)


@router.post("/jobs/{job_id}", response_model=BulkMatchingResponse, summary="Match up to 50 applied resumes")
async def match_candidates_to_job(job_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await matching_service.match_many(user, job_id)
