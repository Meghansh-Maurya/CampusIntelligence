# Campus Intelligence & Placement Assistant — Backend

A learning-oriented FastAPI backend covering the agreed project phases: student accounts/workspace, document management, academic RAG chat, resume analysis, personalized study planning, interview practice, progress tracking/analytics, and shared platform capabilities.

> **Scope note:** Automated job discovery and a job-matching/recommendation engine are intentionally not included. The application tracker records opportunities that a student enters manually. Resume keyword coverage can compare a resume with a job description supplied by the student.

## Technology

- Python 3.12
- FastAPI + Uvicorn
- PostgreSQL + SQLAlchemy 2.x + Psycopg 3
- Pydantic Settings
- Firebase Admin SDK for production token verification
- Google Gen AI SDK (`google-genai`) for Gemini text generation and embeddings (defaults: `gemini-3.8-flash` and `gemini-embedding-2`; both are configurable in `.env`)
- PyMuPDF for selectable-text PDF extraction
- Alembic for schema migrations
- pytest for unit tests

Embeddings are currently stored as JSON arrays in PostgreSQL and ranked in Python. This keeps initial setup easy and avoids requiring the PostgreSQL `vector` extension. It is suitable only for small learning/demo datasets. For larger datasets, migrate embeddings to `pgvector` and perform similarity search in PostgreSQL.

## Important limitations

- Supports **text-based PDF files** up to `MAX_UPLOAD_MB` and `MAX_PDF_PAGES`. Scanned PDFs require OCR, which is not implemented.
- AI features require a valid Gemini API key. When enabled, the backend sends the question and retrieved text, resume text, syllabus excerpts, or interview context needed for the requested task to the configured Gemini API. Do not upload highly sensitive material unless you have reviewed the provider and retention terms. If no key is configured, PDF extraction and lexical indexing still work, but generation, embeddings, resume analysis, syllabus-topic extraction, and mock interviews that require the LLM will return an informative error or use lexical retrieval until generation is requested.
- Development authentication is only for local testing. It trusts `X-Dev-User-Id` and must never be deployed to a public environment. Production must use `AUTH_MODE=firebase`, Firebase ID-token verification, and `DEBUG=false`.
- Resume analysis is evaluated against the bundled `reference/ATS_Resume_Template_2026.pdf`. The fixed rubric allocates 80 points to the template's eight content sections and 20 points to PDF-format checks. Objective checks run in Python; Gemini rates only the semantic criteria stated by the template. This is a template-compliance score, **not** a score from an employer's ATS or a hiring prediction.
- If a job description is supplied, Gemini produces a separate evidence-based job-description alignment report. That report does not change the template score and is not a job recommendation or ranking feature. A skill not found in the resume is reported as missing evidence, not proof that the candidate lacks the skill.
- PDF-format inspection uses text extraction and PDF geometry heuristics for page count, section order, likely columns, typography, margins/alignment, spacing consistency, bullet consistency and text extractability. It cannot reliably reproduce every visual detail or employer ATS behavior; users should visually review the source PDF too.
- The model is told to treat document contents as untrusted text, but prompt instructions alone are not a complete defense against prompt injection. Keep access checks, AI output validation, testing, rate limits and cost controls in place.
- Local file storage is provided for development. For deployment, use private object storage with access controls and lifecycle cleanup.
- `AUTO_CREATE_TABLES=true` is convenient locally. For production, set it to `false` and use the versioned Alembic migration.

## 1. Prerequisites

- Python 3.12
- PostgreSQL installed and running
- A PostgreSQL database. This README assumes the database name `Campus_Intelligence`, matching the local database used during project setup. PostgreSQL folds unquoted identifiers to lowercase; if your database was created with a different exact name, update `DB_NAME` to match it.
- A Gemini API key to test AI features
- Firebase project credentials only when switching to production Firebase authentication

## 2. Install locally (Windows PowerShell)

Extract this backend as its own folder. The Python package is deliberately named lowercase `app` (the recommended convention); do not mix these files with an older uppercase `App` package.

```powershell
cd campus_intelligence_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and edit at least:

```dotenv
DB_USER=postgres
DB_PASSWORD=YOUR_LOCAL_POSTGRES_PASSWORD
DB_HOST=localhost
DB_PORT=5432
DB_NAME=Campus_Intelligence
AUTH_MODE=development
DEBUG=true
```

Do not commit `.env`. The provided `.gitignore` excludes it.

To enable Gemini-dependent features, set a valid `GEMINI_API_KEY` in `.env`. The model IDs are configurable through `GEMINI_MODEL` and `GEMINI_EMBEDDING_MODEL`.

Start the backend from this directory:

```powershell
python -m uvicorn app.main:app --reload
```

Open:

- Health check: http://127.0.0.1:8000/health
- Database readiness: http://127.0.0.1:8000/health/ready
- Interactive API docs: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

On startup, local mode creates missing tables through SQLAlchemy metadata. It does not drop or replace existing tables.

## 3. Test protected endpoints locally

With `AUTH_MODE=development` and `DEBUG=true`, protected endpoints use a local development identity. Swagger UI may show the headers below as optional parameters, or you can send them with any HTTP client:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/users/me" `
  -Headers @{ "X-Dev-User-Id" = "demo-student"; "X-Dev-Email" = "student@example.local" }
