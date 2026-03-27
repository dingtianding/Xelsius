from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Domain ---


class Transaction(BaseModel):
    date: str
    description: str
    amount: float
    category: str = ""


# --- Tool protocol ---


class ToolName(str, Enum):
    CATEGORIZE_TRANSACTIONS = "categorize_transactions"
    CREATE_SUMMARY_SHEET = "create_summary_sheet"
    HIGHLIGHT_ANOMALIES = "highlight_anomalies"
    RESET_TRANSACTIONS = "reset_transactions"


class ToolCall(BaseModel):
    tool: ToolName
    args: dict[str, Any] = Field(default_factory=dict)


# --- Diff types ---


class CellChange(BaseModel):
    row: int
    column: str
    before: str | float
    after: str | float


class UpdateCellsDiff(BaseModel):
    type: str = "update_cells"
    changes: list[CellChange]


class CreateSheetDiff(BaseModel):
    type: str = "create_sheet"
    name: str
    data: list[dict[str, Any]]


Diff = UpdateCellsDiff | CreateSheetDiff


# --- API ---


class UploadResponse(BaseModel):
    transactions: list[Transaction]
    count: int


class ApplyRequest(BaseModel):
    diff: Diff


class ApplyResponse(BaseModel):
    transactions: list[Transaction]


class DirectToolRequest(BaseModel):
    tool: ToolName
    args: dict[str, Any] = Field(default_factory=dict)


class RunRequest(BaseModel):
    prompt: str
    api_key: str | None = None


class RunResponse(BaseModel):
    tool: str
    args: dict[str, Any]
    diff: Diff
    remaining: int | None = None


# --- Audit ---


class AuditEntry(BaseModel):
    prompt: str
    tool: str
    args: dict[str, Any]
    diff: Diff
    timestamp: datetime = Field(default_factory=datetime.utcnow)
