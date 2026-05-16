# HIWALOY

> **"How It Will ACTUALLY Look On You"**
> Yapay zeka destekli beden uyum tahmini, satın alma riski analizi ve konuşma-tabanlı alışveriş asistanı platformu.

Hackathon MVP — primary user-facing language: **Turkish**. Internal code/docs: English.

---

## What is HIWALOY?

HIWALOY is a purchase-confidence system that takes a garment photo + a user's body profile and produces:

- the **recommended clothing size** for that specific item
- a **confidence score** (0–100%) reflecting how certain the prediction is
- a **purchase risk assessment** (low / medium / high) with explicit risk factors
- a **per-category risk heat map** (e.g. shirts → omuz / kol / bel, jeans → bel / kalça / bacak, dress → omuz / bel / kalça)
- a **similar-user return-reason panel** — *"Benzer kullanıcıların %42'si boy nedeniyle iade etmiş"* — grounded in real review data with cohort scope badges
- a **per-product conversational chat** answering 5 high-impact Turkish question types
- community insights drawn from a RAG over the Turkish review corpus
- an **AI stylist** that picks 3 catalog items grounded in the user's profile + budget

The goal is to reduce wrong-size purchases, fit mismatch, return rates, and the "I'm not sure if this is for me" hesitation.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router) · TailwindCSS · shadcn/ui · Framer Motion · NextAuth (Google) |
| Backend | FastAPI (Python 3.11) · SQLModel · python-jose |
| AI pipeline | LangGraph · Gemini 3.1 Flash Lite (multimodal) · Gemini text-embedding-004 |
| Vector store | ChromaDB (in-memory seeded in DEMO_MODE) |
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

Start the stack with the launcher for your OS (it disables Docker BuildKit, which trips on the dynamic Next.js route on some platforms):

- **Windows (PowerShell):** `.\start-demo.ps1`
- **macOS / Linux:** `chmod +x ./start-demo.sh && ./start-demo.sh`

Wait for `Application startup complete.` then open **http://localhost:3000**

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

```bash
docker compose down          # stop
```

### Option B — Local dev (no Docker)

**Requirements:** Python 3.11+, Node.js 18+, PostgreSQL 15+, (optional) ChromaDB on port 8001.

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate                 # Windows
# source .venv/bin/activate             # macOS/Linux
pip install -r requirements.txt
# create backend/.env — see .env.example
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

### First-run data prep (live mode only)

When `DEMO_MODE=false`, the review corpus must be enriched and ingested into ChromaDB before similar-user panels can return real numbers:

```bash
cd backend
python -m scripts.augment_reviews        # writes data/reviews_enriched.jsonl
python -m scripts.ingest                 # ingests into ChromaDB
```

The enriched JSONL is committed to git, so step 1 is usually a no-op. Step 2 is required once per fresh ChromaDB instance.

---

## Environment Variables

Copy `.env.example` → `.env` and adjust. **Never commit `.env`.**

| Variable | Default | Required | Purpose |
|----------|---------|----------|---------|
| `DEMO_MODE` | `true` | No | Forces `MockAIClient` + in-memory ChromaDB seed. Set `false` for real Gemini. |
| `GEMINI_API_KEY` | *(empty)* | Yes if `DEMO_MODE=false` | Google AI Studio API key. |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | No | Multimodal model used by analyzer + narrative_composer + stylist. |
| `EMBEDDING_MODEL` | *(empty)* | No | Set to `text-embedding-004` to route Chroma queries through Gemini embeddings (else MiniLM via Chroma default). |
| `ENABLE_GEMINI_NARRATIVE` | `false` | No | Opt-in Gemini polish over the deterministic QA answer. See **QA composition** below. |
| `NEXTAUTH_SECRET` | *(empty)* | Yes | Shared HS256 secret. Frontend signs Bearer tokens, backend verifies. Must match between the two. |
| `POSTGRES_PASSWORD` | `hiwaloy_local` | Yes | |
| `POSTGRES_PORT` | `5433` | Yes | |
| `CHROMA_HOST` | `localhost` | Yes if `DEMO_MODE=false` | |
| `CHROMA_PORT` | `8001` | Yes if `DEMO_MODE=false` | |
| `BACKEND_PORT` | `8000` | Yes | |
| `FRONTEND_PORT` | `3000` | Yes | |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Yes | Baked into the Next.js build. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | *(empty)* | Yes | NextAuth Google OAuth credentials (frontend only). |

