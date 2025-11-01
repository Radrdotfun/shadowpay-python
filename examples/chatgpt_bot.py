"""Example: ChatGPT billing bot with automated payments."""

from shadowpay import AutomatedPaymentBot
import os

# Note: This example requires OpenAI library: pip install openai
# import openai


class ChatGPTBot:
    """ChatGPT bot that charges automatically for each request."""

    def __init__(self, user_wallet: str, service_key: str = "ChatGPT Bot"):
        """
        Initialize ChatGPT bot with payment capability.

        Args:
            user_wallet: User's Solana wallet address
            service_key: Service identifier (must match user's authorization)
        """
        self.payment_bot = AutomatedPaymentBot(
            settler_url="https://shadow.radr.fun/shadowpay",
            user_wallet=user_wallet,
            service_key=service_key,
            prover_url="http://localhost:3001",
        )

        # Check authorization on startup
        auth = self.payment_bot.check_authorization()
        if not auth:
            raise Exception(
                f"Not authorized! Please authorize '{service_key}' to spend on your behalf."
            )

        print(f"✅ Bot authorized!")
        print(f"   Daily limit: {auth.max_daily_spend_sol} SOL")
        print(f"   Per-tx limit: {auth.max_amount_per_tx_sol} SOL")
        print(f"   Spent today: {auth.spent_today_sol} SOL")
        print(f"   Remaining: {auth.remaining_today_sol} SOL")

    def chat(self, message: str, cost_per_request: float = 0.001) -> str:
        """
        Send a message to ChatGPT and pay automatically.

        Args:
            message: User message
            cost_per_request: Cost per API call in SOL

        Returns:
            ChatGPT response
        """
        # Make payment FIRST (automated, no user confirmation!)
        print(f"\n💰 Making payment: {cost_per_request} SOL")
        tx_hash = self.payment_bot.make_payment(
            amount_sol=cost_per_request,
            resource="/api/chatgpt",
            metadata={"message_preview": message[:50]},
        )

        print(f"✅ Payment settled: {tx_hash}")
        print(f"   Explorer: https://explorer.solana.com/tx/{tx_hash}")

        # NOW call ChatGPT API (payment already settled!)
        # Uncomment if you have OpenAI API key:
        # response = openai.ChatCompletion.create(
        #     model="gpt-4",
        #     messages=[{"role": "user", "content": message}]
        # )
        # return response.choices[0].message.content

        # Mock response for demo
        return f"[Mock ChatGPT Response to: {message}]"


def main():
    """Run ChatGPT bot example."""
    # User's wallet (this would come from your app)
    USER_WALLET = os.getenv("USER_WALLET", "AVSSWPbWRYDF7w8GZcrP6yVWsmRWPshMnziHqFQ5RaDR")

    print("🤖 Starting ChatGPT Bot with Automated Payments\n")

    try:
        # Create bot
        bot = ChatGPTBot(user_wallet=USER_WALLET)

        # Make some requests (each one pays automatically!)
        questions = [
            "What is ShadowPay?",
            "How do zero-knowledge proofs work?",
            "Explain Solana in simple terms.",
        ]

        for question in questions:
            print(f"\n❓ Question: {question}")
            answer = bot.chat(question, cost_per_request=0.001)
            print(f"💬 Answer: {answer}")

        # Check spending after all requests
        print("\n" + "=" * 60)
        print("📊 Session Summary:")
        spent = bot.payment_bot.get_spending_today()
        remaining = bot.payment_bot.get_remaining_limit()
        print(f"   Total spent today: {spent} SOL")
        print(f"   Remaining limit: {remaining} SOL")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

