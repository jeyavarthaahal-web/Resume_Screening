from pathlib import Path
import asyncio
import json
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from app.dependencies import CurrentUser, require_current_user
from app.main import app
from app.nlp.job_cleaner import clean_job_text
from app.nlp.job_extractor import extract_job_profile
from app.nlp.job_section_detector import detect_job_sections
from app.parsers.base import ResumeParserError
from app.parsers.job_document_parser import JobDocumentParser
from app.schemas.job import JobCreateRequest, JobStructuredProfile
from app.services.job_service import JobService, job_service
from app.utils.file_validation import UploadValidationError, validate_resume_upload

SAMPLE = Path(__file__).parent / "fixtures" / "sample_job_description.txt"

def test_job_cleaner_preserves_technical_terms_and_rejoins_wrapped_lines():
    cleaned = clean_job_text("Build Node.\njs services with C++ and C#;\u00a0support NLP.\n\n\n Team work")
    assert "Node.js services" in cleaned
    assert "C++ and C#" in cleaned
    assert "NLP" in cleaned
    assert "\n\n\n" not in cleaned

def test_section_detector_tolerates_case_punctuation_and_order():
    sections = detect_job_sections("PREFERRED QUALIFICATIONS:\nKubernetes is a plus.\n\nKey Responsibilities:\nBuild systems.")
    assert sections["preferred"] == ["Kubernetes is a plus."]
    assert sections["responsibilities"] == ["Build systems."]

def test_job_extractor_separates_skills_and_extracts_structured_fields():
    profile = extract_job_profile(SAMPLE.read_text(encoding="utf-8"))
    required = {s["name"]: s for s in profile["required_skills"]}
    preferred = {s["name"]: s for s in profile["preferred_skills"]}
    assert profile["job_title"] == "Senior Machine Learning Engineer"
    assert profile["department"] == "AI Platform"
    assert profile["employment_type"] == "full_time"
    assert profile["work_mode"] == "Remote"
    assert (profile["minimum_experience"], profile["maximum_experience"]) == (3, None)
    assert required["PostgreSQL"]["original_name"] == "Postgres"
    assert "Kubernetes" in preferred and "Kubernetes" not in required
    assert profile["education_requirement"]["degree_level"] == "Bachelor"
    assert profile["responsibilities"][0].startswith("Design and deploy")
    assert {c["name"] for c in profile["certifications"]} == {"AWS Certified"}
    assert "Health insurance" in profile["benefits"]

@pytest.mark.parametrize(("text", "expected"), [
    ("At least 4 years of experience", (4.0, None)),
    ("3-5 years of experience", (3.0, 5.0)),
    ("1 year preferred", (None, None)),
    ("Fresh graduates welcome", (0.0, None)),
    ("0-2 years", (0.0, 2.0)),
])
def test_experience_ranges(text, expected):
    profile = extract_job_profile(f"Role\nRequirements\n{text} and Python.")
    assert (profile["minimum_experience"], profile["maximum_experience"]) == expected

def test_skills_without_a_required_or_preferred_label_default_to_preferred():
    profile = extract_job_profile("Data Engineer\nSkills\nPython, SQL and PostgreSQL experience.")
    assert not profile["required_skills"]
    assert {s["name"] for s in profile["preferred_skills"]} >= {"Python", "SQL", "PostgreSQL"}

def test_job_document_parser_reads_docx_paragraphs_and_tables():
    from io import BytesIO
    from docx import Document
    output = BytesIO(); doc = Document(); doc.add_paragraph("Responsibilities")
    table = doc.add_table(rows=1, cols=2); table.cell(0, 0).text = "Python"; table.cell(0, 1).text = "Postgres"
    doc.save(output)
    parsed = JobDocumentParser().parse(".docx", output.getvalue())
    assert "Responsibilities" in parsed.text and "Python | Postgres" in parsed.text

def test_job_document_parser_reports_invalid_and_encrypted_pdf():
    from io import BytesIO
    from pypdf import PdfWriter
    output = BytesIO(); writer = PdfWriter(); writer.add_blank_page(width=72, height=72); writer.encrypt("secret"); writer.write(output)
    with pytest.raises(ResumeParserError, match="valid, unencrypted PDF"):
        JobDocumentParser().parse(".pdf", b"%PDF-this-is-not-valid")
    with pytest.raises(ResumeParserError, match="password-protected"):
        JobDocumentParser().parse(".pdf", output.getvalue())

