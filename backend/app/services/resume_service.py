"""RLS-respecting Supabase Storage/PostgREST writes for processed resumes."""

import logging
from urllib.parse import quote
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.dependencies import CurrentUser
from app.parsers.base import ParsedDocument
from app.parsers.docx_parser import DOCXResumeParser
from app.parsers.pdf_parser import PDFResumeParser
from app.schemas.resume import ParserMetadata, ResumeProfile, ResumeRecord, ResumeUploadResponse
from app.utils.file_validation import ValidatedResume

logger = logging.getLogger(__name__)
BUCKET_NAME = 'talentiq-resumes'


class ResumePersistenceError(RuntimeError):
    pass


class ResumeService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.supabase_url.rstrip('/')

    def parse(self, extension: str, file_bytes: bytes) -> ParsedDocument:
        parser = PDFResumeParser() if extension == '.pdf' else DOCXResumeParser()
        return parser.parse(file_bytes)

    def _headers(self, user: CurrentUser, *, content_type: str | None = None, prefer: str | None = None) -> dict[str, str]:
        headers = {
            'apikey': self.settings.supabase_publishable_key,
            'Authorization': f'Bearer {user.access_token}',
        }
        if content_type:
            headers['Content-Type'] = content_type
        if prefer:
            headers['Prefer'] = prefer
        return headers

    async def _account_type(self, client: httpx.AsyncClient, user: CurrentUser) -> str:
        response = await client.get(
            f'{self.base_url}/rest/v1/profiles',
            params={'select': 'account_type', 'id': f'eq.{user.id}'},
            headers=self._headers(user),
        )
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail='Your session has expired. Sign in again to upload a resume.')
        if response.status_code == 403:
            raise HTTPException(status_code=403, detail='Your account cannot access the resume profile.')
        if response.status_code >= 500:
            raise ResumePersistenceError('Profile lookup failed.')
        if response.status_code != 200:
            raise ResumePersistenceError('Profile lookup was rejected.')
        rows = response.json()
        return rows[0].get('account_type', '') if rows else ''

    async def _cleanup(self, client: httpx.AsyncClient, user: CurrentUser, object_path: str, resume_id: UUID, has_resume: bool, object_uploaded: bool) -> None:
        if has_resume or object_uploaded:
            try:
                deleted = await client.delete(
                    f'{self.base_url}/rest/v1/resumes',
                    params={'id': f'eq.{resume_id}'},
                    headers=self._headers(user),
                )
                if deleted.status_code >= 400:
                    raise ResumePersistenceError('Resume metadata rollback failed.')
            except (httpx.HTTPError, ResumePersistenceError):
                logger.warning('Could not roll back resume metadata for user %s.', user.id)
                try:
                    await client.patch(
                        f'{self.base_url}/rest/v1/resumes',
                        params={'id': f'eq.{resume_id}'},
                        json={'status': 'failed'},
                        headers=self._headers(user, content_type='application/json', prefer='return=minimal'),
                    )
                except httpx.HTTPError:
                    logger.warning('Could not mark resume processing as failed for user %s.', user.id)
        if object_uploaded:
            try:
                deleted_object = await client.request(
                    'DELETE',
                    f'{self.base_url}/storage/v1/object/{BUCKET_NAME}',
                    headers=self._headers(user, content_type='application/json'),
                    json={'prefixes': [object_path]},
                )
                if deleted_object.status_code >= 400:
                    logger.warning('Could not clean up resume object for user %s.', user.id)
            except httpx.HTTPError:
                logger.warning('Could not clean up resume object for user %s.', user.id)

    async def save_processed_resume(
        self,
        user: CurrentUser,
        upload: ValidatedResume,
        file_bytes: bytes,
        raw_text: str,
        profile_data: ResumeProfile,
        document: ParsedDocument,
    ) -> ResumeUploadResponse:
        if not self.base_url or not self.settings.supabase_publishable_key:
            raise HTTPException(status_code=503, detail='Resume storage is not configured on the server.')

        timeout = httpx.Timeout(30.0, connect=8.0)
        resume_id = uuid4()
        object_path = f'{user.id}/{resume_id}/{upload.file_name}'
        encoded_path = quote(object_path, safe='/')
        has_resume = False
        object_uploaded = False
        client = httpx.AsyncClient(timeout=timeout)
        try:
            account_type = await self._account_type(client, user)
            if account_type != 'job_seeker':
                raise HTTPException(status_code=403, detail='Resume uploads are available to job seeker accounts.')

            object_uploaded = True  # Treat a dropped response as an ambiguous upload and attempt cleanup.
            stored = await client.post(
                f'{self.base_url}/storage/v1/object/{BUCKET_NAME}/{encoded_path}',
                content=file_bytes,
                headers=self._headers(user, content_type=upload.file_type),
            )
            if stored.status_code not in (200, 201):
                raise ResumePersistenceError('Resume file storage failed.')
            resume_payload = {
                'id': str(resume_id),
                'candidate_id': str(user.id),
                'file_name': upload.file_name,
                'file_path': object_path,
                'file_type': upload.file_type,
                'file_size': upload.file_size,
                'raw_text': raw_text,
                'status': 'processing',
            }
            inserted = await client.post(
                f'{self.base_url}/rest/v1/resumes',
                json=resume_payload,
                headers=self._headers(user, content_type='application/json', prefer='return=representation'),
            )
            if inserted.status_code not in (200, 201):
                raise ResumePersistenceError('Resume metadata could not be saved.')
            has_resume = True
            inserted_rows = inserted.json()
            if not inserted_rows:
                raise ResumePersistenceError('Resume metadata was not returned after insert.')

            profile_payload = {
                'resume_id': str(resume_id),
                'candidate_id': str(user.id),
                'full_name': profile_data.full_name,
                'email': profile_data.email,
                'phone': profile_data.phone,
                'location': profile_data.location,
                'summary': profile_data.summary,
                'years_experience': profile_data.years_experience,
                'education_json': [item.model_dump(mode='json') for item in profile_data.education],
                'experience_json': [item.model_dump(mode='json') for item in profile_data.experience],
                'skills_json': profile_data.skills.model_dump(mode='json'),
                'certifications_json': [item.model_dump(mode='json') for item in profile_data.certifications],
                'projects_json': [item.model_dump(mode='json') for item in profile_data.projects],
                'languages_json': [item.model_dump(mode='json') for item in profile_data.languages],
                'achievements_json': [item.model_dump(mode='json') for item in profile_data.achievements],
            }
            profile_response = await client.post(
                f'{self.base_url}/rest/v1/resume_profiles',
                json=profile_payload,
                headers=self._headers(user, content_type='application/json', prefer='return=minimal'),
            )
            if profile_response.status_code not in (200, 201, 204):
                raise ResumePersistenceError('Extracted profile could not be saved.')

            updated = await client.patch(
                f'{self.base_url}/rest/v1/resumes',
                params={'id': f'eq.{resume_id}'},
                json={'status': 'processed'},
                headers=self._headers(user, content_type='application/json', prefer='return=representation'),
            )
            if updated.status_code not in (200, 204):
                raise ResumePersistenceError('Resume processing status could not be updated.')
            rows = updated.json() if updated.content else []
            record_data = rows[0] if rows else inserted_rows[0]
            record_data['status'] = 'processed'
            record = ResumeRecord.model_validate(record_data)
            return ResumeUploadResponse(
                status='processed',
                resume=record,
                profile=profile_data,
                parser=ParserMetadata(page_count=document.page_count, document_metadata=document.metadata),
            )
        except HTTPException:
            raise
        except Exception as error:
            logger.exception('Resume processing persistence failed for user %s.', user.id)
            await self._cleanup(client, user, object_path, resume_id, has_resume, object_uploaded)
            raise HTTPException(status_code=502, detail='Your resume was processed but could not be saved. Please try again.') from error
        finally:
            await client.aclose()
