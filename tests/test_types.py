"""Tests for type definitions."""

import time
from shadowpay.types import SpendingAuthorization, EscrowBalance


def test_spending_authorization_properties():
    """Test SpendingAuthorization property calculations."""
    auth = SpendingAuthorization(
        id=1,
        user_wallet="test_wallet",
        authorized_service="TestService",
        max_amount_per_tx=10000000,  # 0.01 SOL in lamports
        max_daily_spend=1000000000,  # 1 SOL in lamports
        spent_today=100000000,  # 0.1 SOL in lamports
        last_reset_date="2024-01-01",
        valid_until=int(time.time()) + 86400,
        user_signature="test_sig",
        revoked=False,
        created_at=int(time.time()),
    )

    assert auth.max_amount_per_tx_sol == 0.01
    assert auth.max_daily_spend_sol == 1.0
    assert auth.spent_today_sol == 0.1
    assert auth.remaining_today_sol == 0.9
    assert auth.is_valid is True


def test_spending_authorization_expired():
    """Test expired authorization is not valid."""
    auth = SpendingAuthorization(
        id=1,
        user_wallet="test_wallet",
        authorized_service="TestService",
        max_amount_per_tx=10000000,
        max_daily_spend=1000000000,
        spent_today=0,
        last_reset_date="2024-01-01",
        valid_until=int(time.time()) - 86400,  # Expired yesterday
        user_signature="test_sig",
        revoked=False,
        created_at=int(time.time()),
    )

    assert auth.is_valid is False


def test_spending_authorization_revoked():
    """Test revoked authorization is not valid."""
    auth = SpendingAuthorization(
        id=1,
        user_wallet="test_wallet",
        authorized_service="TestService",
        max_amount_per_tx=10000000,
        max_daily_spend=1000000000,
        spent_today=0,
        last_reset_date="2024-01-01",
        valid_until=int(time.time()) + 86400,
        user_signature="test_sig",
        revoked=True,  # Revoked
        created_at=int(time.time()),
    )

    assert auth.is_valid is False


def test_escrow_balance():
    """Test EscrowBalance calculations."""
    balance = EscrowBalance(
        wallet_address="test_wallet",
        balance=1500000000,  # 1.5 SOL in lamports
    )

    assert balance.balance_sol == 1.5
    assert balance.wallet_address == "test_wallet"

