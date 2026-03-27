# Xelsius

**Cursor for accountants** — an agent layer that sits on top of financial data tools, proposes deterministic diffs, and never mutates data directly.

Users describe what they want in natural language. Xelsius resolves it to a structured tool call, computes the diff, and returns it for review before anything changes.

## Architecture

```
Request → Agent → Tool → Adapter → Diff → Audit Log → Response
```

| Layer | Responsibility |
|-------|---------------|
| **Agent** | Resolves natural language → structured tool call |
| **Tools** | Pure functions that compute diffs (no side effects) |
| **Adapters** | Interface to data sources (in-memory, Google Sheets, Excel, QuickBooks) |
| **Audit** | Logs every prompt, tool, args, diff, and timestamp |

## Core Principles

- The system **never** directly mutates data
- Every action returns a **proposed diff** for review
- All operations are **deterministic** and **auditable**
- Adapter-based design — not tied to any specific spreadsheet or UI

## Tools (MVP)

| Tool | Description |
|------|-------------|
| `categorize_transactions` | Categorize transactions by keyword matching |
| `create_summary_sheet` | Aggregate totals grouped by a field |
| `highlight_anomalies` | Flag transactions above a threshold |

## Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API

### `POST /agent/run`

```json
{
  "prompt": "categorize all transactions"
}
```

Response:

```json
{
  "tool": "categorize_transactions",
  "args": {},
  "diff": {
    "type": "update_cells",
    "changes": [
      { "row": 0, "column": "category", "before": "", "after": "Travel" },
      { "row": 1, "column": "category", "before": "", "after": "Food" }
    ]
  }
}
```

### `GET /audit/log`

Returns the full audit trail of all proposed actions.

## Project Structure

```
app/
  agent/service.py       # Rule-based prompt → tool call resolver
  tools/
    registry.py          # Tool whitelist and execution
    categorize.py        # Keyword-based categorization
    summary.py           # Aggregation by group
    anomalies.py         # Threshold-based flagging
  adapters/
    base.py              # SpreadsheetAdapter interface
    memory.py            # In-memory adapter with sample data
  audit/logger.py        # Audit trail
  models.py              # Pydantic models
  main.py                # FastAPI entrypoint
```

## Tech Stack

- **Python** / **FastAPI**
- **Pydantic** for validation
- Rule-based agent (LLM integration planned)

## Roadmap

- [ ] LLM-powered agent (Claude)
- [ ] Google Sheets adapter
- [ ] Excel adapter
- [ ] QuickBooks adapter
- [ ] Diff review + apply flow