def test_upload_validation_rejects_bad_type_and_oversize():
    with pytest.raises(UploadValidationError, match="PDF or DOCX"):
        validate_resume_upload("jd.txt", b"some text")

def test_job_schemas_reject_blank_title_and_invalid_experience_range():
    with pytest.raises(ValueError):
        JobCreateRequest(title="  ", description="A sufficiently long job description goes here.")
    with pytest.raises(ValueError):
        JobStructuredProfile(minimum_experience=6, maximum_experience=2)

def test_job_analysis_api_requires_authentication():
    with TestClient(app) as client:
        response = client.post("/api/jobs/analyze", data={"description": "A sufficiently long job description for the API test."})
    assert response.status_code == 401

def test_job_analysis_api_rejects_job_seekers(monkeypatch):
    user = CurrentUser(id=UUID("00000000-0000-0000-0000-000000000001"), access_token="token")
    app.dependency_overrides[require_current_user] = lambda: user
    async def mocked_client(_user):
        return httpx.AsyncClient(base_url="https://supabase.test", transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[{"account_type":"job_seeker"}])))
    monkeypatch.setattr(job_service, "_client", mocked_client)
    try:
        with TestClient(app) as client:
            response = client.post("/api/jobs/analyze", data={"description": SAMPLE.read_text(encoding="utf-8")})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(require_current_user, None)

def test_job_analysis_api_returns_structured_profile_for_recruiter(monkeypatch):
    user = CurrentUser(id=UUID("00000000-0000-0000-0000-000000000001"), access_token="token")
    app.dependency_overrides[require_current_user] = lambda: user
    async def mocked_client(_user):
        return httpx.AsyncClient(base_url="https://supabase.test", transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[{"account_type":"recruiter"}])))
    monkeypatch.setattr(job_service, "_client", mocked_client)
    try:
        with TestClient(app) as client:
            response = client.post("/api/jobs/analyze", data={"description": SAMPLE.read_text(encoding="utf-8")})
        assert response.status_code == 200
        body = response.json()
        assert body["analysis_status"] == "analyzed"
        assert body["job_title"] == "Senior Machine Learning Engineer"
        assert body["required_skills"] and body["preferred_skills"]
    finally:
        app.dependency_overrides.pop(require_current_user, None)

def test_job_create_uses_verified_owner_and_persists_normalized_requirements(monkeypatch):
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    user = CurrentUser(id=user_id, access_token="verified-user-token")
    written: dict = {"jobs": [], "requirements": []}
    def handler(request: httpx.Request):
        if request.url.path.endswith("/profiles"):
            assert request.headers["Authorization"] == "Bearer verified-user-token"
            return httpx.Response(200, json=[{"account_type": "recruiter"}])
        if request.method == "POST" and request.url.path.endswith("/jobs"):
            body = json.loads(request.content); written["jobs"].append(body)
            return httpx.Response(201, json=[body])
        if request.method == "POST" and request.url.path.endswith("/job_requirements"):
            written["requirements"] = json.loads(request.content)
            return httpx.Response(201)
        if request.method == "GET" and request.url.path.endswith("/job_requirements"):
            return httpx.Response(200, json=[{"skill_name": x["skill_name"], "skill_type": x["skill_type"]} for x in written["requirements"]])
        return httpx.Response(404)
    async def mocked_client(_user):
        return httpx.AsyncClient(base_url="https://supabase.test", headers={"Authorization": "Bearer verified-user-token"}, transport=httpx.MockTransport(handler))
    service = JobService(); service.base_url = "https://supabase.test"; monkeypatch.setattr(service, "_client", mocked_client)
    request = JobCreateRequest(title="Senior Machine Learning Engineer", description=SAMPLE.read_text(encoding="utf-8"))
    result = asyncio.run(service.create_job(user, request))
    assert written["jobs"][0]["recruiter_id"] == str(user_id)
    assert written["jobs"][0]["analysis_status"] == "analyzed"
    req = {x["skill_name"]: x for x in written["requirements"]}
    assert req["PostgreSQL"]["skill_type"] == "required" and req["PostgreSQL"]["importance"] == 4
    assert req["Kubernetes"]["skill_type"] == "preferred" and req["Kubernetes"]["importance"] == 2
    assert result.recruiter_id == user_id
