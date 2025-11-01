"""Type definitions for ShadowPay SDK."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import time


@dataclass
class SpendingAuthorization:
    """Represents a spending authorization."""

    id: int
    user_wallet: str
    authorized_service: str
    max_amount_per_tx: int  # lamports
    max_daily_spend: int  # lamports
    spent_today: int  # lamports
    last_reset_date: str
    valid_until: int  # Unix timestamp
    user_signature: str
    revoked: bool
    created_at: int

    @property
    def max_amount_per_tx_sol(self) -> float:
        """Get max amount per transaction in SOL."""
        return self.max_amount_per_tx / 1e9

    @property
    def max_daily_spend_sol(self) -> float:
        """Get max daily spend in SOL."""
        return self.max_daily_spend / 1e9

    @property
    def spent_today_sol(self) -> float:
        """Get amount spent today in SOL."""
        return self.spent_today / 1e9

    @property
    def remaining_today_sol(self) -> float:
        """Get remaining daily limit in SOL."""
        return (self.max_daily_spend - self.spent_today) / 1e9

    @property
    def is_valid(self) -> bool:
        """Check if authorization is valid."""
        return not self.revoked and time.time() < self.valid_until

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_wallet": self.user_wallet,
            "authorized_service": self.authorized_service,
            "max_amount_per_tx": self.max_amount_per_tx,
            "max_daily_spend": self.max_daily_spend,
            "spent_today": self.spent_today,
            "last_reset_date": self.last_reset_date,
            "valid_until": self.valid_until,
            "user_signature": self.user_signature,
            "revoked": self.revoked,
            "created_at": self.created_at,
        }


@dataclass
class PaymentResult:
    """Result of a payment operation."""

    success: bool
    tx_hash: Optional[str] = None
    network_id: Optional[str] = None
    error: Optional[str] = None
    amount_sol: Optional[float] = None
    resource: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "tx_hash": self.tx_hash,
            "network_id": self.network_id,
            "error": self.error,
            "amount_sol": self.amount_sol,
            "resource": self.resource,
        }


@dataclass
class EscrowBalance:
    """Represents an escrow balance."""

    wallet_address: str
    balance: int  # lamports

    @property
    def balance_sol(self) -> float:
        """Get balance in SOL."""
        return self.balance / 1e9

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "wallet_address": self.wallet_address,
            "balance": self.balance,
            "balance_sol": self.balance_sol,
        }


@dataclass
class APIKeyInfo:
    """Information about an API key."""

    api_key: str
    wallet_address: Optional[str] = None
    treasury_wallet: Optional[str] = None
    created_at: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "api_key": self.api_key,
            "wallet_address": self.wallet_address,
            "treasury_wallet": self.treasury_wallet,
            "created_at": self.created_at,
        }

