from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routes.resumes import router as resumes_router
from app.routes.jobs import router as jobs_router
from app.routes.matching import router as matching_router
from app.routes.ranking import router as ranking_router
from app.routes.recruiter import router as recruiter_router
from app.routes.career_assistant import router as career_assistant_router

settings = get_settings()
configured_origins = [origin.strip().rstrip('/') for origin in settings.frontend_origins.split(',') if origin.strip()]
is_development = settings.environment.strip().lower() in {'development', 'dev', 'local'}
if '*' in configured_origins:
    raise RuntimeError('FRONTEND_ORIGINS must list explicit origins; wildcard CORS is not supported.')
development_origins = [
    'http://localhost:5173',
    'http://localhost:5174',
    'http://localhost:5178',
    'http://localhost:8000',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
    'http://127.0.0.1:5178',
    'http://127.0.0.1:8000',
] if is_development else []
app = FastAPI(
    title=settings.app_name,
    description="TalentIQ API for authenticated resume intake, job intelligence, matching, and score explanations.",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *development_origins,
        *configured_origins,
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?" if is_development else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

app.include_router(resumes_router)
app.include_router(jobs_router)
app.include_router(matching_router)
app.include_router(ranking_router)
app.include_router(recruiter_router)
app.include_router(career_assistant_router)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "TalentIQ API"}


# Unified single-origin hosting: serve compiled React SPA from frontend/dist
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    if full_path.startswith("api/") or full_path in {"docs", "redoc", "openapi.json"}:
        raise HTTPException(status_code=404, detail="Not Found")
    file_path = frontend_dist / full_path
    if full_path and file_path.is_file():
        return FileResponse(file_path)
    index_html = frontend_dist / "index.html"
    if index_html.is_file():
        return FileResponse(index_html)
    return {
        "status": "ok",
        "service": "TalentIQ API",
        "message": "Frontend build not found. Run 'npm run build' inside frontend/ to serve the UI here.",
    }
