from __future__ import annotations

import asyncio
import json
from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.dependencies import CurrentUser
from app.main import app
from app.ranking.explainability_engine import build_explanation
from app.ranking.score_explainer import build_score_breakdown
from app.ranking.skill_explainer import classify_skills
from app.services.matching_service import matching_service
from app.services.ranking_service import RankingService

USER_ID = UUID("10000000-0000-0000-0000-000000000001")
CANDIDATE_ID = UUID("10000000-0000-0000-0000-000000000002")
JOB_ID = UUID("10000000-0000-0000-0000-000000000010")
RESUME_ID = UUID("10000000-0000-0000-0000-000000000020")


def _result():
    return {
        "id": "10000000-0000-0000-0000-000000000030", "job_id": str(JOB_ID), "resume_id": str(RESUME_ID),
        "candidate_id": str(CANDIDATE_ID), "overall_score": 84.98, "semantic_score": 86.2,
        "skills_score": 80, "experience_score": 90, "education_score": 100,
        "projects_score": 70, "created_at": "2026-09-27T12:00:00Z",
    }


def _profile():
    return {
        "resume_id": str(RESUME_ID), "candidate_id": str(CANDIDATE_ID),
        "summary": "Python engineer building machine learning products.", "years_experience": 4,
        "skills_json": {"programming_languages": ["Python", "Postgres", "ReactJS", "NodeJS", "Machine Learning"]},
        "experience_json": [{"job_title": "Software Engineer", "company": "Example Tech", "start_date": "2022", "end_date": "2026", "description": "Built Python services."}],
        "education_json": [{"degree": "B.Tech", "field_of_study": "AI and Data Science", "institution": "Example University"}],
        "projects_json": [{"project_name": "ML screening tool", "description": "Resume similarity service", "technologies": ["Python", "Machine Learning"]}],
    }


def _job():
    return {
        "id": str(JOB_ID), "recruiter_id": str(USER_ID), "title": "ML Engineer", "description": "Build ML products",
        "summary": "Build machine learning products with Python.", "responsibilities": ["Build model-backed products."],
        "education_requirement": "Bachelor's in AI or Data Science", "education_json": None,
        "experience_min": 3, "experience_max": None, "status": "published",
    }


def test_skill_classifications_preserve_importance_and_normalized_aliases():
    rows = [
        {"skill_name": "Python", "skill_type": "required"},
        {"skill_name": "PostgreSQL", "skill_type": "required"},
        {"skill_name": "React", "skill_type": "required"},
        {"skill_name": "Node.js", "skill_type": "preferred"},
        {"skill_name": "AWS", "skill_type": "preferred"},
    ]
    result = classify_skills(["Python", "Postgres", "ReactJS", "NodeJS"], rows)
    assert [(item["name"], item["importance"]) for item in result["matched"]] == [
        ("Python", "required"), ("PostgreSQL", "required"), ("React", "required"), ("Node.js", "preferred")
    ]
    assert result["missing"] == [{"name": "AWS", "importance": "preferred", "status": "missing"}]
    assert result["partial"] == []


def test_partial_relations_are_curated_and_do_not_equate_unrelated_skills():
    result = classify_skills(["Angular", "Java"], [
        {"skill_name": "React", "skill_type": "required"},
        {"skill_name": "Python", "skill_type": "required"},
    ])
    assert result["partial"][0]["resume_skill"] == "Angular"
    assert result["missing"][0]["name"] == "Python"
    assert all(item["name"] != "Java" for group in result.values() for item in group)


def test_score_breakdown_uses_task6_weights_and_persisted_score_values():
    result = _result()
    parts = build_score_breakdown(result)
    assert {key: item["weight"] for key, item in parts.items()} == {
        "semantic": .4, "skills": .25, "experience": .15, "education": .1, "projects": .1,
    }
    assert parts["semantic"]["score"] == 86.2
    assert parts["semantic"]["weighted_contribution"] == 34.48
    assert sum(item["weighted_contribution"] for item in parts.values()) == pytest.approx(result["overall_score"], abs=.02)


def test_inconsistent_persisted_overall_is_not_silently_recalculated():
    result = {**_result(), "overall_score": 82.35}
    with pytest.raises(ValueError, match="do not reconcile"):
        build_score_breakdown(result)