### DEMO_MODE

When `DEMO_MODE=true`:
- `MockAIClient` returns deterministic body + garment + stylist analysis (no Gemini API call)
- Review Intelligence uses a seeded **in-memory** ChromaDB stub — no external ChromaDB needed
- Pipeline completes in ~1 second with realistic Turkish output
- The 218-test suite uses this mode by default

When `DEMO_MODE=false`:
- `GEMINI_API_KEY` required
- ChromaDB must be running at `CHROMA_HOST:CHROMA_PORT`
- Real Gemini 3.1 Flash Lite runs multimodal analysis on uploaded images
- Real cohort lookups run against the enriched 200-row review corpus

---

## Repo Layout

```
HACKATHON/
├── frontend/                            Next.js 14 app
│   ├── app/
│   │   ├── page.tsx                     Landing + recent-history grid
│   │   ├── login/                       Google OAuth (NextAuth)
│   │   ├── onboarding/                  Profile creation (UC-01)
│   │   ├── analyze/                     Upload + analysis + QA chat (UC-02–07)
│   │   ├── stilist/                     AI Stylist suggestions
│   │   └── history/                     Analysis history (UC-08)
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── agent-pipeline.tsx       Live 7-node LangGraph visualisation
│   │   │   ├── body-heatmap.tsx         Per-category risk heatmap (5 regions)
│   │   │   ├── similar-users-panel.tsx  Cohort return-reason bars
│   │   │   └── product-qa-chat.tsx      5-intent conversational follow-up
│   │   └── ui/                          shadcn primitives
│   ├── lib/
│   │   ├── api.ts                       apiFetch() with auto Bearer injection
│   │   ├── auth.ts                      NextAuth config (Google, HS256)
│   │   └── i18n/tr.ts                   All Turkish UI strings
│   └── middleware.ts                    Route guard
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── client.py                MockAIClient / RealGeminiClient
│   │   │   ├── nodes.py                 7 LangGraph pipeline nodes + heatmap dispatch
│   │   │   ├── graph.py                 LangGraph StateGraph wiring
│   │   │   ├── state.py                 PipelineState TypedDict
│   │   │   ├── embeddings.py            Gemini text-embedding-004 adapter
│   │   │   ├── qa_intent.py             Regex Turkish intent router (5 intents)
│   │   │   ├── qa_facts.py              Deterministic fact collectors per intent
│   │   │   └── qa_narrative.py          Optional Gemini polish + honesty validator
│   │   ├── api/
│   │   │   ├── analyze.py               POST /analyze
│   │   │   ├── auth.py                  Bearer JWT dependency
│   │   │   ├── cohort.py                GET /analyses/{id}/cohort (lazy)
│   │   │   ├── history.py               GET /history list + detail
│   │   │   ├── profile.py               POST/GET /profile
│   │   │   ├── qa.py                    POST /qa (chat)
│   │   │   └── stylist.py               POST /stilist (Gemini 3-pick)
│   │   ├── models/                      SQLModel ORM (User, Analysis)
│   │   ├── repositories/                Data access layer
│   │   ├── schemas/                     Pydantic request/response models
│   │   ├── services/
│   │   │   ├── catalog.py               garments.json + derived price/breath/season
│   │   │   ├── cohort.py                Two-stage cohort + return-reason aggregation
│   │   │   ├── fabric_rules.py          Shared breathability + season lookup
│   │   │   ├── image_store.py           Image validation and storage
│   │   │   └── review_service.py        ChromaDB RAG with tiered metadata filter
│   │   └── config.py                    Pydantic Settings (env vars)
│   ├── scripts/
│   │   ├── augment_reviews.py           Deterministic enrichment → reviews_enriched.jsonl
│   │   └── ingest.py                    Chroma ingest with full metadata
│   └── tests/                           228 tests (pytest)
│
├── data/
│   ├── garments.json                    50 catalog items
│   ├── reviews.jsonl                    200 raw Turkish reviews
│   └── reviews_enriched.jsonl           Same 200 + returned/return_reason/breath/season/category
│
├── docker-compose.yml
├── .env.example
└── DEMO.md                              Hackathon demo guide
```

