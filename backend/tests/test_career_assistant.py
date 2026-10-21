import asyncio
from uuid import UUID, uuid4

from app.dependencies import CurrentUser
from app.services.career_assistant_service import CareerAssistantService


def test_skill_gap_analysis_identifies_missing_and_partial_skills():
    service = CareerAssistantService()

    result = service._build_skill_gap(
        candidate_skills=["Python", "SQL", "Communication"],
        required_skills=["Python", "SQL", "FastAPI", "Docker"],
        preferred_skills=["Leadership"],
    )

    assert "Python" in result["matched_skills"]
    assert "FastAPI" in result["missing_skills"]
    assert "Docker" in result["missing_skills"]
    assert "Leadership" in result["missing_skills"]
    assert "SQL" in result["matched_skills"]


def test_chat_does_not_persist_assistant_message_with_user_credentials(monkeypatch):
    service = CareerAssistantService()
    user = CurrentUser(id=uuid4(), access_token="test-token")
    session_id = uuid4()
    message_id = uuid4()
    written_roles = []

    async def ensure_session(_user, _title, _session_type=None):
        return {"id": str(session_id)}

    async def write_message(_user, _session_id, role, _content, _metadata=None):
        written_roles.append(role)
        return {"id": str(message_id)}

    monkeypatch.setattr(service, "_ensure_session", ensure_session)
    monkeypatch.setattr(service, "_write_message", write_message)

    result = asyncio.run(service.chat(user, "Help me improve my resume"))

    assert written_roles == ["user"]
    assert result["message"]["id"] == str(message_id)
    assert result["response"]
    assert result["session_id"] == str(session_id)


def test_session_creation_uses_only_columns_in_database_schema(monkeypatch):
    service = CareerAssistantService()
    user = CurrentUser(id=uuid4(), access_token="test-token")
    created_payload = {}

    class Response:
        def __init__(self, status_code, body):
            self.status_code = status_code
            self.body = body

        def json(self):
            return self.body

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, *_args, **_kwargs):
            return Response(200, [])

        async def post(self, *_args, json, **_kwargs):
            created_payload.update(json)
            return Response(201, [{"id": str(uuid4()), **json}])

    monkeypatch.setattr("app.services.career_assistant_service.httpx.AsyncClient", lambda **_kwargs: Client())

    result = asyncio.run(service._ensure_session(user, "Career Assistant"))

    assert set(created_payload) == {"candidate_id", "title"}
    assert result["title"] == "Career Assistant"


def test_chat_route_handles_missing_message_id(monkeypatch):
    from app.routes.career_assistant import chat_with_assistant, service
    from app.schemas.career_assistant import CareerAssistantSessionInput

    user = CurrentUser(id=uuid4(), access_token="test-token")
    session_id = uuid4()

    async def mock_chat(_user, _message, _session_id=None, _session_type=None):
        return {"session_id": str(session_id), "message": {}, "response": "Hello!"}

    monkeypatch.setattr(service, "chat", mock_chat)
    response = asyncio.run(chat_with_assistant(CareerAssistantSessionInput(message="Hi"), current_user=user))
    assert response.response == "Hello!"
    assert response.message_id is None
    assert response.session_id == session_id
