from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import DSARecord, JobApplication, Project, User
from app.schemas import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    DSARecordCreate,
    DSARecordRead,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)

projects_router = APIRouter()
dsa_router = APIRouter()
applications_router = APIRouter()


@projects_router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Project:
    row = Project(user_id=current_user.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@projects_router.get("", response_model=list[ProjectRead])
def list_projects(
    project_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Project]:
    stmt = select(Project).where(Project.user_id == current_user.id).order_by(Project.created_at.desc())
    if project_status:
        if project_status not in {"planned", "in_progress", "completed", "on_hold"}:
            raise HTTPException(status_code=422, detail="Unsupported project status.")
        stmt = stmt.where(Project.status == project_status)
    return list(db.scalars(stmt).all())


@projects_router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    row = db.scalar(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    updates = payload.model_dump(exclude_unset=True)
    for key in {"name", "status", "skills", "milestones"}:
        if key in updates and updates[key] is None:
            raise HTTPException(status_code=422, detail=f"{key} cannot be null; use an empty list to clear list fields.")
    for key, value in updates.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@projects_router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    row = db.scalar(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    db.delete(row)
    db.commit()


@dsa_router.post("", response_model=DSARecordRead, status_code=status.HTTP_201_CREATED)
def create_dsa_record(payload: DSARecordCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> DSARecord:
    row = DSARecord(user_id=current_user.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@dsa_router.get("", response_model=list[DSARecordRead])
def list_dsa_records(
    topic: str | None = None,
    record_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DSARecord]:
    stmt = select(DSARecord).where(DSARecord.user_id == current_user.id).order_by(DSARecord.created_at.desc()).limit(limit)
    if topic:
        stmt = stmt.where(DSARecord.topic == topic)
    if record_status:
        if record_status not in {"solved", "attempted", "revisit"}:
            raise HTTPException(status_code=422, detail="Unsupported DSA status.")
        stmt = stmt.where(DSARecord.status == record_status)
    return list(db.scalars(stmt).all())


@dsa_router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dsa_record(record_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    row = db.scalar(select(DSARecord).where(DSARecord.id == record_id, DSARecord.user_id == current_user.id))
    if row is None:
        raise HTTPException(status_code=404, detail="DSA record not found.")
    db.delete(row)
    db.commit()


@applications_router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> JobApplication:
    row = JobApplication(user_id=current_user.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@applications_router.get("", response_model=list[ApplicationRead])
def list_applications(
    application_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobApplication]:
    stmt = select(JobApplication).where(JobApplication.user_id == current_user.id).order_by(JobApplication.created_at.desc())
    if application_status:
        allowed = {"saved", "applied", "screening", "interview", "offer", "rejected", "withdrawn"}
        if application_status not in allowed:
            raise HTTPException(status_code=422, detail="Unsupported application status.")
        stmt = stmt.where(JobApplication.status == application_status)
    return list(db.scalars(stmt).all())


@applications_router.patch("/{application_id}", response_model=ApplicationRead)
def update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobApplication:
    row = db.scalar(select(JobApplication).where(JobApplication.id == application_id, JobApplication.user_id == current_user.id))
    if row is None:
        raise HTTPException(status_code=404, detail="Application record not found.")
    updates = payload.model_dump(exclude_unset=True)
    for key in {"company", "role", "status"}:
        if key in updates and updates[key] is None:
            raise HTTPException(status_code=422, detail=f"{key} cannot be null.")
    for key, value in updates.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@applications_router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    row = db.scalar(select(JobApplication).where(JobApplication.id == application_id, JobApplication.user_id == current_user.id))
    if row is None:
        raise HTTPException(status_code=404, detail="Application record not found.")
    db.delete(row)
    db.commit()
