# Campus Intelligence frontend

React 19 + TypeScript + Vite frontend connected to the FastAPI backend.

## Setup (Windows CMD)

```cmd
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open http://127.0.0.1:5173. Build check:

```cmd
npm run build
```

## Environment

`VITE_API_BASE_URL` points to the backend API prefix. `VITE_DEV_USER_ID` and `VITE_DEV_EMAIL` are development-only identity headers and work only while backend `AUTH_MODE=development` and `DEBUG=true`. They are not authentication and must not be used for a public deployment. Firebase client authentication is not wired in this initial integration.

Never put Gemini API keys, database passwords or Firebase service-account credentials in frontend environment variables. Browser-visible variables must not contain secrets.

## Implemented screens

- Dashboard and live analytics overview
- PDF document upload, listing, filtering, download and deletion
- Academic assistant with saved conversations and source citations
- Resume upload workflow integration, template-based analysis and history
- Study plan creation, task completion and deletion
- AI mock interview sessions, answer evaluation and summary
- Project, DSA and manual job-application tracking
- Student profile editing

AI-dependent functions require a valid Gemini API key in `backend/.env`. Academic Q&A can return an evidence-limited response when no indexed passages are available. The resume analyzer and mock interviews require Gemini.
