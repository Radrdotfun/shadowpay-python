"""Tests for AutomatedPaymentBot."""

import pytest
from shadowpay.testing import MockAutomatedPaymentBot, MockShadowPayClient
from shadowpay.exceptions import (
    DailyLimitExceededError,
    PerTransactionLimitExceededError,
)


def test_bot_initialization():
    """Test bot can be initialized with mock client."""
    client = MockShadowPayClient()
    bot = MockAutomatedPaymentBot(
        user_wallet="test_wallet",
        service_key="TestBot",
        mock_client=client,
    )
    assert bot.user_wallet == "test_wallet"
    assert bot.service_key == "TestBot"


def test_bot_make_payment():
    """Test bot can make payment."""
    client = MockShadowPayClient()
    client.authorize_service("test_wallet", "TestBot", max_daily=1.0)

    bot = MockAutomatedPaymentBot(
        user_wallet="test_wallet",
        service_key="TestBot",
        mock_client=client,
    )

    tx_hash = bot.make_payment(0.001, "/api/test")
    assert tx_hash.startswith("mock_tx_")


def test_bot_daily_limit():
    """Test bot enforces daily limit."""
    client = MockShadowPayClient()
    client.authorize_service("test_wallet", "TestBot", max_daily=0.01)

    bot = MockAutomatedPaymentBot(
        user_wallet="test_wallet",
        service_key="TestBot",
        mock_client=client,
    )

    # First payment should succeed
    bot.make_payment(0.005, "/api/test")

    # Second payment should exceed limit
    with pytest.raises(DailyLimitExceededError):
        bot.make_payment(0.01, "/api/test")


def test_bot_per_tx_limit():
    """Test bot enforces per-transaction limit."""
    client = MockShadowPayClient()
    client.authorize_service("test_wallet", "TestBot", max_per_tx=0.01, max_daily=1.0)

    bot = MockAutomatedPaymentBot(
        user_wallet="test_wallet",
        service_key="TestBot",
        mock_client=client,
    )

    # Payment exceeding per-tx limit should fail
    with pytest.raises(PerTransactionLimitExceededError):
        bot.make_payment(0.02, "/api/test")


def test_bot_spending_tracking():
    """Test bot tracks spending correctly."""
    client = MockShadowPayClient()
    client.authorize_service("test_wallet", "TestBot", max_daily=1.0)

    bot = MockAutomatedPaymentBot(
        user_wallet="test_wallet",
        service_key="TestBot",
        mock_client=client,
    )

    # Make some payments
    bot.make_payment(0.001, "/api/test1")
    bot.make_payment(0.002, "/api/test2")
    bot.make_payment(0.003, "/api/test3")

    # Check spending
    spent = bot.get_spending_today()
    assert spent == 0.006

    remaining = bot.get_remaining_limit()
    assert remaining == pytest.approx(0.994)

