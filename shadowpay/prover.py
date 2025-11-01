"""Prover client for ZK proof generation via Node.js sidecar."""

import requests
import logging
from typing import Dict, Any, Optional
from shadowpay.exceptions import ProverServiceNotAvailableError

logger = logging.getLogger(__name__)


class ProverClient:
    """Client for Node.js prover sidecar service."""

    def __init__(self, prover_url: str = "http://localhost:3001", timeout: int = 120):
        """
        Initialize prover client.

        Args:
            prover_url: URL of the prover service
            timeout: Request timeout in seconds (proofs can take 30-90s)
        """
        self.prover_url = prover_url.rstrip("/")
        self.timeout = timeout
        self._check_health()

    def _check_health(self) -> None:
        """
        Verify prover service is running.

        Raises:
            ProverServiceNotAvailableError: If service is not available
        """
        try:
            response = requests.get(f"{self.prover_url}/health", timeout=5)
            response.raise_for_status()
            logger.info(f"Prover service available at {self.prover_url}")
        except requests.RequestException as e:
            logger.error(f"Prover service not available: {e}")
            raise ProverServiceNotAvailableError(
                f"Prover service not running at {self.prover_url}. "
                "Start it with: cd prover-service && npm start"
            )

    def generate_proof(
        self,
        circuit_input: Dict[str, Any],
        circuit_type: str = "spending",
    ) -> Dict[str, Any]:
        """
        Generate ZK proof via sidecar service.

        Args:
            circuit_input: Input data for the circuit
            circuit_type: Type of circuit (spending, shadowid, etc.)

        Returns:
            Dictionary containing proof and publicSignals

        Raises:
            ProverServiceNotAvailableError: If service request fails
        """
        try:
            logger.info(f"Generating {circuit_type} proof...")
            response = requests.post(
                f"{self.prover_url}/prove",
                json={
                    "input": circuit_input,
                    "circuitType": circuit_type,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()

            result = response.json()
            logger.info("Proof generated successfully")
            return result

        except requests.RequestException as e:
            logger.error(f"Failed to generate proof: {e}")
            raise ProverServiceNotAvailableError(f"Failed to generate proof: {e}")

    def verify_proof(
        self,
        proof: Dict[str, Any],
        public_signals: list,
        circuit_type: str = "spending",
    ) -> bool:
        """
        Verify a ZK proof via sidecar service.

        Args:
            proof: The proof to verify
            public_signals: Public signals for the proof
            circuit_type: Type of circuit

        Returns:
            True if proof is valid
        """
        try:
            response = requests.post(
                f"{self.prover_url}/verify",
                json={
                    "proof": proof,
                    "publicSignals": public_signals,
                    "circuitType": circuit_type,
                },
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            return result.get("valid", False)

        except requests.RequestException as e:
            logger.error(f"Failed to verify proof: {e}")
            return False

