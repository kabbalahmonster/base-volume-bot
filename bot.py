#!/usr/bin/env python3
"""
Complete Volume Bot Implementation
==================================
Production-ready volume generation bot for any token on Base.

Fixed Version - All critical issues resolved.
"""

import os
import sys
import json
import time
import logging
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Tuple
import getpass

# Web3 and crypto
from web3 import Web3
from eth_account import Account
from eth_abi import encode

# Rich CLI
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.logging import RichHandler

# Import wallet and DEX routers
from wallet import SecureKeyManager, SecureWallet
from oneinch_router import OneInchAggregator
from dex_router import MultiDEXRouter
from zerox_router import ZeroXAggregator

# Constants
COMPUTE_TOKEN = "0x696381f39F17cAD67032f5f52A4924ce84e51BA3"
WETH = "0x4200000000000000000000000000000000000006"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

RPC_URLS = {
    "base": [
        # NOTE: Rate limit considerations:
        # - mainnet.base.org: Official RPC, strict rate limits (429 errors common)
        # - base.drpc.org: Public dRPC, higher rate limits (preferred for testing)
        # - base.llamarpc.com: Returns empty contract code for some tokens (avoid)
        "https://base.drpc.org",
        "https://mainnet.base.org",
        "https://base.llamarpc.com",
    ]
}

