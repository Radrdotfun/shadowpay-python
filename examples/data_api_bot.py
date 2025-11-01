"""Example: Premium data API with rate limiting."""

from shadowpay import AutomatedPaymentBot, DailyLimitExceededError
import os
import time
from typing import Dict, Any


class PremiumDataAPI:
    """Premium data API with automated per-query billing."""

    def __init__(
        self,
        user_wallet: str,
        service_key: str = "Premium Data API",
        cost_per_query: float = 0.0001,
    ):
        """
        Initialize premium data API client.

        Args:
            user_wallet: User's wallet address
            service_key: Service identifier
            cost_per_query: Cost per API query in SOL
        """
        self.cost_per_query = cost_per_query

        self.bot = AutomatedPaymentBot(
            settler_url="https://shadow.radr.fun/shadowpay",
            user_wallet=user_wallet,
            service_key=service_key,
            prover_url="http://localhost:3001",
        )

        # Verify authorization
        auth = self.bot.check_authorization()
        if not auth:
            raise Exception(f"Not authorized for {service_key}")

        print(f"✅ Premium Data API initialized")
        print(f"   Cost per query: {cost_per_query} SOL")
        print(f"   Daily budget: {auth.max_daily_spend_sol} SOL")
        print(f"   Max queries/day: {int(auth.max_daily_spend_sol / cost_per_query)}")

    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get market data for a symbol.

        Args:
            symbol: Trading symbol (e.g., BTC, ETH)

        Returns:
            Market data dictionary

        Raises:
            DailyLimitExceededError: If daily spending limit reached
        """
        try:
            # Check remaining budget before making request
            remaining = self.bot.get_remaining_limit()
            if remaining < self.cost_per_query:
                raise Exception(
                    f"Insufficient remaining budget: {remaining} SOL "
                    f"(need {self.cost_per_query} SOL)"
                )

            # Make payment
            print(f"💰 Querying {symbol}... ({self.cost_per_query} SOL)")
            tx_hash = self.bot.make_payment(
                amount_sol=self.cost_per_query,
                resource=f"/api/market/{symbol}",
                metadata={"symbol": symbol, "query_time": time.time()},
            )

            # Fetch data (mock for example)
            data = self._fetch_market_data(symbol)
            print(f"✅ Data received (tx: {tx_hash[:16]}...)")

            return data

        except DailyLimitExceededError as e:
            print(f"❌ Daily limit exceeded!")
            print(f"   Spent: {e.spent} SOL")
            print(f"   Limit: {e.limit} SOL")
            print(f"   Resets at midnight UTC")
            raise

    def _fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Mock data fetching (replace with real API call)."""
        # In production, call your actual data API here
        import random

        return {
            "symbol": symbol,
            "price": round(random.uniform(100, 50000), 2),
            "volume_24h": round(random.uniform(1000000, 10000000), 2),
            "change_24h": round(random.uniform(-10, 10), 2),
            "timestamp": time.time(),
        }

    def get_batch_data(self, symbols: list) -> Dict[str, Dict[str, Any]]:
        """
        Get market data for multiple symbols.

        Args:
            symbols: List of symbols

        Returns:
            Dictionary mapping symbol to market data
        """
        results = {}

        for symbol in symbols:
            try:
                results[symbol] = self.get_market_data(symbol)
            except DailyLimitExceededError:
                print(f"⚠️  Stopping batch query - daily limit reached")
                break
            except Exception as e:
                print(f"⚠️  Failed to get data for {symbol}: {e}")
                results[symbol] = {"error": str(e)}

        return results


def main():
    """Run data API example."""
    USER_WALLET = os.getenv("USER_WALLET", "AVSSWPbWRYDF7w8GZcrP6yVWsmRWPshMnziHqFQ5RaDR")

    print("📊 Premium Data API Demo\n")

    try:
        # Initialize API client
        api = PremiumDataAPI(user_wallet=USER_WALLET, cost_per_query=0.0001)

        # Query single symbol
        print("\n--- Single Query ---")
        btc_data = api.get_market_data("BTC")
        print(f"BTC Price: ${btc_data['price']:,.2f}")
        print(f"24h Change: {btc_data['change_24h']:+.2f}%")

        # Query multiple symbols
        print("\n--- Batch Query ---")
        symbols = ["BTC", "ETH", "SOL", "MATIC", "AVAX"]
        results = api.get_batch_data(symbols)

        for symbol, data in results.items():
            if "error" not in data:
                print(
                    f"{symbol:6s} ${data['price']:>10,.2f}  {data['change_24h']:>+6.2f}%"
                )

        # Show spending summary
        print("\n--- Summary ---")
        spent = api.bot.get_spending_today()
        remaining = api.bot.get_remaining_limit()
        queries_made = len([r for r in results.values() if "error" not in r]) + 1
        queries_remaining = int(remaining / api.cost_per_query)

        print(f"Queries made: {queries_made}")
        print(f"Queries remaining: {queries_remaining}")
        print(f"Spent: {spent} SOL")
        print(f"Remaining: {remaining} SOL")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

