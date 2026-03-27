# Xelsius

**Cursor for accountants** — an agent layer that proposes deterministic diffs on financial data. Never mutates directly.

## Architecture

```
Request → Agent → Tool → Adapter → Diff → Audit Log → Response
```

| Layer | Location | Role |
|-------|----------|------|
| Agent | `app/agent/service.py` | LLM-powered intent router — ONLY outputs `{ tool, args }` |
| Tools | `app/tools/` | Pure functions that compute diffs (no side effects) |
| Ingest | `app/ingest/` | File parsing: `data.py` (CSV/Excel), `ocr.py` (image/PDF via vision) |
| Adapters | `app/adapters/` | Interface to data sources (in-memory for now) |
| Rate Limit | `app/ratelimit.py` | IP-based free tier (10 req/24h), BYOK unlimited |
| Audit | `app/audit/logger.py` | Logs every prompt, tool, args, diff, timestamp |
| API | `app/main.py` | FastAPI endpoints (see below) |
| Frontend | `web/` | Next.js (App Router, TypeScript, Tailwind, AG Grid) |

## Backend (FastAPI)

- Runs on port 8888
- Sample data: 10 transactions in `app/adapters/memory.py`
- Three MVP tools: `categorize_transactions`, `create_summary_sheet`, `highlight_anomalies`
- All tools return diffs (`update_cells` or `create_sheet`), never mutate data
- Models in `app/models.py` (Pydantic)

### API endpoints

```
GET  /transactions           → Transaction[]
POST /agent/run              { "prompt", "api_key?" } → { tool, args, diff, remaining? }
POST /agent/apply            { "diff" } → { transactions }
POST /ingest/data            multipart file (CSV/Excel) → { transactions, count }
POST /ingest/ocr             multipart file (image/PDF) → { transactions, count }
GET  /audit/log              → AuditEntry[]
```

- `x-api-key` header or `api_key` body field for BYOK
- Free tier: 10 requests/24h per IP (configurable via `XELSIUS_FREE_LIMIT`)

## Frontend (Next.js)

- Located in `web/`
- App Router, TypeScript, Tailwind
- Will show: transaction table, prompt input, diff preview, apply button, audit log

## Execution Model

- Agent ONLY selects tool + args (non-deterministic, uses LLM)
- Tools perform ALL computation deterministically (pure functions, no LLM)
- Agent NEVER generates diffs, modifies data, or computes aggregates
- AI is a router, NOT part of the data pipeline

## Core Principles

1. System NEVER directly mutates data
2. Always returns a proposed diff for human review
3. Tools are deterministic and auditable — same input, same output
4. Adapter-based (not tied to any UI or spreadsheet)
5. AI hallucination is impossible because AI never touches data

## Project Plan

- Phase 1: Full-stack web demo (portfolio piece)
- Phase 2: Google Sheets sidebar addon

## Stack

- Backend: Python / FastAPI / Pydantic
- Frontend: Next.js / TypeScript / Tailwind
- No database yet (in-memory)
