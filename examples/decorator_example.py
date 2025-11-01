"""Example: Using the @requires_payment decorator."""

from shadowpay import AutomatedPaymentBot, requires_payment, set_global_bot
from shadowpay.decorators import track_spending
import os


# Example 1: Using global bot with decorator
def example_global_bot():
    """Demonstrate decorator with global bot."""
    print("=== Example 1: Global Bot ===\n")

    USER_WALLET = os.getenv("USER_WALLET", "AVSSWPbWRYDF7w8GZcrP6yVWsmRWPshMnziHqFQ5RaDR")

    # Create and set global bot
    bot = AutomatedPaymentBot(
        settler_url="https://shadow.radr.fun/shadowpay",
        user_wallet=USER_WALLET,
        service_key="Decorator Example",
        prover_url="http://localhost:3001",
    )
    set_global_bot(bot)

    # Now any function with @requires_payment will use this bot
    @requires_payment(amount_sol=0.001)
    def expensive_operation(data: str) -> str:
        """This function requires payment before execution."""
        print(f"   Processing: {data}")
        return f"Processed: {data.upper()}"

    @requires_payment(amount_sol=0.0005, resource="/api/quick")
    def quick_operation(x: int) -> int:
        """Another paid function with custom resource."""
        print(f"   Computing: {x} * 2")
        return x * 2

    try:
        # These calls will automatically make payments!
        result1 = expensive_operation("hello world")
        print(f"   Result: {result1}\n")

        result2 = quick_operation(42)
        print(f"   Result: {result2}\n")

        # Check spending
        spent = bot.get_spending_today()
        print(f"💰 Total spent: {spent} SOL\n")

    except Exception as e:
        print(f"❌ Error: {e}\n")


# Example 2: Decorator with inline parameters
def example_inline_parameters():
    """Demonstrate decorator with inline bot creation."""
    print("=== Example 2: Inline Parameters ===\n")

    USER_WALLET = os.getenv("USER_WALLET", "AVSSWPbWRYDF7w8GZcrP6yVWsmRWPshMnziHqFQ5RaDR")

    @requires_payment(
        amount_sol=0.01,
        service_key="ML Model Service",
        user_wallet=USER_WALLET,
        resource="/api/ml/predict",
    )
    def run_ml_model(input_data: dict) -> dict:
        """Run ML model inference (costs 0.01 SOL per call)."""
        print(f"   Running ML model on: {input_data}")
        # Simulate ML inference
        return {"prediction": "positive", "confidence": 0.95}

    try:
        # Payment happens automatically!
        result = run_ml_model({"text": "This is great!"})
        print(f"   Result: {result}\n")

    except Exception as e:
        print(f"❌ Error: {e}\n")


# Example 3: Tracking spending across multiple functions
def example_spending_tracking():
    """Demonstrate spending tracking decorator."""
    print("=== Example 3: Spending Tracking ===\n")

    USER_WALLET = os.getenv("USER_WALLET", "AVSSWPbWRYDF7w8GZcrP6yVWsmRWPshMnziHqFQ5RaDR")

    bot = AutomatedPaymentBot(
        settler_url="https://shadow.radr.fun/shadowpay",
        user_wallet=USER_WALLET,
        service_key="Tracked Service",
        prover_url="http://localhost:3001",
    )
    set_global_bot(bot)

    @track_spending
    @requires_payment(amount_sol=0.001)
    def api_call_1():
        """First API call."""
        print("   Executing API call 1")
        return "result1"

    @track_spending
    @requires_payment(amount_sol=0.002)
    def api_call_2():
        """Second API call."""
        print("   Executing API call 2")
        return "result2"

    @track_spending
    def process_batch():
        """Process batch with multiple sub-calls."""
        print("   Processing batch...")
        api_call_1()
        api_call_1()
        api_call_2()
        print("   Batch complete")

    try:
        process_batch()

    except Exception as e:
        print(f"❌ Error: {e}\n")


# Example 4: Function with error handling
def example_error_handling():
    """Demonstrate error handling with decorators."""
    print("=== Example 4: Error Handling ===\n")

    USER_WALLET = os.getenv("USER_WALLET", "AVSSWPbWRYDF7w8GZcrP6yVWsmRWPshMnziHqFQ5RaDR")

    bot = AutomatedPaymentBot(
        settler_url="https://shadow.radr.fun/shadowpay",
        user_wallet=USER_WALLET,
        service_key="Error Example",
        prover_url="http://localhost:3001",
    )
    set_global_bot(bot)

    @requires_payment(amount_sol=0.001)
    def risky_operation(fail: bool = False):
        """Operation that might fail."""
        if fail:
            raise ValueError("Operation failed!")
        return "success"

    try:
        # Payment happens, then function executes successfully
        result = risky_operation(fail=False)
        print(f"   ✅ Success: {result}")

        # Payment happens, but function fails (payment still processed!)
        result = risky_operation(fail=True)
        print(f"   This won't print")

    except ValueError as e:
        print(f"   ⚠️  Function failed: {e}")
        print(f"   (Note: Payment was already processed!)\n")


def main():
    """Run all examples."""
    print("🎯 ShadowPay Decorator Examples\n")

    try:
        example_global_bot()
        input("Press Enter to continue to next example...")
        print()

        example_inline_parameters()
        input("Press Enter to continue to next example...")
        print()

        example_spending_tracking()
        input("Press Enter to continue to next example...")
        print()

        example_error_handling()

    except Exception as e:
        print(f"\n❌ Example failed: {e}")


if __name__ == "__main__":
    main()

