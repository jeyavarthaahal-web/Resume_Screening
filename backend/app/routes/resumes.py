"""Authenticated resume upload and deterministic extraction endpoint."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.dependencies import CurrentUser, require_current_user
from app.nlp.resume_cleaner import clean_resume_text
from app.nlp.resume_extractor import extract_resume_profile
from app.parsers.base import ResumeParserError
from app.schemas.resume import ResumeUploadResponse
from app.services.resume_service import ResumeService
from app.utils.file_validation import MAX_RESUME_BYTES, UploadValidationError, validate_resume_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/resumes', tags=['resumes'])
resume_service = ResumeService()


@router.post(
    '/upload',
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Upload and process a resume',
    description=(
        'Requires a Supabase access token in the Authorization: Bearer header. '
        'Accepts one PDF or DOCX file up to 10 MB. The candidate identity is '
        'verified with Supabase Auth and all Storage/PostgREST writes use that '
        'user token, so Task 3 RLS remains active. No OCR is performed.'
    ),
    responses={
        401: {'description': 'Missing, invalid, or expired Supabase session'},
        403: {'description': 'Uploads require a job seeker account'},
        413: {'description': 'File exceeds the 10 MB limit'},
        422: {'description': 'Unsupported, invalid, or unreadable resume'},
        502: {'description': 'Supabase Storage or database could not save the result'},
        503: {'description': 'Supabase backend configuration is missing or unavailable'},
    },
)
async def upload_resume(
    file: UploadFile = File(..., description='One PDF or DOCX file (maximum 10 MB)'),
    current_user: CurrentUser = Depends(require_current_user),
) -> ResumeUploadResponse:
    try:
        file_bytes = await file.read(MAX_RESUME_BYTES + 1)
        if len(file_bytes) > MAX_RESUME_BYTES:
            raise HTTPException(status_code=413, detail='The file is too large. The maximum resume size is 10 MB.')
        upload = validate_resume_upload(file.filename, file_bytes)
        document = await run_in_threadpool(resume_service.parse, upload.extension, file_bytes)
        cleaned_text = clean_resume_text(document.text)
        if not cleaned_text:
            raise HTTPException(status_code=422, detail='No readable text was found in this resume.')
        profile, _sections = await run_in_threadpool(extract_resume_profile, cleaned_text)
        return await resume_service.save_processed_resume(
            current_user,
            upload,
            file_bytes,
            document.text,
            profile,
            document,
        )
    except UploadValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ResumeParserError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        logger.exception('Unexpected resume upload failure for user %s.', current_user.id)
        raise HTTPException(status_code=500, detail='We could not process this resume. Please try again.') from error
    finally:
        await file.close()
