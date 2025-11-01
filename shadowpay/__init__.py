"""ShadowPay Python SDK - Privacy-preserving payments on Solana."""

from shadowpay.client import ShadowPayClient
from shadowpay.bot import AutomatedPaymentBot
from shadowpay.async_bot import AsyncAutomatedPaymentBot
from shadowpay.types import SpendingAuthorization, PaymentResult, EscrowBalance
from shadowpay.exceptions import (
    ShadowPayError,
    AuthorizationExpiredError,
    DailyLimitExceededError,
    InsufficientBalanceError,
    InvalidAuthorizationError,
    InvalidAPIKeyError,
    PerTransactionLimitExceededError,
    ProverServiceNotAvailableError,
    NodeNotFoundError,
)
from shadowpay.decorators import requires_payment, set_global_bot

__version__ = "1.0.0"
__all__ = [
    "ShadowPayClient",
    "AutomatedPaymentBot",
    "AsyncAutomatedPaymentBot",
    "SpendingAuthorization",
    "PaymentResult",
    "EscrowBalance",
    "ShadowPayError",
    "AuthorizationExpiredError",
    "DailyLimitExceededError",
    "InsufficientBalanceError",
    "InvalidAuthorizationError",
    "InvalidAPIKeyError",
    "PerTransactionLimitExceededError",
    "ProverServiceNotAvailableError",
    "NodeNotFoundError",
    "requires_payment",
    "set_global_bot",
]

