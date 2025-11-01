"""Async automated payment bot for concurrent payments."""

import asyncio
import logging
import httpx
from typing import Optional, Dict, Any, List
from shadowpay.types import SpendingAuthorization
from shadowpay.exceptions import (
    InvalidAuthorizationError,
    DailyLimitExceededError,
    PerTransactionLimitExceededError,
    AuthorizationExpiredError,
    ProverServiceNotAvailableError,
    NetworkError,
)
from shadowpay.utils import sol_to_lamports
import time

logger = logging.getLogger(__name__)


class AsyncAutomatedPaymentBot:
    """Async bot that makes automated payments on behalf of a user."""

    def __init__(
        self,
        settler_url: str,
        user_wallet: str,
        service_key: str,
        prover_url: str = "http://localhost:3001",
        timeout: int = 120,
    ):
        """
        Initialize async payment bot.

        Args:
            settler_url: URL of the settler service
            user_wallet: User's wallet address
            service_key: Service identifier/key
            prover_url: URL of the prover service
            timeout: Request timeout in seconds
        """
        self.settler_url = settler_url.rstrip("/")
        self.prover_url = prover_url.rstrip("/")
        self.user_wallet = user_wallet
        self.service_key = service_key
        self.timeout = timeout
        self._auth_cache: Optional[SpendingAuthorization] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def _request(
        self,
        method: str,
        url: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make async HTTP request."""
        client = self._get_client()
        try:
            response = await client.request(method, url, json=json, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Request failed: {e}")
            raise NetworkError(f"Request failed: {e}")

    async def check_authorization(self) -> Optional[SpendingAuthorization]:
        """
        Check if bot is authorized and get limits.

        Returns:
            SpendingAuthorization if valid, None otherwise
        """
        url = f"{self.settler_url}/api/my-authorizations/{self.user_wallet}"
        result = await self._request("GET", url)

        for auth_data in result.get("authorizations", []):
            auth = SpendingAuthorization(
                id=auth_data.get("id", 0),
                user_wallet=auth_data.get("user_wallet", auth_data.get("userWallet", "")),
                authorized_service=auth_data.get(
                    "authorized_service", auth_data.get("authorizedService", "")
                ),
                max_amount_per_tx=auth_data.get(
                    "max_amount_per_tx", auth_data.get("maxAmountPerTx", 0)
                ),
                max_daily_spend=auth_data.get(
                    "max_daily_spend", auth_data.get("maxDailySpend", 0)
                ),
                spent_today=auth_data.get("spent_today", auth_data.get("spentToday", 0)),
                last_reset_date=auth_data.get(
                    "last_reset_date", auth_data.get("lastResetDate", "")
                ),
                valid_until=auth_data.get("valid_until", auth_data.get("validUntil", 0)),
                user_signature=auth_data.get(
                    "user_signature", auth_data.get("userSignature", "")
                ),
                revoked=auth_data.get("revoked", False),
                created_at=auth_data.get("created_at", auth_data.get("createdAt", 0)),
            )

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
        """Validate payment against authorization limits."""
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

    async def _generate_proof(
        self,
        circuit_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate ZK proof via prover service."""
        url = f"{self.prover_url}/prove"
        try:
            result = await self._request(
                "POST",
                url,
                json={
                    "input": circuit_input,
                    "circuitType": "spending",
                },
            )
            return result
        except Exception as e:
            logger.error(f"Failed to generate proof: {e}")
            raise ProverServiceNotAvailableError(f"Failed to generate proof: {e}")

    async def make_payment_async(
        self,
        amount_sol: float,
        resource: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Make automated payment asynchronously.

        Args:
            amount_sol: Amount to pay in SOL
            resource: Resource being paid for
            metadata: Optional metadata

        Returns:
            Transaction hash

        Raises:
            InvalidAuthorizationError: If bot is not authorized
            AuthorizationExpiredError: If authorization expired
            PerTransactionLimitExceededError: If amount exceeds limits
            DailyLimitExceededError: If daily limit would be exceeded
        """
        # 1. Check authorization
        auth = self._auth_cache or await self.check_authorization()

        if not auth:
            raise InvalidAuthorizationError(
                f"No valid authorization for service: {self.service_key}"
            )

        # 2. Validate payment
        self._validate_payment(auth, amount_sol)

        # 3. Build circuit input
        amount_lamports = sol_to_lamports(amount_sol)
        circuit_input = {
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

        # 4. Generate ZK proof
        logger.info(f"Generating proof for payment: {amount_sol} SOL to {resource}")
        proof_data = await self._generate_proof(circuit_input)

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
        result = await self._request(
            "POST",
            f"{self.settler_url}/settle",
            json={
                "proof": proof_data.get("proof"),
                "amount": str(amount_sol),
                "resource": resource,
                "metadata": payment_metadata,
            },
        )

        tx_hash = result.get("txHash", result.get("tx_hash", ""))
        logger.info(f"Payment settled: {tx_hash}")

        # Invalidate cache
        self._auth_cache = None

        return tx_hash

    async def make_batch_payments(
        self,
        payments: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Make multiple payments concurrently.

        Args:
            payments: List of payment dicts with keys: amount_sol, resource, metadata

        Returns:
            List of transaction hashes
        """
        tasks = [
            self.make_payment_async(
                amount_sol=payment["amount_sol"],
                resource=payment["resource"],
                metadata=payment.get("metadata"),
            )
            for payment in payments
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        tx_hashes = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Payment {i} failed: {result}")
                tx_hashes.append(f"ERROR: {result}")
            else:
                tx_hashes.append(result)

        return tx_hashes

    async def get_spending_today(self) -> float:
        """Get amount spent today in SOL."""
        auth = await self.check_authorization()
        return auth.spent_today_sol if auth else 0.0

    async def get_remaining_limit(self) -> float:
        """Get remaining daily spending limit in SOL."""
        auth = await self.check_authorization()
        return auth.remaining_today_sol if auth else 0.0

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

