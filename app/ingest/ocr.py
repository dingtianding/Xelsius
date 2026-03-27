"""Extract transactions from images and PDFs using Claude vision."""

from __future__ import annotations

import base64
import json
import os
from typing import BinaryIO

import anthropic

from app.models import Transaction

_SYSTEM = (
    "You are a financial document parser. Extract every transaction from the "
    "uploaded document and return them as a JSON array. Each object must have: "
    '"date" (string, ISO or as-printed), "description" (string), "amount" (number, '
    "positive for credits/income, negative for debits/expenses), and optionally "
    '"category" (string). Return ONLY the JSON array, no markdown or explanation.'
)

_MEDIA_TYPES: dict[str, str] = {
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/webp": "image/webp",
    "image/gif": "image/gif",
    "application/pdf": "application/pdf",
}

_client: anthropic.Anthropic | None = None


def _get_client(user_api_key: str | None = None) -> anthropic.Anthropic:
    if user_api_key:
        return anthropic.Anthropic(api_key=user_api_key)
    global _client
    if _client is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _client = anthropic.Anthropic(api_key=key)
    return _client


def extract_transactions(
    file: BinaryIO,
    content_type: str,
    user_api_key: str | None = None,
) -> list[Transaction]:
    """Send an image or PDF to Claude vision and parse out transactions."""
    media_type = _MEDIA_TYPES.get(content_type)
    if not media_type:
        raise ValueError(f"Unsupported file type: {content_type}")

    file_bytes = file.read()
    encoded = base64.standard_b64encode(file_bytes).decode("utf-8")

    if content_type == "application/pdf":
        source_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": encoded,
            },
        }
    else:
        source_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": encoded,
            },
        }

    client = _get_client(user_api_key)
    response = client.messages.create(
        model=os.environ.get("XELSIUS_MODEL", "claude-haiku-4-5"),
        max_tokens=4096,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    source_block,
                    {"type": "text", "text": "Extract all transactions from this document."},
                ],
            }
        ],
    )

    raw_text = next(
        (b.text for b in response.content if b.type == "text"),
        "[]",
    )

    # Strip markdown fences if Claude wraps the JSON
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]

    rows = json.loads(text)
    if not isinstance(rows, list):
        raise ValueError("Claude did not return a JSON array")

    transactions: list[Transaction] = []
    for row in rows:
        transactions.append(
            Transaction(
                date=str(row.get("date", "")),
                description=str(row.get("description", "")),
                amount=float(row.get("amount", 0)),
                category=str(row.get("category", "")),
            )
        )

    return transactions
