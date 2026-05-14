# HIWALOY

> **"How It Will ACTUALLY Look On You"**  
> Yapay zeka destekli beden uyum tahmini ve satın alma riski analizi platformu.

Hackathon MVP — primary user-facing language: **Turkish**. Internal code/docs: English.

---

## What is HIWALOY?

HIWALOY is a purchase-confidence system that analyzes a garment image and a user's body measurements to predict:

- the **recommended clothing size** for that specific item
- a **confidence score** (0–100%) reflecting how certain the prediction is
- a **purchase risk assessment** (low / medium / high) with specific risk factors
- **community insights** drawn from similar user reviews via RAG

The goal is to reduce wrong-size purchases, fit mismatch, and e-commerce return rates.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router) · TailwindCSS · shadcn/ui · Framer Motion |
| Backend | FastAPI (Python 3.11) |
| AI pipeline | LangGraph · Gemini 1.5 Flash (multimodal) |
| Vector store | ChromaDB (in-memory in DEMO_MODE) |
| Database | PostgreSQL 16 |
| Containers | Docker · Docker Compose |

---

## Quick Start

### Option A — Docker (recommended)

```bash
git clone <repo>
cd HACKATHON
cp .env.example .env        # defaults have DEMO_MODE=true
```

Then start the stack with the launcher for your OS (the launcher disables
Docker BuildKit, which is required because the Next.js dynamic route
`app/history/[id]/page.tsx` trips BuildKit's glob parser on some platforms):

- **Windows (PowerShell):** `.\start-demo.ps1`
- **macOS / Linux:** `chmod +x ./start-demo.sh && ./start-demo.sh`

Wait for `Application startup complete.` then open **http://localhost:3000**

API docs: http://localhost:8000/docs  
Health: http://localhost:8000/api/v1/health

```bash
docker compose down          # stop
```

### Option B — Local dev (no Docker)

**Requirements:** Python 3.11+, Node.js 18+, PostgreSQL 15+

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate               # Windows
# source .venv/bin/activate          # macOS/Linux
pip install -r requirements.txt
# create backend/.env — see .env.example
DEMO_MODE=true uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000

---

## Environment Variables

Copy `.env.example` → `.env` and adjust. **Never commit `.env`.**

| Variable | Default | Required |
|----------|---------|----------|
| `DEMO_MODE` | `true` | No — set `false` for real Gemini |
| `GEMINI_API_KEY` | *(empty)* | Only when `DEMO_MODE=false` |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Only when `DEMO_MODE=false` |
| `POSTGRES_PASSWORD` | `hiwaloy_local` | Yes |
| `POSTGRES_PORT` | `5433` | Yes |
| `BACKEND_PORT` | `8000` | Yes |
| `FRONTEND_PORT` | `3000` | Yes |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Yes (baked into build) |

### DEMO_MODE

When `DEMO_MODE=true`:
- `MockAIClient` returns deterministic body + garment analysis (no Gemini API call)
- Review Intelligence uses a seeded **in-memory** ChromaDB — no external ChromaDB needed
- Pipeline completes in ~1 second with realistic Turkish output

When `DEMO_MODE=false`:
- `GEMINI_API_KEY` required
- ChromaDB must be running at `CHROMA_HOST:CHROMA_PORT`
- Real Gemini 1.5 Flash multimodal analysis runs on uploaded images

---

## Repo Layout

```
HACKATHON/
├── frontend/                 Next.js 14 app
│   ├── app/
│   │   ├── page.tsx          Landing page
│   │   ├── onboarding/       Profile creation (UC-01)
│   │   ├── analyze/          Garment upload + AI analysis (UC-02 to UC-07)
│   │   └── history/          Analysis history (UC-08)
│   ├── components/           Shared UI components
│   └── lib/api/              Type-safe API client
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── client.py     MockAIClient / RealGeminiClient
│   │   │   ├── nodes.py      6 LangGraph pipeline nodes
│   │   │   ├── graph.py      LangGraph StateGraph wiring
│   │   │   └── state.py      PipelineState TypedDict
│   │   ├── api/              FastAPI routers
│   │   ├── models/           SQLModel ORM models
│   │   ├── repositories/     Data access layer
│   │   ├── schemas/          Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── review_service.py   ChromaDB RAG + demo seeding
│   │   │   └── image_store.py      Image validation and storage
│   │   └── config.py         Pydantic Settings (env vars)
│   └── tests/                124 tests (pytest)
│
├── docker-compose.yml
├── .env.example
└── DEMO.md                   Hackathon demo guide
```

---

## AI Pipeline

```
POST /api/v1/analyze
        │
        ▼
 intent_validator        ← sanity-check inputs
        │ (valid)
        ▼
    analyzer             ← asyncio.gather(body_analysis, garment_analysis)
    (Gemini multimodal / MockAIClient)
        │
        ▼
 review_retriever        ← ChromaDB cosine similarity + Jaccard dedup
    (RAG / seeded mock)
        │
        ▼
recommendation_generator ← deterministic BMI + fit_type + brand delta
        │
        ▼
  risk_evaluator         ← confidence + fabric + brand + review signals
        │
        ▼
 turkish_formatter       ← assembles final JSON with all Turkish fields
        │
        ▼
  GarmentUploadResponse  (202 Accepted)
```

All output fields are Turkish: `explanation_tr`, `risk_level_tr`, `risk_factors_tr`, `uncertainty_tr`, `community_insights_tr`.

---

## API Endpoints

| Method | Path | Use Case |
|--------|------|----------|
| `GET` | `/api/v1/health` | Liveness check |
| `POST` | `/api/v1/profile` | UC-01: Create user profile |
| `GET` | `/api/v1/profile/{user_id}` | UC-01: Get profile |
| `POST` | `/api/v1/analyze` | UC-02–07: Upload garment + run full analysis |
| `GET` | `/api/v1/history/{user_id}` | UC-08: List analyses |
| `GET` | `/api/v1/history/{user_id}/{analysis_id}` | UC-08: Analysis detail |

---

## Tests

```bash
cd backend
pytest                   # 124 tests
pytest -v --tb=short     # verbose output
```

Coverage: unit tests (AI client, pipeline nodes, review intelligence), integration tests (full HTTP request/response cycle), upload error paths, CORS, history isolation.

---

## Limitations

See `docs/KNOWN_LIMITATIONS.md` for an honest account of MVP boundaries. In short: the size recommendation is **deterministic** (BMI + deltas), not learned from a trained model. Gemini provides qualitative garment and body analysis but does not output numeric measurements. Review data is curated/seeded, not scraped at runtime.

---

## Documentation

| Document | Purpose |
|----------|---------|
| `DEMO.md` | Hackathon demo guide and troubleshooting |
| `docs/DEMO_SCRIPT.md` | 3–5 minute Turkish presentation script |
| `docs/SRS_COMPLIANCE.md` | UC-01 to UC-08 implementation mapping |
| `docs/KNOWN_LIMITATIONS.md` | Honest MVP scope and boundaries |
