# Frequently Asked Questions

## General Questions

### Q: Is this bot free to use?
**A:** Yes, the bot software is free and open source. You only pay network gas fees for transactions.

### Q: Can I lose money using this bot?
**A:** Yes. This is a trading bot that buys and sells tokens. Token prices can go down. Only trade what you can afford to lose.

### Q: Do I need programming skills?
**A:** Basic command line knowledge is helpful but not required. The setup wizard guides you through everything.

## Setup Questions

### Q: How much ETH do I need to start?
**A:** Minimum 0.01 ETH on Base network:
- 0.005 ETH for trading
- 0.005 ETH for gas reserves

### Q: Where do I get Base ETH?
**A:** Options:
1. Bridge from Ethereum mainnet (expensive)
2. Buy on Coinbase and withdraw to Base
3. Use a Base faucet for test amounts

### Q: What is an API key and do I need one?
**A:** API keys are for 0x and 1inch aggregators. They provide better prices but aren't required - the bot works with direct DEX routing.

### Q: Is my private key safe?
**A:** Yes, if you:
- Use a strong encryption password
- Keep `.bot_wallet.enc` secure
- Don't share your password

## Trading Questions

### Q: Which tokens can I trade?
**A:** Any token on Base with liquidity on:
- Aerodrome ✅
- Uniswap V3 ✅
- Uniswap V2 ✅

V4-only tokens (like COMPUTE) need 0x aggregator.

### Q: Why did my trade fail?
**A:** Common reasons:
1. Insufficient ETH for gas
2. Pool has no liquidity
3. Slippage too low
4. Network congestion
5. Token has transfer restrictions

### Q: How do I stop the bot?
**A:** Press Ctrl+C. The bot will gracefully stop after completing the current cycle.

### Q: Can I run multiple bots?
**A:** Yes, but each needs:
- Separate wallet
- Separate config
- Sufficient ETH balance

## COMPUTE-Specific Questions

### Q: Can I trade COMPUTE with this bot?
**A:** Currently limited. COMPUTE is V4-only and requires:
- 0x aggregator (if they add V4 support), OR
- Direct V4 implementation (not yet ready)

### Q: When will COMPUTE trading work?
**A:** Options:
1. 0x adds V4 support (out of our control)
2. We implement direct V4 Universal Router (in progress)
3. COMPUTE gets V3/V2 liquidity (token team)

### Q: Can I use 1inch for COMPUTE?
**A:** Same limitation - 1inch doesn't route V4 yet.

## Technical Questions

### Q: What is slippage?
**A:** The maximum price difference you'll accept. 2% slippage means you accept up to 2% worse price than quoted.

### Q: What is gas price?
**A:** The fee paid to network validators. Higher = faster transaction. Bot defaults to max 5 gwei.

### Q: What is a DEX?
**A:** Decentralized Exchange - smart contracts that allow trading without intermediaries.

### Q: What is Aerodrome?
**A:** The most popular DEX on Base. Uses Solidly-style pools. Where BNKR has its liquidity.

### Q: What is 0x?
**A:** An aggregator that finds the best prices across all DEXs automatically.

## Troubleshooting

### Q: "No wallet file found" error?
**A:** Run `python bot.py setup` first to create a wallet.

### Q: "Insufficient ETH balance" but I have ETH?
**A:** Make sure your ETH is on Base network, not Ethereum mainnet.

### Q: Bot hangs on "Connecting..."?
**A:** RPC may be slow. Try:
1. Wait 30 seconds
2. Switch RPC in config
3. Check your internet connection

### Q: Transaction pending forever?
**A:** Gas price may be too low. The bot will retry with higher gas.

### Q: "replacement transaction underpriced"?
**A:** Fixed in latest version. Update to latest commit.

## Security Questions

### Q: Can the developers steal my funds?
**A:** No. The code is open source and:
- Your keys are encrypted locally
- No external servers receive your keys
- Only you control your wallet

### Q: Should I use this with my main wallet?
**A:** No. Create a new wallet specifically for the bot. Only fund it with what you're willing to trade.

### Q: Is the code audited?
**A:** Yes, see SECURITY_AUDIT_REPORT.md. Grade: B+ (Good with minor improvements).

### Q: What if I forget my password?
**A:** There is no password recovery. You'll need to:
1. Create new wallet
2. Transfer funds manually
3. Import private key if you saved it

## Support

### Q: Where can I get help?
**A:** 
- GitHub Issues: https://github.com/kabbalahmonster/base-volume-bot/issues
- Check docs/ folder for detailed guides
- Review error messages carefully

### Q: I found a bug, what should I do?
**A:** 
1. Check if it's already reported on GitHub
2. Create a new issue with:
   - What you were doing
   - Error message
   - Your config (remove API keys)

### Q: Can I contribute to the project?
**A:** Yes! Pull requests welcome:
- Bug fixes
- Documentation
- New features
- Testing

## Advanced Questions

### Q: Can I modify the trading strategy?
**A:** Yes, edit `bot.py`. The main logic is in `execute_buy()` and `execute_sell()`.

### Q: Can I add a new DEX?
**A:** Yes, see ROUTERS.md for instructions on adding custom routers.

### Q: Can I run this on a server?
**A:** Yes. Use the systemd service file or Docker.

### Q: Can I use a hardware wallet?
**A:** Not directly. You'd need to modify the code to use Web3.py with hardware wallet support.

## Roadmap Questions

### Q: What's next for the bot?
**A:** Priorities:
1. Direct V4 Universal Router support
2. Better logging and monitoring
3. Web dashboard
4. Multi-wallet support

### Q: Will you add other chains?
**A:** Possible. The code is designed to be chain-agnostic. Priority chains:
- Ethereum mainnet
- Arbitrum
- Optimism

### Q: Will you add limit orders?
**A:** Possible future feature. Would require off-chain order monitoring.
