"""Recruiter-only job description analysis and management endpoints."""
import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from starlette.concurrency import run_in_threadpool
from app.dependencies import CurrentUser, require_current_user
from app.nlp.job_cleaner import clean_job_text
from app.nlp.job_extractor import extract_job_profile
from app.parsers.base import ResumeParserError
from app.parsers.job_document_parser import JobDocumentParser
from app.schemas.job import JobAnalysisResponse, JobCreateRequest, JobResponse, JobUpdateRequest
from app.services.job_service import job_service
from app.utils.file_validation import MAX_RESUME_BYTES, UploadValidationError, validate_resume_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])
document_parser = JobDocumentParser()

@router.post("/analyze", response_model=JobAnalysisResponse, summary="Analyze a pasted or uploaded job description")
async def analyze_job_description(description: str | None = Form(default=None), file: UploadFile | None = File(default=None), current_user: CurrentUser = Depends(require_current_user)) -> JobAnalysisResponse:
    client = await job_service._client(current_user)
    try:
        await job_service._ensure_recruiter(client, current_user)
    finally: await client.aclose()
    if bool(description and description.strip()) == bool(file):
        raise HTTPException(status_code=422, detail="Provide either job description text or one PDF/DOCX file.")
    try:
        if file:
            data = await file.read(MAX_RESUME_BYTES + 1)
            if len(data) > MAX_RESUME_BYTES: raise HTTPException(status_code=413, detail="The job description file exceeds the 10 MB limit.")
            upload = validate_resume_upload(file.filename, data)
            parsed = await run_in_threadpool(document_parser.parse, upload.extension, data)
            raw = parsed.text
        else:
            raw = description or ""
        cleaned = clean_job_text(raw)
        if len(cleaned) < 40: raise HTTPException(status_code=422, detail="Add a little more detail to the job description before analyzing it.")
        if len(cleaned) > 50000: raise HTTPException(status_code=413, detail="The job description exceeds the 50,000 character limit.")
        profile = await run_in_threadpool(extract_job_profile, raw)
        return JobAnalysisResponse.model_validate({**profile, "raw_description": raw, "cleaned_description": cleaned})
    except UploadValidationError as error:
        raise HTTPException(status_code=422, detail=str(error).replace("resume", "job description")) from error
    except ResumeParserError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except HTTPException: raise
    except Exception:
        logger.exception("Unexpected job description analysis failure for %s", current_user.id)
        raise HTTPException(status_code=500, detail="We could not analyze this job description. Please try again.") from None
    finally:
        if file: await file.close()

@router.get("", response_model=list[JobResponse], summary="List the recruiter's jobs")
async def list_jobs(user: CurrentUser = Depends(require_current_user)): return await job_service.list_jobs(user)

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED, summary="Create a recruiter-owned job")
async def create_job(request: JobCreateRequest, user: CurrentUser = Depends(require_current_user)): return await job_service.create_job(user, request)

@router.get("/{job_id}", response_model=JobResponse, summary="Get one recruiter-owned job")
async def get_job(job_id: str, user: CurrentUser = Depends(require_current_user)): return await job_service.get_job(user, job_id)

@router.put("/{job_id}", response_model=JobResponse, summary="Update a recruiter-owned job")
async def update_job(job_id: str, request: JobUpdateRequest, user: CurrentUser = Depends(require_current_user)):
    changes = request.model_dump(exclude_unset=True)
    if "title" in changes and changes["title"] is not None: changes["title"] = changes["title"].strip()
    return await job_service.update_job(user, job_id, changes)

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a recruiter-owned job")
async def delete_job(job_id: str, user: CurrentUser = Depends(require_current_user)):
    await job_service.delete_job(user, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
