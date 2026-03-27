"""Parse structured files (CSV, Excel) into Transaction objects."""

from __future__ import annotations

import csv
import io
from typing import BinaryIO

from app.models import Transaction

# Column name aliases — normalize whatever the user's file uses
_ALIASES: dict[str, list[str]] = {
    "date": ["date", "transaction date", "trans date", "posted date", "posting date"],
    "description": ["description", "memo", "name", "payee", "merchant", "details", "transaction description"],
    "amount": ["amount", "total", "value", "debit", "sum", "transaction amount"],
    "category": ["category", "type", "tag", "label"],
}


def _normalize_header(header: str) -> str | None:
    """Map a raw column header to a Transaction field name."""
    cleaned = header.strip().lower()
    for field, aliases in _ALIASES.items():
        if cleaned in aliases:
            return field
    return None


def _build_column_map(headers: list[str]) -> dict[int, str]:
    """Map column indices to Transaction field names."""
    col_map: dict[int, str] = {}
    for idx, header in enumerate(headers):
        field = _normalize_header(header)
        if field:
            col_map[idx] = field
    return col_map


def _row_to_transaction(row: dict[str, str]) -> Transaction:
    amount_str = row.get("amount", "0").replace(",", "").replace("$", "").strip()
    try:
        amount = float(amount_str)
    except ValueError:
        amount = 0.0

    return Transaction(
        date=row.get("date", "").strip(),
        description=row.get("description", "").strip(),
        amount=amount,
        category=row.get("category", "").strip(),
    )


def parse_csv(file: BinaryIO, encoding: str = "utf-8") -> list[Transaction]:
    """Parse a CSV file into Transaction objects."""
    text = file.read().decode(encoding)
    reader = csv.reader(io.StringIO(text))

    headers = next(reader, None)
    if not headers:
        raise ValueError("CSV file is empty")

    col_map = _build_column_map(headers)
    if "date" not in col_map.values() or "amount" not in col_map.values():
        raise ValueError(
            f"CSV must have at least 'date' and 'amount' columns. "
            f"Found: {[h.strip() for h in headers]}"
        )

    transactions: list[Transaction] = []
    for row_values in reader:
        if not any(v.strip() for v in row_values):
            continue
        row_dict = {col_map[i]: v for i, v in enumerate(row_values) if i in col_map}
        transactions.append(_row_to_transaction(row_dict))

    return transactions


def parse_excel(file: BinaryIO) -> list[Transaction]:
    """Parse an Excel (.xlsx) file into Transaction objects."""
    import openpyxl

    wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        raise ValueError("Excel file has no active sheet")

    rows = ws.iter_rows(values_only=True)
    header_row = next(rows, None)
    if not header_row:
        raise ValueError("Excel file is empty")

    headers = [str(h) if h is not None else "" for h in header_row]
    col_map = _build_column_map(headers)
    if "date" not in col_map.values() or "amount" not in col_map.values():
        raise ValueError(
            f"Excel must have at least 'date' and 'amount' columns. "
            f"Found: {[h.strip() for h in headers]}"
        )

    transactions: list[Transaction] = []
    for row_values in rows:
        str_values = [str(v) if v is not None else "" for v in row_values]
        if not any(v.strip() for v in str_values):
            continue
        row_dict = {col_map[i]: v for i, v in enumerate(str_values) if i in col_map}
        transactions.append(_row_to_transaction(row_dict))

    wb.close()
    return transactions
