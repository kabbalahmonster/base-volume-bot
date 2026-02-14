"""
$COMPUTE Volume Bot for Base Blockchain

A production-ready Python trading bot for generating volume on $COMPUTE token.

Usage:
    from volume_bot import ComputeTrader, Config, SecureWallet
    
    # See README.md for full documentation
"""

__version__ = "1.0.0"
__author__ = "OpenClaw Agent"
__license__ = "MIT"

from config import Config, ConfigManager
from wallet import SecureWallet
from trader import ComputeTrader
from utils import (
    logger,
    GasOptimizer,
    HealthMonitor,
    format_wei,
    format_eth,
    format_duration,
    TransactionError,
    InsufficientFundsError,
    GasPriceError,
)

__all__ = [
    "Config",
    "ConfigManager", 
    "SecureWallet",
    "ComputeTrader",
    "logger",
    "GasOptimizer",
    "HealthMonitor",
    "format_wei",
    "format_eth",
    "format_duration",
    "TransactionError",
    "InsufficientFundsError",
    "GasPriceError",
]
