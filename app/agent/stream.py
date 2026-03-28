"""Streaming agent execution — sends thinking steps over a callback."""

from __future__ import annotations

import os
from typing import Any, Callable

from app.agent.context import build_context
from app.agent.providers import get_provider
from app.models import AuditEntry, Diff, ToolCall, ToolName, Workpaper

from app.agent.service import _TOOLS, _SYSTEM_BASE, resolve_tool
from app.tools.registry import execute

StepCallback = Callable[[str, dict[str, Any]], None]


def run_agent_streaming(
    prompt: str,
    workpaper: Workpaper,
    audit_log: list[AuditEntry],
    on_step: StepCallback,
    user_api_key: str | None = None,
    provider: str | None = None,
) -> tuple[ToolCall, Diff]:
    """Run the agent pipeline, calling on_step at each stage.

    on_step(event_type, data) is called with:
      ("thinking", {"message": "..."})
      ("context_built", {"token_estimate": N})
      ("calling_claude", {"model": "..."})
      ("tool_selected", {"tool": "...", "args": {...}})
      ("executing_tool", {"tool": "..."})
      ("diff_computed", {"diff_type": "...", "summary": "..."})
      ("done", {"tool": "...", "args": {...}})
    """
    # Step 1: Build context
    on_step("thinking", {"message": "Analyzing your workpaper state..."})
    context = build_context(workpaper, audit_log)
    on_step("context_built", {"token_estimate": len(context.split())})

    # Step 2: Call LLM
    chosen = provider or (get_provider() if not user_api_key else "anthropic")
    on_step("calling_llm", {"message": f"Asking {chosen} to pick the best tool...", "provider": chosen})

    tool_call = resolve_tool(prompt, user_api_key=user_api_key, context=context, provider=provider)

    on_step("tool_selected", {
        "message": f"Selected: {tool_call.tool.value}",
        "tool": tool_call.tool.value,
        "args": tool_call.args,
    })

    # Step 4: Execute tool
    on_step("executing_tool", {
        "message": f"Running {tool_call.tool.value}...",
        "tool": tool_call.tool.value,
    })

    diff = execute(tool_call.tool, workpaper, tool_call.args)

    # Step 5: Summarize result
    if diff.type == "update_cells":
        summary = f"{len(diff.changes)} cell changes"
    elif diff.type == "create_sheet":
        summary = f"Created sheet '{diff.name}' with {len(diff.data)} rows"
    elif diff.type == "set_materiality":
        summary = f"Materiality: overall=${diff.config.overall:,.2f}"
    elif diff.type == "add_tickmark":
        summary = f"{len(diff.tickmarks)} tickmark(s) added"
    elif diff.type == "add_adjusting_entries":
        summary = f"{len(diff.entries)} journal entry line(s)"
    else:
        summary = "Completed"

    on_step("diff_computed", {"message": summary, "diff_type": diff.type, "summary": summary})
    on_step("done", {"tool": tool_call.tool.value, "args": tool_call.args})

    return tool_call, diff
