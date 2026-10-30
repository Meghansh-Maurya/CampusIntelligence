# Campus Intelligence & Placement Assistant

A single repository containing the FastAPI backend and the React + TypeScript frontend starter.

## Repository layout

```text
Campus_Intelligence_Project/
  backend/   FastAPI API, database models, AI services, migrations, tests and backend docs
  frontend/  React + TypeScript + Vite starter UI
  README.md this file
```

## Important project status

- The backend is a learning-oriented baseline covering the agreed phases and API routes. See `backend/README.md` for configuration, API examples, limitations and deployment notes.
- The frontend is an initial starter, not a finished implementation of all pages. It currently includes the project shell, navigation placeholders and a light/dark theme toggle. We will build the actual screens and connect them to the backend incrementally.
- No real `.env` file, API key, password, Firebase service-account credential, `node_modules` or Python virtual environment is included.
- The standalone automated job-matching/recommendation engine and the previously removed optional advanced-features phase remain out of scope. Resume analysis can compare against a student-provided JD; application tracking is manual.

## Run the backend

See `backend/README.md`. Quick local start (Windows PowerShell):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit backend/.env with your PostgreSQL settings and optional Gemini key.
python -m uvicorn app.main:app --reload
```

Backend docs: http://127.0.0.1:8000/docs

## Run the frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Vite normally serves the frontend at http://127.0.0.1:5173.

## Learning workflow

Do not treat this archive as a reason to skip understanding the implementation. Read the backend learning guide and continue the frontend in small chunks: environment setup, React entry point, components, design system, layout, routing, authentication and feature pages. Review and test each change before moving on.
