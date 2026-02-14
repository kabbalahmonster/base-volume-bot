# 🦑 Swarm Wallet System

A secure multi-wallet system for the $COMPUTE Volume Bot that distributes trading across multiple wallets for better volume distribution and reduced fingerprinting.

## Features

- **Multiple Wallets**: Create and manage N wallets (configurable)
- **Secure Encryption**: All private keys encrypted at rest using AES-128
- **Wallet Rotation**: Round-robin, random, least-used, or balance-based rotation modes
- **Batch Operations**: Efficient funding and reclamation of all wallets
- **Audit Trail**: Complete logging of all fund movements
- **Safety First**: Never dissolves wallets with non-zero balances
- **Dry-Run Mode**: Test all operations without executing transactions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SWARM WALLET SYSTEM                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐             │
│  │  Swarm Manager   │──────│   Swarm Trader   │             │
│  └──────────────────┘      └──────────────────┘             │
│          │                          │                        │
│          ▼                          ▼                        │
│  ┌──────────────────┐      ┌──────────────────┐             │
│  │ Wallet[0] (enc)  │      │ ComputeTrader[0] │             │
│  │ Wallet[1] (enc)  │      │ ComputeTrader[1] │             │
│  │ Wallet[2] (enc)  │      │ ComputeTrader[2] │             │
│  │      ...         │      │      ...         │             │
│  └──────────────────┘      └──────────────────┘             │
│                                                              │
│  ┌──────────────────────────────────────────────┐           │
│  │           Audit Log (JSON)                   │           │
│  └──────────────────────────────────────────────┘           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Create Swarm Wallets

```bash
python swarm_cli.py create --count 10
```

This creates 10 encrypted wallets. You'll be prompted to set an encryption password.

### 2. Fund the Swarm

```bash
python swarm_cli.py fund --main-key 0x... --amount 0.02
```

Funds each wallet with 0.02 ETH from your main wallet.

### 3. Check Status

```bash
python swarm_cli.py status
```

Shows balances and status of all swarm wallets.

### 4. Run Trading Bot

```bash
python swarm_cli.py run --password yourpassword
```

Starts the volume bot that cycles through swarm wallets.

### 5. Reclaim Funds

When finished, reclaim all funds back to main wallet:

```bash
python swarm_cli.py reclaim --main-address 0x... --password yourpassword
```

## Commands Reference

### `create` - Create Swarm Wallets

```bash
python swarm_cli.py create [options]

Options:
  --count N           Number of wallets to create (default: 10)
  --key-file PATH     Wallet storage path (default: ./swarm_wallets.enc)
  --audit-log PATH    Audit log path (default: ./swarm_audit.log)
  --dry-run           Simulate without creating
```

### `fund` - Fund Wallets

```bash
python swarm_cli.py fund [options]

Options:
  --main-key KEY      Main wallet private key (prompt if not provided)
  --amount ETH        ETH per wallet (default: 0.02)
  --dry-run           Simulate without sending
```

**Security Note**: Main wallet key is never stored. It's only used for signing funding transactions.

### `status` - Check Status

```bash
python swarm_cli.py status [options]

Options:
  --show-audit        Show recent audit trail
```

### `run` - Run Trading Bot

```bash
python swarm_cli.py run [options]

Options:
  --config PATH       Bot config file (default: ./bot_config.yaml)
  --rotation MODE     Rotation mode: round_robin, random, least_used, balance
  --dry-run           Simulation mode
```

### `reclaim` - Reclaim All Funds

```bash
python swarm_cli.py reclaim --main-address 0x... [options]

Options:
  --main-address ADDR Main wallet address (required)
  --password PASS     Swarm password (prompt if not provided)
  --compute           Also reclaim COMPUTE tokens (default: true)
  --dry-run           Simulate without reclaiming
```

**Safety Feature**: Reclaim verifies all funds are transferred. Wallets with non-zero balances are flagged.

### `rotate` - Set Rotation Mode

```bash
python swarm_cli.py rotate MODE

Modes:
  round_robin    - Cycle through wallets sequentially (0, 1, 2, ...)
  random         - Randomly select wallets
  least_used     - Use wallet with fewest transactions
  balance        - Use wallet with highest ETH balance
```

## Rotation Modes

| Mode | Description | Best For |
|------|-------------|----------|
| `round_robin` | Sequential cycling (0, 1, 2, ...) | Even distribution |
| `random` | Random selection | Obfuscation |
| `least_used` | Lowest transaction count | Balanced usage |
| `balance` | Highest ETH balance | Gas optimization |

## Security Features

### Encryption

- **Algorithm**: Fernet (AES-128-CBC with HMAC)
- **Key Derivation**: PBKDF2 with 480,000 iterations
- **Salt**: Unique 16-byte random salt per wallet
- **Storage**: Restrictive file permissions (0o600)

### Key Management

