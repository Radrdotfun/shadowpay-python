"""Main ShadowPay client for API interactions."""

import requests
import logging
from typing import Optional, Dict, Any, List
from shadowpay.types import SpendingAuthorization, EscrowBalance, APIKeyInfo
from shadowpay.exceptions import (
    ShadowPayError,
    InvalidAPIKeyError,
    NetworkError,
)
from shadowpay.utils import retry_with_backoff, sol_to_lamports
import time

logger = logging.getLogger(__name__)


class ShadowPayClient:
    """Main client for ShadowPay API interactions."""

    def __init__(
        self,
        settler_url: str = "https://shadow.radr.fun/shadowpay",
        network: str = "solana-mainnet",
        api_key: Optional[str] = None,
        timeout: int = 30,
        log_level: int = logging.INFO,
    ):
        """
        Initialize ShadowPay client.

        Args:
            settler_url: Base URL of the settler service
            network: Network identifier (solana-mainnet, solana-devnet)
            api_key: Optional API key for authenticated requests
            timeout: Request timeout in seconds
            log_level: Logging level
        """
        self.settler_url = settler_url.rstrip("/")
        self.network = network
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

        # Setup logging
        logger.setLevel(log_level)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    @retry_with_backoff(max_retries=3, exceptions=(NetworkError,))
    def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        require_auth: bool = False,
    ) -> Any:
        """
        Make HTTP request to settler.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            json: JSON body for POST requests
            params: Query parameters
            require_auth: Whether to require API key authentication

        Returns:
            Response JSON data

        Raises:
            InvalidAPIKeyError: If authentication fails
            ShadowPayError: If request fails
            NetworkError: If network request fails
        """
        url = f"{self.settler_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if require_auth and self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            logger.debug(f"{method} {url}")
            response = self.session.request(
                method=method,
                url=url,
                json=json,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code == 401:
                raise InvalidAPIKeyError("Invalid or missing API key")
            elif response.status_code == 400:
                error_data = response.json() if response.text else {}
                raise ShadowPayError(error_data.get("error", "Bad request"))
            elif response.status_code >= 500:
                raise NetworkError(f"Server error: {response.status_code}")

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Network request failed: {e}")
            raise NetworkError(f"Network request failed: {e}")

    # ==================== API Key Management ====================

    def generate_api_key(
        self,
        wallet_address: Optional[str] = None,
        treasury_wallet: Optional[str] = None,
    ) -> APIKeyInfo:
        """
        Generate new API key.

        Args:
            wallet_address: Optional wallet address
            treasury_wallet: Optional treasury wallet

        Returns:
            APIKeyInfo with the generated key
        """
        data = {}
        if wallet_address:
            data["walletAddress"] = wallet_address
        if treasury_wallet:
            data["treasuryWallet"] = treasury_wallet

        result = self._request("POST", "/v1/keys/new", json=data if data else None)
        return APIKeyInfo(
            api_key=result.get("api_key", result.get("apiKey", "")),
            wallet_address=result.get("wallet_address", result.get("walletAddress")),
            treasury_wallet=result.get("treasury_wallet", result.get("treasuryWallet")),
            created_at=result.get("created_at", result.get("createdAt")),
        )

    def get_api_key_by_wallet(self, wallet: str) -> APIKeyInfo:
        """
        Get API key for a wallet address.

        Args:
            wallet: Wallet address

        Returns:
            APIKeyInfo for the wallet
        """
        result = self._request("GET", f"/v1/keys/by-wallet/{wallet}")
        return APIKeyInfo(
            api_key=result.get("api_key", result.get("apiKey", "")),
            wallet_address=result.get("wallet_address", result.get("walletAddress")),
            treasury_wallet=result.get("treasury_wallet", result.get("treasuryWallet")),
        )

    def rotate_api_key(self, current_key: str) -> APIKeyInfo:
        """
        Rotate API key.

        Args:
            current_key: Current API key

        Returns:
            APIKeyInfo with new key
        """
        result = self._request("POST", "/v1/keys/rotate", json={"current_key": current_key})
        return APIKeyInfo(
            api_key=result.get("api_key", result.get("apiKey", "")),
            wallet_address=result.get("wallet_address", result.get("walletAddress")),
        )

    # ==================== Escrow Management ====================

    def get_escrow_balance(self, wallet: str) -> EscrowBalance:
        """
        Get escrow balance for a wallet.

        Args:
            wallet: Wallet address

        Returns:
            EscrowBalance for the wallet
        """
        result = self._request("GET", f"/api/escrow/balance/{wallet}")
        return EscrowBalance(
            wallet_address=result.get("wallet_address", result.get("walletAddress", wallet)),
            balance=result.get("balance", 0),
        )

    def deposit_to_escrow(
        self,
        wallet: str,
        amount_sol: float,
        signature: str,
    ) -> Dict[str, Any]:
        """
        Deposit funds to escrow.

        Args:
            wallet: Wallet address
            amount_sol: Amount to deposit in SOL
            signature: Transaction signature

        Returns:
            Deposit result
        """
        result = self._request(
            "POST",
            "/api/escrow/deposit",
            json={
                "wallet": wallet,
                "amount": str(amount_sol),
                "signature": signature,
            },
        )
        return result

    # ==================== Authorization Management ====================

    def authorize_spending(
        self,
        user_wallet: str,
        service_name: str,
        max_amount_per_tx: float,  # SOL
        max_daily_spend: float,  # SOL
        valid_days: int,
        user_signature: str,
    ) -> Dict[str, Any]:
        """
        Register spending authorization.

        Args:
            user_wallet: User's wallet address
            service_name: Name of the authorized service
            max_amount_per_tx: Maximum amount per transaction in SOL
            max_daily_spend: Maximum daily spending in SOL
            valid_days: Number of days authorization is valid
            user_signature: User's signature

        Returns:
            Authorization result
        """
        valid_until = int(time.time()) + (valid_days * 24 * 60 * 60)

        result = self._request(
            "POST",
            "/api/authorize-spending",
            json={
                "user_wallet": user_wallet,
                "authorized_service": service_name,
                "max_amount_per_tx": str(max_amount_per_tx),
                "max_daily_spend": str(max_daily_spend),
                "valid_until": valid_until,
                "user_signature": user_signature,
            },
        )
        return result

    def revoke_authorization(
        self,
        user_wallet: str,
        service_name: str,
        user_signature: str,
    ) -> Dict[str, Any]:
        """
        Revoke spending authorization.

        Args:
            user_wallet: User's wallet address
            service_name: Name of the service to revoke
            user_signature: User's signature

        Returns:
            Revocation result
        """
        result = self._request(
            "POST",
            "/api/revoke-authorization",
            json={
                "user_wallet": user_wallet,
                "authorized_service": service_name,
                "user_signature": user_signature,
            },
        )
        return result

    def list_authorizations(self, wallet: str) -> List[SpendingAuthorization]:
        """
        List all authorizations for a wallet.

        Args:
            wallet: Wallet address

        Returns:
            List of SpendingAuthorization objects
        """
        result = self._request("GET", f"/api/my-authorizations/{wallet}")
        authorizations = []

        for auth_data in result.get("authorizations", []):
            # Convert field names (handle both snake_case and camelCase)
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
            authorizations.append(auth)

        return authorizations

    # ==================== x402 Protocol ====================

    def verify_payment(self, proof: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify payment using x402 protocol.

        Args:
            proof: ZK proof data
            metadata: Payment metadata

        Returns:
            Verification result
        """
        result = self._request(
            "POST",
            "/verify",
            json={
                "proof": proof,
                "metadata": metadata,
            },
        )
        return result

    def settle_payment(
        self,
        proof: Dict[str, Any],
        amount: float,
        resource: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Settle payment using x402 protocol.

        Args:
            proof: ZK proof data
            amount: Payment amount in SOL
            resource: Resource being paid for
            metadata: Additional metadata

        Returns:
            Settlement result with txHash
        """
        payload = {
            "proof": proof,
            "amount": str(amount),
            "resource": resource,
        }
        if metadata:
            payload["metadata"] = metadata

        result = self._request("POST", "/settle", json=payload)
        return result

    def get_supported_features(self) -> Dict[str, Any]:
        """
        Get supported features of the settler.

        Returns:
            Dictionary of supported features
        """
        result = self._request("GET", "/supported")
        return result

    # ==================== ShadowID ====================

    def register_shadowid(
        self,
        wallet: str,
        commitment: str,
        signature: str,
    ) -> Dict[str, Any]:
        """
        Register a ShadowID.

        Args:
            wallet: Wallet address
            commitment: Commitment hash
            signature: User signature

        Returns:
            Registration result
        """
        result = self._request(
            "POST",
            "/api/shadowid/register",
            json={
                "wallet": wallet,
                "commitment": commitment,
                "signature": signature,
            },
        )
        return result

    def generate_shadowid_proof(
        self,
        wallet: str,
        nullifier: str,
    ) -> Dict[str, Any]:
        """
        Generate ShadowID proof.

        Args:
            wallet: Wallet address
            nullifier: Nullifier for the proof

        Returns:
            Proof data
        """
        result = self._request(
            "POST",
            "/api/shadowid/proof",
            json={
                "wallet": wallet,
                "nullifier": nullifier,
            },
        )
        return result

    def get_shadowid_root(self) -> Dict[str, Any]:
        """
        Get current ShadowID merkle root.

        Returns:
            Current root data
        """
        result = self._request("GET", "/api/shadowid/root")
        return result