def test_explanation_is_grounded_and_covers_experience_education_projects():
    requirements = [
        {"skill_name": "Python", "skill_type": "required"},
        {"skill_name": "PostgreSQL", "skill_type": "required"},
        {"skill_name": "AWS", "skill_type": "preferred"},
    ]
    output = build_explanation(_result(), _profile(), _job(), requirements)
    assert output.overall_score == 84.98
    assert [item.name for item in output.matched_skills] == ["Python", "PostgreSQL"]
    assert [(item.name, item.importance) for item in output.missing_skills] == [("AWS", "preferred")]
    assert output.experience_context.status == "matched"
    assert output.education_context.status == "matched"
    assert [item.project_name for item in output.relevant_projects] == ["ML screening tool"]
    assert "AWS" in output.explanation and "4 years" in output.explanation
    assert all(item.text for item in output.evidence)
    assert all(item.source in {"resume", "job"} for item in output.evidence)


def test_missing_fields_are_unknown_and_never_create_candidate_strength_claims():
    profile = {"resume_id": str(RESUME_ID), "candidate_id": str(CANDIDATE_ID)}
    job = {**_job(), "education_requirement": "Bachelor's degree", "experience_min": 3}
    output = build_explanation(_result(), profile, job, [])
    assert output.experience_context.status == "not_identified"
    assert output.education_context.status == "not_identified"
    assert output.data_quality == "limited"
    assert not output.strengths
    assert not [item for item in output.evidence if item.source == "resume"]
    assert any(item.status == "not_identified" for item in output.gaps)


def test_below_minimum_experience_is_described_with_extracted_values():
    profile = {**_profile(), "years_experience": 1.0}
    output = build_explanation(_result(), profile, _job(), [])
    assert output.experience_context.status == "below_requirement"
    gap = next(item for item in output.gaps if item.status == "below_requirement")
    assert "1 years" in gap.description and "3 years" in gap.description


def test_maximum_only_experience_requirement_is_not_reported_as_a_minimum():
    job = {**_job(), "experience_min": None, "experience_max": 8}
    output = build_explanation(_result(), _profile(), job, [])
    assert output.experience_context.status == "maximum_only"
    assert "no minimum" in output.explanation


def _client(handler):
    return httpx.AsyncClient(base_url="https://supabase.test", headers={"Authorization": "Bearer recruiter-token"}, transport=httpx.MockTransport(handler))


def test_authorized_recruiter_explains_only_owned_job_and_persists_traceable_data(monkeypatch):
    service = RankingService()
    service.matching.base_url = "https://supabase.test"
    patched = []
    result = _result()
    profile = _profile()
    job = _job()
    application = {"job_id": str(JOB_ID), "candidate_id": str(CANDIDATE_ID), "resume_id": str(RESUME_ID), "created_at": "2026-01-01T00:00:00Z"}

    def handler(request):
        path = request.url.path
        if path.endswith("/profiles"): return httpx.Response(200, json=[{"account_type": "recruiter"}])
        if path.endswith("/jobs"): return httpx.Response(200, json=[job])
        if path.endswith("/job_candidates"): return httpx.Response(200, json=[application])
        if path.endswith("/screening_results") and request.method == "GET": return httpx.Response(200, json=[result])
        if path.endswith("/resumes"): return httpx.Response(200, json=[{"id": str(RESUME_ID), "candidate_id": str(CANDIDATE_ID), "status": "processed"}])
        if path.endswith("/resume_profiles"): return httpx.Response(200, json=[profile])
        if path.endswith("/job_requirements"): return httpx.Response(200, json=[{"skill_name": "Python", "skill_type": "required"}])
        if path.endswith("/screening_results") and request.method == "PATCH": patched.append(json.loads(request.content)); return httpx.Response(204)
        return httpx.Response(404)

    async def fake_client(_user): return _client(handler)
    monkeypatch.setattr(service.matching, "_client", fake_client)
    output = asyncio.run(service.get_explanation(CurrentUser(id=USER_ID, access_token="recruiter-token"), JOB_ID, RESUME_ID))
    assert output.overall_score == result["overall_score"]
    assert output.matched_skills[0].name == "Python"
    assert len(patched) == 1 and patched[0]["explanation"] == output.explanation
    assert patched[0]["score_breakdown"]["semantic"]["score"] == result["semantic_score"]
    assert isinstance(patched[0]["matched_skills"], list)