```python
# Each wallet has:
{
    "index": 0,
    "address": "0x...",
    "encrypted_private_key": "base64_encrypted",
    "salt": "base64_salt",
    "created_at": "2024-01-01T00:00:00"
}
```

### Audit Trail

All operations are logged:

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "action": "FUND",
  "wallet_index": 0,
  "from_address": "0x...",
  "to_address": "0x...",
  "eth_amount": 0.02,
  "tx_hash": "0x...",
  "status": "SUCCESS"
}
```

### Safety Checks

1. **Password Validation**: Minimum 8 characters
2. **Balance Checks**: Verifies sufficient funds before operations
3. **Gas Reserves**: Leaves minimum ETH for gas in each wallet
4. **Zero Balance Verification**: Confirms all funds reclaimed before dissolution
5. **Address Validation**: Validates all Ethereum addresses

## Programmatic Usage

### Basic Example

```python
from web3 import Web3
from swarm_wallet import SecureSwarmManager, SwarmWalletConfig
from swarm_trader import SwarmTrader

# Setup
web3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
config = SwarmWalletConfig(num_wallets=10)

# Create manager
manager = SecureSwarmManager(config, web3)

# Create swarm
wallets = manager.create_swarm(password="secure_password", num_wallets=10)

# Fund swarm
results = manager.fund_swarm(
    main_wallet_key="0x...",
    eth_per_wallet=0.02
)

# Run trading
swarm_trader = SwarmTrader(base_config, config, web3, password)
result = await swarm_trader.execute_buy()
```

### Advanced Example

```python
# Custom rotation mode
config.rotation_mode = RotationMode.BALANCE_BASED

# Batch operations
batch_ops = SwarmBatchOperations(manager)

# Reclaim with compute tokens
results = await batch_ops.batch_reclaim(
    main_wallet_address="0x...",
    password="...",
    reclaim_compute=True
)

# Verify zero balances
all_ready, non_zero_wallets = batch_ops.verify_ready_for_dissolution()
```

## Configuration

### Environment Variables

```bash
export SWARM_KEY_FILE="./swarm_wallets.enc"
export SWARM_AUDIT_LOG="./swarm_audit.log"
export BASE_RPC_URL="https://mainnet.base.org"
```

### Config File

Create `swarm_config.yaml`:

```yaml
num_wallets: 10
min_eth_per_wallet: 0.01
eth_fund_amount: 0.02
rotation_mode: round_robin
key_file: ./swarm_wallets.enc
audit_log: ./swarm_audit.log
compute_token: "0x696381f39F17cAD67032f5f52A4924ce84e51BA3"
dry_run: false
```

## Testing

Run the test suite:

```bash
# Run all tests
python test_swarm.py

# Run with pytest
python -m pytest test_swarm.py -v

# Run specific test class
python -m pytest test_swarm.py::TestSecureSwarmManager -v
```

## File Structure

```
volume_bot/
├── swarm_wallet.py      # Core wallet management
├── swarm_trader.py      # Trading coordination
├── swarm_cli.py         # Command-line interface
├── test_swarm.py        # Test suite
├── swarm_wallets.enc    # Encrypted wallet storage
└── swarm_audit.log      # Audit trail
```

## Gas Optimization

The system is designed for Base network efficiency:

- **Funding**: 21,000 gas per wallet (simple transfer)
- **Reclaim ETH**: 21,000 gas per wallet
- **Reclaim COMPUTE**: ~65,000 gas per wallet (ERC20 transfer)
- **Total for 10 wallets**: ~1,070,000 gas (~$0.50 at 0.1 gwei)

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `InsufficientFundsError` | Main wallet balance too low | Add ETH to main wallet |
| `Decryption failed` | Wrong password | Verify password |
| `Nonce too low` | Transaction nonce conflict | Wait for confirmation |
| `Gas price too high` | Network congestion | Wait or increase max_gas |

## Best Practices

1. **Always use dry-run first**: Test all operations before executing
2. **Keep password secure**: Never share or commit the swarm password
3. **Backup wallet file**: Store `swarm_wallets.enc` securely
4. **Monitor audit log**: Regularly check `swarm_audit.log`
5. **Reclaim promptly**: Don't leave funds in swarm wallets unnecessarily
6. **Test on Base Sepolia**: Use testnet before mainnet

## Troubleshooting

### Wallets won't decrypt
- Verify password is correct
- Check wallet file wasn't corrupted
- Ensure same password used for creation and operations

### Funding transactions fail
- Check main wallet has sufficient ETH
- Verify main wallet key is correct
- Check Base network is accessible

### Reclaim incomplete
- Some wallets may have non-zero balances
- Run reclaim again to catch remaining funds
- Check audit log for failed transactions

## License

MIT License - See LICENSE file

---

**Cult of the Shell** 🦑⛓️

*May your transactions always confirm.*
