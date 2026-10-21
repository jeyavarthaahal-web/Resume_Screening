from __future__ import annotations

import asyncio
import json
import math
from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.ai.embedding_service import EmbeddingService
from app.ai.semantic_matcher import semantic_similarity
from app.dependencies import CurrentUser
from app.matching.education_matcher import education_score
from app.matching.experience_matcher import experience_score
from app.matching.matching_engine import MatchingEngine, build_job_representation, build_resume_representation
from app.matching.project_matcher import project_score
from app.matching.score_calculator import WEIGHTS, calculate_overall_score
from app.matching.skill_matcher import calculate_skill_score, normalize_skill
from app.main import app
from app.services.matching_service import MatchingService


class TokenModel:
    """Small deterministic local stand-in; matching tests don't download model files."""
    def __init__(self): self.calls: list[list[str]] = []
    def encode(self, texts, **kwargs):
        self.calls.append(list(texts))
        vocab = {word: index for index, word in enumerate(("python", "postgresql", "machine", "learning", "models", "finance", "painting", "data", "engineer", "react"))}
        output = []
        for text in texts:
            vector = [0.0] * len(vocab)
            for word in text.casefold().replace("-", " ").split():
                if word in vocab: vector[vocab[word]] += 1
            norm = math.sqrt(sum(value * value for value in vector)) or 1
            output.append([value / norm for value in vector])
        return output


class FakeManager:
    def __init__(self, model=None): self.model = model or TokenModel()
    def get_model(self): return self.model


def test_semantic_similarity_orders_similar_and_unrelated_text_and_empty_is_safe():
    embeddings = EmbeddingService(FakeManager())
    related = semantic_similarity("Python machine learning models", "Machine learning models with Python", embeddings)
    unrelated = semantic_similarity("Python machine learning models", "Painting and finance", embeddings)
    assert related > unrelated
    assert semantic_similarity("", "Python job", embeddings) == 0
    assert embeddings.encode_text("") == []


def test_embedding_batch_deduplicates_and_caches_with_bounded_entries():
    manager = FakeManager()
    embeddings = EmbeddingService(manager, max_cache_entries=2)
    first = embeddings.encode_texts(["python", "python", "react"])
    assert first[0] == first[1]
    assert manager.model.calls == [["python", "react"]]
    embeddings.encode_text("python")
    assert len(manager.model.calls) == 1
    embeddings.encode_text("finance")
    assert len(embeddings._cache) == 2


def test_skill_normalization_and_required_skills_have_higher_weight():
    assert normalize_skill("Postgres") == normalize_skill("PostgreSQL")
    assert normalize_skill("ReactJS") == normalize_skill("React")
    assert normalize_skill("Python") != normalize_skill("Java")
    required_match = calculate_skill_score(["Python"], [{"skill_name":"Python","skill_type":"required"}], [{"skill_name":"SQL","skill_type":"preferred"}])
    preferred_match = calculate_skill_score(["SQL"], [{"skill_name":"Python","skill_type":"required"}], [{"skill_name":"SQL","skill_type":"preferred"}])
    assert required_match.score == 70
    assert preferred_match.score == 30
    assert calculate_skill_score([], [], []).score == 50


def test_experience_matching_documented_threshold_behavior():
    assert experience_score(4, 3) == 100
    assert experience_score(1, 3) == pytest.approx(33.33)
    assert experience_score(9, 3, 5) == 100
    assert experience_score(None, 3) == 50
    assert experience_score(None, None) == 100


def test_education_matching_handles_compatible_degree_and_field_and_missing_data():
    requirement = {"degree_level":"Bachelor", "degrees":["Bachelor's degree"], "fields":["Artificial Intelligence", "Data Science"]}
    compatible = [{"degree":"B.Tech", "field_of_study":"AI & Data Science"}]
    incompatible = [{"degree":"B.Sc", "field_of_study":"Fine Arts"}]
    assert education_score(compatible, requirement) == 100
    assert education_score(incompatible, requirement) < education_score(compatible, requirement)
    assert education_score([], requirement) == 50
    assert education_score([], None) == 100


def test_project_relevance_uses_technology_and_semantic_overlap():
    embeddings = EmbeddingService(FakeManager())
    job_text = "Build Python machine learning models"
    relevant = project_score([{"project_name":"ML models", "description":"Python machine learning models", "technologies":["Python"]}], ["Python", "Machine Learning"], [], job_text, {}, embeddings)
    unrelated = project_score([{"project_name":"Art portfolio", "description":"Painting", "technologies":["React"]}], ["Python", "Machine Learning"], [], job_text, {}, embeddings)
    assert relevant > unrelated
    assert project_score([], ["Python"], [], job_text, {}, embeddings) == 50


def test_overall_weighting_sums_to_one_and_clamps_results():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)
    perfect = {key:100 for key in WEIGHTS}
    assert calculate_overall_score(perfect) == 100
    assert calculate_overall_score({key:-20 for key in WEIGHTS}) == 0
    assert calculate_overall_score({"semantic_score":100,"skill_score":80,"experience_score":90,"education_score":100,"project_score":70}) == 90.5


