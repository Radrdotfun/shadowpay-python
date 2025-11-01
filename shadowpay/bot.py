"""Automated payment bot for making payments on behalf of users."""

import logging
from typing import Optional, Dict, Any
from shadowpay.client import ShadowPayClient
from shadowpay.prover import ProverClient
from shadowpay.types import SpendingAuthorization
from shadowpay.exceptions import (
    InvalidAuthorizationError,
    DailyLimitExceededError,
    PerTransactionLimitExceededError,
    AuthorizationExpiredError,
)
from shadowpay.utils import sol_to_lamports

logger = logging.getLogger(__name__)


class AutomatedPaymentBot:
    """Bot that makes automated payments on behalf of a user."""

    def __init__(
        self,
        settler_url: str,
        user_wallet: str,
        service_key: str,
        prover_url: str = "http://localhost:3001",
    ):
        """
        Initialize payment bot.

        Args:
            settler_url: URL of the settler service
            user_wallet: User's wallet address
            service_key: Service identifier/key
            prover_url: URL of the prover service
        """
        self.client = ShadowPayClient(settler_url)
        self.prover = ProverClient(prover_url)
        self.user_wallet = user_wallet
        self.service_key = service_key
        self._auth_cache: Optional[SpendingAuthorization] = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.client.close()

    def check_authorization(self) -> Optional[SpendingAuthorization]:
        """
        Check if bot is authorized and get limits.

        Returns:
            SpendingAuthorization if valid, None otherwise

        Raises:
            InvalidAuthorizationError: If no valid authorization found
        """
        auths = self.client.list_authorizations(self.user_wallet)

        for auth in auths:
            if auth.authorized_service == self.service_key and auth.is_valid:
                self._auth_cache = auth
                logger.info(f"Authorization found: {auth.max_daily_spend_sol} SOL/day")
                return auth

        logger.warning(f"No valid authorization found for service: {self.service_key}")
        return None

    def _validate_payment(
        self,
        auth: SpendingAuthorization,
        amount_sol: float,
    ) -> None:
        """
        Validate payment against authorization limits.

        Args:
            auth: Authorization to validate against
            amount_sol: Amount to pay in SOL

        Raises:
            AuthorizationExpiredError: If authorization expired
            PerTransactionLimitExceededError: If amount exceeds per-tx limit
            DailyLimitExceededError: If amount would exceed daily limit
        """
        if not auth.is_valid:
            raise AuthorizationExpiredError(
                f"Authorization expired on {auth.valid_until}. Please re-authorize."
            )

        amount_lamports = sol_to_lamports(amount_sol)

        if amount_lamports > auth.max_amount_per_tx:
            raise PerTransactionLimitExceededError(
                f"Payment {amount_sol} SOL exceeds per-transaction limit "
                f"{auth.max_amount_per_tx_sol} SOL"
            )

        if (auth.spent_today + amount_lamports) > auth.max_daily_spend:
            raise DailyLimitExceededError(
                f"Would exceed daily limit. Spent: {auth.spent_today_sol} SOL, "
                f"Limit: {auth.max_daily_spend_sol} SOL, Requested: {amount_sol} SOL",
                spent=auth.spent_today_sol,
                limit=auth.max_daily_spend_sol,
            )

    def _build_circuit_input(
        self,
        auth: SpendingAuthorization,
        amount_sol: float,
        resource: str,
    ) -> Dict[str, Any]:
        """
        Build circuit input for ZK proof generation.

        Args:
            auth: Spending authorization
            amount_sol: Payment amount in SOL
            resource: Resource being paid for

        Returns:
            Circuit input dictionary
        """
        amount_lamports = sol_to_lamports(amount_sol)

        return {
            "userWallet": self.user_wallet,
            "authorizedService": self.service_key,
            "amount": str(amount_lamports),
            "maxAmountPerTx": str(auth.max_amount_per_tx),
            "maxDailySpend": str(auth.max_daily_spend),
            "spentToday": str(auth.spent_today),
            "validUntil": str(auth.valid_until),
            "resource": resource,
            "authorizationId": str(auth.id),
        }

    def make_payment(
        self,
        amount_sol: float,
        resource: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Make automated payment (no user confirmation required).

        Args:
            amount_sol: Amount to pay in SOL
            resource: Resource being paid for
            metadata: Optional metadata for the payment

        Returns:
            Transaction hash

        Raises:
            InvalidAuthorizationError: If bot is not authorized
            AuthorizationExpiredError: If authorization expired
            PerTransactionLimitExceededError: If amount exceeds limits
            DailyLimitExceededError: If daily limit would be exceeded
        """
        # 1. Check authorization
        auth = self._auth_cache or self.check_authorization()

        if not auth:
            raise InvalidAuthorizationError(
                f"No valid authorization for service: {self.service_key}. "
                "User must authorize this service first."
            )

        # 2. Validate payment
        self._validate_payment(auth, amount_sol)

        # 3. Build circuit input
        circuit_input = self._build_circuit_input(auth, amount_sol, resource)

        # 4. Generate ZK proof
        logger.info(f"Generating proof for payment: {amount_sol} SOL to {resource}")
        proof_data = self.prover.generate_proof(circuit_input, circuit_type="spending")

        # 5. Prepare metadata
        payment_metadata = {
            "userWallet": self.user_wallet,
            "serviceAuth": self.service_key,
            "authorizationId": auth.id,
        }
        if metadata:
            payment_metadata.update(metadata)

        # 6. Settle payment
        logger.info(f"Settling payment: {amount_sol} SOL")
        result = self.client.settle_payment(
            proof=proof_data.get("proof"),
            amount=amount_sol,
            resource=resource,
            metadata=payment_metadata,
        )

        tx_hash = result.get("txHash", result.get("tx_hash", ""))
        logger.info(f"Payment settled: {tx_hash}")

        # Invalidate cache to force refresh on next payment
        self._auth_cache = None

        return tx_hash

    def get_spending_today(self) -> float:
        """
        Get amount spent today in SOL.

        Returns:
            Amount spent today in SOL
        """
        auth = self.check_authorization()
        return auth.spent_today_sol if auth else 0.0

    def get_remaining_limit(self) -> float:
        """
        Get remaining daily spending limit in SOL.

        Returns:
            Remaining daily limit in SOL
        """
        auth = self.check_authorization()
        return auth.remaining_today_sol if auth else 0.0

    def get_authorization_info(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed authorization information.

        Returns:
            Dictionary with authorization details or None
        """
        auth = self.check_authorization()
        if not auth:
            return None

        return {
            "service": auth.authorized_service,
            "max_per_transaction_sol": auth.max_amount_per_tx_sol,
            "max_daily_spend_sol": auth.max_daily_spend_sol,
            "spent_today_sol": auth.spent_today_sol,
            "remaining_today_sol": auth.remaining_today_sol,
            "valid_until": auth.valid_until,
            "is_valid": auth.is_valid,
        }

