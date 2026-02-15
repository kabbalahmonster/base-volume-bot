# ❓ Frequently Asked Questions

Quick answers to common questions.

---

## Getting Started

### What do I need to get started?

- Python 3.9+
- 0.01 ETH on Base network
- Basic command line knowledge

### How long does setup take?

About 15-25 minutes including funding.

---

## Wallets & Security

### How are private keys stored?

Encrypted with PBKDF2-HMAC-SHA256 (600k iterations) and stored in `.wallet.enc`.

### What if I forget my password?

There is no recovery. You must remember your password or export the key first.

### Can I use my existing wallet?

The bot generates wallets for security. You can fund the generated wallet from your main wallet.

---

## Trading

### How much ETH do I need?

| Strategy | ETH Needed |
|----------|------------|
| Testing | 0.01 |
| Small Scale | 0.05 |
| Standard | 0.1 |
| Aggressive | 0.5+ |

### Can I change settings while running?

Yes, edit `bot_config.json` and restart the bot.

### What happens if I stop the bot?

Pending transactions complete, position remains. Resume anytime.

---

## Troubleshooting

### "Failed to decrypt wallet"

Wrong password. Try again or re-run setup.

### "Insufficient funds"

Send more ETH to your wallet or reduce `buy_amount_eth`.

### "Gas price exceeds maximum"

Increase `max_gas_gwei` in config or wait for lower gas.

### "Failed to connect to RPC"

Check internet connection. Bot auto-retries other RPCs.

---

## Costs

### What are the total costs?

- Gas fees: ~$0.0005-0.001 per transaction
- No developer fees
- No subscription costs

### Example daily cost?

Standard settings: ~$0.08/day in gas fees.

---

See [SETUP.md](SETUP.md) for detailed setup instructions.
