from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import CurrentUser, require_current_user
from app.schemas.recruiter import CompareInput, NoteInput, NoteUpdate
from app.services.recruiter_workspace_service import recruiter_workspace_service as workspace

router = APIRouter(prefix="/api/recruiter", tags=["recruiter workspace"])


@router.get("/dashboard")
async def dashboard(user: CurrentUser = Depends(require_current_user)):
    return await workspace.dashboard(user)


@router.get("/jobs")
async def jobs(user: CurrentUser = Depends(require_current_user)):
    return await workspace.jobs(user)


@router.get("/jobs/{job_id}")
async def job(job_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await workspace.job(user, job_id)


@router.get("/jobs/{job_id}/candidates")
async def candidates(
    job_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = Query("", max_length=100),
    score: str = Query("all", pattern="^(all|80\\+|70\\+|60\\+|below60)$"),
    shortlist: str = Query("all", pattern="^(all|yes|no)$"),
    experience: str = Query("all", pattern="^(all|1\\+|3\\+|5\\+)$"),
    skill: str = Query("", max_length=160),
    sort: str = Query("recent", pattern="^(recent|updated|experience|score)$"),
    user: CurrentUser = Depends(require_current_user),
):
    return await workspace.candidates(user, job_id, page, page_size, q, score, shortlist, experience, skill, sort)


@router.get("/jobs/{job_id}/candidates/{candidate_id}")
async def candidate(job_id: UUID, candidate_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await workspace.candidate(user, job_id, candidate_id)


@router.get("/jobs/{job_id}/candidates/{candidate_id}/resumes/{resume_id}/download")
async def resume_download(job_id: UUID, candidate_id: UUID, resume_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await workspace.resume_download(user, job_id, candidate_id, resume_id)


@router.get("/jobs/{job_id}/shortlist")
async def shortlist(job_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await workspace.shortlist(user, job_id)


@router.post("/jobs/{job_id}/shortlist/{candidate_id}")
async def add_shortlist(job_id: UUID, candidate_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await workspace.change_shortlist(user, job_id, candidate_id, True)


@router.delete("/jobs/{job_id}/shortlist/{candidate_id}")
async def remove_shortlist(job_id: UUID, candidate_id: UUID, user: CurrentUser = Depends(require_current_user)):
    return await workspace.change_shortlist(user, job_id, candidate_id, False)


@router.post("/candidates/{candidate_id}/notes")
async def create_note(candidate_id: UUID, payload: NoteInput, user: CurrentUser = Depends(require_current_user)):
    return await workspace.create_note(user, candidate_id, payload.job_id, payload.note)


@router.patch("/notes/{note_id}")
async def update_note(note_id: UUID, payload: NoteUpdate, user: CurrentUser = Depends(require_current_user)):
    return await workspace.update_note(user, note_id, payload.note)


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: UUID, user: CurrentUser = Depends(require_current_user)):
    await workspace.update_note(user, note_id)


@router.post("/compare")
async def compare(payload: CompareInput, user: CurrentUser = Depends(require_current_user)):
    return await workspace.compare(user, payload.job_id, payload.candidate_ids)
