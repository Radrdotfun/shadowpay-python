"""Mock client for testing."""

import time
import uuid
from typing import Dict, List, Optional, Any
from shadowpay.types import SpendingAuthorization, EscrowBalance, PaymentResult
from shadowpay.exceptions import (
    DailyLimitExceededError,
    PerTransactionLimitExceededError,
    InvalidAuthorizationError,
)


class MockShadowPayClient:
    """Mock ShadowPay client for unit tests."""

    def __init__(self):
        """Initialize mock client."""
        self.balances: Dict[str, int] = {}  # wallet -> lamports
        self.authorizations: Dict[str, List[SpendingAuthorization]] = {}
        self.payments: List[Dict[str, Any]] = []
        self.tx_counter = 0

    def set_balance(self, wallet: str, balance_sol: float) -> None:
        """Set mock escrow balance."""
        self.balances[wallet] = int(balance_sol * 1e9)

    def authorize_service(
        self,
        wallet: str,
        service_name: str,
        max_per_tx: float = 0.1,
        max_daily: float = 1.0,
        valid_days: int = 30,
    ) -> SpendingAuthorization:
        """Create mock authorization."""
        auth = SpendingAuthorization(
            id=len(self.authorizations.get(wallet, [])) + 1,
            user_wallet=wallet,
            authorized_service=service_name,
            max_amount_per_tx=int(max_per_tx * 1e9),
            max_daily_spend=int(max_daily * 1e9),
            spent_today=0,
            last_reset_date=time.strftime("%Y-%m-%d"),
            valid_until=int(time.time()) + (valid_days * 24 * 60 * 60),
            user_signature="mock_signature",
            revoked=False,
            created_at=int(time.time()),
        )

        if wallet not in self.authorizations:
            self.authorizations[wallet] = []
        self.authorizations[wallet].append(auth)

        return auth

    def get_escrow_balance(self, wallet: str) -> EscrowBalance:
        """Get mock escrow balance."""
        return EscrowBalance(
            wallet_address=wallet,
            balance=self.balances.get(wallet, 0),
        )

    def list_authorizations(self, wallet: str) -> List[SpendingAuthorization]:
        """List mock authorizations."""
        return self.authorizations.get(wallet, [])

    def make_payment(
        self,
        wallet: str,
        service_name: str,
        amount_sol: float,
        resource: str,
    ) -> str:
        """Make mock payment."""
        # Find authorization
        auths = self.list_authorizations(wallet)
        auth = None
        for a in auths:
            if a.authorized_service == service_name and a.is_valid:
                auth = a
                break

        if not auth:
            raise InvalidAuthorizationError(f"No authorization for {service_name}")

        amount_lamports = int(amount_sol * 1e9)

        # Check limits
        if amount_lamports > auth.max_amount_per_tx:
            raise PerTransactionLimitExceededError(
                f"Amount {amount_sol} exceeds per-tx limit {auth.max_amount_per_tx_sol}"
            )

        if (auth.spent_today + amount_lamports) > auth.max_daily_spend:
            raise DailyLimitExceededError(
                f"Would exceed daily limit",
                spent=auth.spent_today_sol,
                limit=auth.max_daily_spend_sol,
            )

        # Update spending
        auth.spent_today += amount_lamports

        # Generate mock tx hash
        self.tx_counter += 1
        tx_hash = f"mock_tx_{self.tx_counter}_{uuid.uuid4().hex[:8]}"

        # Record payment
        self.payments.append(
            {
                "wallet": wallet,
                "service": service_name,
                "amount_sol": amount_sol,
                "resource": resource,
                "tx_hash": tx_hash,
                "timestamp": time.time(),
            }
        )

        return tx_hash

    def get_spent_today(self, wallet: str, service_name: str) -> int:
        """Get amount spent today in lamports."""
        auths = self.list_authorizations(wallet)
        for auth in auths:
            if auth.authorized_service == service_name:
                return auth.spent_today
        return 0

    def get_payment_history(self) -> List[Dict[str, Any]]:
        """Get all mock payments."""
        return self.payments

    def reset(self) -> None:
        """Reset all mock data."""
        self.balances.clear()
        self.authorizations.clear()
        self.payments.clear()
        self.tx_counter = 0


class MockAutomatedPaymentBot:
    """Mock automated payment bot for testing."""

    def __init__(
        self,
        user_wallet: str,
        service_key: str,
        mock_client: Optional[MockShadowPayClient] = None,
    ):
        """Initialize mock bot."""
        self.user_wallet = user_wallet
        self.service_key = service_key
        self.client = mock_client or MockShadowPayClient()

        # Auto-create authorization if client is new
        if user_wallet not in self.client.authorizations:
            self.client.authorize_service(user_wallet, service_key)

    def make_payment(
        self,
        amount_sol: float,
        resource: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Make mock payment."""
        return self.client.make_payment(
            self.user_wallet,
            self.service_key,
            amount_sol,
            resource,
        )

    def check_authorization(self) -> Optional[SpendingAuthorization]:
        """Check authorization."""
        auths = self.client.list_authorizations(self.user_wallet)
        for auth in auths:
            if auth.authorized_service == self.service_key and auth.is_valid:
                return auth
        return None

    def get_spending_today(self) -> float:
        """Get spending today in SOL."""
        spent = self.client.get_spent_today(self.user_wallet, self.service_key)
        return spent / 1e9

    def get_remaining_limit(self) -> float:
        """Get remaining limit in SOL."""
        auth = self.check_authorization()
        if not auth:
            return 0.0
        return auth.remaining_today_sol

