# HIWALOY

> "How It Will ACTUALLY Look On You"
> AI-powered fashion fit & purchase risk analysis platform.

Hackathon MVP. Primary user-facing language: **Turkish**. Internal code/docs: English.

This is the **Phase 0 skeleton**: services, configs, and health endpoints only. AI agents, LangGraph wiring, and the data layer are added in subsequent phases per `docs/01_architecture.md`.

---

## Stack

- **Frontend:** Next.js (App Router) + TailwindCSS + shadcn/ui + Framer Motion
- **Backend:** FastAPI (Python)
- **AI Layer (added later):** Gemini API, LangChain, LangGraph
- **Databases:** PostgreSQL, ChromaDB
- **Infra:** Docker, Docker Compose

## Repo layout

```
frontend/             Next.js app
backend/              FastAPI app
docker-compose.yml    All services
.env.example          Root orchestration env
```

## Quick start (Docker)

1. Copy env example:
   ```bash
   cp .env.example .env
   ```
2. Bring up the stack:
   ```bash
   docker compose up --build
   ```
3. Health checks:
   - Frontend: http://localhost:3000
   - Backend health: http://localhost:8000/api/v1/health

## Local dev (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate     # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

## Tests / checks

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run lint
npm run build
```

## Phase status

- [x] Phase 0: Foundations (this commit)
- [ ] Phase 1: Data layer (Postgres tables, Chroma ingestion)
- [ ] Phase 2: Profile & upload (UC-01, UC-02)
- [ ] Phase 3: Body / Garment analyzer agents (UC-03, UC-04)
- [ ] Phase 4: Review intelligence RAG (UC-06)
- [ ] Phase 5: Recommendation + Risk (UC-05, UC-07)
- [ ] Phase 6: LangGraph wiring
- [ ] Phase 7: History UI + composite frontend (UC-08)
- [ ] Phase 8: Hardening + review

## Secrets

Never commit `.env`. Gemini and embedding keys are required from Phase 3 onward — empty in Phase 0.
