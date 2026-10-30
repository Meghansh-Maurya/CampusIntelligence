from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.models import Base
from app.routes import academic, analytics, documents, interviews, resumes, study_plans, users
from app.routes.progress import applications_router, dsa_router, projects_router

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:
        # Convenient for a learning project/local development. Use Alembic migrations for deployments.
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Private academic and placement workspace for students.",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Dev-User-Id", "X-Dev-Email"],
)

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["Users and profiles"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(academic.router, prefix="/academic", tags=["Academic RAG assistant"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resume analysis"])
api_router.include_router(study_plans.router, prefix="/study-plans", tags=["Personalized study planner"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["Interview preparation"])
api_router.include_router(projects_router, prefix="/progress/projects", tags=["Projects and milestones"])
api_router.include_router(dsa_router, prefix="/progress/dsa", tags=["DSA progress"])
api_router.include_router(applications_router, prefix="/applications", tags=["Manual application tracker"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics dashboard"])
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """Liveness check; does not require a database round trip."""
    return {"status": "ok", "service": "campus-intelligence-api", "version": settings.app_version}


@app.get("/health/ready", tags=["Health"])
def readiness() -> dict[str, str]:
    """Readiness check including a database query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logging.getLogger(__name__).exception("Readiness check failed")
        raise HTTPException(status_code=503, detail="Database is not reachable.") from exc
    return {"status": "ready", "database": "connected"}
