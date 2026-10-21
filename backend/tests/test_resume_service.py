import asyncio
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException
import pytest

from app.dependencies import CurrentUser
from app.parsers.base import ParsedDocument
from app.schemas.resume import ResumeProfile, Skills
from app.services import resume_service as resume_service_module
from app.services.resume_service import ResumeService
from app.utils.file_validation import ValidatedResume

USER_ID = UUID('9dcf3d14-4695-4db9-8331-95f81438c3bd')


class FakeResponse:
    def __init__(self, status_code: int, data=None):
        self.status_code = status_code
        self.data = data
        self.content = b'[]' if data is not None else b''

    def json(self):
        return self.data


class FakeSupabaseClient:
    outcome = 'success'
    calls = []

    def __init__(self, *args, **kwargs):
        self.calls = []
        FakeSupabaseClient.calls = self.calls
        self.closed = False
        self.resume_id = None

    async def get(self, url, **kwargs):
        self.calls.append(('GET', url, kwargs))
        return FakeResponse(200, [{'account_type': 'job_seeker'}])

    async def post(self, url, **kwargs):
        self.calls.append(('POST', url, kwargs))
        if '/storage/' in url:
            return FakeResponse(200, {})
        if url.endswith('/rest/v1/resumes'):
            self.resume_id = kwargs['json']['id']
            return FakeResponse(201, [{
                'id': self.resume_id, 'candidate_id': str(USER_ID), 'file_name': 'Alex.pdf',
                'file_type': 'application/pdf', 'file_size': 1234, 'status': 'processing',
                'created_at': '2026-09-26T12:00:00Z',
            }])
        if url.endswith('/rest/v1/resume_profiles') and self.outcome == 'profile-failure':
            return FakeResponse(403, {'message': 'RLS rejected insert'})
        return FakeResponse(201, {})

    async def patch(self, url, **kwargs):
        self.calls.append(('PATCH', url, kwargs))
        return FakeResponse(200, [{
            'id': self.resume_id, 'candidate_id': str(USER_ID), 'file_name': 'Alex.pdf',
            'file_type': 'application/pdf', 'file_size': 1234, 'status': 'processed',
            'created_at': '2026-09-26T12:00:00Z',
        }])

    async def delete(self, url, **kwargs):
        self.calls.append(('DELETE', url, kwargs))
        return FakeResponse(204)

    async def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return FakeResponse(200)

    async def aclose(self):
        self.closed = True


def make_service(monkeypatch, outcome='success'):
    FakeSupabaseClient.outcome = outcome
    monkeypatch.setattr(resume_service_module.httpx, 'AsyncClient', FakeSupabaseClient)
    service = ResumeService()
    service.settings = SimpleNamespace(
        supabase_url='https://talentiq.example',
        supabase_publishable_key='sb_publishable_test',
        supabase_service_role_key='must-not-be-used',
    )
    service.base_url = service.settings.supabase_url
    return service


def test_persistence_forwards_user_jwt_and_stores_processed_profile(monkeypatch):
    service = make_service(monkeypatch)
    user = CurrentUser(id=USER_ID, access_token='user-session-jwt')
    upload = ValidatedResume('Alex.pdf', 'application/pdf', 1234, '.pdf')
    profile = ResumeProfile(full_name='Alex Kumar', skills=Skills(technical=['Python'], programming_languages=['Python']))
    response = asyncio.run(service.save_processed_resume(
        user, upload, b'%PDF-test', 'raw resume text', profile, ParsedDocument('raw resume text', page_count=1),
    ))

    assert response.status == 'processed'
    assert response.resume.candidate_id == USER_ID
    assert response.profile.full_name == 'Alex Kumar'
    assert response.parser.page_count == 1
    storage_call = next(call for call in FakeSupabaseClient.calls if call[0] == 'POST' and '/storage/' in call[1])
    assert storage_call[1].startswith(f'https://talentiq.example/storage/v1/object/talentiq-resumes/{USER_ID}/')
    for method, _url, kwargs in FakeSupabaseClient.calls:
        headers = kwargs.get('headers', {})
        if headers:
            assert headers['Authorization'] == 'Bearer user-session-jwt'
            assert headers['apikey'] == 'sb_publishable_test'
            assert 'must-not-be-used' not in str(headers.values())
    profile_call = next(call for call in FakeSupabaseClient.calls if call[0] == 'POST' and call[1].endswith('/rest/v1/resume_profiles'))
    assert profile_call[2]['json']['candidate_id'] == str(USER_ID)
    assert profile_call[2]['json']['skills_json']['programming_languages'] == ['Python']


def test_persistence_rolls_back_storage_and_metadata_when_profile_insert_fails(monkeypatch):
    service = make_service(monkeypatch, outcome='profile-failure')
    user = CurrentUser(id=USER_ID, access_token='user-session-jwt')
    upload = ValidatedResume('Alex.pdf', 'application/pdf', 1234, '.pdf')
    profile = ResumeProfile(full_name='Alex Kumar')

    with pytest.raises(HTTPException) as error:
        asyncio.run(service.save_processed_resume(
            user, upload, b'%PDF-test', 'raw resume text', profile, ParsedDocument('raw resume text', page_count=1),
        ))
    assert error.value.status_code == 502
    assert 'RLS rejected insert' not in error.value.detail
    deletes = [call for call in FakeSupabaseClient.calls if call[0] == 'DELETE']
    assert any(call[1].endswith('/rest/v1/resumes') for call in deletes)
    assert any(call[1].endswith('/storage/v1/object/talentiq-resumes') for call in deletes)
