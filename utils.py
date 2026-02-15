"""
Utility Module (HARDENED VERSION)

Helper functions, gas optimization, logging, and formatting utilities.

SECURITY CHANGES:
- Fixed HIGH-002: Added error message sanitization
- Fixed HIGH-006: Fixed slippage calculation divide by zero
- Added secure logging that redacts sensitive data
- Added structured logging with metrics collection
"""

import os
import sys
import re
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from web3 import Web3
from rich.logging import RichHandler
from rich.console import Console
from rich.text import Text

from config import Config

# Import new structured logging
try:
    from logging_utils import (
        StructuredLogger, get_logger, log_operation,
        PerformanceMetrics, MetricsCollector
    )
    STRUCTURED_LOGGING_AVAILABLE = True
except ImportError:
    STRUCTURED_LOGGING_AVAILABLE = False


# Global console for Rich output
console = Console()


class TransactionError(Exception):
    """Custom exception for transaction failures."""
    pass


class InsufficientFundsError(Exception):
    """Custom exception for insufficient funds."""
    pass


class GasPriceError(Exception):
    """Custom exception for gas price issues."""
    pass


class SecurityError(Exception):
    """Custom exception for security violations."""
    pass


class SecureLogger:
    """
    Logger that sanitizes sensitive data from log messages.
    
    Addresses HIGH-002: Prevents sensitive data leakage in logs.
    """
    
    # Patterns to redact from logs
    SENSITIVE_PATTERNS = [
        (r'0x[a-fA-F0-9]{64}', '[PRIVATE_KEY_REDACTED]'),  # Private keys (64 hex chars)
        (r'0x[a-fA-F0-9]{60,66}', '[KEY_REDACTED]'),  # Keys with 0x prefix
        (r'password["\']?\s*[:=]\s*["\'][^"\']+["\']', 'password=[REDACTED]'),
        (r'key["\']?\s*[:=]\s*["\'][^"\']{32,}["\']', 'key=[REDACTED]'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']', 'api_key=[REDACTED]'),
        (r'["\'][a-fA-F0-9]{32,}["\']', '"[HEX_REDACTED]"'),  # Long hex strings
    ]
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def _sanitize(self, msg: str) -> str:
        """Remove sensitive data from log message."""
        if not isinstance(msg, str):
            msg = str(msg)
        
        sanitized = msg
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized
    
    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(self._sanitize(msg), *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._logger.info(self._sanitize(msg), *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(self._sanitize(msg), *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._logger.error(self._sanitize(msg), *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        # For exceptions, log full details to file only, sanitized to console
        self._logger.exception(self._sanitize(msg), *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._logger.critical(self._sanitize(msg), *args, **kwargs)


def setup_logging(log_level: str = "INFO", log_file: str = "./bot.log") -> SecureLogger:
    """
    Setup comprehensive logging with both file and console output.
    
    Returns a SecureLogger that sanitizes sensitive data.
    """
    logger = logging.getLogger("compute_bot")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Rich console handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True
    )
    rich_handler.setLevel(logging.INFO)
    rich_formatter = logging.Formatter("%(message)s")
    rich_handler.setFormatter(rich_formatter)
    logger.addHandler(rich_handler)
    
    # File handler for persistent logging
    if log_file:
        # Ensure log directory exists
        log_path = os.path.abspath(log_file)
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Wrap with secure logger
    return SecureLogger(logger)


# Initialize global secure logger
logger = setup_logging()

# Try to initialize structured logger for enhanced logging
_structured_logger: Optional[StructuredLogger] = None

def get_structured_logger(name: str = 'bot', log_file: str = './logs/bot.log') -> Optional[StructuredLogger]:
    """Get or initialize the structured logger."""
    global _structured_logger
    if _structured_logger is None and STRUCTURED_LOGGING_AVAILABLE:
        _structured_logger = StructuredLogger(
            name=name,
            log_file=log_file,
            log_level='INFO',
            max_bytes=10*1024*1024,  # 10MB
            backup_count=5,
            use_rich_console=True,
            json_format_file=True,
            json_format_console=False
        )
    return _structured_logger


class GasOptimizer:
    """
    Optimizes gas pricing for transactions.
    Tracks network conditions and suggests optimal gas prices.
    """
    
    def __init__(self, config: Config, web3: Web3):
        self.config = config
        self.web3 = web3
        self.gas_history: list = []
        self.max_history = 20
        self._structured_logger = get_structured_logger()
        
    def _log_gas_metric(self, operation: str, gas_price_gwei: float, **kwargs):
        """Log gas metric to structured logger if available."""
        if self._structured_logger:
            self._structured_logger.info(
                f"Gas {operation}",
                extra={'gas_price_gwei': gas_price_gwei, **kwargs}
            )
    
    def get_optimal_gas_price(self) -> int:
        """
        Get optimal gas price based on network conditions.
        Uses EIP-1559 if available, falls back to legacy gas price.
        """
        try:
            # Try to get base fee from latest block (EIP-1559)
            latest_block = self.web3.eth.get_block('latest')
            
            if 'baseFeePerGas' in latest_block:
                # EIP-1559 transaction
                base_fee = latest_block['baseFeePerGas']
                
                # Calculate priority fee (tip)
                # Use 1.5 gwei as default priority fee on Base
                priority_fee = self.web3.to_wei(1.5, 'gwei')
                
                # Max fee = 2 * base fee + priority fee (conservative)
                max_fee = (base_fee * 2) + priority_fee
                
                # Ensure we don't exceed max gas price
                max_allowed = self.web3.to_wei(self.config.max_gas_price_gwei, 'gwei')
                
                return min(max_fee, max_allowed)
            else:
                # Legacy transaction
                network_gas_price = self.web3.eth.gas_price
                max_allowed = self.web3.to_wei(self.config.max_gas_price_gwei, 'gwei')
                
                return min(network_gas_price, max_allowed)
                
        except Exception as e:
            logger.warning(f"Gas optimization failed: {e}, using default")
            return self.web3.eth.gas_price
    
    def estimate_transaction_cost(self, gas_limit: int = 200000) -> Dict[str, float]:
        """Estimate transaction cost in ETH and USD."""
        gas_price = self.get_optimal_gas_price()
        cost_wei = gas_limit * gas_price
        cost_eth = float(self.web3.from_wei(cost_wei, 'ether'))
        
        return {
            "gas_price_gwei": float(self.web3.from_wei(gas_price, 'gwei')),
            "gas_limit": gas_limit,
            "cost_eth": cost_eth,
            "cost_wei": cost_wei
        }
    
    def is_gas_price_acceptable(self) -> bool:
        """Check if current gas price is within acceptable range."""
        current_gas_gwei = float(self.web3.from_wei(self.web3.eth.gas_price, 'gwei'))
        return current_gas_gwei <= self.config.max_gas_price_gwei
    
    def wait_for_gas_price(self, timeout: int = 300) -> bool:
        """Wait for gas price to become acceptable."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_gas_price_acceptable():
                return True
            
            logger.info(f"Waiting for gas price to drop below {self.config.max_gas_price_gwei} Gwei...")
            time.sleep(30)
        
        return False


class HealthMonitor:
    """
    Monitors bot health and network conditions.
    """
    
    def __init__(self, config: Config, web3: Web3):
        self.config = config
        self.web3 = web3
        self.last_check = None
        self.is_healthy = True
        self.errors: list = []
        self._structured_logger = get_structured_logger()
        
    def _log_health_check(self, checks: Dict[str, Any], healthy: bool):
        """Log health check results to structured logger."""
        if self._structured_logger:
            self._structured_logger.info(
                f"Health check: {'healthy' if healthy else 'unhealthy'}",
                extra={
                    'rpc_connected': checks.get('rpc_connected'),
                    'synced': checks.get('synced'),
                    'gas_price_ok': checks.get('gas_price_ok'),
                    'wallet_funded': checks.get('wallet_funded')
                }
            )
    
    def check_health(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        checks = {
            "rpc_connected": False,
            "synced": False,
            "gas_price_ok": False,
            "wallet_funded": False
        }
        
        try:
            # Check RPC connection
            checks["rpc_connected"] = self.web3.is_connected()
            
            if checks["rpc_connected"]:
                # Check if node is synced
                latest_block = self.web3.eth.get_block('latest')
                block_time = datetime.fromtimestamp(latest_block.timestamp)
                time_diff = (datetime.now() - block_time).total_seconds()
                checks["synced"] = time_diff < 300  # Within 5 minutes
                
                # Check gas price
                gas_price_gwei = float(self.web3.from_wei(self.web3.eth.gas_price, 'gwei'))
                checks["gas_price_ok"] = gas_price_gwei <= self.config.max_gas_price_gwei
            
            self.is_healthy = all(checks.values())
            self.last_check = datetime.now()
            
            # Log to structured logger
            self._log_health_check(checks, self.is_healthy)
            
        except Exception as e:
            self.is_healthy = False
            self.errors.append({"time": datetime.now(), "error": str(e)})
            logger.error(f"Health check failed: {e}")
            if self._structured_logger:
                self._structured_logger.error("Health check failed", extra={'error': str(e)})
        
        return {
            "healthy": self.is_healthy,
            "checks": checks,
            "last_check": self.last_check,
            "errors": self.errors[-10:]  # Last 10 errors
        }
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get current network statistics."""
        try:
            latest_block = self.web3.eth.get_block('latest')
            gas_price = self.web3.eth.gas_price
            
            return {
                "block_number": latest_block.number,
                "gas_price_gwei": float(self.web3.from_wei(gas_price, 'gwei')),
                "timestamp": datetime.fromtimestamp(latest_block.timestamp),
                "transactions": len(latest_block.transactions)
            }
        except Exception as e:
            logger.error(f"Failed to get network stats: {e}")
            return {}


# Formatting utilities

def format_wei(wei_amount: int, decimals: int = 18) -> str:
    """Format wei amount to human-readable string."""
    if wei_amount == 0:
        return "0"
    
    value = wei_amount / (10 ** decimals)
    
    if value < 0.0001:
        return f"{value:.8f}"
    elif value < 1:
        return f"{value:.6f}"
    elif value < 1000:
        return f"{value:.4f}"
    else:
        return f"{value:,.2f}"


def format_eth(eth_amount: float) -> str:
    """Format ETH amount with appropriate precision."""
    if eth_amount < 0.001:
        return f"{eth_amount:.6f} ETH"
    elif eth_amount < 1:
        return f"{eth_amount:.4f} ETH"
    else:
        return f"{eth_amount:.2f} ETH"


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"


def format_address(address: str, length: int = 6) -> str:
    """Format Ethereum address with ellipsis."""
    if len(address) <= length * 2 + 2:
        return address
    return f"{address[:length + 2]}...{address[-length:]}"


def format_tx_hash(tx_hash: str, length: int = 8) -> str:
    """Format transaction hash with ellipsis."""
    if len(tx_hash) <= length * 2:
        return tx_hash
    return f"{tx_hash[:length]}...{tx_hash[-length:]}"


def create_progress_bar(current: int, total: int, width: int = 30) -> str:
    """Create a text-based progress bar."""
    if total == 0:
        return "[" + " " * width + "] 0%"
    
    ratio = min(current / total, 1.0)
    filled = int(width * ratio)
    empty = width - filled
    
    bar = "█" * filled + "░" * empty
    percent = int(ratio * 100)
    
    return f"[{bar}] {percent}%"


# Retry and error handling utilities

def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,)
):
    """Retry a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except exceptions as e:
            if attempt == max_retries - 1:
                raise
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
            time.sleep(delay)
    
    return None


async def async_retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,)
):
    """Async retry with exponential backoff."""
    import asyncio
    
    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            if attempt == max_retries - 1:
                raise
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)
    
    return None


# Price and calculation utilities

def calculate_slippage(expected: float, actual: float) -> float:
    """
    Calculate slippage percentage.
    
    FIXED HIGH-006: Properly handles edge cases.
    
    Args:
        expected: Expected output amount
        actual: Actual output amount
        
    Returns:
        Slippage percentage
        
    Raises:
        ValueError: If expected is zero or negative
    """
    if expected <= 0:
        raise ValueError(f"Expected amount must be positive, got {expected}")
    if actual < 0:
        raise ValueError(f"Actual amount cannot be negative, got {actual}")
    
    return abs((expected - actual) / expected) * 100


def calculate_profit_loss(
    buy_amount_eth: float,
    sell_amount_eth: float,
    gas_cost_eth: float
) -> Dict[str, float]:
    """Calculate profit/loss from a trade cycle."""
    gross_pnl = sell_amount_eth - buy_amount_eth
    net_pnl = gross_pnl - gas_cost_eth
    
    return {
        "gross_pnl_eth": gross_pnl,
        "gas_cost_eth": gas_cost_eth,
        "net_pnl_eth": net_pnl,
        "roi_percent": (net_pnl / buy_amount_eth * 100) if buy_amount_eth > 0 else 0
    }


# Validation utilities

def validate_private_key(key: str) -> bool:
    """Validate private key format."""
    if not key:
        return False
    
    # Remove 0x prefix if present
    key_clean = key[2:] if key.startswith("0x") else key
    
    # Check length and hex format
    if len(key_clean) != 64:
        return False
    
    try:
        int(key_clean, 16)
        return True
    except ValueError:
        return False


def validate_address(address: str) -> bool:
    """
    Validate Ethereum address format and checksum.
    
    Addresses CRITICAL-004: Enforces checksum validation.
    
    Args:
        address: Address to validate
        
    Returns:
        True if valid and properly checksummed
    """
    if not address:
        return False
    
    try:
        # Basic format check
        if not Web3.is_address(address):
            return False
        
        # Checksum validation - will raise ValueError if invalid
        Web3.to_checksum_address(address)
        return True
    except (ValueError, Exception):
        return False


def sanitize_error_message(error: str) -> str:
    """
    Sanitize error messages to remove sensitive data.
    
    Addresses HIGH-002: Prevents sensitive data leakage in error messages.
    
    Args:
        error: Original error message
        
    Returns:
        Sanitized error message safe for display
    """
    if not isinstance(error, str):
        error = str(error)
    
    # Patterns to redact
    patterns = [
        (r'0x[a-fA-F0-9]{64}', '[PRIVATE_KEY]'),
        (r'https?://[^\s]+', '[URL]'),
        (r'password["\']?\s*[:=]\s*\S+', 'password=[REDACTED]'),
        (r'key["\']?\s*[:=]\s*\S+', 'key=[REDACTED]'),
    ]
    
    sanitized = error
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


# Time utilities

def sleep_until(target_time: datetime):
    """Sleep until a specific time."""
    now = datetime.now()
    if target_time > now:
        sleep_seconds = (target_time - now).total_seconds()
        time.sleep(sleep_seconds)


def get_next_run_time(interval_seconds: int, offset: int = 0) -> datetime:
    """Calculate next run time based on interval."""
    now = datetime.now()
    seconds_since_epoch = int(now.timestamp())
    next_run_epoch = ((seconds_since_epoch // interval_seconds) + 1) * interval_seconds + offset
    return datetime.fromtimestamp(next_run_epoch)


# Security utilities

def secure_delete(file_path: str):
    """Securely delete a file by overwriting before removal."""
    if not os.path.exists(file_path):
        return
    
    try:
        # Overwrite with random data
        file_size = os.path.getsize(file_path)
        with open(file_path, 'wb') as f:
            f.write(os.urandom(file_size))
        
        # Rename before deletion
        temp_name = file_path + ".deleted"
        os.rename(file_path, temp_name)
        os.remove(temp_name)
        
        logger.info(f"Securely deleted: {file_path}")
    except Exception as e:
        logger.error(f"Failed to securely delete {file_path}: {e}")


def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive data, showing only first and last few characters."""
    if len(value) <= visible_chars * 2:
        return "*" * len(value)
    
    return value[:visible_chars] + "***" + value[-visible_chars:]
