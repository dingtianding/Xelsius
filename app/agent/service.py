import os

import anthropic

from app.models import ToolCall, ToolName

_TOOLS = [
    {
        "name": ToolName.CATEGORIZE_TRANSACTIONS.value,
        "description": (
            "Categorize transactions by inferring a category (e.g. Travel, Food, "
            "Shopping, Entertainment, Utilities, Housing, Income) from each "
            "transaction's description. Use when the user wants to label, classify, "
            "or categorize their transactions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": ToolName.CREATE_SUMMARY_SHEET.value,
        "description": (
            "Create a summary sheet that aggregates transaction totals and counts "
            "grouped by a specified field. Use when the user wants a summary, "
            "totals, or an overview of their spending."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "groupBy": {
                    "type": "string",
                    "description": "The transaction field to group by.",
                    "enum": ["category", "date", "description"],
                    "default": "category",
                },
            },
            "required": [],
        },
    },
    {
        "name": ToolName.HIGHLIGHT_ANOMALIES.value,
        "description": (
            "Flag transactions whose absolute amount exceeds a threshold. "
            "Use when the user wants to find outliers, large transactions, "
            "or suspicious activity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "number",
                    "description": "Amount threshold above which a transaction is flagged.",
                    "default": 1000,
                },
            },
            "required": [],
        },
    },
]

_SYSTEM = (
    "You are Xelsius, an AI accounting assistant. The user will describe what "
    "they want done with their financial transactions. Pick the single best tool "
    "and supply the correct arguments. Do not explain — just call the tool."
)

_host_client: anthropic.Anthropic | None = None


def _get_host_client() -> anthropic.Anthropic:
    """Client using the app owner's API key (for free-tier visitors)."""
    global _host_client
    if _host_client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set — cannot serve free-tier requests")
        _host_client = anthropic.Anthropic(api_key=key)
    return _host_client


def _get_client(user_api_key: str | None = None) -> anthropic.Anthropic:
    if user_api_key:
        return anthropic.Anthropic(api_key=user_api_key)
    return _get_host_client()


def resolve_tool(prompt: str, user_api_key: str | None = None) -> ToolCall:
    """Use Claude to map a natural-language prompt to a structured tool call."""
    client = _get_client(user_api_key)

    response = client.messages.create(
        model=os.environ.get("XELSIUS_MODEL", "claude-haiku-4-5"),
        max_tokens=256,
        system=_SYSTEM,
        tools=_TOOLS,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return ToolCall(tool=ToolName(block.name), args=block.input)

    raise ValueError(f"Claude did not return a tool call for prompt: {prompt!r}")
