# 📚 Swarm API Reference

Complete reference for the Swarm Mode API and command-line interface.

## Table of Contents

1. [CLI Commands](#cli-commands)
2. [Python API](#python-api)
3. [Configuration Schema](#configuration-schema)
4. [Data Models](#data-models)
5. [Events & Callbacks](#events--callbacks)
6. [Error Handling](#error-handling)

---

## CLI Commands

### Global Options

All commands support these global options:

```bash
python swarm.py [GLOBAL_OPTIONS] <command> [ARGS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--config-dir` | Configuration directory | `./swarm_configs` |
| `--log-level` | Logging level | `INFO` |
| `--no-color` | Disable colored output | `false` |
| `--help` | Show help message | - |

### Command: `init`

Initialize a new swarm configuration.

```bash
python swarm.py init [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--name` | Swarm name | Prompt |
| `--workers` | Number of workers | Prompt |
| `--funding` | ETH per worker | Prompt |
| `--strategy` | Trading strategy | `uniform` |
| `--queen-config` | Path to queen wallet config | `./bot_config.yaml` |

**Example:**

```bash
# Interactive mode
python swarm.py init

# Non-interactive mode
python swarm.py init \
  --name "production_swarm" \
  --workers 20 \
  --funding 0.01 \
  --strategy staggered
```

**Returns:**
- Exit code 0 on success
- Creates `swarm_configs/<name>.yaml`
- Creates `swarm_configs/<name>/workers/` directory

---

### Command: `fund`

Fund all workers from queen wallet.

```bash
python swarm.py fund <swarm_name> [OPTIONS]
```

**Arguments:**
- `swarm_name` - Name of the swarm to fund

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--amount` | Override funding amount | From config |
| `--top-up-gas` | Only add gas reserves | `false` |
| `--workers` | Specific workers to fund (comma-separated) | All |
| `--dry-run` | Simulate without sending | `false` |

**Example:**

```bash
# Fund all workers
python swarm.py fund my_swarm

# Fund specific workers
python swarm.py fund my_swarm --workers worker_01,worker_02

# Top up gas only
python swarm.py fund my_swarm --top-up-gas --amount 0.002
```

**Output:**
```
🐝 Funding Swarm: my_swarm

Required: 0.15 ETH
Queen Balance: 2.5 ETH ✓

Funding:
  worker_01: 0.015 ETH ✓ (tx: 0x...)
  worker_02: 0.015 ETH ✓ (tx: 0x...)
  ...

✓ Complete. Gas spent: 0.00021 ETH
```

---

### Command: `start`

Start the swarm (all workers).

```bash
python swarm.py start <swarm_name> [OPTIONS]
```

**Arguments:**
- `swarm_name` - Name of the swarm

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--workers` | Specific workers to start | All |
| `--reclaim-after-cycles` | Auto-reclaim after N cycles | Disabled |
| `--reclaim-at` | Auto-reclaim at datetime | Disabled |
| `--detach` | Run in background | `false` |
| `--debug` | Enable debug logging | `false` |

**Example:**

```bash
# Start all workers
python swarm.py start my_swarm

# Start specific workers
python swarm.py start my_swarm --workers worker_01,worker_02

# Start with auto-reclaim
python swarm.py start my_swarm --reclaim-after-cycles 5

# Run detached (background)
python swarm.py start my_swarm --detach
```

---

### Command: `stop`

Stop the swarm or specific workers.

```bash
python swarm.py stop <swarm_name> [OPTIONS]
```

**Arguments:**
- `swarm_name` - Name of the swarm

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--workers` | Specific workers to stop | All |
| `--force` | Immediate stop (no graceful shutdown) | `false` |
| `--reclaim` | Reclaim funds after stopping | `false` |
| `--timeout` | Seconds to wait for graceful stop | `60` |

**Example:**

```bash
# Graceful stop all workers
python swarm.py stop my_swarm

# Stop specific worker
python swarm.py stop my_swarm --workers worker_05

# Force stop
python swarm.py stop my_swarm --force

# Stop and reclaim
python swarm.py stop my_swarm --reclaim
```

---

### Command: `status`

Show swarm status.

```bash
python swarm.py status <swarm_name> [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--watch` | Refresh every N seconds | Disabled |
| `--format` | Output format: `table`, `json`, `yaml` | `table` |
| `--workers` | Filter to specific workers | All |

**Example:**

```bash
# Standard status
python swarm.py status my_swarm

# Watch mode (5 second refresh)
python swarm.py status my_swarm --watch 5

# JSON output
python swarm.py status my_swarm --format json
```

**JSON Output Structure:**

```json
{
  "swarm_name": "my_swarm",
  "status": "running",
  "workers": {
    "total": 10,
    "active": 10,
    "stopped": 0,
    "error": 0
  },
  "stats": {
    "total_trades": 245,
    "successful_trades": 240,
    "total_volume_eth": 0.48,
    "total_gas_eth": 0.005
  },
  "workers": [
    {
      "name": "worker_01",
      "address": "0x7a3F...9E2D",
      "status": "active",
      "balance_eth": 0.008,
      "balance_compute": 45.2,
      "trades_completed": 25
    }
  ]
}
```

---

### Command: `reclaim`

Reclaim funds from workers to queen wallet.

```bash
python swarm.py reclaim <swarm_name> [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--workers` | Specific workers to reclaim | All |
| `--eth-only` | Only reclaim ETH | `false` |
| `--tokens-only` | Only reclaim tokens | `false` |
| `--retry-failed` | Retry failed reclaims | `false` |
| `--gas-boost` | Multiply gas price by factor | `1.0` |

**Example:**

```bash
# Full reclaim
python swarm.py reclaim my_swarm

# Reclaim specific workers
python swarm.py reclaim my_swarm --workers worker_01,worker_02

# Retry failed
python swarm.py reclaim my_swarm --retry-failed
```

---

### Command: `logs`

View worker logs.

```bash
python swarm.py logs <swarm_name> [worker_name] [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--follow` | Tail logs in real-time | `false` |
| `--lines` | Number of lines to show | `100` |
| `--since` | Show logs since time | All |

**Example:**

```bash
# Show last 100 lines
python swarm.py logs my_swarm worker_01

# Follow mode
python swarm.py logs my_swarm worker_01 --follow

# Last 50 lines
python swarm.py logs my_swarm --lines 50
```

---

### Command: `dashboard`

Launch web dashboard.

```bash
python swarm.py dashboard <swarm_name> [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--host` | Bind address | `127.0.0.1` |
| `--port` | Port number | `8080` |
| `--no-browser` | Don't open browser | `false` |

**Example:**

```bash
# Default dashboard
python swarm.py dashboard my_swarm

# Custom port
python swarm.py dashboard my_swarm --port 3000

# Remote access (be careful!)
python swarm.py dashboard my_swarm --host 0.0.0.0 --port 8080
```

---

### Command: `stats`

Show detailed statistics.

```bash
python swarm.py stats <swarm_name> [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--period` | Stats period: `1h`, `24h`, `7d`, `30d`, `all` | `24h` |
| `--format` | Output format | `table` |

**Example:**

```bash
# Last 24 hours
python swarm.py stats my_swarm

# Last 7 days
python swarm.py stats my_swarm --period 7d

# All time
python swarm.py stats my_swarm --period all
```

---

### Command: `config`

Manage swarm configuration.

```bash
python swarm.py config <swarm_name> <action> [OPTIONS]
```

**Actions:**
- `show` - Display current configuration
- `set` - Update a configuration value
- `edit` - Open in editor
- `validate` - Check configuration validity

**Example:**

```bash
# Show config
python swarm.py config my_swarm show

# Update value
python swarm.py config my_swarm set max_gas_gwei 1.0

# Validate
python swarm.py config my_swarm validate
```

---

## Python API

### SwarmManager

Main class for programmatic swarm control.

```python
from swarm_manager import SwarmManager, SwarmConfig

# Initialize
manager = SwarmManager(config_path="./swarm_configs")
```

#### Methods

##### `create_swarm(config: SwarmConfig) -> Swarm`

Create a new swarm.

```python
from swarm_manager import SwarmConfig, WorkerConfig

config = SwarmConfig(
    name="my_swarm",
    worker_count=10,
    funding_per_worker_eth=0.01,
    strategy="staggered",
    queen_config_path="./bot_config.yaml"
)

swarm = manager.create_swarm(config)
```

**Parameters:**
- `config` (`SwarmConfig`) - Configuration object

**Returns:** `Swarm` object

**Raises:**
- `SwarmExistsError` - Swarm with this name already exists
- `InvalidConfigError` - Configuration is invalid

---

##### `fund_swarm(swarm_name: str, options: FundOptions = None) -> FundingResult`

Fund all workers in a swarm.

```python
from swarm_manager import FundOptions

options = FundOptions(
    workers=["worker_01", "worker_02"],  # Specific workers, or None for all
    amount_eth=0.015,  # Override amount
    dry_run=False
)

result = manager.fund_swarm("my_swarm", options)

print(f"Funded: {result.workers_funded}")
print(f"Total ETH: {result.total_eth_sent}")
print(f"Gas spent: {result.gas_cost_eth}")
```

**Returns:** `FundingResult`

```python
@dataclass
class FundingResult:
    success: bool
    workers_funded: int
    total_eth_sent: float
    gas_cost_eth: float
    transactions: List[FundingTx]
    errors: List[FundingError]
```

---

##### `start_swarm(swarm_name: str, options: StartOptions = None) -> SwarmHandle`

Start a swarm.

```python
from swarm_manager import StartOptions

options = StartOptions(
    workers=None,  # All workers
    detach=False,
    reclaim_after_cycles=None,
    on_event=my_callback
)

handle = manager.start_swarm("my_swarm", options)

# Wait for completion
handle.wait()

# Or stop manually
handle.stop()
```

**Returns:** `SwarmHandle` - Control handle for the running swarm

---

##### `stop_swarm(swarm_name: str, options: StopOptions = None) -> StopResult`

Stop a swarm.

```python
from swarm_manager import StopOptions

options = StopOptions(
    workers=None,  # All workers
    force=False,
    reclaim=False,
    timeout_seconds=60
)

result = manager.stop_swarm("my_swarm", options)
```

---

##### `reclaim_swarm(swarm_name: str, options: ReclaimOptions = None) -> ReclaimResult`

Reclaim funds from workers.

```python
from swarm_manager import ReclaimOptions

options = ReclaimOptions(
    workers=None,
    eth_only=False,
    tokens_only=False,
    gas_boost=1.0
)

result = manager.reclaim_swarm("my_swarm", options)

print(f"ETH reclaimed: {result.total_eth}")
print(f"Tokens reclaimed: {result.total_tokens}")
print(f"Profit: {result.net_profit_eth}")
```

---

##### `get_status(swarm_name: str) -> SwarmStatus`

Get current swarm status.

```python
status = manager.get_status("my_swarm")

print(f"Active: {status.active_workers}/{status.total_workers}")
print(f"Total trades: {status.stats.total_trades}")

for worker in status.workers:
    print(f"{worker.name}: {worker.status} - {worker.balance_eth} ETH")
```

**Returns:** `SwarmStatus`

```python
@dataclass
class SwarmStatus:
    swarm_name: str
    status: str  # "running", "stopped", "partial"
    total_workers: int
    active_workers: int
    stopped_workers: int
    error_workers: int
    workers: List[WorkerStatus]
    stats: SwarmStats
    
@dataclass
class WorkerStatus:
    name: str
    address: str
    status: str  # "active", "stopped", "error", "pending"
    balance_eth: float
    balance_compute: float
    trades_completed: int
    last_trade_time: Optional[datetime]
    error_message: Optional[str]
```

---

##### `get_stats(swarm_name: str, period: str = "24h") -> SwarmStats`

Get trading statistics.

```python
stats = manager.get_stats("my_swarm", period="7d")

print(f"Trades: {stats.total_trades}")
print(f"Success rate: {stats.success_rate_percent}%")
print(f"Volume: {stats.total_volume_eth} ETH")
print(f"Gas costs: {stats.total_gas_eth} ETH")
print(f"Profit/Loss: {stats.net_pnl_eth} ETH")
```

---

### Worker

Individual worker control.

```python
# Get worker instance
worker = manager.get_worker("my_swarm", "worker_01")

# Control individual worker
worker.start()
worker.stop()
worker.restart()

# Get worker info
info = worker.get_info()
print(f"Balance: {info.balance_eth}")
print(f"Status: {info.status}")

# Execute trade manually
result = worker.execute_buy()
result = worker.execute_sell()
```

---

## Configuration Schema

### Swarm Configuration File

```yaml
# swarm_configs/<name>.yaml

# Basic Information
swarm_name: string           # Required: Unique swarm name
version: "1.0"               # Config version

# Queen Wallet
queen_wallet:
  config_path: string        # Path to queen wallet config
  # OR explicit address (less secure)
  # address: "0x..."

# Worker Configuration
workers:
  count: integer             # Number of workers (2-100)
  name_prefix: string        # Worker name prefix (default: "worker")
  
  # Worker directory structure
  storage:
    path: string             # Where to store worker keys
    encryption: string       # Encryption method ("fernet")

# Funding Configuration
funding:
  amount_per_worker_eth: float      # ETH to fund each worker
  gas_reserve_per_worker_eth: float # Extra for gas
  total_required_eth: float         # Auto-calculated
  
  # Auto-funding options
  auto_fund:
    enabled: boolean
    trigger: string         # "low_balance", "schedule", "never"
    threshold_eth: float    # Fund when balance drops below

# Trading Strategy
strategy:
  type: string              # "uniform", "staggered", "randomized", "wave"
  
  # Type-specific config
  config:
    # For "uniform":
    buy_amount_eth: float
    buy_interval_minutes: int
    sell_after_buys: int
    slippage_percent: float
    max_gas_gwei: float
    
    # For "staggered":
    base_interval_minutes: int
    stagger_offset_seconds: int
    randomize_interval_percent: float
    
    # For "randomized":
    buy_amount_eth:
      min: float
      max: float
    buy_interval_minutes:
      min: int
      max: int
    
    # For "wave":
    wave_size: int
    wave_interval_minutes: int

# Security Settings
security:
  auto_reclaim_on_stop: boolean
  
  # Loss protection
  max_loss_per_worker_percent: float  # Stop if loss exceeds %
  emergency_stop_balance_eth: float   # Stop if balance below
  
  # Rate limiting
  max_transactions_per_minute: int
  cooldown_after_error_seconds: int

# Reclaim Settings
reclaim:
  auto_reclaim:
    enabled: boolean
    trigger: string        # "cycle_complete", "profit_threshold", "schedule"
    
  profit_threshold:
    min_profit_eth: float
    
  schedule:
    - "08:00"
    - "20:00"
    
  reserves:
    min_eth_per_worker: float
    min_compute_per_worker: float

# Monitoring
monitoring:
  log_level: string        # "DEBUG", "INFO", "WARNING", "ERROR"
  health_check_interval_seconds: int
  save_trade_history: boolean
  
  # Metrics
  metrics:
    enabled: boolean
    retention_days: int

# Alerting
alerts:
  telegram:
    enabled: boolean
    bot_token: string
    chat_id: string
    
  webhook:
    enabled: boolean
    url: string
    events: [string]
    
  conditions:
    low_balance_threshold_eth: float
    error_rate_threshold_percent: float
    min_workers_healthy_percent: float

# Network
network:
  rpc_url: string
  chain_id: int
  fallback_rpc_urls: [string]
  
  # Gas settings
  gas_price_strategy: string  # "legacy", "eip1559", "aggressive"
  max_gas_price_gwei: float
  priority_fee_gwei: float

# Token Contracts
tokens:
  compute: string          # COMPUTE token address
  weth: string             # WETH address

# Uniswap V3
uniswap:
  router: string
  quoter: string
  factory: string
  pool_fee: int            # 500, 3000, 10000
```

---

## Data Models

### SwarmConfig

```python
@dataclass
class SwarmConfig:
    """Complete swarm configuration."""
    
    # Basic
    name: str
    version: str = "1.0"
    
    # Workers
    worker_count: int = 10
    name_prefix: str = "worker"
    
    # Funding
    funding_per_worker_eth: float = 0.01
    gas_reserve_eth: float = 0.005
    
    # Strategy
    strategy: str = "uniform"  # uniform, staggered, randomized, wave
    strategy_config: Dict[str, Any] = field(default_factory=dict)
    
    # Queen
    queen_config_path: str = "./bot_config.yaml"
    
    # Security
    auto_reclaim_on_stop: bool = True
    max_loss_percent: float = 50.0
    
    # Paths
    config_dir: str = "./swarm_configs"
```

### TradeResult

```python
@dataclass
class TradeResult:
    """Result of a trade operation."""
    
    success: bool
    trade_type: str  # "buy" or "sell"
    
    # Transaction
    tx_hash: Optional[str]
    block_number: Optional[int]
    gas_used: Optional[int]
    gas_cost_eth: Optional[float]
    
    # Trade details
    amount_in: Optional[float]
    amount_out: Optional[float]
    token_in: Optional[str]
    token_out: Optional[str]
    
    # Timing
    timestamp: datetime
    duration_seconds: float
    
    # Error (if failed)
    error: Optional[str]
```

### WorkerInfo

```python
@dataclass
class WorkerInfo:
    """Information about a worker."""
    
    name: str
    address: str
    
    # Status
    status: str
    pid: Optional[int]  # Process ID if running
    
    # Balances
    balance_eth: float
    balance_compute: float
    
    # Trading stats
    trades_completed: int
    trades_failed: int
    total_volume_eth: float
    total_gas_eth: float
    
    # Timing
    started_at: Optional[datetime]
    last_trade_at: Optional[datetime]
    uptime_seconds: int
    
    # Current cycle
    current_cycle_buys: int
    target_cycle_buys: int
```

---

## Events & Callbacks

### Event Types

```python
class SwarmEvent(Enum):
    # Lifecycle
    SWARM_STARTED = "swarm_started"
    SWARM_STOPPED = "swarm_stopped"
    
    # Worker events
    WORKER_STARTED = "worker_started"
    WORKER_STOPPED = "worker_stopped"
    WORKER_ERROR = "worker_error"
    
    # Trading events
    TRADE_SUCCESS = "trade_success"
    TRADE_FAILED = "trade_failed"
    CYCLE_COMPLETE = "cycle_complete"
    
    # Funding events
    FUNDING_COMPLETE = "funding_complete"
    RECLAIM_COMPLETE = "reclaim_complete"
    LOW_BALANCE = "low_balance"
    
    # System events
    HEALTH_CHECK_FAILED = "health_check_failed"
    GAS_PRICE_HIGH = "gas_price_high"
    RPC_ERROR = "rpc_error"
```

### Event Handler

```python
from swarm_manager import SwarmManager, SwarmEvent

def my_event_handler(event: SwarmEvent, data: dict):
    """Handle swarm events."""
    
    if event == SwarmEvent.TRADE_SUCCESS:
        print(f"Trade success: {data['tx_hash']}")
        
    elif event == SwarmEvent.WORKER_ERROR:
        print(f"Worker error: {data['worker']} - {data['error']}")
        
    elif event == SwarmEvent.LOW_BALANCE:
        print(f"Low balance on {data['worker']}: {data['balance']} ETH")
        # Auto-fund
        manager.fund_swarm(data['swarm'], workers=[data['worker']])

# Register handler
manager = SwarmManager()
manager.on(SwarmEvent.TRADE_SUCCESS, my_event_handler)
manager.on(SwarmEvent.WORKER_ERROR, my_event_handler)
```

### Event Data Structures

```python
# TRADE_SUCCESS
trade_data = {
    "swarm": "my_swarm",
    "worker": "worker_01",
    "tx_hash": "0x...",
    "trade_type": "buy",
    "amount_eth": 0.002,
    "amount_compute": 45.5,
    "gas_cost_eth": 0.0001,
    "timestamp": "2025-01-15T10:30:00Z"
}

# WORKER_ERROR
error_data = {
    "swarm": "my_swarm",
    "worker": "worker_01",
    "error": "Insufficient funds",
    "error_type": "InsufficientFundsError",
    "recoverable": False,
    "timestamp": "2025-01-15T10:30:00Z"
}

# LOW_BALANCE
balance_data = {
    "swarm": "my_swarm",
    "worker": "worker_01",
    "balance_eth": 0.0005,
    "threshold_eth": 0.001,
    "needs_funding": True
}
```

---

## Error Handling

### Exception Hierarchy

```
SwarmException
├── ConfigError
│   ├── InvalidConfigError
│   ├── ConfigNotFoundError
│   └── ConfigValidationError
├── WorkerError
│   ├── WorkerNotFoundError
│   ├── WorkerStartError
│   ├── WorkerStopError
│   └── WorkerFundError
├── FundingError
│   ├── InsufficientFundsError
│   ├── FundingTxFailedError
│   └── QueenBalanceError
├── ReclaimError
│   ├── ReclaimFailedError
│   └── NoFundsToReclaimError
├── TradingError
│   ├── TradeFailedError
│   ├── GasPriceError
│   ├── SlippageError
│   └── RPCError
└── SecurityError
    ├── EncryptionError
    ├── UnauthorizedError
    └── MaxLossExceededError
```

### Error Handling Example

```python
from swarm_manager import (
    SwarmManager,
    InsufficientFundsError,
    WorkerStartError,
    GasPriceError
)

manager = SwarmManager()

try:
    manager.fund_swarm("my_swarm")
except InsufficientFundsError as e:
    print(f"Queen wallet needs more ETH: {e.required} ETH required")
    
try:
    manager.start_swarm("my_swarm")
except WorkerStartError as e:
    print(f"Failed to start {e.worker}: {e.reason}")
    
except GasPriceError as e:
    print(f"Gas too high: {e.current_gwei} > {e.max_gwei}")
    # Wait and retry
    time.sleep(300)
    manager.start_swarm("my_swarm")
```

### Retry Logic

```python
from swarm_manager import retry_with_backoff

@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    exceptions=(RPCError, GasPriceError)
)
def execute_trade_with_retry():
    return manager.execute_trade("my_swarm", "worker_01")
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SWARM_CONFIG_DIR` | Configuration directory | `./swarm_configs` |
| `SWARM_LOG_LEVEL` | Default log level | `INFO` |
| `SWARM_RPC_URL` | Default RPC endpoint | From config |
| `SWARM_PASSWORD` | Encryption password (use with caution) | Prompt |
| `SWARM_TELEGRAM_BOT_TOKEN` | Telegram bot token for alerts | None |
| `SWARM_TELEGRAM_CHAT_ID` | Telegram chat ID for alerts | None |
| `SWARM_WEBHOOK_URL` | Webhook URL for alerts | None |

---

*Last updated: 2025-02-14*
*API Version: 1.0.0*
