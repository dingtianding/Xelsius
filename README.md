# Xelsius

**Cursor for accountants** — an AI-powered audit workpaper system that proposes deterministic diffs on financial data. Never mutates directly.

Users describe what they want in natural language. Xelsius resolves it to a structured tool call, computes the diff, and returns it for review before anything changes.

## Execution Model

- **Agent** = AI router (non-deterministic) — ONLY selects tool + args
- **Tools** = deterministic executors — perform ALL computation, return diffs
- **AI never touches data** — hallucination is impossible because AI is a router, not part of the data pipeline

## Architecture

```
Request → Agent → Tool → Adapter → Diff → Audit Log → Response
```

| Layer | Location | Responsibility |
|-------|----------|---------------|
| **Agent** | `app/agent/` | LLM-powered intent router (Claude Haiku) with RAG context |
| **Tools** | `app/tools/` | Pure functions that compute diffs (no side effects) |
| **Ingest** | `app/ingest/` | File parsing: CSV/Excel (data.py), image/PDF OCR (ocr.py) |
| **Adapters** | `app/adapters/` | Interface to data sources (in-memory workpaper) |
| **Audit** | `app/audit/` | Logs every prompt, tool, args, diff, and timestamp |
| **Rate Limit** | `app/ratelimit.py` | IP-based free tier (10 req/24h), BYOK unlimited |

## Core Principles

1. System **never** directly mutates data
2. Every action returns a **proposed diff** for human review
3. Tools are **deterministic** — same input, same output
4. Adapter-based — not tied to any specific UI or spreadsheet
5. AI hallucination is impossible because AI never touches data

## Workpaper Model

The `Workpaper` is the single source of truth, holding all audit tabs:

| Tab | Model | Description |
|-----|-------|-------------|
| Transactions | `Transaction` | Raw financial data (uploaded or sample) |
| Trial Balance | `Account` | All accounts with debit/credit balances and prior year |
| Materiality | `MaterialityConfig` | Tiered: overall, performance, trivial thresholds |
| Lead Sheet | Generated | Summary by account type with PY comparison |
| Adjusting Entries | `AdjustingEntry` | Proposed audit adjustments (balanced journal entries) |
| Detail Testing | `SampleItem` | Sampled transactions with test results |
| Analytical Review | `AnalyticalResult` | Variance analysis with materiality flags |
| Tickmarks | `Tickmark` | Per-cell audit marks (✓ ◊ △ ✗ ○) with legend |
| Conclusion | Generated | Summary findings |

## Tools

### Implemented

| Tool | Description |
|------|-------------|
| `categorize_transactions` | Categorize transactions by keyword matching |
| `create_summary_sheet` | Aggregate totals grouped by a field |
| `highlight_anomalies` | Flag transactions above a threshold |
| `reset_transactions` | Clear all category assignments |

### MVP (In Progress)

| Tool | Description |
|------|-------------|
| `build_trial_balance` | Aggregate transactions into accounts with debit/credit balances |
| `compute_materiality` | Compute tiered materiality from account balances |
| `build_lead_sheet` | Summary by account type with PY comparison and materiality flags |
| `propose_adjusting_entry` | Create balanced journal entries for audit adjustments |
| `add_tickmark` / `generate_tickmark_legend` | Attach audit marks to cells, auto-generate legend |

### Future

| Tool | Description |
|------|-------------|
| `run_analytical_procedures` | Variance analysis: compare to PY, budget, expectations |
| `select_sample` | Statistical sampling: random, monetary unit, top-N |
| `record_test_result` | Mark sample items as tested with results and tickmarks |
| `generate_conclusion` | Auto-generate audit conclusion from workpaper state |

## API

```
GET  /transactions           → Transaction[]
GET  /workpaper              → full Workpaper object
POST /agent/run              { prompt, api_key? } → { tool, args, diff, remaining? }
POST /tools/run              { tool, args } → { tool, args, diff }  (direct, no AI)
POST /agent/apply            { diff } → { transactions }
POST /ingest/data            multipart file (CSV/Excel) → { transactions, count }
POST /ingest/ocr             multipart file (image/PDF) → { transactions, count }
GET  /audit/log              → AuditEntry[]
```

- `x-api-key` header or `api_key` body field for BYOK (bring your own key)
- Free tier: 10 requests/24h per IP, configurable via `XELSIUS_FREE_LIMIT`
- Direct tool execution (`/tools/run`) bypasses AI and rate limits — for preset buttons

## Quick Start

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env  # add your ANTHROPIC_API_KEY
uvicorn app.main:app --port 8888 --reload

# Frontend
cd web && npm install && npm run dev
```

## Testing

```bash
python -m pytest app/ -v  # 62+ tests, ~1s
```

Tests are colocated with source (`*_test.py`). Claude API calls are mocked in integration tests — no API key needed for CI.

## Tech Stack

- **Backend:** Python / FastAPI / Pydantic / Anthropic SDK
- **Frontend:** Next.js / TypeScript / Tailwind / AG Grid
- **LLM:** Claude Haiku 4.5 (default, configurable via `XELSIUS_MODEL`)
- **CI:** GitHub Actions (`.github/workflows/backend.yml`)
- **No database** — in-memory (persistence planned)

## Project Structure

```
app/
  agent/
    service.py             # Claude API tool routing
    context.py             # RAG context assembly (transactions + history + domain)
  tools/
    registry.py            # Tool registration and execution
    categorize.py          # Keyword-based categorization
    summary.py             # Aggregation by group
    anomalies.py           # Threshold-based flagging
    reset.py               # Clear categories
    trial_balance.py       # (planned) Build trial balance from transactions
    materiality.py         # (planned) Compute tiered materiality
    lead_sheet.py          # (planned) Lead sheet with PY comparison
    adjusting.py           # (planned) Balanced journal entries
    tickmarks.py           # (planned) Audit marks + legend
  ingest/
    data.py                # CSV/Excel parsing
    ocr.py                 # Image/PDF extraction via Claude vision
  adapters/
    base.py                # SpreadsheetAdapter interface
    memory.py              # In-memory adapter with sample data
  audit/logger.py          # Audit trail
  ratelimit.py             # IP-based rate limiting
  models.py                # Pydantic models (Workpaper, Account, Diff types, etc.)
  main.py                  # FastAPI entrypoint
web/                       # Next.js frontend (AG Grid spreadsheet UI)
```

## Roadmap

### Phase 1: Full-Stack Web Demo (Portfolio) ← Current
- [x] Backend: agent, tools, adapters, audit pipeline
- [x] Claude API integration (tool use for routing)
- [x] RAG context (transactions + history + domain knowledge)
- [x] File upload: CSV/Excel parsing, PDF/image OCR
- [x] Free tier rate limiting + BYOK API keys
- [x] Direct tool execution (preset buttons, no AI)
- [x] Workpaper model with all audit data types
- [ ] Trial balance, materiality, lead sheet tools
- [ ] Adjusting entries + tickmarks
- [ ] Agent wiring for audit tools
- [ ] Frontend: upload, workpaper tabs, tickmark UI

### Phase 2: Advanced Audit Tools
- [ ] Analytical procedures (variance analysis)
- [ ] Statistical sampling (random, MUS, top-N)
- [ ] Detail testing with results recording
- [ ] Auto-generated audit conclusion
- [ ] Multi-turn conversation (context-aware follow-ups)

### Phase 3: Production
- [ ] Google Sheets sidebar addon
- [ ] Persistent storage (database)
- [ ] Multi-user / authentication
- [ ] Excel adapter
- [ ] QuickBooks adapter
