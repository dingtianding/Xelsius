import io

import pytest

from app.ingest.data import parse_csv


def _csv_file(content: str) -> io.BytesIO:
    return io.BytesIO(content.encode("utf-8"))


def test_parse_basic_csv():
    csv = "Date,Description,Amount\n2026-01-01,Coffee,5.50\n2026-01-02,Rent,2100\n"
    txns = parse_csv(_csv_file(csv))
    assert len(txns) == 2
    assert txns[0].date == "2026-01-01"
    assert txns[0].description == "Coffee"
    assert txns[0].amount == 5.50
    assert txns[1].amount == 2100.0


def test_parse_csv_with_aliases():
    csv = "Transaction Date,Memo,Total,Type\n2026-03-01,Uber ride,45.00,Travel\n"
    txns = parse_csv(_csv_file(csv))
    assert txns[0].date == "2026-03-01"
    assert txns[0].description == "Uber ride"
    assert txns[0].amount == 45.0
    assert txns[0].category == "Travel"


def test_parse_csv_strips_dollar_signs():
    csv = "Date,Description,Amount\n2026-01-01,Lunch,$12.50\n"
    txns = parse_csv(_csv_file(csv))
    assert txns[0].amount == 12.50


def test_parse_csv_strips_commas_in_amount():
    csv = "Date,Description,Amount\n2026-01-01,Salary,\"5,200.00\"\n"
    txns = parse_csv(_csv_file(csv))
    assert txns[0].amount == 5200.0


def test_parse_csv_skips_empty_rows():
    csv = "Date,Description,Amount\n2026-01-01,Coffee,5.0\n,,\n2026-01-02,Tea,3.0\n"
    txns = parse_csv(_csv_file(csv))
    assert len(txns) == 2


def test_parse_csv_missing_columns_raises():
    csv = "Name,Value\nFoo,123\n"
    with pytest.raises(ValueError, match="date.*amount"):
        parse_csv(_csv_file(csv))


def test_parse_empty_csv_raises():
    with pytest.raises(ValueError, match="empty"):
        parse_csv(_csv_file(""))
