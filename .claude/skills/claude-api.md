---
name: claude-api
description: Hook up Claude LLM integration for Xelsius agent and tools
---

# Claude API Integration Skill

Use this skill when adding or modifying LLM-powered features in the Xelsius backend.

## Stack

- SDK: `anthropic` Python package
- Default model: `claude-haiku-4-5` (fast, cheap for tool routing)
- Override via env: `XELSIUS_MODEL=claude-opus-4-6`
- API key: `ANTHROPIC_API_KEY` env var (never hardcode)

## Architecture

The agent layer (`app/agent/service.py`) uses Claude's tool use API to resolve
natural-language prompts into structured `ToolCall` objects. The flow:

1. User sends a prompt to `POST /agent/run`
2. Agent sends the prompt to Claude with tool definitions matching our `ToolName` enum
3. Claude picks the best tool and returns args via `tool_use` content block
4. Agent parses the response into a `ToolCall(tool=..., args=...)`
5. Downstream pipeline (registry, adapter, diff, audit) is unchanged

## Patterns

### Adding a new tool to the LLM

1. Add the enum value to `ToolName` in `app/models.py`
2. Create the tool function in `app/tools/` with `@register(ToolName.NEW_TOOL)`
3. Add a matching tool definition to `_TOOLS` in `app/agent/service.py`:
   - `name` must match the `ToolName` value exactly
   - `description` should be clear enough for Claude to know when to pick it
   - `input_schema` defines the args Claude will supply
4. Import the tool module in `app/main.py` to trigger registration

### Switching models

Set `XELSIUS_MODEL` in `.env`. Use `claude-haiku-4-5` for development/cost savings,
`claude-sonnet-4-6` or `claude-opus-4-6` for higher accuracy.

### Testing without API calls

Set `XELSIUS_USE_RULES=1` to fall back to keyword matching (not yet implemented —
add if needed for CI).

## Key files

- `app/agent/service.py` — LLM integration (tool definitions, Claude call)
- `app/models.py` — `ToolName` enum, `ToolCall` model
- `app/tools/registry.py` — tool registration
- `.env.example` — required env vars
