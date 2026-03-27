# Xelsius

**Cursor for accountants** — an agent layer that proposes deterministic diffs on financial data. Never mutates directly.

## Architecture

```
Request → Agent → Tool → Adapter → Diff → Audit Log → Response
```

| Layer | Location | Role |
|-------|----------|------|
| Agent | `app/agent/service.py` | Resolves natural language → structured tool call (rule-based, LLM later) |
| Tools | `app/tools/` | Pure functions that compute diffs (no side effects) |
| Adapters | `app/adapters/` | Interface to data sources (in-memory for now) |
| Audit | `app/audit/logger.py` | Logs every prompt, tool, args, diff, timestamp |
| API | `app/main.py` | FastAPI — `POST /agent/run`, `GET /audit/log` |
| Frontend | `web/` | Next.js (App Router, TypeScript, Tailwind) |

## Backend (FastAPI)

- Runs on port 8888
- Sample data: 10 transactions in `app/adapters/memory.py`
- Three MVP tools: `categorize_transactions`, `create_summary_sheet`, `highlight_anomalies`
- All tools return diffs (`update_cells` or `create_sheet`), never mutate data
- Models in `app/models.py` (Pydantic)

### API shape

```
POST /agent/run  { "prompt": "..." }
→ { "tool": "...", "args": {...}, "diff": {...} }

GET /audit/log
→ [{ "prompt", "tool", "args", "diff", "timestamp" }, ...]
```

## Frontend (Next.js)

- Located in `web/`
- App Router, TypeScript, Tailwind
- Will show: transaction table, prompt input, diff preview, apply button, audit log

## Core Principles

1. System NEVER directly mutates data
2. Always returns a proposed diff
3. Deterministic and auditable
4. Adapter-based (not tied to any UI or spreadsheet)

## Project Plan

- Phase 1: Full-stack web demo (portfolio piece)
- Phase 2: Google Sheets sidebar addon

## Stack

- Backend: Python / FastAPI / Pydantic
- Frontend: Next.js / TypeScript / Tailwind
- No database yet (in-memory)
