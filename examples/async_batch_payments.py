"""Example: Async batch payments for high-throughput applications."""

import asyncio
import time
from shadowpay import AsyncAutomatedPaymentBot
import os


async def main():
    """Demonstrate async batch payment processing."""
    USER_WALLET = os.getenv("USER_WALLET", "AVSSWPbWRYDF7w8GZcrP6yVWsmRWPshMnziHqFQ5RaDR")

    print("⚡ Async Batch Payment Demo\n")

    async with AsyncAutomatedPaymentBot(
        settler_url="https://shadow.radr.fun/shadowpay",
        user_wallet=USER_WALLET,
        service_key="Batch Processor",
        prover_url="http://localhost:3001",
    ) as bot:
        # Check authorization
        auth = await bot.check_authorization()
        if not auth:
            print("❌ Not authorized! Please authorize 'Batch Processor' first.")
            return

        print(f"✅ Authorized for batch processing")
        print(f"   Daily limit: {auth.max_daily_spend_sol} SOL")
        print(f"   Per-tx limit: {auth.max_amount_per_tx_sol} SOL\n")

        # Example 1: Concurrent individual payments
        print("--- Concurrent Payments ---")
        start_time = time.time()

        tasks = [
            bot.make_payment_async(0.0001, f"/api/item_{i}", {"item_id": i})
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = [r for r in results if isinstance(r, str)]
        failed = [r for r in results if isinstance(r, Exception)]

        duration = time.time() - start_time

        print(f"✅ Completed 10 payments in {duration:.2f}s")
        print(f"   Successful: {len(successful)}")
        print(f"   Failed: {len(failed)}")
        print(f"   Throughput: {10/duration:.1f} payments/sec\n")

        # Example 2: Batch payment helper
        print("--- Batch Payment Helper ---")
        start_time = time.time()

        payments = [
            {
                "amount_sol": 0.0001,
                "resource": f"/api/service/{i}",
                "metadata": {"service_id": i, "batch_id": "batch_001"},
            }
            for i in range(20)
        ]

        tx_hashes = await bot.make_batch_payments(payments)

        duration = time.time() - start_time
        successful_count = len([tx for tx in tx_hashes if not tx.startswith("ERROR")])

        print(f"✅ Batch payment completed in {duration:.2f}s")
        print(f"   Total payments: {len(payments)}")
        print(f"   Successful: {successful_count}")
        print(f"   Throughput: {len(payments)/duration:.1f} payments/sec\n")

        # Show summary
        print("--- Summary ---")
        spent = await bot.get_spending_today()
        remaining = await bot.get_remaining_limit()

        print(f"Total spent today: {spent} SOL")
        print(f"Remaining limit: {remaining} SOL")


async def rate_limited_processor():
    """Example: Process work items with rate-limited payments."""
    USER_WALLET = os.getenv("USER_WALLET", "AVSSWPbWRYDF7w8GZcrP6yVWsmRWPshMnziHqFQ5RaDR")

    print("\n🔄 Rate-Limited Processor Demo\n")

    async with AsyncAutomatedPaymentBot(
        settler_url="https://shadow.radr.fun/shadowpay",
        user_wallet=USER_WALLET,
        service_key="Rate Limited Processor",
        prover_url="http://localhost:3001",
    ) as bot:
        # Simulate processing work items
        work_items = [f"task_{i}" for i in range(50)]
        processed = 0
        errors = 0

        print(f"Processing {len(work_items)} work items...")

        for item in work_items:
            try:
                # Check if we have budget
                remaining = await bot.get_remaining_limit()
                if remaining < 0.0001:
                    print(f"\n⚠️  Daily limit approaching. Processed {processed} items.")
                    break

                # Make payment and process
                tx_hash = await bot.make_payment_async(
                    amount_sol=0.0001,
                    resource=f"/api/process/{item}",
                )

                processed += 1

                if processed % 10 == 0:
                    print(f"Processed {processed} items...")

            except Exception as e:
                errors += 1
                print(f"❌ Failed to process {item}: {e}")

        print(f"\n✅ Processing complete!")
        print(f"   Processed: {processed}")
        print(f"   Errors: {errors}")
        print(f"   Success rate: {processed/(processed+errors)*100:.1f}%")


if __name__ == "__main__":
    print("Choose demo:")
    print("1. Batch payments")
    print("2. Rate-limited processor")
    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "1":
        asyncio.run(main())
    elif choice == "2":
        asyncio.run(rate_limited_processor())
    else:
        print("Running both demos...\n")
        asyncio.run(main())
        asyncio.run(rate_limited_processor())

