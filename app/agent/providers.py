"""LLM provider abstraction — swap between Gemini (free) and Claude."""

from __future__ import annotations

import os
from typing import Any

from app.models import ToolCall, ToolName


def get_provider() -> str:
    return os.environ.get("XELSIUS_LLM_PROVIDER", "gemini")


def resolve_via_anthropic(
    prompt: str,
    system: str,
    tools: list[dict[str, Any]],
    api_key: str | None = None,
) -> ToolCall:
    import anthropic

    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
    else:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        client = anthropic.Anthropic(api_key=key)

    response = client.messages.create(
        model=os.environ.get("XELSIUS_MODEL", "claude-haiku-4-5"),
        max_tokens=256,
        system=system,
        tools=tools,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return ToolCall(tool=ToolName(block.name), args=block.input)

    raise ValueError(f"Claude did not return a tool call for prompt: {prompt!r}")


def resolve_via_gemini(
    prompt: str,
    system: str,
    tools: list[dict[str, Any]],
    api_key: str | None = None,
) -> ToolCall:
    from google import genai
    from google.genai import types

    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=key)

    # Convert Anthropic tool format → Gemini FunctionDeclaration
    function_declarations = []
    for tool in tools:
        schema = tool.get("input_schema", {})
        function_declarations.append(
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool.get("description", ""),
                parameters_json_schema=schema,
            )
        )

    gemini_tool = types.Tool(function_declarations=function_declarations)

    model = os.environ.get("XELSIUS_GEMINI_MODEL", "gemini-2.0-flash")

    response = client.models.generate_content(
        model=model,
        contents=f"{system}\n\nUser request: {prompt}",
        config=types.GenerateContentConfig(
            tools=[gemini_tool],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )

    if response.function_calls:
        fc = response.function_calls[0]
        return ToolCall(tool=ToolName(fc.name), args=dict(fc.args) if fc.args else {})

    raise ValueError(f"Gemini did not return a tool call for prompt: {prompt!r}")
