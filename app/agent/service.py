from app.models import ToolCall, ToolName

# Rule-based routing — will be replaced by LLM later.
_RULES: list[tuple[list[str], ToolName, dict]] = [
    (
        ["categorize", "classify", "label"],
        ToolName.CATEGORIZE_TRANSACTIONS,
        {},
    ),
    (
        ["summary", "summarize", "aggregate", "total"],
        ToolName.CREATE_SUMMARY_SHEET,
        {"groupBy": "category"},
    ),
    (
        ["highlight", "anomaly", "anomalies", "flag", "outlier"],
        ToolName.HIGHLIGHT_ANOMALIES,
        {"threshold": 1000},
    ),
]


def resolve_tool(prompt: str) -> ToolCall:
    """Map a natural-language prompt to a structured tool call."""
    lower = prompt.lower()
    for keywords, tool, default_args in _RULES:
        if any(kw in lower for kw in keywords):
            return ToolCall(tool=tool, args=default_args)
    raise ValueError(f"No matching tool for prompt: {prompt!r}")
