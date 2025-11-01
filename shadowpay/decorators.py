"""Decorator patterns for ShadowPay SDK."""

import logging
from functools import wraps
from typing import Optional, Callable, Any
from shadowpay.bot import AutomatedPaymentBot
from shadowpay.exceptions import ShadowPayError

logger = logging.getLogger(__name__)

# Global bot instance (set by user)
_global_bot: Optional[AutomatedPaymentBot] = None


def set_global_bot(bot: AutomatedPaymentBot) -> None:
    """
    Set global payment bot for decorator usage.

    Args:
        bot: AutomatedPaymentBot instance
    """
    global _global_bot
    _global_bot = bot


def requires_payment(
    amount_sol: float,
    resource: Optional[str] = None,
    service_key: Optional[str] = None,
    user_wallet: Optional[str] = None,
    settler_url: str = "https://shadow.radr.fun/shadowpay",
    prover_url: str = "http://localhost:3001",
) -> Callable:
    """
    Decorator that requires payment before function execution.

    Usage:
        # Option 1: Use global bot
        set_global_bot(my_bot)

        @requires_payment(amount_sol=0.001)
        def my_function():
            pass

        # Option 2: Specify bot parameters
        @requires_payment(
            amount_sol=0.001,
            service_key='MyService',
            user_wallet='...'
        )
        def my_function():
            pass

    Args:
        amount_sol: Amount to charge in SOL
        resource: Resource identifier (defaults to function name)
        service_key: Service key (required if no global bot)
        user_wallet: User wallet (required if no global bot)
        settler_url: Settler URL (if creating bot)
        prover_url: Prover URL (if creating bot)

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Determine resource name
            res = resource or f"/{func.__module__}.{func.__name__}"

            # Get or create bot
            bot = _global_bot
            if bot is None:
                if not service_key or not user_wallet:
                    raise ValueError(
                        "Either set global bot with set_global_bot() or provide "
                        "service_key and user_wallet to decorator"
                    )
                bot = AutomatedPaymentBot(
                    settler_url=settler_url,
                    user_wallet=user_wallet,
                    service_key=service_key,
                    prover_url=prover_url,
                )

            # Make payment
            try:
                logger.info(f"Making payment for {func.__name__}: {amount_sol} SOL")
                tx_hash = bot.make_payment(
                    amount_sol=amount_sol,
                    resource=res,
                    metadata={
                        "function": func.__name__,
                        "module": func.__module__,
                    },
                )
                logger.info(f"Payment successful: {tx_hash}")

                # Execute function
                return func(*args, **kwargs)

            except ShadowPayError as e:
                logger.error(f"Payment failed for {func.__name__}: {e}")
                raise

        return wrapper

    return decorator


def track_spending(func: Callable) -> Callable:
    """
    Decorator that logs spending information after function execution.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        if _global_bot is None:
            logger.warning("No global bot set, cannot track spending")
            return func(*args, **kwargs)

        # Get initial spending
        try:
            initial_spent = _global_bot.get_spending_today()
        except Exception as e:
            logger.warning(f"Could not get initial spending: {e}")
            initial_spent = 0.0

        # Execute function
        result = func(*args, **kwargs)

        # Get final spending
        try:
            final_spent = _global_bot.get_spending_today()
            spent_in_call = final_spent - initial_spent

            logger.info(
                f"Function {func.__name__} spent {spent_in_call} SOL. "
                f"Total today: {final_spent} SOL"
            )
        except Exception as e:
            logger.warning(f"Could not get final spending: {e}")

        return result

    return wrapper

