"""Tests for ShadowPayClient."""

import pytest
from shadowpay import ShadowPayClient
from shadowpay.exceptions import NetworkError


def test_client_initialization():
    """Test client can be initialized."""
    client = ShadowPayClient(
        settler_url="https://shadow.radr.fun/shadowpay",
        network="solana-mainnet",
    )
    assert client.settler_url == "https://shadow.radr.fun/shadowpay"
    assert client.network == "solana-mainnet"


def test_client_context_manager():
    """Test client works as context manager."""
    with ShadowPayClient() as client:
        assert client.session is not None
    # Session should be closed after exit


def test_url_normalization():
    """Test URL trailing slash is removed."""
    client = ShadowPayClient(settler_url="https://example.com/")
    assert client.settler_url == "https://example.com"


# Add more tests as needed

