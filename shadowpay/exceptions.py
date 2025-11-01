"""Custom exceptions for ShadowPay SDK."""


class ShadowPayError(Exception):
    """Base exception for all ShadowPay errors."""

    pass


class InvalidAPIKeyError(ShadowPayError):
    """Raised when API key is invalid or missing."""

    pass


class AuthorizationExpiredError(ShadowPayError):
    """Raised when spending authorization has expired."""

    pass


class DailyLimitExceededError(ShadowPayError):
    """Raised when daily spending limit is exceeded."""

    def __init__(self, message: str, spent: float = 0, limit: float = 0):
        super().__init__(message)
        self.spent = spent
        self.limit = limit


class InsufficientBalanceError(ShadowPayError):
    """Raised when escrow balance is insufficient."""

    pass


class InvalidAuthorizationError(ShadowPayError):
    """Raised when authorization is invalid or not found."""

    pass


class PerTransactionLimitExceededError(ShadowPayError):
    """Raised when single transaction exceeds per-transaction limit."""

    pass


class ProverServiceNotAvailableError(ShadowPayError):
    """Raised when prover service is not available."""

    pass


class NodeNotFoundError(ShadowPayError):
    """Raised when Node.js is not found on system."""

    pass


class NetworkError(ShadowPayError):
    """Raised when network request fails."""

    pass


class SettlementError(ShadowPayError):
    """Raised when payment settlement fails."""

    pass


class ProverError(ShadowPayError):
    """Base exception for prover-related errors."""

    pass


class ProverSubprocessError(ProverError):
    """Raised when subprocess prover fails."""

    pass

