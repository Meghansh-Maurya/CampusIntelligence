from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserRead(ORMModel):
    id: UUID
    email: str | None
    full_name: str | None
    department: str | None
    year_of_study: int | None
    skills: list[str]
    interests: list[str]
    career_goals: list[str]
    created_at: datetime


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    department: str | None = Field(default=None, max_length=160)
    year_of_study: int | None = Field(default=None, ge=1, le=8)
    skills: list[str] | None = Field(default=None, max_length=100)
    interests: list[str] | None = Field(default=None, max_length=100)
    career_goals: list[str] | None = Field(default=None, max_length=50)


class DocumentRead(ORMModel):
    id: UUID
    original_filename: str
    document_type: str
    subject: str | None
    content_type: str
    file_size_bytes: int
    page_count: int
    status: str
    created_at: datetime


class Citation(BaseModel):
    source_number: int
    document_id: UUID
    document_name: str
    page_number: int | None
    excerpt: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=5000)
    conversation_id: UUID | None = None
    document_ids: list[UUID] | None = Field(default=None, max_length=50)


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    citations: list[Citation]


class MessageRead(ORMModel):
    id: UUID
    role: str
    content: str
    citations: list[dict[str, Any]]
    created_at: datetime


class ConversationRead(ORMModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class ResumeAnalyzeRequest(BaseModel):
    document_id: UUID
    job_description: str | None = Field(default=None, max_length=20000)


class ResumeAnalysisRead(ORMModel):
    id: UUID
    document_id: UUID | None
    resume_filename: str
    extracted_data: dict[str, Any]
    feedback: dict[str, Any]
    resume_score: int
    score_breakdown: dict[str, Any]
    job_description_alignment: dict[str, Any] = Field(validation_alias="keyword_coverage")
    created_at: datetime


class StudyTopicInput(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    estimated_minutes: int = Field(default=60, ge=15, le=2000)
    preparation_status: Literal["not_started", "in_progress", "completed"] = "not_started"


class StudyPlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    subject: str = Field(min_length=1, max_length=160)
    exam_date: date
    available_minutes_per_day: int = Field(ge=15, le=720)
    study_weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5], min_length=1, max_length=7)
    topics: list[StudyTopicInput] = Field(default_factory=list, max_length=150)
    source_document_ids: list[UUID] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_days_and_topics(self) -> "StudyPlanCreate":
        if any(day < 0 or day > 6 for day in self.study_weekdays):
            raise ValueError("study_weekdays must contain Python weekday numbers 0 through 6.")
        if not self.topics and not self.source_document_ids:
            raise ValueError("Provide topics or source_document_ids from uploaded syllabus material.")
        if len(set(self.study_weekdays)) != len(self.study_weekdays):
            raise ValueError("study_weekdays cannot contain duplicate days.")
        return self


class StudyTaskRead(ORMModel):
    id: UUID
    title: str
    topic: str
    scheduled_date: date | None
    estimated_minutes: int
    status: str
    notes: str | None
    completed_at: datetime | None


class StudyPlanRead(ORMModel):
    id: UUID
    title: str
    subject: str
    exam_date: date
    available_minutes_per_day: int
    study_weekdays: list[int]
    topics: list[dict[str, Any]]
    overloaded: bool
    unscheduled_minutes: int
    source_document_ids: list[str]
    created_at: datetime
    updated_at: datetime
    tasks: list[StudyTaskRead]


class StudyTaskUpdate(BaseModel):
    status: Literal["pending", "in_progress", "completed", "skipped"]
    notes: str | None = Field(default=None, max_length=2000)


class InterviewStartRequest(BaseModel):
    role: str = Field(min_length=2, max_length=200)
    job_description: str | None = Field(default=None, max_length=12000)
    skill_focus: list[str] = Field(default_factory=list, max_length=30)


class InterviewAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=10000)


class InterviewSessionRead(ORMModel):
    id: UUID
    role: str
    job_description: str | None
    skill_focus: list[str]
    status: str
    summary: dict[str, Any]
    created_at: datetime
    ended_at: datetime | None


class InterviewTurnRead(ORMModel):
    id: UUID
    role: str
    content: str
    evaluation: dict[str, Any]
    created_at: datetime


class InterviewSessionDetail(InterviewSessionRead):
    turns: list[InterviewTurnRead]


class InterviewAnswerResponse(BaseModel):
    evaluation: dict[str, Any]
    next_question: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: Literal["planned", "in_progress", "completed", "on_hold"] = "planned"
    skills: list[str] = Field(default_factory=list, max_length=100)
    milestones: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    repository_url: str | None = Field(default=None, max_length=500)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: Literal["planned", "in_progress", "completed", "on_hold"] | None = None
    skills: list[str] | None = Field(default=None, max_length=100)
    milestones: list[dict[str, Any]] | None = Field(default=None, max_length=100)
    repository_url: str | None = Field(default=None, max_length=500)


class ProjectRead(ORMModel):
    id: UUID
    name: str
    description: str | None
    status: str
    skills: list[str]
    milestones: list[dict[str, Any]]
    repository_url: str | None
    created_at: datetime
    updated_at: datetime


class DSARecordCreate(BaseModel):
    problem_name: str = Field(min_length=1, max_length=240)
    topic: str = Field(min_length=1, max_length=120)
    platform: str | None = Field(default=None, max_length=120)
    difficulty: Literal["easy", "medium", "hard", "unknown"] = "unknown"
    status: Literal["solved", "attempted", "revisit"] = "solved"
    notes: str | None = Field(default=None, max_length=5000)
    solved_at: datetime | None = None


class DSARecordRead(ORMModel):
    id: UUID
    problem_name: str
    topic: str
    platform: str | None
    difficulty: str
    status: str
    notes: str | None
    solved_at: datetime | None
    created_at: datetime


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=1000)
    status: Literal["saved", "applied", "screening", "interview", "offer", "rejected", "withdrawn"] = "applied"
    applied_on: date | None = None
    next_step_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None, min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=1000)
    status: Literal["saved", "applied", "screening", "interview", "offer", "rejected", "withdrawn"] | None = None
    applied_on: date | None = None
    next_step_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)


class ApplicationRead(ORMModel):
    id: UUID
    company: str
    role: str
    source_url: str | None
    status: str
    applied_on: date | None
    next_step_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AnalyticsOverview(BaseModel):
    documents_total: int
    resume_analyses_total: int
    study_plans_total: int
    study_tasks_completed: int
    study_tasks_pending: int
    interview_sessions_total: int
    projects_total: int
    projects_completed: int
    dsa_problems_solved: int
    dsa_problems_attempted: int
    applications_total: int
    applications_by_status: dict[str, int]
    upcoming_deadlines: list[dict[str, Any]]
