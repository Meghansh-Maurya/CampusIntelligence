from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import DSARecord, Document, InterviewSession, JobApplication, Project, ResumeAnalysis, StudyPlan, StudyTask, User
from app.schemas import AnalyticsOverview

router = APIRouter()


def _count(db: Session, statement) -> int:
    return int(db.scalar(statement) or 0)


@router.get("/overview", response_model=AnalyticsOverview)
def analytics_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> AnalyticsOverview:
    uid = current_user.id
    documents_total = _count(db, select(func.count()).select_from(Document).where(Document.user_id == uid))
    analyses_total = _count(db, select(func.count()).select_from(ResumeAnalysis).where(ResumeAnalysis.user_id == uid))
    plans_total = _count(db, select(func.count()).select_from(StudyPlan).where(StudyPlan.user_id == uid))
    completed_tasks = _count(
        db,
        select(func.count()).select_from(StudyTask).join(StudyPlan, StudyTask.plan_id == StudyPlan.id)
        .where(StudyPlan.user_id == uid, StudyTask.status == "completed"),
    )
    pending_tasks = _count(
        db,
        select(func.count()).select_from(StudyTask).join(StudyPlan, StudyTask.plan_id == StudyPlan.id)
        .where(StudyPlan.user_id == uid, StudyTask.status.in_(["pending", "in_progress"])),
    )
    interviews_total = _count(db, select(func.count()).select_from(InterviewSession).where(InterviewSession.user_id == uid))
    projects_total = _count(db, select(func.count()).select_from(Project).where(Project.user_id == uid))
    projects_completed = _count(db, select(func.count()).select_from(Project).where(Project.user_id == uid, Project.status == "completed"))
    dsa_solved = _count(db, select(func.count()).select_from(DSARecord).where(DSARecord.user_id == uid, DSARecord.status == "solved"))
    dsa_attempted = _count(db, select(func.count()).select_from(DSARecord).where(DSARecord.user_id == uid, DSARecord.status == "attempted"))
    applications_total = _count(db, select(func.count()).select_from(JobApplication).where(JobApplication.user_id == uid))
    status_rows = db.execute(
        select(JobApplication.status, func.count())
        .where(JobApplication.user_id == uid)
        .group_by(JobApplication.status)
    ).all()
    applications_by_status = {str(status): int(count) for status, count in status_rows}

    upcoming_deadlines: list[dict] = []
    tasks = db.execute(
        select(StudyTask.id, StudyTask.title, StudyTask.scheduled_date)
        .join(StudyPlan, StudyTask.plan_id == StudyPlan.id)
        .where(
            StudyPlan.user_id == uid,
            StudyTask.scheduled_date >= date.today(),
            StudyTask.status.in_(["pending", "in_progress"]),
        )
        .order_by(StudyTask.scheduled_date.asc())
        .limit(8)
    ).all()
    upcoming_deadlines.extend({"kind": "study_task", "id": str(row.id), "title": row.title, "date": row.scheduled_date.isoformat()} for row in tasks)
    apps = db.execute(
        select(JobApplication.id, JobApplication.company, JobApplication.role, JobApplication.next_step_date)
        .where(JobApplication.user_id == uid, JobApplication.next_step_date >= date.today())
        .order_by(JobApplication.next_step_date.asc())
        .limit(5)
    ).all()
    upcoming_deadlines.extend(
        {"kind": "application_follow_up", "id": str(row.id), "title": f"{row.company} — {row.role}", "date": row.next_step_date.isoformat()}
        for row in apps
    )
    upcoming_deadlines.sort(key=lambda item: item["date"])

    return AnalyticsOverview(
        documents_total=documents_total,
        resume_analyses_total=analyses_total,
        study_plans_total=plans_total,
        study_tasks_completed=completed_tasks,
        study_tasks_pending=pending_tasks,
        interview_sessions_total=interviews_total,
        projects_total=projects_total,
        projects_completed=projects_completed,
        dsa_problems_solved=dsa_solved,
        dsa_problems_attempted=dsa_attempted,
        applications_total=applications_total,
        applications_by_status=applications_by_status,
        upcoming_deadlines=upcoming_deadlines[:10],
    )
