# ShadowPay Python SDK

[![PyPI version](https://badge.fury.io/py/shadowpay.svg)](https://badge.fury.io/py/shadowpay)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Production-ready Python SDK for ShadowPay** - Privacy-preserving automated payments on Solana using Zero-Knowledge proofs.

Perfect for AI/ML developers, data scientists, and automation engineers who need seamless payment integration.

## ✨ Features

- 🤖 **Automated Payments** - No user confirmation needed after authorization
- 🔒 **Privacy-Preserving** - Zero-knowledge proofs protect sensitive data
- ⚡ **Async Support** - High-throughput concurrent payments
- 🎯 **Simple API** - Working example in 10 lines of code
- 🛡️ **Safe Spending Limits** - Per-transaction and daily limits
- 🐍 **Pythonic** - Type hints, context managers, decorators
- 🧪 **Testing Tools** - Mock clients for easy unit testing

## 🚀 Quick Start

### Installation

```bash
pip install shadowpay
```

### 10-Line Example

```python
from shadowpay import AutomatedPaymentBot

# Create bot
bot = AutomatedPaymentBot(
    settler_url='https://shadow.radr.fun/shadowpay',
    user_wallet='YOUR_WALLET_ADDRESS',
    service_key='My Service'
)

# Make payment (automated - no user confirmation!)
tx_hash = bot.make_payment(
    amount_sol=0.001,
    resource='/api/service'
)

print(f"Payment settled: {tx_hash}")
```

## 📋 Prerequisites

### 1. Start the Prover Service

The SDK requires a Node.js prover service for ZK proof generation:

```bash
cd prover-service
npm install
npm start
```

The prover service will run on `http://localhost:3001`.

**Docker:**
```bash
cd prover-service
docker build -t shadowpay-prover .
docker run -d -p 3001:3001 shadowpay-prover
```

### 2. User Authorization

Before your bot can make payments, users must authorize it:

```python
from shadowpay import ShadowPayClient

client = ShadowPayClient()

# User authorizes your service (requires user signature)
client.authorize_spending(
    user_wallet='USER_WALLET',
    service_name='My Service',
    max_amount_per_tx=0.01,   # Max 0.01 SOL per payment
    max_daily_spend=1.0,       # Max 1 SOL per day
    valid_days=365,            # Valid for 1 year
    user_signature='USER_SIGNATURE'
)
```

## 💡 Usage Examples

### Basic Payment Bot

```python
from shadowpay import AutomatedPaymentBot

bot = AutomatedPaymentBot(
    settler_url='https://shadow.radr.fun/shadowpay',
    user_wallet='USER_WALLET',
    service_key='ChatGPT Bot',
    prover_url='http://localhost:3001'
)

# Check authorization
auth = bot.check_authorization()
print(f"Daily limit: {auth.max_daily_spend_sol} SOL")
print(f"Remaining: {auth.remaining_today_sol} SOL")

# Make payment
tx_hash = bot.make_payment(
    amount_sol=0.001,
    resource='/api/chat',
    metadata={'message_id': '12345'}
)
```

### Async Batch Payments

```python
import asyncio
from shadowpay import AsyncAutomatedPaymentBot

async def main():
    async with AsyncAutomatedPaymentBot(
        settler_url='https://shadow.radr.fun/shadowpay',
        user_wallet='USER_WALLET',
        service_key='Batch Processor'
    ) as bot:
        # Make 100 concurrent payments
        tasks = [
            bot.make_payment_async(0.0001, f'/api/item_{i}')
            for i in range(100)
        ]
        
        results = await asyncio.gather(*tasks)
        print(f"Processed {len(results)} payments")

asyncio.run(main())
```

### Decorator Pattern

```python
from shadowpay import requires_payment, set_global_bot

# Set up bot once
bot = AutomatedPaymentBot(...)
set_global_bot(bot)

# Automatic payment before function execution
@requires_payment(amount_sol=0.001)
def expensive_api_call(data):
    # Payment already settled!
    return process_data(data)

result = expensive_api_call({"query": "..."})
```

### Error Handling

```python
from shadowpay import (
    AutomatedPaymentBot,
    DailyLimitExceededError,
    InvalidAuthorizationError
)

bot = AutomatedPaymentBot(...)

try:
    tx = bot.make_payment(0.001, '/api/service')
except InvalidAuthorizationError:
    print("Not authorized! User needs to authorize service.")
except DailyLimitExceededError as e:
    print(f"Daily limit exceeded. Spent: {e.spent}, Limit: {e.limit}")
```

## 📚 Examples

See the `examples/` directory for complete working examples:

- **[chatgpt_bot.py](examples/chatgpt_bot.py)** - ChatGPT billing bot
- **[data_api_bot.py](examples/data_api_bot.py)** - Premium data API with rate limiting
- **[async_batch_payments.py](examples/async_batch_payments.py)** - High-throughput async payments
- **[decorator_example.py](examples/decorator_example.py)** - Using the @requires_payment decorator

Run examples:
```bash
python examples/chatgpt_bot.py
python examples/data_api_bot.py
```

## 🧪 Testing

### Mock Client

```python
from shadowpay.testing import MockShadowPayClient

# Create mock client
client = MockShadowPayClient()
client.set_balance('wallet', 1.0)  # 1 SOL
client.authorize_service('wallet', 'TestBot', max_daily=10.0)

# Make mock payments
tx = client.make_payment('wallet', 'TestBot', 0.001, '/test')
assert tx.startswith('mock_tx_')

# Verify spending
spent = client.get_spent_today('wallet', 'TestBot')
assert spent == 1000000  # lamports
```

## 🏗️ Architecture

```
Python App
    ↓
ShadowPayClient / AutomatedPaymentBot
    ↓
ProverClient → Node.js Prover Service (snarkjs)
    ↓
ShadowPay Settler API
    ↓
Solana Blockchain
```

## 🔧 Configuration

### Environment Variables

```bash
SHADOWPAY_SETTLER_URL=https://shadow.radr.fun/shadowpay
SHADOWPAY_NETWORK=solana-mainnet
SHADOWPAY_USER_WALLET=YOUR_WALLET
SHADOWPAY_SERVICE_KEY=YOUR_SERVICE
```

### Configuration File

Create `shadowpay.toml`:

```toml
[shadowpay]
settler_url = "https://shadow.radr.fun/shadowpay"
network = "solana-mainnet"
user_wallet = "YOUR_WALLET"
service_key = "YOUR_SERVICE"

[limits]
max_per_transaction = 0.01
max_daily_spend = 1.0
retry_attempts = 3
timeout_seconds = 30
```

## 📖 API Reference

### ShadowPayClient

Main client for API interactions:

```python
client = ShadowPayClient(
    settler_url='https://shadow.radr.fun/shadowpay',
    network='solana-mainnet',
    api_key=None,
    timeout=30
)

# API Key Management
client.generate_api_key()
client.get_api_key_by_wallet(wallet)
client.rotate_api_key(current_key)

# Escrow
client.get_escrow_balance(wallet)
client.deposit_to_escrow(wallet, amount_sol, signature)

# Authorization
client.authorize_spending(...)
client.revoke_authorization(...)
client.list_authorizations(wallet)

# Payments
client.settle_payment(proof, amount, resource, metadata)
```

### AutomatedPaymentBot

Bot for making automated payments:

```python
bot = AutomatedPaymentBot(
    settler_url='...',
    user_wallet='...',
    service_key='...',
    prover_url='http://localhost:3001'
)

# Check authorization
auth = bot.check_authorization()

# Make payment
tx_hash = bot.make_payment(amount_sol, resource, metadata)

# Get spending info
spent = bot.get_spending_today()
remaining = bot.get_remaining_limit()
```

### AsyncAutomatedPaymentBot

Async version for concurrent payments:

```python
async with AsyncAutomatedPaymentBot(...) as bot:
    # Single payment
    tx = await bot.make_payment_async(amount_sol, resource)
    
    # Batch payments
    tx_hashes = await bot.make_batch_payments([
        {'amount_sol': 0.001, 'resource': '/api/1'},
        {'amount_sol': 0.002, 'resource': '/api/2'},
    ])
```

## 🛠️ Development

### Setup

```bash
git clone https://github.com/Lukey372/ShadowPay.git
cd ShadowPay/python-sdk
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
pytest --cov=shadowpay --cov-report=html
```

### Code Quality

```bash
black shadowpay/
ruff check shadowpay/
mypy shadowpay/
```

## 🔒 Security

- ✅ Zero-knowledge proofs protect transaction privacy
- ✅ Daily spending limits prevent abuse
- ✅ Per-transaction limits for safety
- ✅ User authorization required before any payment
- ✅ Authorizations can be revoked anytime

## 📊 Performance

- **Sync client**: ~100ms overhead per payment (excluding proof generation)
- **Async client**: 50-100+ concurrent payments per second
- **Proof generation**: 1-30 seconds (depends on circuit complexity)

## 🤝 Contributing

Contributions welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **API Documentation**: https://registry.scalar.com/@radr/apis/shadowpay-api/latest
- **GitHub**: https://github.com/Radrdotfun/shadowpay-python
- **Test Page**: https://shadow.radr.fun/shadowpay/test-automated-payment.html

## 💬 Support

- GitHub Issues: https://github.com/Radrdotfun/shadowpay-python/issues
- Email: contact@radr.fun

## 🎯 Use Cases

Perfect for:
- 🤖 AI API billing (ChatGPT, Anthropic, OpenAI proxies)
- 📊 Data science APIs (price feeds, analytics, ML models)
- 🔄 Automation scripts and bots
- 🌐 IoT device payments
- 💳 Subscription services
- 🤝 Trading bot marketplaces

## ⚡ Quick Links

- [Examples](examples/) - Working code examples
- [API Reference](docs/api_reference.md) - Complete API documentation
- [Prover Service](prover-service/) - ZK proof generation service
- [Testing Guide](docs/testing.md) - How to test your integration

---

**Made with ❤️ by [RADR](https://radr.fun)**

**Let's make payments private and automated! 🚀**