def test_other_recruiter_job_and_job_seeker_are_rejected(monkeypatch):
    service = RankingService()
    service.matching.base_url = "https://supabase.test"

    def other_job(request):
        if request.url.path.endswith("/profiles"): return httpx.Response(200, json=[{"account_type": "recruiter"}])
        if request.url.path.endswith("/jobs"): return httpx.Response(200, json=[])
        return httpx.Response(404)
    async def client_job(_user): return _client(other_job)
    monkeypatch.setattr(service.matching, "_client", client_job)
    with pytest.raises(HTTPException) as denied_job:
        asyncio.run(service.get_explanation(CurrentUser(id=USER_ID, access_token="recruiter-token"), JOB_ID, RESUME_ID))
    assert denied_job.value.status_code == 404

    def wrong_role(request):
        if request.url.path.endswith("/profiles"): return httpx.Response(200, json=[{"account_type": "job_seeker"}])
        return httpx.Response(404)
    async def client_role(_user): return _client(wrong_role)
    monkeypatch.setattr(service.matching, "_client", client_role)
    with pytest.raises(HTTPException) as denied_role:
        asyncio.run(service.get_explanation(CurrentUser(id=CANDIDATE_ID, access_token="candidate-token"), JOB_ID, RESUME_ID))
    assert denied_role.value.status_code == 403


def test_unassociated_resume_is_rejected_even_for_the_job_owner(monkeypatch):
    service = RankingService()
    service.matching.base_url = "https://supabase.test"
    def handler(request):
        if request.url.path.endswith("/profiles"): return httpx.Response(200, json=[{"account_type": "recruiter"}])
        if request.url.path.endswith("/jobs"): return httpx.Response(200, json=[_job()])
        if request.url.path.endswith("/job_candidates"): return httpx.Response(200, json=[])
        return httpx.Response(404)
    async def fake_client(_user): return _client(handler)
    monkeypatch.setattr(service.matching, "_client", fake_client)
    with pytest.raises(HTTPException) as denied_resume:
        asyncio.run(service.get_explanation(CurrentUser(id=USER_ID, access_token="recruiter-token"), JOB_ID, RESUME_ID))
    assert denied_resume.value.status_code == 403


def test_bulk_explanation_reuses_scores_and_returns_per_resume_failures(monkeypatch):
    service = RankingService()
    service.matching.base_url = "https://supabase.test"
    second_resume = UUID("10000000-0000-0000-0000-000000000021")
    second_candidate = UUID("10000000-0000-0000-0000-000000000003")
    applications = [
        {"job_id": str(JOB_ID), "candidate_id": str(CANDIDATE_ID), "resume_id": str(RESUME_ID), "created_at": "2026-01-01T00:00:00Z"},
        {"job_id": str(JOB_ID), "candidate_id": str(second_candidate), "resume_id": str(second_resume), "created_at": "2026-01-02T00:00:00Z"},
    ]
    patched = []
    result = _result()
    def handler(request):
        path = request.url.path
        if path.endswith("/profiles"): return httpx.Response(200, json=[{"account_type": "recruiter"}])
        if path.endswith("/jobs"): return httpx.Response(200, json=[_job()])
        if path.endswith("/job_candidates"): return httpx.Response(200, json=applications)
        if path.endswith("/job_requirements"): return httpx.Response(200, json=[{"skill_name": "Python", "skill_type": "required"}])
        if path.endswith("/resumes"): return httpx.Response(200, json=[{"id": str(RESUME_ID), "candidate_id": str(CANDIDATE_ID), "status": "processed"}, {"id": str(second_resume), "candidate_id": str(second_candidate), "status": "processed"}])
        if path.endswith("/resume_profiles"):
            return httpx.Response(200, json=[_profile(), {**_profile(), "resume_id": str(second_resume), "candidate_id": str(second_candidate)}])
        if path.endswith("/screening_results") and request.method == "GET": return httpx.Response(200, json=[result])
        if path.endswith("/screening_results") and request.method == "PATCH": patched.append(json.loads(request.content)); return httpx.Response(204)
        return httpx.Response(404)
    async def fake_client(_user): return _client(handler)
    monkeypatch.setattr(service.matching, "_client", fake_client)
    output = asyncio.run(service.explain_job(CurrentUser(id=USER_ID, access_token="recruiter-token"), JOB_ID))
    assert len(output.results) == 1
    assert output.results[0].overall_score == result["overall_score"]
    assert len(output.failures) == 1 and output.failures[0].resume_id == second_resume
    assert len(patched) == 1


def test_ranking_endpoints_require_auth_and_are_registered():
    client = TestClient(app)
    response = client.get(f"/api/ranking/jobs/{JOB_ID}/resumes/{RESUME_ID}")
    assert response.status_code == 401
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/ranking/jobs/{job_id}/resumes/{resume_id}" in paths
    assert "/api/ranking/jobs/{job_id}/resumes/{resume_id}/explain" in paths
    assert "/api/ranking/jobs/{job_id}/explain" in paths