---

## AI Pipeline

```
POST /api/v1/analyze
        │
        ▼
 intent_validator           ← deterministic input sanity (height, weight, garment ref)
        │ (valid)
        ▼
   analyzer                 ← asyncio.gather (body + garment in PARALLEL)
   ├─ analyze_body          ← Gemini multimodal
   └─ analyze_garment       ← Gemini multimodal + is_garment gate
        │
        ▼
 review_retriever           ← ChromaDB cosine ≥ 0.30 + Jaccard dedup
                              · Embeddings: Gemini text-embedding-004 (or MiniLM)
                              · Metadata where-filter with tiered fallback:
                                category → +fit_type → +season → +breathability
        │
        ▼
recommendation_generator    ← deterministic (BMI + fit_type + brand_tendency deltas)
        │
        ▼
  risk_evaluator            ← deterministic (confidence + fabric + brand + review themes)
        │
        ▼
 narrative_composer         ← Gemini text — writes detailed Turkish explanation
                              (the "Detaylı Analiz" card)
        │
        ▼
 turkish_formatter          ← deterministic final assembly:
                              · per-category risk heatmap (omuz/kol/bel,
                                bel/kalça/bacak, omuz/bel/kalça)
                              · garment_meta passthrough for /qa + /cohort
        │
        ▼
 GarmentUploadResponse (202)
```

Then asynchronously, from the frontend:

```
GET /api/v1/analyses/{id}/cohort  → SimilarUsersPanel
  (lazy side-call, never blocks the hero size card)

POST /api/v1/qa  → ProductQAChat
  (5 intents: is_big | fabric_sweat | cut_wide | similar_users | return_reasons)
```

All user-facing output fields are Turkish.

### Where Gemini actually runs

| Node / endpoint | Gemini call | Notes |
|---|---|---|
| `analyzer.analyze_body` | vision + Turkish JSON | always (live mode) |
| `analyzer.analyze_garment` | vision + Turkish JSON + is_garment gate | always (live mode) |
| `review_retriever` | `text-embedding-004` | only when `EMBEDDING_MODEL` is set |
| `narrative_composer` | Gemini text | always (live mode) — writes "Detaylı Analiz" card |
| `/stilist` | `stylist_pick` — picks 3 from catalog | always (live mode) |
| `/qa` | optional polish via `compose_qa_narrative` | only when `ENABLE_GEMINI_NARRATIVE=true` (default OFF) |
| `/analyses/{id}/cohort` | none | pure Python aggregation over enriched JSONL |

---

## API Endpoints

| Method | Path | Use case |
|--------|------|----------|
| `GET` | `/api/v1/health` | Liveness check (no auth) |
| `POST` | `/api/v1/profile` | UC-01 — Create / update profile (Bearer) |
| `GET` | `/api/v1/profile/me` | UC-01 — Get my profile (Bearer) |
| `POST` | `/api/v1/analyze` | UC-02–07 — Upload garment + run full pipeline (Bearer) |
| `GET` | `/api/v1/history` | UC-08 — List my analyses, newest first (Bearer) |
| `GET` | `/api/v1/history/{analysis_id}` | UC-08 — Analysis detail (Bearer) |
| `DELETE` | `/api/v1/history/{analysis_id}` | Delete a single analysis (Bearer) |
| `POST` | `/api/v1/stylist` | AI Stylist — 3 grounded picks from local catalog (Bearer) |
| `GET` | `/api/v1/analyses/{id}/cohort` | Similar-user return-reason stats (Bearer, lazy) |
| `POST` | `/api/v1/qa` | Conversational follow-up — 5 intents anchored to an analysis (Bearer) |

**Auth model:** NextAuth on the frontend signs an HS256 JWT with `NEXTAUTH_SECRET`; the backend verifies the same secret and resolves the user by `google_sub`. Every protected route uses the `get_current_user` dependency.

---

## QA composition (deterministic by default, Gemini opt-in)

The `/qa` endpoint produces Turkish answers in two layers:

