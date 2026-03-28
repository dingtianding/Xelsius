"""Generate 10-K style financial statement PDFs from workpaper data."""

from __future__ import annotations

import io
from collections import defaultdict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import Account, AccountType

# --- Contra account detection ---

_CONTRA_REVENUE_KEYWORDS = {"return", "allowance", "discount"}
_CONTRA_EQUITY_KEYWORDS = {"dividend"}


def _is_contra_revenue(a: Account) -> bool:
    lower = a.name.lower()
    return a.type == AccountType.REVENUE and any(kw in lower for kw in _CONTRA_REVENUE_KEYWORDS)


def _is_contra_equity(a: Account) -> bool:
    lower = a.name.lower()
    return a.type == AccountType.EQUITY and any(kw in lower for kw in _CONTRA_EQUITY_KEYWORDS)


# --- Formatting ---


def _fmt(amount: float) -> str:
    """Format amount with parentheses for negatives, like 10-K filings."""
    if amount < 0:
        return f"({abs(amount):,.0f})"
    return f"{amount:,.0f}"


def _fmt_dollar(amount: float) -> str:
    if amount < 0:
        return f"$({abs(amount):,.0f})"
    return f"${amount:,.0f}"


# --- Table styles ---

COL_WIDTHS = [3.2 * inch, 1.3 * inch, 1.3 * inch]

_HEADER_STYLE = TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ("ALIGN", (0, 0), (0, -1), "LEFT"),
    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
    ("TOPPADDING", (0, 0), (-1, -1), 2),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
])

_TOTAL_LINE = TableStyle([
    ("LINEABOVE", (1, -1), (-1, -1), 0.5, colors.black),
    ("LINEBELOW", (1, -1), (-1, -1), 1.5, colors.black),
    ("FONTNAME", (0, -1), (-1, -1), "Times-Bold"),
])

_GRAND_TOTAL_STYLE = TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), "Times-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 10),
    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ("LINEABOVE", (1, 0), (-1, 0), 1.5, colors.black),
    ("LINEBELOW", (1, 0), (-1, 0), 3, colors.black),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
])


# --- Section builders ---


def _line_items_table(
    accounts: list[Account],
    total_label: str,
    contra_check=None,
) -> tuple[list, float, float]:
    """Build table rows. Returns (elements, total_cy, total_py)."""
    data = [["", "Current Year", "Prior Year"]]
    total_cy = 0.0
    total_py = 0.0

    for a in accounts:
        name = a.name
        cy = a.balance
        py = a.prior_year_balance or 0

        # Contra-asset (negative balance in asset type)
        if a.balance < 0 and a.type == AccountType.ASSET:
            name = f"    Less: {a.name}"

        # Contra-revenue or contra-equity: show as deduction
        if contra_check and contra_check(a):
            name = f"    Less: {a.name}"
            cy = -cy
            py = -py

        total_cy += cy
        total_py += py
        data.append([name, _fmt(cy), _fmt(py)])

    data.append([f"Total {total_label}", _fmt_dollar(total_cy), _fmt_dollar(total_py)])

    t = Table(data, colWidths=COL_WIDTHS)
    t.setStyle(_HEADER_STYLE)
    t.setStyle(_TOTAL_LINE)
    return [t], total_cy, total_py


def _grand_total_row(label: str, cy: float, py: float) -> Table:
    t = Table([[label, _fmt_dollar(cy), _fmt_dollar(py)]], colWidths=COL_WIDTHS)
    t.setStyle(_GRAND_TOTAL_STYLE)
    return t


# --- Main generator ---