# Uniswap V3 Router ABI (minimal)
ROUTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "internalType": "struct IV3SwapRouter.ExactInputSingleParams",
                "name": "params",
                "type": "tuple"
            }
        ],
        "name": "exactInputSingle",
        "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes[]", "name": "data", "type": "bytes[]"}
        ],
        "name": "multicall",
        "outputs": [{"internalType": "bytes[]", "name": "results", "type": "bytes[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "refundETH",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

# ERC20 ABI (minimal)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

console = Console()


@dataclass
class BotConfig:
    """Bot configuration"""
    chain: str = "base"
    buy_amount_eth: float = 0.002
    buy_interval_minutes: int = 5
    sell_after_buys: int = 10
    slippage_percent: float = 2.0
    max_gas_gwei: float = 0.5
    min_eth_balance: float = 0.001
    dry_run: bool = False
    log_level: str = "INFO"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BotConfig':
        return cls(**data)


class VolumeBot:
    """Main volume bot with integrated trading"""

    def __init__(self, config: BotConfig, private_key: str, token_address: str = COMPUTE_TOKEN):
        self.config = config
        self.private_key = private_key
        self.token_address = token_address
        self.token_symbol = "COMPUTE"  # Will be fetched from contract
        self.w3: Optional[Web3] = None
        self.account: Optional[Account] = None
        self.oneinch: Optional[OneInchAggregator] = None
        self.dex_router: Optional[MultiDEXRouter] = None
        self.token_contract = None

        # Stats
        self.buy_count = 0
        self.total_bought_eth = Decimal("0")
        self.total_bought_tokens = Decimal("0")
        self.successful_buys = 0
        self.failed_buys = 0

        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format="%(message)s",
            handlers=[
                RichHandler(console=console, rich_tracebacks=True),
                logging.FileHandler("volume_bot.log")
            ]
        )
        self.logger = logging.getLogger("VolumeBot")
    
    def connect(self) -> bool:
        """Connect to blockchain"""
        console.print("\n[bold cyan]🔗 Connecting to Base...[/bold cyan]")
        
        # Try multiple RPCs
        for rpc_url in RPC_URLS.get(self.config.chain, ["https://base.llamarpc.com"]):
            try:
                self.w3 = Web3(Web3.HTTPProvider(rpc_url))
                if self.w3.is_connected():
                    break
            except:
                continue
        
        if not self.w3 or not self.w3.is_connected():
            console.print("[red]✗ Failed to connect to any RPC[/red]")
            return False
        
        # Setup account
        try:
            self.account = Account.from_key(self.private_key)
        except Exception as e:
            console.print(f"[red]✗ Invalid private key: {e}[/red]")
            return False
        
        # Setup DEX routers (1inch primary, MultiDEX fallback)
        console.print("[dim]Initializing 1inch aggregator...[/dim]")
        self.oneinch = OneInchAggregator(self.w3, self.account)
        self.dex_router = MultiDEXRouter(self.w3, self.account, self.token_address)
        self.token_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.token_address),
            abi=ERC20_ABI
        )
        
        # Try to fetch token symbol
        try:
            self.token_symbol = self.token_contract.functions.symbol().call()
        except:
            self.token_symbol = "TOKEN"  # Fallback
        
        # Check balances
        eth_balance = self.get_eth_balance()
        token_balance = self.get_token_balance()
        
        console.print(f"[green]✓ Connected successfully[/green]")
        console.print(f"[dim]  Address: {self.account.address}[/dim]")
        console.print(f"[dim]  ETH Balance: {eth_balance:.4f} ETH[/dim]")
        console.print(f"[dim]  ${self.token_symbol} Balance: {token_balance:.4f}[/dim]")
        
        if eth_balance < self.config.min_eth_balance:
            console.print(f"[red]⚠ Low ETH balance! Need at least {self.config.min_eth_balance} ETH[/red]")
            return False
        
        return True
    
    def get_eth_balance(self) -> Decimal:
        """Get ETH balance"""
        if not self.w3 or not self.account:
            return Decimal("0")
        balance_wei = self.w3.eth.get_balance(self.account.address)
        return Decimal(self.w3.from_wei(balance_wei, 'ether'))
    
    def get_token_balance(self, token_address: str = None) -> Decimal:
        """Get token balance"""
        if not self.w3 or not self.account:
            return Decimal("0")
        
        # Use instance token if no address provided
        if token_address is None and self.token_contract:
            token = self.token_contract
        else:
            token_addr = token_address or self.token_address
            token = self.w3.eth.contract(
                address=self.w3.to_checksum_address(token_addr),
                abi=ERC20_ABI
            )
        
        balance = token.functions.balanceOf(self.account.address).call()
        decimals = token.functions.decimals().call()
        
        return Decimal(balance) / Decimal(10 ** decimals)
    
    def execute_buy(self) -> bool:
        """Execute buy transaction"""
        self.buy_count += 1
        
        console.print(f"\n[bold cyan]🛒 Buy Attempt {self.buy_count}/{self.config.sell_after_buys}[/bold cyan]")
        
        if self.config.dry_run:
            console.print("[yellow][DRY RUN] Simulating buy...[/yellow]")
            time.sleep(1)
            console.print("[green]✓ [DRY RUN] Buy simulated[/green]")
            return True
        
        try:
            amount_eth = Decimal(str(self.config.buy_amount_eth))
            
            # Check balance
            eth_balance = self.get_eth_balance()
            if eth_balance < amount_eth:
                console.print(f"[red]✗ Insufficient ETH balance[/red]")
                return False
            
            # Try 0x first if API key is configured, then 1inch, then multi-DEX
            use_zerox = hasattr(self.config, 'zerox_api_key') and self.config.zerox_api_key
            use_oneinch = hasattr(self.config, 'oneinch_api_key') and self.config.oneinch_api_key
            
            if use_zerox:
                console.print(f"[dim]Swapping {amount_eth} ETH for ${self.token_symbol} via 0x...[/dim]")
                zerox = ZeroXAggregator(self.w3, self.account, self.config.zerox_api_key)
                success, result = zerox.swap_eth_for_tokens(
                    self.token_address,
                    amount_eth,
                    slippage_percent=self.config.slippage_percent
                )
                if not success:
                    console.print(f"[yellow]⚠ 0x failed: {result}[/yellow]")
                    console.print(f"[dim]Falling back...[/dim]")
                else:
                    console.print(f"[green]✓ Buy successful via 0x![/green]")
                    console.print(f"[dim]  TX: {result[:20]}...[/dim]")
                    self.successful_buys += 1
                    self.total_bought_eth += amount_eth
                    return True
            
            if use_oneinch:
                console.print(f"[dim]Swapping {amount_eth} ETH for ${self.token_symbol} via 1inch...[/dim]")
                success, result = self.oneinch.swap_eth_for_tokens(
                    self.token_address,
                    amount_eth,
                    slippage_percent=self.config.slippage_percent
                )
                if not success:
                    console.print(f"[yellow]⚠ 1inch failed: {result}[/yellow]")
                    console.print(f"[dim]Falling back to multi-DEX router...[/dim]")
                else:
                    console.print(f"[green]✓ Buy successful via 1inch![/green]")
                    console.print(f"[dim]  TX: {result[:20]}...[/dim]")
                    self.successful_buys += 1
                    self.total_bought_eth += amount_eth
                    return True
            
            # Use multi-DEX router (direct swap)
            if (not use_zerox and not use_oneinch) or not success:
                console.print(f"[dim]Swapping {amount_eth} ETH for ${self.token_symbol} via multi-DEX router...[/dim]")
                success, result = self.dex_router.swap_eth_for_tokens(
                    amount_eth,
                    slippage_percent=self.config.slippage_percent
                )

            if success:
                console.print(f"[green]✓ Buy successful![/green]")
                console.print(f"[dim]  TX: {result[:20]}...[/dim]")
                self.successful_buys += 1
                self.total_bought_eth += amount_eth
                return True
            else:
                console.print(f"[red]✗ Transaction failed: {result}[/red]")
                self.failed_buys += 1
                return False
                
        except Exception as e:
            self.logger.error(f"Buy error: {e}")
            console.print(f"[red]✗ Buy failed: {e}[/red]")
            self.failed_buys += 1
            return False
    
    def execute_sell(self) -> bool:
        """Execute sell transaction"""
        console.print(f"\n[bold cyan]💰 Selling all ${self.token_symbol}...[/bold cyan]")
        
        if self.config.dry_run:
            console.print("[yellow][DRY RUN] Simulating sell...[/yellow]")
            time.sleep(1)
            console.print("[green]✓ [DRY RUN] Sell simulated[/green]")
            return True
        
        try:
            # Get COMPUTE balance
            compute_balance = self.get_token_balance()
            if compute_balance <= 0:
                console.print("[red]✗ No COMPUTE to sell[/red]")
                return False
            
            console.print(f"[dim]Selling {compute_balance:.4f} ${self.token_symbol}...[/dim]")
            
            # Execute swap using 1inch (primary) with fallback to multi-DEX router
            console.print(f"[dim]Swapping {compute_balance:.4f} ${self.token_symbol} for ETH via 1inch...[/dim]")

            # Get token decimals
            token_decimals = self.token_contract.functions.decimals().call()

            success, result = self.oneinch.swap_tokens_for_eth(
                self.token_address,
                compute_balance,
                token_decimals=token_decimals,
                slippage_percent=self.config.slippage_percent
            )

            if not success:
                console.print(f"[yellow]⚠ 1inch failed: {result}[/yellow]")
                console.print(f"[dim]Falling back to multi-DEX router...[/dim]")

                success, result = self.dex_router.swap_tokens_for_eth(
                    compute_balance,
                    slippage_percent=self.config.slippage_percent
                )

            if success:
                console.print(f"[green]✓ Sell successful![/green]")
                console.print(f"[dim]  TX: {result[:20]}...[/dim]")
                return True
            else:
                console.print(f"[red]✗ Sell failed: {result}[/red]")
                return False
                
        except Exception as e:
            self.logger.error(f"Sell error: {e}")
            console.print(f"[red]✗ Sell failed: {e}[/red]")
            return False
    
    def withdraw(self, to_address: str, amount_eth: Optional[float] = None, 
                 withdraw_compute: bool = False) -> bool:
        """
        Withdraw funds to external wallet
        
        Args:
            to_address: Destination wallet address
            amount_eth: Amount of ETH to withdraw (None = all except gas reserve)
            withdraw_compute: If True, also withdraw all tokens
        """
        console.print(f"\n[bold yellow]💸 WITHDRAWAL REQUEST[/bold yellow]")
        console.print(f"[dim]From: {self.account.address}[/dim]")
        console.print(f"[dim]To: {to_address}[/dim]")
        
        # Validate address
        if not Web3.is_address(to_address):
            console.print("[red]✗ Invalid destination address[/red]")
            return False
        
        to_address = Web3.to_checksum_address(to_address)
        
        if self.config.dry_run:
            console.print("[yellow][DRY RUN] Would withdraw funds[/yellow]")
            return True
        
        try:
            # Get current balances
            eth_balance = self.get_eth_balance()
            compute_balance = self.get_token_balance()
            
            console.print(f"\n[dim]Current Balances:[/dim]")
            console.print(f"  ETH: {eth_balance:.6f}")
            console.print(f"  ${self.token_symbol}: {compute_balance:.6f}")
            
            # Calculate withdrawal amount
            if amount_eth is None:
                # Leave 0.01 ETH for gas
                amount_eth = float(eth_balance) - 0.01
                if amount_eth <= 0:
                    console.print("[red]✗ Insufficient ETH for withdrawal (need to keep some for gas)[/red]")
                    return False
            
            amount_eth_decimal = Decimal(str(amount_eth))
            
            if amount_eth_decimal > eth_balance:
                console.print(f"[red]✗ Insufficient ETH balance[/red]")
                return False
            
            # Safety confirmation
            console.print(f"\n[yellow]⚠️ You are about to withdraw:[/yellow]")
            console.print(f"  {amount_eth_decimal:.6f} ETH")
            if withdraw_compute:
                console.print(f"  {compute_balance:.6f} ${self.token_symbol}")
            console.print(f"\n[yellow]To: {to_address}[/yellow]")
            
            confirm = input("\nType 'WITHDRAW' to confirm: ")
            if confirm != "WITHDRAW":
                console.print("[yellow]⚠️ Withdrawal cancelled[/yellow]")
                return False
            
            # Withdraw ETH
            if amount_eth_decimal > 0:
                console.print(f"\n[dim]Sending {amount_eth_decimal:.6f} ETH...[/dim]")
                
                tx = {
                    'to': to_address,
                    'value': self.w3.to_wei(amount_eth_decimal, 'ether'),
                    'gas': 21000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address),
                    'chainId': 8453
                }
                
                signed = self.account.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                console.print(f"[dim]TX: {self.w3.to_hex(tx_hash)}[/dim]")

                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

                if receipt['status'] == 1:
                    console.print(f"[green]✓ ETH sent: {self.w3.to_hex(tx_hash)[:20]}...[/green]")
                else:
                    console.print("[red]✗ ETH transfer failed[/red]")
                    console.print(f"[red]  Status: {receipt['status']}[/red]")
                    console.print(f"[red]  Gas used: {receipt['gasUsed']}[/red]")
                    console.print(f"[red]  Block: {receipt['blockNumber']}[/red]")
                    return False

            # Withdraw tokens
            if withdraw_compute and compute_balance > 0:
                console.print(f"\n[dim]Sending {compute_balance:.6f} ${self.token_symbol}...[/dim]")
                
                decimals = self.token_contract.functions.decimals().call()
                amount_units = int(compute_balance * (10 ** decimals))
                
                tx = self.token_contract.functions.transfer(to_address, amount_units).build_transaction({
                    'from': self.account.address,
                    'gas': 100000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address),
                    'chainId': 8453
                })
                
                signed = self.account.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                console.print(f"[dim]TX: {self.w3.to_hex(tx_hash)}[/dim]")

                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

                if receipt['status'] == 1:
                    console.print(f"[green]✓ $COMPUTE sent: {self.w3.to_hex(tx_hash)[:20]}...[/green]")
                else:
                    console.print("[red]✗ $COMPUTE transfer failed[/red]")
                    console.print(f"[red]  Status: {receipt['status']}[/red]")
                    console.print(f"[red]  Gas used: {receipt['gasUsed']}[/red]")
                    console.print(f"[red]  Block: {receipt['blockNumber']}[/red]")
                    return False
            
            console.print("\n[bold green]✓ Withdrawal complete![/bold green]")
            
            # Show remaining balance
            remaining_eth = self.get_eth_balance()
            remaining_compute = self.get_token_balance()
            console.print(f"\n[dim]Remaining Balances:[/dim]")
            console.print(f"  ETH: {remaining_eth:.6f}")
            console.print(f"  $COMPUTE: {remaining_compute:.6f}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Withdrawal error: {e}")
            console.print(f"[red]✗ Withdrawal failed: {e}[/red]")
            return False
    
    def show_stats(self):
        """Display current stats"""
        table = Table(title="Bot Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Buy Count", f"{self.buy_count}/{self.config.sell_after_buys}")
        table.add_row("Successful Buys", str(self.successful_buys))
        table.add_row("Failed Buys", str(self.failed_buys))
        table.add_row("Total ETH Spent", f"{self.total_bought_eth:.4f}")
        table.add_row("Dry Run", "Yes" if self.config.dry_run else "No")
        
        console.print(table)
    
    def countdown(self, minutes: int):
        """Show countdown timer"""
        total_seconds = minutes * 60
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Next buy in {minutes} minutes...", total=total_seconds)
            
            for _ in range(total_seconds):
                time.sleep(1)
                progress.advance(task)
    
    def run(self):
        """Main bot loop"""
        # Connect first to get token symbol
        if not self.connect():
            return
        
        # Now print banner with correct symbol
        console.print(Panel.fit(
            f"[bold cyan]${self.token_symbol} Volume Bot[/bold cyan]\n"
            "[dim]Cult of the Shell | Base Network[/dim]",
            box=box.DOUBLE
        ))
        
        # Show config
        console.print(f"\n[dim]Configuration:[/dim]")
        console.print(f"  Buy Amount: {self.config.buy_amount_eth} ETH")
        console.print(f"  Interval: {self.config.buy_interval_minutes} minutes")
        console.print(f"  Sell After: {self.config.sell_after_buys} buys")
        console.print(f"  Slippage: {self.config.slippage_percent}%")
        console.print(f"  Mode: {'DRY RUN' if self.config.dry_run else 'LIVE'}")
        
        self.show_stats()
        
        console.print("\n[bold green]🚀 Starting volume bot...[/bold green]")
        console.print("[dim]Press Ctrl+C to stop\n[/dim]")
        
        try:
            while True:
                # Execute buy
                if self.execute_buy():
                    self.show_stats()
                    
                    # Check if time to sell
                    if self.buy_count >= self.config.sell_after_buys:
                        console.print("\n[bold yellow]🎯 Target reached! Selling all...[/bold yellow]")
                        
                        if self.execute_sell():
                            console.print("[bold green]✓ Cycle complete! Restarting...[/bold green]")
                            self.buy_count = 0
                            self.successful_buys = 0
                            self.total_bought_eth = Decimal("0")
                            time.sleep(5)
                        else:
                            console.print("[red]✗ Sell failed. Continuing buys...[/red]")
                
                # Countdown to next buy
                self.countdown(self.config.buy_interval_minutes)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Bot stopped by user[/yellow]")
            self.show_stats()
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            console.print(f"\n[red]✗ Fatal error: {e}[/red]")