1. **Deterministic floor** — pure Python fact collectors (`app/ai/qa_facts.py`) read the persisted analysis (`garment_meta`, `recommendation`, `risk_evaluation`), the catalog, and the cohort aggregation. They emit a Turkish `verdict_tr` string and a list of `evidence_tr` bullets. **All numbers and percentages come from real data.** No LLM is called.

2. **Optional Gemini polish** — when `ENABLE_GEMINI_NARRATIVE=true`, the deterministic verdict is sent to Gemini for a more natural Turkish rewrite. An honesty-rail validator (`app/ai/qa_narrative.py`) extracts every number / percentage from the rewrite and rejects any that wasn't present in the deterministic verdict or its facts dict. **On rejection, the deterministic verdict ships instead** — the floor is never below the deterministic answer.

The flag defaults OFF so the demo is reproducible.

---

## Similar-User Return Reason Panel

Lazy-loaded via `GET /api/v1/analyses/{id}/cohort` after the hero size card paints. The cohort uses **two-stage relaxation** to avoid empty panels on sparse data:

- **Stage A:** same `category` + `brand_sizing_tendency` + height ±5cm + weight ±7kg
- **Stage B fallback:** same `category` only

Confidence bands gate what gets published:
- `high` (n ≥ 15) — percentages and reasons shown
- `medium` (5 ≤ n < 15) — same, with smaller cohort badge
- `low` (n < 5) — percentages suppressed, panel shows "Yeterli benzer kullanıcı verisi yok"

The scope is surfaced in the UI badge ("Benzer 18 alıcı, aynı kategori, ±5cm boy"), so the panel never overclaims its sample. Return reasons are derived deterministically from review themes via a precedence-ordered keyword map (`backend/scripts/augment_reviews.py`).

---

## Per-category risk heatmap

`turkish_formatter` reads `garment.category` and emits region triplets:

| Category | Regions |
|---|---|
| shirt / tshirt / jacket / unknown | omuz · kol · bel |
| jeans | bel · kalça · bacak |
| dress | omuz · bel · kalça |

The frontend SVG mannequin is full-body and only shades the regions present in the response. When the upload isn't a garment (Gemini `is_garment=false`), the heatmap and similar-users panel and QA chat are all hidden — the user sees only the polite "kıyafet bulunamadı" card.

Without a body image, any `high` status auto-caps to `medium` — we don't claim high-risk on data we don't have.

---

## Tests

```bash
cd backend
pytest                       # 228 tests
pytest -q                    # short summary
pytest tests/test_pipeline.py -v    # verbose, single module
```

Coverage:
- Unit: AI client, pipeline nodes, review intelligence, cohort service, QA intent router, QA fact collectors, QA narrative validator, augment script, fabric rules
- Integration: full HTTP request/response for profile, analyze, history, stylist, cohort, qa
- Honesty rails: low-confidence cohort never publishes a percentage, Gemini polish gets rejected when it invents a number
- Per-category heatmap dispatch + body-image cap
- Garment-invalid gates on `/qa` and `/cohort`
- Tiered metadata filter relaxation in `review_service.query()`

---

## Honesty rails (what we will not do)

- **No invented numbers.** Every percentage and count in a user-facing answer is traceable to either the persisted analysis, the catalog, or the cohort aggregation. The QA narrative validator enforces this even when Gemini is on.
- **No hallucinated personalization.** History intent is intentionally NOT shipped — we don't have a purchase-feedback loop and won't fake one.
- **No subjective beauty judgments.** Prompts forbid them; deterministic templates never reach for them.
- **No high-risk claims without evidence.** Heatmap `high` caps to `medium` without a body photo. Cohort `low` band caps to no-percentages display.
- **Reproducible data.** `data/reviews_enriched.jsonl` is committed to git; re-running `augment_reviews.py` produces the same output.

See `docs/KNOWN_LIMITATIONS.md` for the full honest scope statement.

---

## Documentation

| Document | Purpose |
|----------|---------|
| `DEMO.md` | Hackathon demo guide and troubleshooting |
| `docs/DEMO_SCRIPT.md` | 3–5 minute Turkish presentation script |
| `docs/SRS_COMPLIANCE.md` | UC-01 to UC-08 implementation mapping |
| `docs/KNOWN_LIMITATIONS.md` | Honest MVP scope and boundaries |
| `HIWALOY_FULL_SRS.pdf` | Original system requirements (source of truth) |