```

Use different `X-Dev-User-Id` values to test user data isolation. This mechanism is deliberately guarded by `DEBUG=true`, but that does **not** make it safe for deployment. Use Firebase authentication in production.

## 4. Production Firebase authentication

1. Configure Firebase Authentication in the React client.
2. The client obtains a Firebase ID token after sign-in and sends `Authorization: Bearer <ID_TOKEN>` to this API.
3. Set `AUTH_MODE=firebase` and `DEBUG=false` in the backend environment.
4. Provide `FIREBASE_PROJECT_ID` and either `FIREBASE_SERVICE_ACCOUNT_JSON` or `GOOGLE_APPLICATION_CREDENTIALS` using a secure deployment secret/configuration.
5. Never place Firebase service-account credentials in frontend code or Git.

The backend verifies the token using Firebase Admin SDK; the client-provided user ID is not trusted in Firebase mode.

## 5. API routes

All feature routes are under `/api/v1` unless specified.

| Area | Routes | What they do |
|---|---|---|
| Health | `GET /health`, `GET /health/ready` | Liveness and database readiness |
| Profile | `GET /users/me`, `PATCH /users/me`, `DELETE /users/me` | Read/update/delete own workspace |
| Documents | `POST /documents`, `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/download`, `DELETE /documents/{id}` | Upload/manage private PDFs |
| Academic RAG | `POST /academic/chat`, `GET /academic/conversations`, `GET /academic/conversations/{id}`, `DELETE /academic/conversations/{id}` | Ask evidence-grounded academic questions and retrieve chat history |
| Resume | `POST /resumes/analyze`, `GET /resumes/analyses`, `GET /resumes/analyses/{id}`, `GET /resumes/compare` | Parse/review resumes, inspect history, compare analysis scores |
| Study planner | `POST /study-plans`, `GET /study-plans`, `GET /study-plans/{id}`, `PATCH /study-plans/{id}/tasks/{task_id}`, `DELETE /study-plans/{id}` | Schedule tasks within available time and update completion |
| Interviews | `POST /interviews`, `GET /interviews`, `GET /interviews/{id}`, `POST /interviews/{id}/answers`, `POST /interviews/{id}/end` | Generate interview questions, evaluate answers, summarize sessions |
| Projects | `POST /progress/projects`, `GET /progress/projects`, `PATCH /progress/projects/{id}`, `DELETE /progress/projects/{id}` | Track projects and milestones |
| DSA | `POST /progress/dsa`, `GET /progress/dsa`, `DELETE /progress/dsa/{id}` | Record DSA practice |
| Applications | `POST /applications`, `GET /applications`, `PATCH /applications/{id}`, `DELETE /applications/{id}` | Manually track application status/follow-up dates |
| Analytics | `GET /analytics/overview` | Aggregate counts and upcoming deadlines from stored data |

### Upload a PDF

`POST /api/v1/documents` uses `multipart/form-data` with:

- `file`: a text-based PDF
- `document_type`: one of `syllabus`, `notes`, `previous_year_paper`, `placement_notification`, `job_description`, `resume`
- `subject`: optional text

### Ask the academic assistant

`POST /api/v1/academic/chat` JSON body:

```json
{
  "question": "Explain the key ideas in Unit 3 using my notes.",
  "document_ids": ["UUID-OF-AN-OWNED-ACADEMIC-DOCUMENT"],
  "conversation_id": null
}
```

`document_ids` is optional. When omitted, retrieval uses the user's own ready syllabus, notes and previous-year-paper documents. Resume files and other document categories are excluded from academic retrieval.

### Analyze a resume against the reference template

The bundled `reference/ATS_Resume_Template_2026.pdf` is the evaluation standard. It defines the Header, Summary, Education, Experience, Projects, Technical Skills, Achievements and Certifications content checks. PDF layout is inspected separately.

`POST /api/v1/resumes/analyze` JSON body:

```json
{
  "document_id": "UUID-OF-AN-OWNED-RESUME-DOCUMENT",
  "job_description": null
}
```

- **Resume-only mode:** leave `job_description` as `null` or omit it. The report gives section-by-section template scores, a PDF-format score, strengths and corrections.
- **Resume + JD mode:** provide the text of one job description. The same template score is calculated, and a separate GenAI job-description alignment report identifies requirements as `evidenced`, `partial_evidence` or `not_found`. The JD report does not affect the template score.

The fixed 100-point rubric is: Header 10, Summary 8, Education 10, Experience 12, Projects 18, Technical Skills 12, Achievements 5, Certifications 5, PDF Format 20. Each format check has an individually capped weight; the sum of its displayed check maxima is exactly 20. AI rating-to-points conversion is `good=100%`, `partial=50%`, `weak=25%`, `missing=0%`; objective structural checks are calculated in Python. Missing section headings cannot receive that section's content points. The original PDF must still exist in private storage because format evaluation reads its page geometry and text spans.

The response includes `score_breakdown.content_sections`, `score_breakdown.format`, `feedback.section_feedback`, `feedback.format_feedback`, and `job_description_alignment` (the separate JD alignment report; `available=false` when no JD was supplied). The stored database column remains `keyword_coverage` for backward-compatible schema storage, while the API response exposes the clearer `job_description_alignment` name. JD-alignment ratings of `evidenced` or `partial_evidence` are retained only when Gemini supplies a verbatim quote found in the uploaded resume text; unverified positive claims are downgraded to `not_found`. All positive AI evidence quotes are checked against extracted resume text before being returned. This is a project-specific rubric, not a universal ATS score or hiring prediction.

For the full point-by-point breakdown, see [`RESUME_EVALUATION_RUBRIC.md`](RESUME_EVALUATION_RUBRIC.md). The section weights follow the uploaded template's content expectations; they are our transparent project rubric, not weights defined by the template publisher. The template contains an Experience section, so the strict rubric may deduct points when a fresher has no experience entry. It must never encourage a student to fabricate experience.

### Create a study plan

`POST /api/v1/study-plans` JSON body with manually defined topics:

```json
{
  "title": "DAA exam revision",
  "subject": "Design and Analysis of Algorithms",
  "exam_date": "2027-01-15",
  "available_minutes_per_day": 120,
  "study_weekdays": [0, 1, 2, 3, 4, 5],
  "topics": [
    {"name": "Asymptotic analysis", "estimated_minutes": 90, "preparation_status": "in_progress"},
    {"name": "Greedy algorithms", "estimated_minutes": 120, "preparation_status": "not_started"}
  ],
  "source_document_ids": []
}
```

Python weekday numbers use Monday `0` through Sunday `6`. Instead of `topics`, you can provide owned syllabus document IDs; the AI extracts candidate topics from those files when a Gemini key is configured. The planner uses deterministic scheduling logic and flags work that cannot fit before the exam date.

### Start a mock interview

`POST /api/v1/interviews` JSON body:

```json
{
  "role": "Python Backend Intern",
  "job_description": "Optional job description text",
  "skill_focus": ["Python", "FastAPI", "SQL"]
}
```

A session can be ended to save a structured summary. LLM-based feedback is practice guidance, not a validated hiring assessment.

## 6. Database migrations

A baseline PostgreSQL migration and Alembic configuration are included. When you change SQLAlchemy models, create a new migration and inspect it before applying it:

```powershell
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

