import pytest

from app.models import Account, AccountType, Workpaper
from app.tools.materiality import compute_materiality


def _wp() -> Workpaper:
    return Workpaper(accounts=[
        Account(number="1000", name="Cash", type=AccountType.ASSET, balance=500000),
        Account(number="4000", name="Sales Revenue", type=AccountType.REVENUE, balance=1000000),
        Account(number="4100", name="Service Revenue", type=AccountType.REVENUE, balance=200000),
        Account(number="5000", name="COGS", type=AccountType.EXPENSE, balance=700000),
        Account(number="5100", name="Wages", type=AccountType.EXPENSE, balance=200000),
    ])


def test_materiality_revenue_basis():
    diff = compute_materiality(_wp(), {"basis": "revenue"})
    config = diff.config
    assert config.basis == "revenue"
    assert config.basis_amount == 1200000  # 1M + 200K
    assert config.overall == 60000  # 5% of 1.2M
    assert config.performance == 39000  # 65% of 60K
    assert config.trivial == 3000  # 5% of 60K


def test_materiality_total_assets_basis():
    diff = compute_materiality(_wp(), {"basis": "total_assets"})
    assert diff.config.basis_amount == 500000
    assert diff.config.overall == 5000  # 1% of 500K


def test_materiality_net_income_basis():
    diff = compute_materiality(_wp(), {"basis": "net_income"})
    # revenue 1.2M - expenses 900K = 300K
    assert diff.config.basis_amount == 300000
    assert diff.config.overall == 15000  # 5% of 300K


def test_materiality_custom_percentages():
    diff = compute_materiality(_wp(), {
        "basis": "revenue",
        "percentage": 0.03,
        "performance_ratio": 0.75,
        "trivial_ratio": 0.10,
    })
    assert diff.config.overall == 36000  # 3% of 1.2M
    assert diff.config.performance == 27000  # 75% of 36K
    assert diff.config.trivial == 3600  # 10% of 36K


def test_materiality_no_accounts_raises():
    with pytest.raises(ValueError, match="No accounts"):
        compute_materiality(Workpaper(), {})


def test_materiality_unknown_basis_raises():
    with pytest.raises(ValueError, match="Unknown"):
        compute_materiality(_wp(), {"basis": "nonsense"})
