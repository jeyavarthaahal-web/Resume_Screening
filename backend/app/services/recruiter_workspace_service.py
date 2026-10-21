"""RLS-scoped recruiter workspace reads and writes over Supabase PostgREST."""
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException
from urllib.parse import quote

from app.dependencies import CurrentUser
from app.services.matching_service import MatchingPersistenceError, matching_service


class RecruiterWorkspaceService:
    def __init__(self) -> None:
        self.matching = matching_service

    async def _client(self, user: CurrentUser) -> httpx.AsyncClient:
        return await self.matching._client(user)

    async def _get(self, client: httpx.AsyncClient, table: str, params: dict[str, Any], limit: int = 1000) -> list[dict[str, Any]]:
        response = await client.get(f"{self.matching.base_url}/rest/v1/{table}", params={**params, "limit": limit})
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Recruiter workspace data could not be loaded.")
        return response.json()

    async def _owned_job(self, client: httpx.AsyncClient, user: CurrentUser, job_id: UUID) -> dict[str, Any]:
        rows = await self._get(client, "jobs", {"select": "*", "id": f"eq.{job_id}", "recruiter_id": f"eq.{user.id}"}, 1)
        if not rows:
            raise HTTPException(status_code=404, detail="Job not found.")
        return rows[0]

    async def _applications(self, client: httpx.AsyncClient, job_id: UUID) -> list[dict[str, Any]]:
        return await self._get(client, "job_candidates", {"select": "job_id,candidate_id,resume_id,created_at", "job_id": f"eq.{job_id}", "order": "created_at.desc"})

    async def _candidate_rows(self, client: httpx.AsyncClient, job_id: UUID, recruiter_id: UUID) -> list[dict[str, Any]]:
        apps = await self._applications(client, job_id)
        if not apps:
            return []
        ids = list(dict.fromkeys(row["candidate_id"] for row in apps))
        resumes = list(dict.fromkeys(row["resume_id"] for row in apps))
        in_candidates = "in.(" + ",".join(ids) + ")"
        in_resumes = "in.(" + ",".join(resumes) + ")"
        profiles, people, results, shortlists, resume_rows = await __import__("asyncio").gather(
            self._get(client, "resume_profiles", {"select": "resume_id,candidate_id,full_name,email,phone,location,summary,years_experience,skills_json,experience_json,education_json,projects_json,certifications_json,languages_json,updated_at", "resume_id": in_resumes}),
            self._get(client, "profiles", {"select": "id,full_name,email,phone,location", "id": in_candidates}),
            self._get(client, "screening_results", {"select": "id,job_id,resume_id,candidate_id,overall_score,semantic_score,skills_score,experience_score,education_score,projects_score,matched_skills,partial_skills,missing_skills,strengths,gaps,evidence,score_breakdown,explanation,ranking_details,created_at", "job_id": f"eq.{job_id}", "resume_id": in_resumes, "order": "created_at.desc,id.desc"}),
            self._get(client, "shortlists", {"select": "id,job_id,candidate_id,status,created_at,updated_at", "job_id": f"eq.{job_id}", "recruiter_id": f"eq.{recruiter_id}"}),
            self._get(client, "resumes", {"select": "id,file_name", "id": in_resumes})
        )
        person_by_id = {row["id"]: row for row in people}
        profile_by_resume = {row["resume_id"]: row for row in profiles}
        latest = {}
        for row in results:
            latest.setdefault(row["resume_id"], row)
        shortlist_by_candidate = {row["candidate_id"]: row for row in shortlists}
        resume_by_id = {row["id"]: row for row in resume_rows}
        out = []
        for app in apps:
            profile = profile_by_resume.get(app["resume_id"], {})
            person = person_by_id.get(app["candidate_id"], {})
            out.append({
                "job_id": job_id, "candidate_id": app["candidate_id"], "resume_id": app["resume_id"],
                "applied_at": app.get("created_at"), "candidate": {**person, **{k: v for k, v in profile.items() if v}},
                "profile": profile, "resume": resume_by_id.get(app["resume_id"], {}), "result": latest.get(app["resume_id"]),
                "shortlist": shortlist_by_candidate.get(app["candidate_id"]),
            })
        return out

    async def dashboard(self, user: CurrentUser) -> dict[str, Any]:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            jobs, profile = await __import__("asyncio").gather(
                self._get(client, "jobs", {"select": "id,title,status,created_at,updated_at,department,location,employment_type", "recruiter_id": f"eq.{user.id}", "order": "created_at.desc"}),
                self._get(client, "profiles", {"select": "id,full_name,company_name", "id": f"eq.{user.id}"}, 1),
            )
            job_ids = [job["id"] for job in jobs]
            activity: list[dict[str, Any]] = [{"kind": "job", "title": job["title"], "created_at": job.get("created_at"), "job_id": job["id"]} for job in jobs[:8]]
            if job_ids:
                job_filter = "in.(" + ",".join(job_ids) + ")"
                applications, shortlisted, results, notes = await __import__("asyncio").gather(
                    self._get(client, "job_candidates", {"select": "job_id,candidate_id,resume_id,created_at", "job_id": job_filter}),
                    self._get(client, "shortlists", {"select": "id,job_id,candidate_id,created_at", "job_id": job_filter, "recruiter_id": f"eq.{user.id}", "order": "created_at.desc"}),
                    self._get(client, "screening_results", {"select": "job_id,overall_score,candidate_id,resume_id,created_at", "job_id": job_filter, "order": "created_at.desc,id.desc"}),
                    self._get(client, "candidate_notes", {"select": "job_id,candidate_id,created_at", "job_id": job_filter, "recruiter_id": f"eq.{user.id}", "order": "created_at.desc"}),
                )
                job_by_id = {job["id"]: job["title"] for job in jobs}
                activity.extend({"kind": "shortlist", "title": job_by_id.get(item["job_id"], "Job"), "created_at": item.get("created_at"), "job_id": item["job_id"]} for item in shortlisted[:8])
                activity.extend({"kind": "note", "title": job_by_id.get(item["job_id"], "Job"), "created_at": item.get("created_at"), "job_id": item["job_id"]} for item in notes[:8])
                score_by_resume: dict[tuple[str, str], tuple[str, float]] = {}
                for result in results:
                    value = result.get("overall_score")
                    if value is not None:
                        score_by_resume.setdefault((result["job_id"], result["resume_id"]), (result["candidate_id"], float(value)))
            else:
                applications, shortlisted, score_by_resume = [], [], {}
            scores = [value for _, value in score_by_resume.values()]
            screened_candidates = {candidate_id for candidate_id, _ in score_by_resume.values()}
            return {"profile": profile[0] if profile else {}, "total_jobs": len(jobs), "active_jobs": sum(j.get("status") == "published" for j in jobs),
                    "total_candidates": len({r["candidate_id"] for r in applications}), "screened_candidates": len(screened_candidates),
                    "shortlisted_candidates": len({r["candidate_id"] for r in shortlisted}), "average_match_score": round(sum(scores) / len(scores), 1) if scores else None,
                    "jobs": jobs[:8], "recent_activity": sorted(activity, key=lambda a: a.get("created_at") or "", reverse=True)[:8]}
        finally:
            await client.aclose()

    async def jobs(self, user: CurrentUser) -> list[dict[str, Any]]:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            jobs = await self._get(client, "jobs", {"select": "*", "recruiter_id": f"eq.{user.id}", "order": "created_at.desc"})
            for job in jobs:
                requirements = await self._get(client, "job_requirements", {"select": "skill_name,skill_type,importance", "job_id": f"eq.{job['id']}"})
                applicants = await self._applications(client, UUID(job["id"]))
                job["requirements"] = requirements
                job["candidate_count"] = len(applicants)
                job["analysis_status"] = "analyzed" if requirements or job.get("summary") else "pending"
            return jobs
        finally:
            await client.aclose()

    async def job(self, user: CurrentUser, job_id: UUID) -> dict[str, Any]:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            job = await self._owned_job(client, user, job_id)
            job["requirements"] = await self._get(client, "job_requirements", {"select": "skill_name,skill_type,importance", "job_id": f"eq.{job_id}"})
            job["candidate_count"] = len(await self._applications(client, job_id))
            return job
        finally:
            await client.aclose()

    async def candidates(self, user: CurrentUser, job_id: UUID, page: int = 1, page_size: int = 20, q: str = "", score: str = "all", shortlist: str = "all", experience: str = "all", skill: str = "", sort: str = "recent") -> dict[str, Any]:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            await self._owned_job(client, user, job_id)
            rows = await self._candidate_rows(client, job_id, user.id)
            requirements = await self._get(client, "job_requirements", {"select": "skill_name,skill_type", "job_id": f"eq.{job_id}"})
            required = [r["skill_name"] for r in requirements if r.get("skill_type") == "required"]
            term = q.casefold().strip()
            def keep(row: dict[str, Any]) -> bool:
                result, profile = row.get("result") or {}, row.get("profile") or {}
                candidate = row.get("candidate") or {}
                text = " ".join(str(candidate.get(k) or "") for k in ("full_name", "email")) + " " + str(profile.get("skills_json") or "")
                if term and term not in text.casefold(): return False
                val = result.get("overall_score")
                if score != "all" and (val is None or (score == "below60" and float(val) >= 60) or (score.endswith("+") and float(val) < float(score[:-1]))): return False
                if shortlist == "yes" and not row.get("shortlist"): return False
                if shortlist == "no" and row.get("shortlist"): return False
                years = profile.get("years_experience")
                if experience.endswith("+") and (years is None or float(years) < float(experience[:-1])): return False
                if skill and skill.casefold() not in str(profile.get("skills_json") or "").casefold(): return False
                return True
            rows = [r for r in rows if keep(r)]
            if sort == "score": rows.sort(key=lambda r: (r.get("result") or {}).get("overall_score") is not None, reverse=True); rows.sort(key=lambda r: float((r.get("result") or {}).get("overall_score") or -1), reverse=True)
            elif sort == "experience": rows.sort(key=lambda r: float((r.get("profile") or {}).get("years_experience") or -1), reverse=True)
            elif sort == "updated": rows.sort(key=lambda r: (r.get("profile") or {}).get("updated_at") or "", reverse=True)
            total = len(rows); start = (page - 1) * page_size
            return {"items": rows[start:start + page_size], "page": page, "page_size": page_size, "total": total, "required_skills": required}
        finally:
            await client.aclose()

    async def candidate(self, user: CurrentUser, job_id: UUID, candidate_id: UUID) -> dict[str, Any]:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            await self._owned_job(client, user, job_id)
            row = next((r for r in await self._candidate_rows(client, job_id, user.id) if r["candidate_id"] == str(candidate_id)), None)
            if row is None:
                raise HTTPException(status_code=404, detail="Candidate not found for this job.")
            row["notes"] = await self._get(client, "candidate_notes", {"select": "id,job_id,candidate_id,note,created_at,updated_at", "job_id": f"eq.{job_id}", "candidate_id": f"eq.{candidate_id}", "recruiter_id": f"eq.{user.id}", "order": "created_at.desc"})
            return row
        finally:
            await client.aclose()

    async def resume_download(self, user: CurrentUser, job_id: UUID, candidate_id: UUID, resume_id: UUID) -> dict[str, str]:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            await self._owned_job(client, user, job_id)
            apps = await self._applications(client, job_id)
            if not any(r["candidate_id"] == str(candidate_id) and r["resume_id"] == str(resume_id) for r in apps):
                raise HTTPException(status_code=404, detail="Resume not found for this candidate and job.")
            rows = await self._get(client, "resumes", {"select": "id,file_name,file_path,status", "id": f"eq.{resume_id}", "candidate_id": f"eq.{candidate_id}"}, 1)
            if not rows or rows[0].get("status") != "processed":
                raise HTTPException(status_code=404, detail="Processed resume file not found.")
            path = quote(rows[0]["file_path"], safe="/")
            response = await client.post(f"{self.matching.base_url}/storage/v1/object/sign/talentiq-resumes/{path}", json={"expiresIn": 300})
            if response.status_code not in (200, 201):
                raise HTTPException(status_code=502, detail="The resume file could not be opened.")
            signed = response.json().get("signedURL") or response.json().get("signedUrl")
            if not signed:
                raise HTTPException(status_code=502, detail="The resume file could not be opened.")
            return {"file_name": rows[0]["file_name"], "url": self.matching.base_url + signed if signed.startswith("/") else signed}
        finally:
            await client.aclose()

    async def shortlist(self, user: CurrentUser, job_id: UUID) -> list[dict[str, Any]]:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            await self._owned_job(client, user, job_id)
            candidate_rows = await self._candidate_rows(client, job_id, user.id)
            return [row for row in candidate_rows if row.get("shortlist")]
        finally:
            await client.aclose()

    async def change_shortlist(self, user: CurrentUser, job_id: UUID, candidate_id: UUID, add: bool) -> Any:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            await self._owned_job(client, user, job_id)
            if not any(r["candidate_id"] == str(candidate_id) for r in await self._applications(client, job_id)):
                raise HTTPException(status_code=404, detail="Candidate not found for this job.")
            url = f"{self.matching.base_url}/rest/v1/shortlists"
            params = {"job_id": f"eq.{job_id}", "candidate_id": f"eq.{candidate_id}", "recruiter_id": f"eq.{user.id}"}
            if not add:
                response = await client.delete(url, params=params)
                if response.status_code not in (200, 204): raise HTTPException(status_code=502, detail="The shortlist could not be updated.")
                return {"shortlisted": False}
            response = await client.get(url, params={**params, "select": "id,job_id,candidate_id,recruiter_id,status,created_at", "limit": 1})
            if response.status_code != 200: raise HTTPException(status_code=502, detail="The shortlist could not be checked.")
            if response.json(): return response.json()[0]
            response = await client.post(url, json={"job_id": str(job_id), "candidate_id": str(candidate_id), "recruiter_id": str(user.id)}, headers={"Prefer": "return=representation"})
            if response.status_code not in (200, 201): raise HTTPException(status_code=502, detail="The candidate could not be added to the shortlist.")
            return response.json()[0]
        finally:
            await client.aclose()

    async def create_note(self, user: CurrentUser, candidate_id: UUID, job_id: UUID, note: str) -> dict[str, Any]:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            await self._owned_job(client, user, job_id)
            if not any(r["candidate_id"] == str(candidate_id) for r in await self._applications(client, job_id)):
                raise HTTPException(status_code=404, detail="Candidate not found for this job.")
            response = await client.post(f"{self.matching.base_url}/rest/v1/candidate_notes", json={"job_id": str(job_id), "candidate_id": str(candidate_id), "recruiter_id": str(user.id), "note": note.strip()}, headers={"Prefer": "return=representation"})
            if response.status_code not in (200, 201): raise HTTPException(status_code=502, detail="The note could not be saved.")
            return response.json()[0]
        finally:
            await client.aclose()

    async def update_note(self, user: CurrentUser, note_id: UUID, note: str | None = None) -> Any:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            params = {"id": f"eq.{note_id}", "recruiter_id": f"eq.{user.id}"}
            if note is None:
                response = await client.delete(f"{self.matching.base_url}/rest/v1/candidate_notes", params=params)
            else:
                from datetime import datetime, timezone
                response = await client.patch(f"{self.matching.base_url}/rest/v1/candidate_notes", params=params, json={"note": note.strip(), "updated_at": datetime.now(timezone.utc).isoformat()}, headers={"Prefer": "return=representation"})
            if response.status_code not in (200, 204): raise HTTPException(status_code=502, detail="The note could not be updated.")
            if note is None: return None
            if not response.json(): raise HTTPException(status_code=404, detail="Note not found.")
            return response.json()[0]
        finally:
            await client.aclose()

    async def compare(self, user: CurrentUser, job_id: UUID, candidate_ids: list[UUID]) -> list[dict[str, Any]]:
        client = await self._client(user)
        try:
            await self.matching._require_role(client, user, "recruiter")
            await self._owned_job(client, user, job_id)
            if len(set(candidate_ids)) != len(candidate_ids): raise HTTPException(status_code=422, detail="Choose each candidate only once.")
            rows = await self._candidate_rows(client, job_id, user.id)
            by_id = {r["candidate_id"]: r for r in rows}
            if any(str(cid) not in by_id for cid in candidate_ids): raise HTTPException(status_code=403, detail="Every candidate must be associated with this job.")
            payload = {"job_id": str(job_id), "candidate_ids": [str(cid) for cid in candidate_ids], "recruiter_id": str(user.id)}
            response = await client.post(f"{self.matching.base_url}/rest/v1/candidate_comparisons", json=payload)
            if response.status_code not in (200, 201): raise HTTPException(status_code=502, detail="The comparison could not be saved.")
            return [by_id[str(cid)] for cid in candidate_ids]
        finally:
            await client.aclose()


recruiter_workspace_service = RecruiterWorkspaceService()
