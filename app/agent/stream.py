"""Streaming agent execution — sends thinking steps over a callback."""

from __future__ import annotations

import os
from typing import Any, Callable

import anthropic

from app.agent.context import build_context
from app.models import AuditEntry, Diff, ToolCall, ToolName, Workpaper

# Reuse tool definitions and system prompt from service module
from app.agent.service import _TOOLS, _SYSTEM_BASE, _get_client
from app.tools.registry import execute

StepCallback = Callable[[str, dict[str, Any]], None]


def run_agent_streaming(
    prompt: str,
    workpaper: Workpaper,
    audit_log: list[AuditEntry],
    on_step: StepCallback,
    user_api_key: str | None = None,
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

    # Step 2: Call Claude
    model = os.environ.get("XELSIUS_MODEL", "claude-haiku-4-5")
    on_step("calling_claude", {"message": f"Asking Claude ({model}) to pick the best tool...", "model": model})

    client = _get_client(user_api_key)
    system = f"{_SYSTEM_BASE}\n\n{context}" if context else _SYSTEM_BASE

    response = client.messages.create(
        model=model,
        max_tokens=256,
        system=system,
        tools=_TOOLS,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )

    # Step 3: Parse tool selection
    tool_call: ToolCall | None = None
    for block in response.content:
        if block.type == "tool_use":
            tool_call = ToolCall(tool=ToolName(block.name), args=block.input)
            break

    if tool_call is None:
        raise ValueError(f"Claude did not return a tool call for prompt: {prompt!r}")

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
