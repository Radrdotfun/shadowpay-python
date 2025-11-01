"""Utility functions for ShadowPay SDK."""

import os
import time
import logging
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)


def sol_to_lamports(sol: float) -> int:
    """Convert SOL to lamports."""
    return int(sol * 1e9)


def lamports_to_sol(lamports: int) -> float:
    """Convert lamports to SOL."""
    return lamports / 1e9


def get_env_or_default(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable or return default."""
    return os.environ.get(key, default)


def validate_wallet_address(address: str) -> bool:
    """Basic validation of Solana wallet address."""
    if not address:
        return False
    # Solana addresses are base58 encoded, typically 32-44 characters
    return 32 <= len(address) <= 44


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Decorator to retry function with exponential backoff."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
            return func(*args, **kwargs)

        return wrapper

    return decorator


def format_transaction_hash(tx_hash: str, network: str = "solana-mainnet") -> str:
    """Format transaction hash with explorer URL."""
    if network.startswith("solana"):
        cluster = "" if "mainnet" in network else "?cluster=devnet"
        return f"https://explorer.solana.com/tx/{tx_hash}{cluster}"
    return tx_hash


def setup_logging(level: int = logging.INFO) -> None:
    """Setup logging for ShadowPay SDK."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

