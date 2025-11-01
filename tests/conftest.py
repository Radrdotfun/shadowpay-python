"""Pytest configuration and fixtures."""

import pytest
from shadowpay.testing import MockShadowPayClient, MockAutomatedPaymentBot


@pytest.fixture
def mock_client():
    """Provide a mock ShadowPay client."""
    client = MockShadowPayClient()
    client.set_balance("test_wallet", 10.0)  # 10 SOL
    return client


@pytest.fixture
def mock_bot(mock_client):
    """Provide a mock automated payment bot."""
    mock_client.authorize_service(
        wallet="test_wallet",
        service_name="TestBot",
        max_per_tx=0.1,
        max_daily=1.0,
    )
    return MockAutomatedPaymentBot(
        user_wallet="test_wallet",
        service_key="TestBot",
        mock_client=mock_client,
    )


@pytest.fixture
def test_wallet():
    """Provide a test wallet address."""
    return "AVSSWPbWRYDF7w8GZcrP6yVWsmRWPshMnziHqFQ5RaDR"

