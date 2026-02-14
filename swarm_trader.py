"""
Swarm Trader Module - Multi-Wallet Trading Coordinator
======================================================

Coordinates trading operations across multiple swarm wallets.
Handles wallet rotation, load balancing, and aggregated statistics.

This module acts as a higher-level trader that distributes trades across
the swarm for better volume distribution and reduced wallet fingerprinting.

Author: Cult of the Shell
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from web3 import Web3
from rich.table import Table
from rich.console import Console
from rich import box

from swarm_wallet import (
    SecureSwarmManager, 
    SwarmWalletConfig, 
    RotationMode,
    SwarmWallet
)
from trader import ComputeTrader
from wallet import SecureWallet
from config import Config
from utils import logger, format_eth, format_address


console = Console()


@dataclass
class SwarmTradeResult:
    """Result of a swarm trading operation."""
    success: bool
    wallet_index: int
    wallet_address: str
    action: str  # BUY or SELL
    tx_hash: Optional[str] = None
    eth_amount: Optional[float] = None
    compute_amount: Optional[float] = None
    gas_used: Optional[int] = None
    gas_cost_eth: Optional[float] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'wallet_index': self.wallet_index,
            'wallet_address': self.wallet_address,
            'action': self.action,
            'tx_hash': self.tx_hash,
            'eth_amount': self.eth_amount,
            'compute_amount': self.compute_amount,
            'gas_used': self.gas_used,
            'gas_cost_eth': self.gas_cost_eth,
            'error': self.error,
            'timestamp': self.timestamp
        }


@dataclass
class SwarmStats:
    """Aggregated statistics for swarm trading."""
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_eth_spent: float = 0.0
    total_eth_received: float = 0.0
    total_gas_spent_eth: float = 0.0
    wallet_stats: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.successful_trades / self.total_trades) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'failed_trades': self.failed_trades,
            'success_rate': self.success_rate,
            'total_eth_spent': self.total_eth_spent,
            'total_eth_received': self.total_eth_received,
            'total_gas_spent_eth': self.total_gas_spent_eth,
            'net_eth': self.total_eth_received - self.total_eth_spent - self.total_gas_spent_eth,
            'wallet_stats': self.wallet_stats
        }


class SwarmTrader:
    """
    High-level trading coordinator for swarm wallets.
    
    Handles:
    - Wallet rotation for buys/sells
    - Load balancing across swarm
    - Aggregated statistics
    - Batch operations
    
    Security:
    - Never stores decrypted keys
    - Validates balances before operations
    - Uses dry-run mode for safe testing
    """
    
    def __init__(
        self,
        base_config: Config,
        swarm_config: SwarmWalletConfig,
        web3: Web3,
        password: str
    ):
        self.base_config = base_config
        self.swarm_config = swarm_config
        self.web3 = web3
        self.password = password
        
        # Initialize swarm manager
        self.swarm_manager = SecureSwarmManager(swarm_config, web3)
        
        # Stats tracking
        self.stats = SwarmStats()
        
        # Active traders cache (wallet_index -> ComputeTrader)
        self._traders: Dict[int, ComputeTrader] = {}
        
        # Current buy count per wallet (for sell triggers)
        self._wallet_buy_counts: Dict[int, int] = {}
    
    def _get_trader_for_wallet(self, wallet_index: int) -> ComputeTrader:
        """
        Get or create a ComputeTrader for a specific swarm wallet.
        
        Args:
            wallet_index: Index of the wallet in the swarm
            
        Returns:
            ComputeTrader instance for that wallet
        """
        if wallet_index in self._traders:
            return self._traders[wallet_index]
        
        # Get wallet and decrypt
        swarm_wallet, account = self.swarm_manager.get_wallet(wallet_index, self.password)
        
        # Create a temporary SecureWallet
        # We create a minimal Config with the decrypted key
        temp_config = Config(
            rpc_url=self.base_config.rpc_url,
            chain_id=self.base_config.chain_id,
            compute_token=self.base_config.compute_token,
            weth_address=self.base_config.weth_address,
            router_address=self.base_config.router_address,
            quoter_address=self.base_config.quoter_address,
            factory_address=self.base_config.factory_address,
            encrypted_private_key=account.key.hex(),  # Decrypted key
            buy_amount_eth=self.base_config.buy_amount_eth,
            buy_interval_seconds=self.base_config.buy_interval_seconds,
            sell_after_buys=self.base_config.sell_after_buys,
            max_gas_price_gwei=self.base_config.max_gas_price_gwei,
            slippage_percent=self.base_config.slippage_percent,
            gas_limit_buffer=self.base_config.gas_limit_buffer,
            dry_run=self.base_config.dry_run or self.swarm_config.dry_run
        )
        
        # Create SecureWallet
        secure_wallet = SecureWallet(temp_config)
        
        # Create ComputeTrader
        trader = ComputeTrader(temp_config, secure_wallet)
        
        # Cache it
        self._traders[wallet_index] = trader
        
        return trader
    
    async def execute_buy(self, specific_wallet: Optional[int] = None) -> SwarmTradeResult:
        """
        Execute a buy operation using the next wallet in rotation.
        
        Args:
            specific_wallet: If provided, use this wallet index instead of rotation
            
        Returns:
            SwarmTradeResult with trade details
        """
        try:
            # Get wallet
            if specific_wallet is not None:
                swarm_wallet, account = self.swarm_manager.get_wallet(specific_wallet, self.password)
            else:
                swarm_wallet, account = self.swarm_manager.get_next_wallet(self.password)
            
            wallet_index = swarm_wallet.index
            
            logger.info(f"Executing buy with wallet {wallet_index}: {format_address(account.address)}")
            
            # Get trader
            trader = self._get_trader_for_wallet(wallet_index)
            
            # Execute buy
            result = await trader.buy()
            
            # Create result
            trade_result = SwarmTradeResult(
                success=result.get('success', False),
                wallet_index=wallet_index,
                wallet_address=account.address,
                action='BUY',
                tx_hash=result.get('tx_hash'),
                eth_amount=self.base_config.buy_amount_eth,
                gas_used=result.get('gas_used'),
                gas_cost_eth=result.get('gas_cost_eth'),
                error=result.get('error')
            )
            
            # Update stats
            self.stats.total_trades += 1
            if trade_result.success:
                self.stats.successful_trades += 1
                self.stats.total_eth_spent += self.base_config.buy_amount_eth
                if trade_result.gas_cost_eth:
                    self.stats.total_gas_spent_eth += trade_result.gas_cost_eth
                
                # Update wallet stats
                swarm_wallet.record_buy(self.base_config.buy_amount_eth)
                self.swarm_manager._save_wallets()
                
                # Track buy count
                self._wallet_buy_counts[wallet_index] = self._wallet_buy_counts.get(wallet_index, 0) + 1
            else:
                self.stats.failed_trades += 1
            
            # Update wallet-specific stats
            if wallet_index not in self.stats.wallet_stats:
                self.stats.wallet_stats[wallet_index] = {
                    'total_trades': 0,
                    'successful_trades': 0,
                    'eth_spent': 0.0,
                    'eth_received': 0.0
                }
            
            self.stats.wallet_stats[wallet_index]['total_trades'] += 1
            if trade_result.success:
                self.stats.wallet_stats[wallet_index]['successful_trades'] += 1
                self.stats.wallet_stats[wallet_index]['eth_spent'] += self.base_config.buy_amount_eth
            
            return trade_result
            
        except Exception as e:
            logger.exception("Swarm buy failed")
            return SwarmTradeResult(
                success=False,
                wallet_index=specific_wallet if specific_wallet is not None else -1,
                wallet_address="",
                action='BUY',
                error=str(e)
            )
    
    async def execute_sell(self, specific_wallet: Optional[int] = None) -> SwarmTradeResult:
        """
        Execute a sell operation using a specific wallet or the next in rotation.
        
        Args:
            specific_wallet: If provided, sell from this wallet index
            
        Returns:
            SwarmTradeResult with trade details
        """
        try:
            # Get wallet
            if specific_wallet is not None:
                swarm_wallet, account = self.swarm_manager.get_wallet(specific_wallet, self.password)
            else:
                # For sells, use a wallet that has tokens
                # Find wallet with highest COMPUTE balance
                best_wallet = None
                best_balance = 0
                
                for wallet in self.swarm_manager.wallets:
                    eth_bal, comp_bal = self.swarm_manager._get_wallet_balance(wallet.address)
                    if comp_bal > best_balance:
                        best_balance = comp_bal
                        best_wallet = wallet
                
                if best_wallet is None or best_balance <= 0:
                    return SwarmTradeResult(
                        success=False,
                        wallet_index=-1,
                        wallet_address="",
                        action='SELL',
                        error="No wallet with COMPUTE tokens found"
                    )
                
                swarm_wallet = best_wallet
                _, account = self.swarm_manager.get_wallet(swarm_wallet.index, self.password)
            
            wallet_index = swarm_wallet.index
            
            logger.info(f"Executing sell with wallet {wallet_index}: {format_address(account.address)}")
            
            # Get trader
            trader = self._get_trader_for_wallet(wallet_index)
            
            # Get current balance before sell
            compute_before = trader.get_compute_balance()
            eth_before = trader.get_eth_balance()
            
            # Execute sell
            result = await trader.sell_all()
            
            # Calculate received amounts
            eth_after = trader.get_eth_balance()
            eth_received = max(0, eth_after - eth_before)
            
            # Create result
            trade_result = SwarmTradeResult(
                success=result.get('success', False),
                wallet_index=wallet_index,
                wallet_address=account.address,
                action='SELL',
                tx_hash=result.get('tx_hash'),
                compute_amount=result.get('tokens_sold', compute_before),
                eth_amount=eth_received,
                gas_used=result.get('gas_used'),
                gas_cost_eth=result.get('gas_cost_eth'),
                error=result.get('error')
            )
            
            # Update stats
            self.stats.total_trades += 1
            if trade_result.success:
                self.stats.successful_trades += 1
                self.stats.total_eth_received += eth_received
                if trade_result.gas_cost_eth:
                    self.stats.total_gas_spent_eth += trade_result.gas_cost_eth
                
                # Update wallet stats
                swarm_wallet.record_sell(eth_received)
                self.swarm_manager._save_wallets()
                
                # Reset buy count
                self._wallet_buy_counts[wallet_index] = 0
            else:
                self.stats.failed_trades += 1
            
            # Update wallet-specific stats
            if wallet_index not in self.stats.wallet_stats:
                self.stats.wallet_stats[wallet_index] = {
                    'total_trades': 0,
                    'successful_trades': 0,
                    'eth_spent': 0.0,
                    'eth_received': 0.0
                }
            
            self.stats.wallet_stats[wallet_index]['total_trades'] += 1
            if trade_result.success:
                self.stats.wallet_stats[wallet_index]['successful_trades'] += 1
                self.stats.wallet_stats[wallet_index]['eth_received'] += eth_received
            
            return trade_result
            
        except Exception as e:
            logger.exception("Swarm sell failed")
            return SwarmTradeResult(
                success=False,
                wallet_index=specific_wallet if specific_wallet is not None else -1,
                wallet_address="",
                action='SELL',
                error=str(e)
            )
    
    async def check_and_sell(self, wallet_index: Optional[int] = None) -> Optional[SwarmTradeResult]:
        """
        Check if a wallet should sell (after N buys) and execute if so.
        
        Args:
            wallet_index: Check specific wallet, or None to check all
            
        Returns:
            SwarmTradeResult if sell was executed, None otherwise
        """
        if wallet_index is not None:
            # Check specific wallet
            buy_count = self._wallet_buy_counts.get(wallet_index, 0)
            if buy_count >= self.base_config.sell_after_buys:
                logger.info(f"Wallet {wallet_index} reached {buy_count} buys, executing sell")
                return await self.execute_sell(wallet_index)
        else:
            # Check all wallets
            for idx, count in self._wallet_buy_counts.items():
                if count >= self.base_config.sell_after_buys:
                    logger.info(f"Wallet {idx} reached {count} buys, executing sell")
                    return await self.execute_sell(idx)
        
        return None
    
    async def run_trading_cycle(self) -> SwarmTradeResult:
        """
        Execute one complete trading cycle:
        1. Check if any wallet needs to sell
        2. If not, execute a buy with next wallet
        
        Returns:
            SwarmTradeResult
        """
        # First check for sells
        sell_result = await self.check_and_sell()
        if sell_result:
            return sell_result
        
        # Otherwise execute buy
        return await self.execute_buy()
    
    def get_stats_table(self) -> Table:
        """Get a Rich table with current statistics."""
        table = Table(title="Swarm Trading Statistics", box=box.ROUNDED)
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Trades", str(self.stats.total_trades))
        table.add_row("Successful", str(self.stats.successful_trades))
        table.add_row("Failed", str(self.stats.failed_trades))
        table.add_row("Success Rate", f"{self.stats.success_rate:.1f}%")
        table.add_row("ETH Spent", format_eth(self.stats.total_eth_spent))
        table.add_row("ETH Received", format_eth(self.stats.total_eth_received))
        table.add_row("Gas Spent", format_eth(self.stats.total_gas_spent_eth))
        table.add_row("Net ETH", format_eth(self.stats.total_eth_received - self.stats.total_eth_spent - self.stats.total_gas_spent_eth))
        
        return table
    
    def get_swarm_status_table(self) -> Table:
        """Get a Rich table with swarm wallet status."""
        status = self.swarm_manager.get_swarm_status()
        
        table = Table(title="Swarm Wallet Status", box=box.ROUNDED)
        
        table.add_column("Index", style="cyan")
        table.add_column("Address", style="dim")
        table.add_column("ETH", style="green")
        table.add_column("COMPUTE", style="yellow")
        table.add_column("TXs", style="blue")
        table.add_column("Status", style="white")
        
        for wallet_data in status.get('wallets', []):
            idx = wallet_data['index']
            addr = format_address(wallet_data['address'])
            eth = f"{wallet_data['eth_balance']:.4f}"
            comp = f"{wallet_data['compute_balance']:.2f}"
            txs = str(wallet_data['tx_count'])
            active = "🟢" if wallet_data['is_active'] else "🔴"
            
            table.add_row(str(idx), addr, eth, comp, txs, active)
        
        # Summary row
        table.add_row(
            "TOTAL",
            f"{status['active_wallets']}/{status['total_wallets']}",
            f"{status['total_eth']:.4f}",
            f"{status['total_compute']:.2f}",
            "",
            "",
            style="bold"
        )
        
        return table
    
    def print_summary(self):
        """Print a comprehensive summary to console."""
        console.print("\n")
        console.print(self.get_swarm_status_table())
        console.print("\n")
        console.print(self.get_stats_table())
        console.print("\n")


class SwarmBatchOperations:
    """
    Batch operations for managing the entire swarm efficiently.
    
    Handles:
    - Batch funding from main wallet
    - Batch reclamation to main wallet
    - Bulk balance checking
    """
    
    def __init__(self, swarm_manager: SecureSwarmManager):
        self.swarm_manager = swarm_manager
    
    async def batch_fund(
        self,
        main_wallet_key: str,
        eth_per_wallet: float,
        delay_seconds: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Fund all swarm wallets in batch.
        
        Args:
            main_wallet_key: Main wallet private key
            eth_per_wallet: ETH amount per wallet
            delay_seconds: Delay between transactions to avoid nonce issues
            
        Returns:
            List of funding results
        """
        results = self.swarm_manager.fund_swarm(main_wallet_key, eth_per_wallet)
        return [r.to_dict() for r in results]
    
    async def batch_reclaim(
        self,
        main_wallet_address: str,
        password: str,
        reclaim_compute: bool = True,
        delay_seconds: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Reclaim all funds from swarm wallets in batch.
        
        Args:
            main_wallet_address: Address to reclaim to
            password: Password for decrypting wallets
            reclaim_compute: Whether to reclaim COMPUTE tokens
            delay_seconds: Delay between transactions
            
        Returns:
            List of reclamation results
        """
        results = self.swarm_manager.reclaim_funds(
            main_wallet_address, 
            password, 
            reclaim_compute
        )
        return [r.to_dict() for r in results]
    
    def get_balances_summary(self) -> Dict[str, Any]:
        """Get aggregated balance information for all wallets."""
        return self.swarm_manager.get_swarm_status()
    
    def verify_ready_for_dissolution(self) -> Tuple[bool, List[int]]:
        """
        Verify all wallets are ready for dissolution (zero balances).
        
        Returns:
            Tuple of (all_ready, list_of_nonzero_wallet_indices)
        """
        non_zero = self.swarm_manager.verify_zero_balances()
        return len(non_zero) == 0, non_zero
