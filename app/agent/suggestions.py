"""Generate AI-powered suggestions based on workpaper state."""

from __future__ import annotations

import json
import os

import anthropic

from app.models import Transaction


def _build_summary(transactions: list[Transaction]) -> str:
    """Build a compact data summary for the LLM."""
    total = len(transactions)
    if total == 0:
        return "No transactions loaded."

    empty_cat = sum(1 for t in transactions if not t.category)
    categories = set(t.category for t in transactions if t.category)
    amounts = [abs(t.amount) for t in transactions]
    avg = sum(amounts) / len(amounts)
    max_amt = max(amounts)
    min_amt = min(amounts)
    total_amt = sum(amounts)

    return (
        f"Transactions: {total}\n"
        f"Uncategorized: {empty_cat}/{total}\n"
        f"Categories in use: {', '.join(sorted(categories)) or 'none'}\n"
        f"Amount range: ${min_amt:,.2f} – ${max_amt:,.2f}\n"
        f"Average: ${avg:,.2f}, Total: ${total_amt:,.2f}"
    )


_SYSTEM = (
    "You are Xelsius, an AI accounting assistant. Given a summary of the user's "
    "financial data, suggest 1-3 high-value actions they should take next.\n\n"
    "Rules:\n"
    "- Only suggest actions you are HIGHLY confident are useful\n"
    "- Each suggestion needs a short label (what the user sees) and a prompt "
    "(what gets sent to the agent)\n"
    "- If the data is already clean and categorized, suggest analytical actions\n"
    "- If data is uncategorized, suggest categorization first\n"
    "- Be specific — use actual numbers from the data\n\n"
    "Return ONLY a JSON array, no markdown, no explanation:\n"
    '[{"label": "...", "prompt": "..."}]'
)


def generate_suggestions(
    transactions: list[Transaction],
    user_api_key: str | None = None,
) -> list[dict[str, str]]:
    """Ask Claude to suggest next actions based on current data."""
    key = user_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return []

    summary = _build_summary(transactions)
    client = anthropic.Anthropic(api_key=key)

    try:
        response = client.messages.create(
            model=os.environ.get("XELSIUS_MODEL", "claude-haiku-4-5"),
            max_tokens=256,
            system=_SYSTEM,
            messages=[{"role": "user", "content": summary}],
        )

        text = response.content[0].text.strip()
        suggestions = json.loads(text)

        if not isinstance(suggestions, list):
            return []

        return [
            {"label": s["label"], "prompt": s["prompt"]}
            for s in suggestions
            if isinstance(s, dict) and "label" in s and "prompt" in s
        ][:3]
    except Exception:
        return []
