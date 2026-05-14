# HIWALOY — Hackathon Demo Guide

**HIWALOY** — "How It Will ACTUALLY Look On You"  
AI-powered fit prediction and purchase risk analysis platform.

---

## Quick Start (Docker — Recommended)

The frontend uses a Next.js dynamic route at `app/history/[id]/page.tsx`. On some
platforms Docker BuildKit interprets the `[id]` directory as a glob character
class and aborts the build with `invalid file request app/history/[id]/page.tsx`.
The launcher scripts disable BuildKit for the compose build, which avoids the
issue. Run the launcher for your OS instead of calling `docker compose` directly.

### 1. Start all services

**Windows (PowerShell):**
```powershell
.\start-demo.ps1
```

**macOS / Linux:**
```bash
chmod +x ./start-demo.sh
./start-demo.sh
```

The script copies `.env.example` to `.env` on first run (defaults to
`DEMO_MODE=true` — no Gemini API key needed), then runs
`docker compose up --build` with BuildKit disabled.

Wait for:
```
hiwaloy-backend   | INFO:     Application startup complete.
hiwaloy-frontend  | ✓ Ready
```

### 2. Open the app
- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

### 3. Stop
```bash
docker compose down
```

### Manual fallback (if you must call compose directly)
Set the env vars yourself before invoking compose:

**PowerShell:**
```powershell
$env:DOCKER_BUILDKIT="0"; $env:COMPOSE_DOCKER_CLI_BUILD="0"; docker compose up --build
```

**bash/zsh:**
```bash
DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker compose up --build
```

---

## Local Dev (No Docker)

Requires: Python 3.11+, Node.js 18+, PostgreSQL 15+

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# Create backend/.env
cp ../.env.example .env
# Edit .env: set POSTGRES_PASSWORD and DATABASE_URL

DEMO_MODE=true uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000

---

## Demo Flow (3 minutes)

1. **Landing page** → shows HIWALOY value proposition in Turkish
2. **Profil Oluştur** (/onboarding):
   - Enter height: `175`, weight: `70`, fit: `Normal Kesim`
   - Click "Profil Oluştur" → redirected to analyze
3. **Kıyafet Analizi** (/analyze):
   - Upload any JPEG/PNG garment image (max 8MB)
   - Click "Analizi Başlat"
   - Watch the 6-step AI analysis progress
   - See: recommended size, confidence score, risk panel, community insights
4. **Geçmiş Analizler** (/history):
   - Lists all analyses for this profile
   - Click any card to see full detail

---

## Demo Mode Details

When `DEMO_MODE=true`:
- **MockAIClient** returns deterministic body + garment analysis (no Gemini API call)
- **Review Intelligence** uses a seeded in-memory ChromaDB (no external ChromaDB needed)
- All Turkish output fields are populated with realistic values
- Confidence score: `0.75`, Risk level: `medium`
- Pipeline completes in ~1 second

When `DEMO_MODE=false`:
- Requires `GEMINI_API_KEY` in `.env`
- Requires ChromaDB running at `CHROMA_HOST:CHROMA_PORT`
- Real multimodal Gemini analysis runs on uploaded images

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO_MODE` | `true` | Use mock AI + in-memory reviews |
| `GEMINI_API_KEY` | *(empty)* | Required only when `DEMO_MODE=false` |
| `POSTGRES_PASSWORD` | `hiwaloy_local` | Local DB password |
| `BACKEND_PORT` | `8000` | Backend port |
| `FRONTEND_PORT` | `3000` | Frontend port |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Backend URL (baked into frontend build) |

---

## Troubleshooting

**"Profil bulunamadı" on analyze page**  
→ Go to /onboarding and create a profile first.

**Backend not responding**  
→ Check `docker compose logs backend`. PostgreSQL must be healthy.

**Build error: `invalid file request app/history/[id]/page.tsx`**  
→ Docker BuildKit's glob handling on Windows breaks on bracket directories.
Use `.\start-demo.ps1` (or the env-var fallback shown in Quick Start) instead
of calling `docker compose up --build` directly. The script sets
`DOCKER_BUILDKIT=0` and `COMPOSE_DOCKER_CLI_BUILD=0` before invoking compose.

**Frontend shows old data after rebuild**  
→ `NEXT_PUBLIC_API_BASE_URL` is baked into the Next.js build. If you change the backend URL, rebuild: `docker compose up --build frontend`.

**Port conflict**  
→ Edit `.env`: change `BACKEND_PORT`, `FRONTEND_PORT`, or `POSTGRES_PORT`.

---

## Architecture Summary

```
Browser (Next.js 14)
    ↕ REST API
FastAPI Backend
    ├── LangGraph Pipeline (6 nodes)
    │     intent_validator → analyzer → review_retriever
    │     → recommendation_generator → risk_evaluator → turkish_formatter
    ├── MockAIClient / RealGeminiClient (multimodal)
    ├── PostgreSQL (profiles, analyses)
    └── ChromaDB (review embeddings — or in-memory in DEMO_MODE)
```