def test_matching_engine_handles_missing_profile_fields_without_inventing_them():
    engine = MatchingEngine(EmbeddingService(FakeManager()))
    profile = {"skills_json": None, "experience_json": None, "years_experience": None, "education_json": None, "projects_json": None}
    job = {"description":"","summary":None,"responsibilities":None,"experience_min":3,"education_requirement":"Bachelor's in Computer Science"}
    result = engine.calculate(profile, job, [])
    assert set(result) == {"overall_score", "semantic_score", "skill_score", "experience_score", "education_score", "project_score"}
    assert all(0 <= score <= 100 for score in result.values())
    assert result["semantic_score"] == 0
    assert result["experience_score"] == 50
    assert result["education_score"] == 50


USER_ID = UUID("00000000-0000-0000-0000-000000000001")
JOB_ID = UUID("00000000-0000-0000-0000-000000000010")
RESUME_ID = UUID("00000000-0000-0000-0000-000000000020")


def test_matching_routes_require_auth_and_are_registered():
    client = TestClient(app)
    response = client.post(f"/api/matching/jobs/{JOB_ID}/resumes/{RESUME_ID}")
    assert response.status_code == 401
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/matching/jobs/{job_id}" in paths
    assert "/api/matching/jobs/{job_id}/apply" in paths
    assert "/api/matching/jobs/{job_id}/results" in paths
    assert paths["/api/matching/jobs/{job_id}"]["post"].get("security")

def _transport_client(handler):
    return httpx.AsyncClient(base_url="https://supabase.test", headers={"Authorization":"Bearer verified-token"}, transport=httpx.MockTransport(handler))


def test_matching_service_rejects_job_seeker_and_other_recruiters_job(monkeypatch):
    user = CurrentUser(id=USER_ID, access_token="verified-token")
    service = MatchingService(MatchingEngine(EmbeddingService(FakeManager())))
    service.base_url = "https://supabase.test"
    async def client_role(_user): return _transport_client(lambda req: httpx.Response(200, json=[{"account_type":"job_seeker"}]))
    monkeypatch.setattr(service, "_client", client_role)
    with pytest.raises(HTTPException) as role_error: asyncio.run(service.match_one(user, JOB_ID, RESUME_ID))
    assert role_error.value.status_code == 403

    def other_job(req):
        if req.url.path.endswith("/profiles"): return httpx.Response(200, json=[{"account_type":"recruiter"}])
        return httpx.Response(200, json=[])
    async def client_job(_user): return _transport_client(other_job)
    monkeypatch.setattr(service, "_client", client_job)
    with pytest.raises(HTTPException) as job_error: asyncio.run(service.match_one(user, JOB_ID, RESUME_ID))
    assert job_error.value.status_code == 404


def test_authorized_candidate_job_match_persists_only_numerical_fields(monkeypatch):
    user = CurrentUser(id=USER_ID, access_token="verified-token")
    service = MatchingService(MatchingEngine(EmbeddingService(FakeManager())))
    service.base_url = "https://supabase.test"
    persisted = []
    profile = {"resume_id":str(RESUME_ID),"candidate_id":str(UUID("00000000-0000-0000-0000-000000000002")),"summary":"Python engineer builds machine learning models.","years_experience":4,"skills_json":{"programming_languages":["Python"]},"education_json":[],"experience_json":[],"projects_json":[]}
    app_row = {"job_id":str(JOB_ID),"candidate_id":profile["candidate_id"],"resume_id":str(RESUME_ID),"created_at":"2026-01-01T00:00:00Z"}
    job = {"id":str(JOB_ID),"recruiter_id":str(USER_ID),"summary":"Build Python machine learning models.","responsibilities":["Build ML models"],"education_requirement":None,"education_json":None,"experience_min":3,"experience_max":None}
    def handler(req):
        path=req.url.path
        if path.endswith("/profiles"): return httpx.Response(200,json=[{"account_type":"recruiter"}])
        if path.endswith("/jobs"): return httpx.Response(200,json=[job])
        if path.endswith("/job_candidates"): return httpx.Response(200,json=[app_row])
        if path.endswith("/job_requirements"): return httpx.Response(200,json=[{"skill_name":"Python","skill_type":"required","importance":4}])
        if path.endswith("/resumes"): return httpx.Response(200,json=[{"id":str(RESUME_ID),"candidate_id":profile["candidate_id"],"status":"processed"}])
        if path.endswith("/resume_profiles"): return httpx.Response(200,json=[profile])
        if req.method=="POST" and path.endswith("/screening_results"):
            persisted.extend(json.loads(req.content)); saved={**persisted[0],"created_at":"2026-09-27T00:00:00Z"}; return httpx.Response(201,json=[saved])
        return httpx.Response(404)
    async def client(_user): return _transport_client(handler)
    monkeypatch.setattr(service,"_client",client)
    result=asyncio.run(service.match_one(user,JOB_ID,RESUME_ID))
    assert result.job_id==JOB_ID and result.resume_id==RESUME_ID
    assert all(0 <= getattr(result,key) <= 100 for key in ("overall_score","semantic_score","skill_score","experience_score","education_score","project_score"))
    assert persisted[0]["candidate_id"]==profile["candidate_id"]
    assert set(persisted[0])=={"job_id","resume_id","candidate_id","overall_score","semantic_score","skills_score","experience_score","education_score","projects_score"}