def generate_financial_statements(
    accounts: list[Account],
    company_name: str = "Sample Manufacturing Co.",
    period: str = "For the Year Ended December 31, 2025",
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FSTitle", parent=styles["Title"],
        fontName="Times-Bold", fontSize=14, spaceAfter=2, alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "FSSubtitle", parent=styles["Normal"],
        fontName="Times-Roman", fontSize=10, spaceAfter=4, alignment=1,
    )
    section_style = ParagraphStyle(
        "FSSection", parent=styles["Normal"],
        fontName="Times-Bold", fontSize=11, spaceBefore=12, spaceAfter=4,
    )
    subsection_style = ParagraphStyle(
        "FSSub", parent=styles["Normal"],
        fontName="Times-Bold", fontSize=10, spaceBefore=6, spaceAfter=2,
    )
    note_style = ParagraphStyle(
        "FSNote", parent=styles["Normal"],
        fontName="Times-Italic", fontSize=8, textColor=colors.gray, spaceBefore=6,
    )

    # Group accounts
    by_type: dict[AccountType, list[Account]] = defaultdict(list)
    for a in accounts:
        by_type[a.type].append(a)

    elements: list = []

    # ==================== BALANCE SHEET ====================
    elements.append(Paragraph(company_name.upper(), title_style))
    elements.append(Paragraph("BALANCE SHEET", title_style))
    elements.append(Paragraph("As of December 31, 2025", subtitle_style))
    elements.append(Paragraph("(In whole dollars)", subtitle_style))
    elements.append(Spacer(1, 12))

    # Assets
    elements.append(Paragraph("ASSETS", section_style))

    current_assets = [a for a in by_type[AccountType.ASSET] if int(a.number) < 1500]
    noncurrent_assets = [a for a in by_type[AccountType.ASSET] if int(a.number) >= 1500]

    ca_total_cy = ca_total_py = 0.0
    if current_assets:
        elements.append(Paragraph("Current Assets", subsection_style))
        rows, ca_total_cy, ca_total_py = _line_items_table(current_assets, "Current Assets")
        elements.extend(rows)

    nca_total_cy = nca_total_py = 0.0
    if noncurrent_assets:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Non-Current Assets", subsection_style))
        rows, nca_total_cy, nca_total_py = _line_items_table(noncurrent_assets, "Non-Current Assets")
        elements.extend(rows)

    total_assets_cy = ca_total_cy + nca_total_cy
    total_assets_py = ca_total_py + nca_total_py
    elements.append(Spacer(1, 4))
    elements.append(_grand_total_row("TOTAL ASSETS", total_assets_cy, total_assets_py))

    # Liabilities & Equity
    elements.append(Spacer(1, 16))
    elements.append(Paragraph("LIABILITIES AND STOCKHOLDERS' EQUITY", section_style))

    current_liab = [a for a in by_type[AccountType.LIABILITY] if int(a.number) < 2700]
    noncurrent_liab = [a for a in by_type[AccountType.LIABILITY] if int(a.number) >= 2700]

    cl_cy = cl_py = 0.0
    if current_liab:
        elements.append(Paragraph("Current Liabilities", subsection_style))
        rows, cl_cy, cl_py = _line_items_table(current_liab, "Current Liabilities")
        elements.extend(rows)

    ncl_cy = ncl_py = 0.0
    if noncurrent_liab:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Non-Current Liabilities", subsection_style))
        rows, ncl_cy, ncl_py = _line_items_table(noncurrent_liab, "Non-Current Liabilities")
        elements.extend(rows)

    # Equity — dividends are contra
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Stockholders' Equity", subsection_style))
    eq_rows, eq_cy, eq_py = _line_items_table(
        by_type[AccountType.EQUITY], "Stockholders' Equity",
        contra_check=_is_contra_equity,
    )
    elements.extend(eq_rows)

    total_le_cy = cl_cy + ncl_cy + eq_cy
    total_le_py = cl_py + ncl_py + eq_py
    elements.append(Spacer(1, 4))
    elements.append(_grand_total_row("TOTAL LIABILITIES AND EQUITY", total_le_cy, total_le_py))

    elements.append(Paragraph("See accompanying notes to financial statements.", note_style))

    # ==================== PAGE BREAK ====================
    elements.append(PageBreak())

    # ==================== INCOME STATEMENT ====================
    elements.append(Paragraph(company_name.upper(), title_style))
    elements.append(Paragraph("STATEMENT OF OPERATIONS", title_style))
    elements.append(Paragraph(period, subtitle_style))
    elements.append(Paragraph("(In whole dollars)", subtitle_style))
    elements.append(Spacer(1, 12))

    # Revenue — sales returns are contra
    elements.append(Paragraph("Revenue", section_style))
    rev_rows, rev_cy, rev_py = _line_items_table(
        by_type[AccountType.REVENUE], "Net Revenue",
        contra_check=_is_contra_revenue,
    )
    elements.extend(rev_rows)

    # Expenses
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Expenses", section_style))
    exp_rows, exp_cy, exp_py = _line_items_table(by_type[AccountType.EXPENSE], "Expenses")
    elements.extend(exp_rows)

    # Net Income
    net_income_cy = rev_cy - exp_cy
    net_income_py = rev_py - exp_py
    elements.append(Spacer(1, 8))
    elements.append(_grand_total_row("NET INCOME", net_income_cy, net_income_py))

    elements.append(Paragraph("See accompanying notes to financial statements.", note_style))

    doc.build(elements)
    return buf.getvalue()
