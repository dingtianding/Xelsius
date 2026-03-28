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


class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class Account(BaseModel):
    number: str
    name: str
    type: AccountType
    balance: float
    prior_year_balance: float | None = None


class MaterialityConfig(BaseModel):
    overall: float
    performance: float
    trivial: float
    basis: str  # e.g. "revenue", "total_assets"
    basis_amount: float


class TickmarkSymbol(str, Enum):
    VERIFIED = "✓"
    AGREED_TO_SOURCE = "◊"
    RECALCULATED = "△"
    EXCEPTION = "✗"
    NO_EXCEPTION = "○"


class Tickmark(BaseModel):
    tab: str
    row: int
    column: str
    symbol: TickmarkSymbol
    note: str = ""


class SampleItem(BaseModel):
    transaction_index: int
    tested: bool = False
    result: str = ""  # "pass", "fail", "exception"
    tickmark: TickmarkSymbol | None = None


class AdjustingEntry(BaseModel):
    entry_number: int
    date: str
    description: str
    account_number: str
    account_name: str
    debit: float = 0.0
    credit: float = 0.0


class AnalyticalResult(BaseModel):
    account_number: str
    account_name: str
    current_balance: float
    prior_balance: float | None = None
    expected: float | None = None
    variance: float = 0.0
    variance_pct: float | None = None
    exceeds_materiality: bool = False
    explanation: str = ""


class TabName(str, Enum):
    TRIAL_BALANCE = "trial_balance"
    LEAD_SHEET = "lead_sheet"
    ADJUSTING_ENTRIES = "adjusting_entries"
    DETAIL_TESTING = "detail_testing"
    ANALYTICAL_REVIEW = "analytical_review"
    TICKMARK_LEGEND = "tickmark_legend"
    CONCLUSION = "conclusion"


class Workpaper(BaseModel):
    transactions: list[Transaction] = Field(default_factory=list)
    accounts: list[Account] = Field(default_factory=list)
    materiality: MaterialityConfig | None = None
    adjusting_entries: list[AdjustingEntry] = Field(default_factory=list)
    sample_items: list[SampleItem] = Field(default_factory=list)
    analytical_results: list[AnalyticalResult] = Field(default_factory=list)
    tickmarks: list[Tickmark] = Field(default_factory=list)
    conclusion: dict[str, Any] = Field(default_factory=dict)


# --- Tool protocol ---


class ToolName(str, Enum):
    # Existing
    CATEGORIZE_TRANSACTIONS = "categorize_transactions"
    CREATE_SUMMARY_SHEET = "create_summary_sheet"
    HIGHLIGHT_ANOMALIES = "highlight_anomalies"
    RESET_TRANSACTIONS = "reset_transactions"
    # Audit
    BUILD_TRIAL_BALANCE = "build_trial_balance"
    BUILD_LEAD_SHEET = "build_lead_sheet"
    COMPUTE_MATERIALITY = "compute_materiality"
    RUN_ANALYTICAL_PROCEDURES = "run_analytical_procedures"
    SELECT_SAMPLE = "select_sample"
    RECORD_TEST_RESULT = "record_test_result"
    PROPOSE_ADJUSTING_ENTRY = "propose_adjusting_entry"
    ADD_TICKMARK = "add_tickmark"
    GENERATE_TICKMARK_LEGEND = "generate_tickmark_legend"
    GENERATE_CONCLUSION = "generate_conclusion"


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


class SetMaterialityDiff(BaseModel):
    type: str = "set_materiality"
    config: MaterialityConfig


class AddTickmarkDiff(BaseModel):
    type: str = "add_tickmark"
    tickmarks: list[Tickmark]


class AddAdjustingEntriesDiff(BaseModel):
    type: str = "add_adjusting_entries"
    entries: list[AdjustingEntry]


class SetSampleResultsDiff(BaseModel):
    type: str = "set_sample_results"
    items: list[SampleItem]


Diff = (
    UpdateCellsDiff
    | CreateSheetDiff
    | SetMaterialityDiff
    | AddTickmarkDiff
    | AddAdjustingEntriesDiff
    | SetSampleResultsDiff
)


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


class SuggestionItem(BaseModel):
    label: str
    prompt: str


class SuggestionsResponse(BaseModel):
    suggestions: list[SuggestionItem]


class RunRequest(BaseModel):
    prompt: str
    api_key: str | None = None


class RunResponse(BaseModel):
    tool: str
    args: dict[str, Any]
    diff: Diff
    remaining: int | None = None


# --- Audit log ---


class AuditEntry(BaseModel):
    prompt: str
    tool: str
    args: dict[str, Any]
    diff: Diff
    timestamp: datetime = Field(default_factory=datetime.utcnow)