def setup_command():
    """Interactive setup - generates new wallet automatically"""
    console.print(Panel.fit(
        "[bold cyan]Volume Bot - Setup[/bold cyan]\n"
        "[dim]Auto-Generated Wallet Mode[/dim]",
        box=box.DOUBLE
    ))
    
    console.print("\n[yellow]⚠️  IMPORTANT:[/yellow]")
    console.print("This will generate a NEW trading wallet for you.")
    console.print("The private key will be encrypted - you will NOT see it.")
    console.print("You MUST fund the displayed address before running the bot.\n")
    
    confirm = input("Generate new trading wallet? (yes/no): ").lower()
    if confirm not in ['yes', 'y']:
        console.print("[yellow]Setup cancelled.[/yellow]")
        return
    
    # Generate new wallet
    import secrets
    from eth_account import Account
    
    # Generate with extra entropy for security
    extra_entropy = secrets.token_hex(32)
    account = Account.create(extra_entropy=extra_entropy)
    private_key = account.key.hex()
    wallet_address = account.address
    
    console.print(f"\n[green]✓ New wallet generated![/green]")
    console.print(f"\n[bold cyan]Your Wallet Address:[/bold cyan]")
    console.print(f"[bold]{wallet_address}[/bold]")
    console.print("\n[yellow]⚠️  FUND THIS ADDRESS BEFORE RUNNING THE BOT[/yellow]")
    console.print("Send ETH on Base network to the address above.")
    console.print("The bot needs ETH for gas and trading.\n")
    
    # Get password
    console.print("[yellow]Create encryption password (min 8 characters):[/yellow]")
    password = getpass.getpass("> ")
    
    if len(password) < 8:
        console.print("[red]Password must be at least 8 characters![/red]")
        return
    
    console.print("[yellow]Confirm password:[/yellow]")
    confirm_pw = getpass.getpass("> ")
    
    if password != confirm_pw:
        console.print("[red]Passwords don't match![/red]")
        return
    
    # Encrypt and save
    key_manager = SecureKeyManager()
    if key_manager.encrypt_and_save(private_key, password):
        console.print("\n[green]✓ Wallet encrypted and saved![/green]")
        
        # Create default config
        config = BotConfig()
        with open("bot_config.json", 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        
        console.print("[green]✓ Default config created (bot_config.json)[/green]")
        console.print("\n" + "="*60)
        console.print("[bold]NEXT STEPS:[/bold]")
        console.print("1. Fund this address with ETH on Base:")
        console.print(f"   {wallet_address}")
        console.print("2. Run: python bot.py balance (to verify funding)")
        console.print("3. Run: python bot.py run --dry-run (test mode)")
        console.print("4. Run: python bot.py run (live trading)")
        console.print("="*60)


def run_command(dry_run: bool = False, token_address: str = COMPUTE_TOKEN):
    """Run the bot"""
    # Load config
    try:
        with open("bot_config.json", 'r') as f:
            config_data = json.load(f)
        config = BotConfig.from_dict(config_data)
    except FileNotFoundError:
        console.print("[red]Config not found. Run 'setup' first.[/red]")
        return
    
    # Get password and load key
    console.print("[yellow]Enter wallet password:[/yellow]")
    password = getpass.getpass("> ")
    
    key_manager = SecureKeyManager()
    private_key = key_manager.load_and_decrypt(password)
    
    if not private_key:
        console.print("[red]Failed to decrypt wallet. Wrong password?[/red]")
        return
    
    # Override dry run
    if dry_run:
        config.dry_run = True
    
    # Run bot with specified token
    console.print(f"[dim]Trading token: {token_address}[/dim]")
    
    bot = VolumeBot(config, private_key, token_address)
    bot.run()


def withdraw_command(to_address: str, amount: Optional[float] = None, 
                     withdraw_compute: bool = False, dry_run: bool = False):
    """Withdraw funds to external wallet"""
    # Load config
    try:
        with open("bot_config.json", 'r') as f:
            config_data = json.load(f)
        config = BotConfig.from_dict(config_data)
    except FileNotFoundError:
        console.print("[red]Config not found. Run 'setup' first.[/red]")
        return
    
    # Get password and load key
    console.print("[yellow]Enter wallet password:[/yellow]")
    password = getpass.getpass("> ")
    
    key_manager = SecureKeyManager()
    private_key = key_manager.load_and_decrypt(password)
    
    if not private_key:
        console.print("[red]Failed to decrypt wallet. Wrong password?[/red]")
        return
    
    # Override dry run
    if dry_run:
        config.dry_run = True
    
    # Initialize bot (just for connection)
    bot = VolumeBot(config, private_key)
    if not bot.connect():
        return
    
    # Execute withdrawal
    bot.withdraw(to_address, amount, withdraw_compute)


def balance_command():
    """Check wallet balances"""
    # Load config
    try:
        with open("bot_config.json", 'r') as f:
            config_data = json.load(f)
        config = BotConfig.from_dict(config_data)
    except FileNotFoundError:
        console.print("[red]Config not found. Run 'setup' first.[/red]")
        return
    
    # Get password and load key
    console.print("[yellow]Enter wallet password:[/yellow]")
    password = getpass.getpass("> ")
    
    key_manager = SecureKeyManager()
    private_key = key_manager.load_and_decrypt(password)
    
    if not private_key:
        console.print("[red]Failed to decrypt wallet. Wrong password?[/red]")
        return
    
    # Initialize bot
    bot = VolumeBot(config, private_key)
    if not bot.connect():
        return
    
    # Show balances
    console.print("\n[bold cyan]💰 Wallet Balances[/bold cyan]")
    console.print(f"[dim]Address: {bot.account.address}[/dim]\n")
    
    table = Table(box=box.ROUNDED)
    table.add_column("Asset", style="cyan")
    table.add_column("Balance", style="green")
    
    eth_balance = bot.get_eth_balance()
    compute_balance = bot.get_token_balance()
    
    # Get token symbol from bot if possible, else default
    token_symbol = "COMPUTE"
    if bot.token_symbol:
        token_symbol = bot.token_symbol
    
    table.add_row("ETH", f"{eth_balance:.6f}")
    table.add_row(f"${token_symbol}", f"{compute_balance:.6f}")
    
    console.print(table)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Volume Bot for Base Network")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Initialize wallet and config")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Start trading bot")
    run_parser.add_argument("--dry-run", action="store_true", help="Simulation mode")
    run_parser.add_argument("--token-address", type=str, default=COMPUTE_TOKEN, 
                           help=f"Token address to trade (default: {COMPUTE_TOKEN})")
    
    # Withdraw command
    withdraw_parser = subparsers.add_parser("withdraw", help="Withdraw funds")
    withdraw_parser.add_argument("to", help="Destination wallet address")
    withdraw_parser.add_argument("--amount", type=float, help="ETH amount (omit for all)")
    withdraw_parser.add_argument("--compute", action="store_true", help="Also withdraw all tokens")
    withdraw_parser.add_argument("--dry-run", action="store_true", help="Simulation mode")
    
    # Balance command
    balance_parser = subparsers.add_parser("balance", help="Check wallet balances")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup_command()
    elif args.command == "run":
        run_command(dry_run=args.dry_run, token_address=args.token_address)
    elif args.command == "withdraw":
        withdraw_command(to_address=args.to, amount=args.amount, 
                        withdraw_compute=args.compute, dry_run=args.dry_run)
    elif args.command == "balance":
        balance_command()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
