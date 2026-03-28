import os

from app.agent.providers import get_provider, resolve_via_anthropic, resolve_via_gemini, resolve_via_groq
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
    {
        "name": ToolName.RESET_TRANSACTIONS.value,
        "description": (
            "Clear all category assignments, resetting every transaction's category "
            "to blank. Use when the user wants to start over, wipe categories, "
            "reset, or clear everything."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # --- Audit tools ---
    {
        "name": ToolName.BUILD_TRIAL_BALANCE.value,
        "description": (
            "Build a trial balance from the workpaper's accounts. Shows all accounts "
            "with debit/credit classification, prior year balances, and balanced totals. "
            "Use when the user wants to see the trial balance or TB."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": ToolName.COMPUTE_MATERIALITY.value,
        "description": (
            "Compute tiered audit materiality (overall, performance, trivial) from "
            "account balances. Use when the user wants to set or calculate materiality."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "basis": {
                    "type": "string",
                    "description": "The financial metric to base materiality on.",
                    "enum": ["revenue", "total_assets", "net_income"],
                    "default": "revenue",
                },
                "percentage": {
                    "type": "number",
                    "description": "Override percentage for overall materiality (e.g. 0.05 for 5%).",
                },
            },
            "required": [],
        },
    },
    {
        "name": ToolName.BUILD_LEAD_SHEET.value,
        "description": (
            "Build a lead sheet — summary by account type with current balance, "
            "prior year comparison, variance, and materiality flags. "
            "Use when the user wants to see the lead sheet or account summary."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": ToolName.PROPOSE_ADJUSTING_ENTRY.value,
        "description": (
            "Propose a balanced adjusting journal entry (debit = credit). "
            "Use when the user wants to record an audit adjustment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Description of the adjustment.",
                },
                "debit_account": {
                    "type": "string",
                    "description": "Account number to debit.",
                },
                "credit_account": {
                    "type": "string",
                    "description": "Account number to credit.",
                },
                "amount": {
                    "type": "number",
                    "description": "Amount of the adjustment.",
                },
                "date": {
                    "type": "string",
                    "description": "Date of the adjustment (ISO format).",
                },
            },
            "required": ["description", "debit_account", "credit_account", "amount"],
        },
    },
    {
        "name": ToolName.ADD_TICKMARK.value,
        "description": (
            "Attach an audit tickmark symbol to a specific cell in the workpaper. "
            "Symbols: ✓ (verified), ◊ (agreed to source), △ (recalculated), "
            "✗ (exception), ○ (no exception). Use when the user wants to mark "
            "an item as tested."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tab": {
                    "type": "string",
                    "description": "The workpaper tab name.",
                    "enum": ["trial_balance", "lead_sheet", "adjusting_entries", "detail_testing"],
                },
                "row": {
                    "type": "integer",
                    "description": "Row index.",
                },
                "column": {
                    "type": "string",
                    "description": "Column name.",
                },
                "symbol": {
                    "type": "string",
                    "description": "Tickmark symbol.",
                    "enum": ["✓", "◊", "△", "✗", "○"],
                },
                "note": {
                    "type": "string",
                    "description": "Optional note explaining the tickmark.",
                },
            },
            "required": ["tab", "row", "column", "symbol"],
        },
    },
    {
        "name": ToolName.GENERATE_TICKMARK_LEGEND.value,
        "description": (
            "Generate a tickmark legend showing all symbols, their descriptions, "
            "and how many times each has been used. Use when the user wants to "
            "see the tickmark legend or summary of audit marks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

_SYSTEM_BASE = (
    "You are Xelsius, an AI accounting assistant. The user will describe what "
    "they want done with their financial transactions. Pick the single best tool "
    "and supply the correct arguments. Use the data context below to choose "
    "smarter arguments (e.g., thresholds based on actual amounts). "
    "Do not explain — just call the tool."
)

def resolve_tool(
    prompt: str,
    user_api_key: str | None = None,
    context: str = "",
    provider: str | None = None,
) -> ToolCall:
    """Route a natural-language prompt to a structured tool call via LLM."""
    system = f"{_SYSTEM_BASE}\n\n{context}" if context else _SYSTEM_BASE

    # BYOK Anthropic key always uses Claude
    if user_api_key:
        return resolve_via_anthropic(prompt, system, _TOOLS, api_key=user_api_key)

    # User-selected provider overrides server default
    chosen = provider or get_provider()
    if chosen == "gemini":
        return resolve_via_gemini(prompt, system, _TOOLS)
    elif chosen == "groq":
        return resolve_via_groq(prompt, system, _TOOLS)
    else:
        return resolve_via_anthropic(prompt, system, _TOOLS)