For a fresh database, the included `0001_initial` migration creates the tables/indexes that are in the baseline schema. Do not use `alembic downgrade base` casually; it removes tables and data. For production, set `AUTO_CREATE_TABLES=false` and run migrations as part of release/deployment.

## 7. Tests

```powershell
python -m pytest -q
```

The included tests cover pure service logic; API/database integration tests still need to be added against a disposable test database before claiming production readiness.

## 8. Docker Compose

After creating `.env` from `.env.example` and reviewing DB settings:

```powershell
docker compose up --build
```

The compose file starts PostgreSQL and the backend. Do not expose development authentication to a public network. For deployment, switch to Firebase auth, disable debug, use private object storage, apply migrations, configure HTTPS and restrict CORS origins.

## Project structure

```text
app/
  core/            # configuration, DB sessions, auth
  routes/          # HTTP endpoints grouped by feature
  services/        # Gemini generation/embeddings, PDF processing, retrieval, template-based resume scoring
reference/         # User-provided ATS_Resume_Template_2026.pdf used as the rubric reference
  main.py          # FastAPI application, middleware and router registration
  models.py        # SQLAlchemy database models
  schemas.py       # Pydantic request/response schemas
migrations/        # Alembic environment and initial revision
 tests/             # Pure service unit tests
```

## Engineering follow-ups before real production use

- Add end-to-end/API tests with a disposable PostgreSQL instance and a mocked AI client.
- Move file storage to private object storage; add file retention and orphan cleanup.
- Move semantic retrieval to `pgvector` (or another vector store) for large libraries.
- Add rate limiting, quotas, AI spend limits, background ingestion, retry handling and monitoring.
- Consider malware scanning and stronger content controls for user uploads.
- Define data retention/export policy, and delete associated vector/derived data when a source document is deleted.
- Evaluate retrieval and generated answers against a curated test set before relying on them for exam preparation.
