#!/usr/bin/env python3
"""
Complete Volume Bot Implementation
=================================
Production-ready volume generation bot for $COMPUTE on Base.
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
from typing import Optional, Dict, Any
import getpass

# Web3 and crypto
from web3 import Web3
from eth_account import Account
from eth_abi import encode

# Encryption
from cryptography.fernet import Fernet
import hashlib
import base64

# Rich CLI
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.logging import RichHandler

# Import trader
from trader import UniswapV3Trader

# Constants
COMPUTE_TOKEN = "0x696381f39F17cAD67032f5f52A4924ce84e51BA3"
WETH = "0x4200000000000000000000000000000000000006"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
ROUTER = "0x2626664c2603336E57B271c5C0b26F421741e481"

RPC_URLS = {
    "base": [
        "https://base.llamarpc.com",
        "https://mainnet.base.org",
        "https://base.drpc.org",
    ]
}

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
    min_eth_balance: float = 0.01
    dry_run: bool = False
    log_level: str = "INFO"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BotConfig':
        return cls(**data)


class SecureKeyManager:
    """Manages encrypted private keys"""
    
    def __init__(self, key_file: str = ".wallet.enc"):
        self.key_file = Path(key_file)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        key = hashlib.sha256(password.encode()).digest()
        return base64.urlsafe_b64encode(key)
    
    def encrypt_and_save(self, private_key: str, password: str) -> bool:
        """Encrypt and save private key"""
        try:
            key = self._derive_key(password)
            f = Fernet(key)
            encrypted = f.encrypt(private_key.encode())
            
            data = {
                "encrypted": encrypted.decode(),
                "created": datetime.now().isoformat(),
            }
            
            with open(self.key_file, 'w') as file:
                json.dump(data, file)
            
            # Set restrictive permissions
            os.chmod(self.key_file, 0o600)
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to save wallet: {e}[/red]")
            return False
    
    def load_and_decrypt(self, password: str) -> Optional[str]:
        """Load and decrypt private key"""
        try:
            if not self.key_file.exists():
                return None
            
            with open(self.key_file, 'r') as file:
                data = json.load(file)
            
            key = self._derive_key(password)
            f = Fernet(key)
            decrypted = f.decrypt(data["encrypted"].encode())
            
            return decrypted.decode()
            
        except Exception as e:
            console.print(f"[red]Failed to decrypt wallet: {e}[/red]")
            return None


class VolumeBot:
    """Main volume bot"""
    
    def __init__(self, config: BotConfig, private_key: str):
        self.config = config
        self.private_key = private_key
        self.w3: Optional[Web3] = None
        self.account: Optional[Account] = None
        self.trader: Optional[UniswapV3Trader] = None
        
        # Stats
        self.buy_count = 0
        self.total_bought_eth = Decimal("0")
        self.total_bought_compute = Decimal("0")
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
            self.trader = UniswapV3Trader(self.w3, self.account, ROUTER)
        except Exception as e:
            console.print(f"[red]✗ Invalid private key: {e}[/red]")
            return False
        
        # Check balances
        eth_balance = self.trader.get_eth_balance()
        compute_balance = self.trader.get_token_balance(COMPUTE_TOKEN)
        
        console.print(f"[green]✓ Connected successfully[/green]")
        console.print(f"[dim]  Address: {self.account.address}[/dim]")
        console.print(f"[dim]  ETH Balance: {eth_balance:.4f} ETH[/dim]")
        console.print(f"[dim]  $COMPUTE Balance: {compute_balance:.4f}[/dim]")
        
        if eth_balance < self.config.min_eth_balance:
            console.print(f"[red]⚠ Low ETH balance! Need at least {self.config.min_eth_balance} ETH[/red]")
            return False
        
        return True
    
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
            eth_balance = self.trader.get_eth_balance()
            if eth_balance < amount_eth:
                console.print(f"[red]✗ Insufficient ETH balance[/red]")
                return False
            
            # Execute swap
            console.print(f"[dim]Swapping {amount_eth} ETH for $COMPUTE...[/dim]")
            
            success, result = self.trader.swap_eth_for_tokens(
                COMPUTE_TOKEN,
                amount_eth,
                self.config.slippage_percent
            )
            
            if success:
                console.print(f"[green]✓ Buy successful![/green]")
                console.print(f"[dim]  TX: {result[:20]}...{result[-8:]}[/dim]")
                self.successful_buys += 1
                self.total_bought_eth += amount_eth
                return True
            else:
                console.print(f"[red]✗ Buy failed: {result}[/red]")
                self.failed_buys += 1
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Buy error: {e}[/red]")
            self.logger.error(f"Buy error: {e}")
            self.failed_buys += 1
            return False
    
    def execute_sell(self) -> bool:
        """Execute sell all transaction"""
        console.print("\n[bold magenta]💰 SELLING ALL POSITIONS[/bold magenta]")
        
        if self.config.dry_run:
            console.print("[yellow][DRY RUN] Simulating sell...[/yellow]")
            time.sleep(1)
            console.print("[green]✓ [DRY RUN] Sell simulated[/green]")
            return True
        
        try:
            # Get current balance
            compute_balance = self.trader.get_token_balance(COMPUTE_TOKEN)
            
            if compute_balance <= 0:
                console.print("[yellow]⚠ No $COMPUTE to sell[/yellow]")
                return True
            
            console.print(f"[dim]Selling {compute_balance:.6f} $COMPUTE...[/dim]")
            
            success, result = self.trader.swap_tokens_for_eth(
                COMPUTE_TOKEN,
                compute_balance,
                self.config.slippage_percent
            )
            
            if success:
                console.print(f"[green]✓ Sell successful![/green]")
                console.print(f"[dim]  TX: {result[:20]}...{result[-8:]}[/dim]")
                return True
            else:
                console.print(f"[red]✗ Sell failed: {result}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Sell error: {e}[/red]")
            self.logger.error(f"Sell error: {e}")
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
    
    def withdraw(self, to_address: str, amount_eth: Optional[float] = None, 
                 withdraw_compute: bool = False) -> bool:
        """
        Withdraw funds to external wallet
        
        Args:
            to_address: Destination wallet address
            amount_eth: Amount of ETH to withdraw (None = all except gas reserve)
            withdraw_compute: If True, also withdraw all $COMPUTE
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
            eth_balance = self.trader.get_eth_balance()
            compute_balance = self.trader.get_token_balance(COMPUTE_TOKEN)
            
            console.print(f"\n[dim]Current Balances:[/dim]")
            console.print(f"  ETH: {eth_balance:.6f}")
            console.print(f"  $COMPUTE: {compute_balance:.6f}")
            
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
                console.print(f"  {compute_balance:.6f} $COMPUTE")
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
                
                signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
                tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
                
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt['status'] == 1:
                    console.print(f"[green]✓ ETH sent: {self.w3.to_hex(tx_hash)[:20]}...[/green]")
                else:
                    console.print("[red]✗ ETH transfer failed[/red]")
                    return False
            
            # Withdraw $COMPUTE
            if withdraw_compute and compute_balance > 0:
                console.print(f"\n[dim]Sending {compute_balance:.6f} $COMPUTE...[/dim]")
                
                token = self.trader.get_token_contract(COMPUTE_TOKEN)
                decimals = token.functions.decimals().call()
                amount_units = int(compute_balance * (10 ** decimals))
                
                tx = token.functions.transfer(to_address, amount_units).build_transaction({
                    'from': self.account.address,
                    'gas': 100000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.account.address),
                })
                
                signed = self.w3.eth.account.sign_transaction(tx, self.account.key)
                tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
                
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt['status'] == 1:
                    console.print(f"[green]✓ $COMPUTE sent: {self.w3.to_hex(tx_hash)[:20]}...[/green]")
                else:
                    console.print("[red]✗ $COMPUTE transfer failed[/red]")
                    return False
            
            console.print("\n[bold green]✓ Withdrawal complete![/bold green]")
            
            # Show remaining balance
            remaining_eth = self.trader.get_eth_balance()
            remaining_compute = self.trader.get_token_balance(COMPUTE_TOKEN)
            console.print(f"\n[dim]Remaining Balances:[/dim]")
            console.print(f"  ETH: {remaining_eth:.6f}")
            console.print(f"  $COMPUTE: {remaining_compute:.6f}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Withdrawal error: {e}")
            console.print(f"[red]✗ Withdrawal failed: {e}[/red]")
            return False
    
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
        console.print(Panel.fit(
            "[bold cyan]$COMPUTE Volume Bot[/bold cyan]\n"
            "[dim]Cult of the Shell | Base Network[/dim]",
            box=box.DOUBLE
        ))
        
        if not self.connect():
            return
        
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
    """Interactive setup with auto-generated wallet"""
    console.print(Panel.fit(
        "[bold cyan]$COMPUTE Volume Bot - Setup[/bold cyan]\n"
        "[dim]Auto-Generated Secure Wallet[/dim]",
        box=box.DOUBLE
    ))
    
    console.print("\n[dim]This will generate a new Ethereum wallet for trading.[/dim]")
    console.print("[dim]Your private key will be encrypted and never displayed.[/dim]\n")
    
    # Confirm wallet generation
    console.print("[yellow]Generate new trading wallet? (yes/no):[/yellow]")
    confirm_gen = input("> ").lower().strip()
    
    if confirm_gen not in ("yes", "y"):
        console.print("[yellow]Setup cancelled.[/yellow]")
        return
    
    # Generate new wallet
    console.print("\n[cyan]🔐 Generating new Ethereum wallet...[/cyan]")
    
    # Create account with extra entropy for security
    import secrets
    extra_entropy = secrets.token_hex(32)
    account = Account.create(extra_entropy=extra_entropy)
    
    private_key = account.key.hex()
    public_address = account.address
    
    console.print(f"[green]✓ Wallet generated successfully![/green]\n")
    
    # Display public address with clear funding instructions
    console.print(Panel(
        f"[bold cyan]📝 Your Trading Wallet Address[/bold cyan]\n\n"
        f"[bold]{public_address}[/bold]\n\n"
        f"[yellow]⚠️  IMPORTANT: Fund this address before running the bot![/yellow]\n"
        f"[dim]• Send ETH on Base network for trading and gas fees[/dim]\n"
        f"[dim]• Recommended minimum: 0.05 ETH[/dim]\n"
        f"[dim]• You can verify the address on basescan.org[/dim]",
        box=box.ROUNDED
    ))
    
    # Get password for encryption
    console.print("\n[yellow]Create encryption password to secure your wallet:[/yellow]")
    console.print("[dim](You will need this password every time you run the bot)[/dim]")
    password = getpass.getpass("> ")
    
    if len(password) < 8:
        console.print("[red]Password must be at least 8 characters![/red]")
        return
    
    console.print("[yellow]Confirm password:[/yellow]")
    confirm = getpass.getpass("> ")
    
    if password != confirm:
        console.print("[red]Passwords don't match![/red]")
        return
    
    # Encrypt and save
    key_manager = SecureKeyManager()
    if key_manager.encrypt_and_save(private_key, password):
        console.print("\n[green]✓ Wallet encrypted and saved securely![/green]")
        
        # Create default config
        config = BotConfig()
        with open("bot_config.json", 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        
        console.print("[green]✓ Default config created (bot_config.json)[/green]")
        
        # Show next steps
        console.print(Panel(
            f"[bold green]✓ Setup Complete![/bold green]\n\n"
            f"[cyan]Next Steps:[/cyan]\n"
            f"1. [yellow]Fund your wallet:[/yellow] Send ETH to {public_address}\n"
            f"2. [yellow]Test mode:[/yellow] python bot.py run --dry-run\n"
            f"3. [yellow]Run live:[/yellow] python bot.py run\n\n"
            f"[dim]Your private key is encrypted and cannot be recovered without your password.[/dim]\n"
            f"[dim]Wallet file: .wallet.enc (permissions: 600)[/dim]",
            box=box.DOUBLE
        ))


def run_command(dry_run: bool = False):
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
    
    # Run bot
    bot = VolumeBot(config, private_key)
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
    
    eth_balance = bot.trader.get_eth_balance()
    compute_balance = bot.trader.get_token_balance(COMPUTE_TOKEN)
    
    table.add_row("ETH", f"{eth_balance:.6f}")
    table.add_row("$COMPUTE", f"{compute_balance:.6f}")
    
    console.print(table)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="$COMPUTE Volume Bot")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Initialize wallet and config")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Start trading bot")
    run_parser.add_argument("--dry-run", action="store_true", help="Simulation mode")
    
    # Withdraw command
    withdraw_parser = subparsers.add_parser("withdraw", help="Withdraw funds")
    withdraw_parser.add_argument("to", help="Destination wallet address")
    withdraw_parser.add_argument("--amount", type=float, help="ETH amount (omit for all)")
    withdraw_parser.add_argument("--compute", action="store_true", help="Also withdraw all $COMPUTE")
    withdraw_parser.add_argument("--dry-run", action="store_true", help="Simulation mode")
    
    # Balance command
    balance_parser = subparsers.add_parser("balance", help="Check wallet balances")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup_command()
    elif args.command == "run":
        run_command(dry_run=args.dry_run)
    elif args.command == "withdraw":
        withdraw_command(to_address=args.to, amount=args.amount, 
                        withdraw_compute=args.compute, dry_run=args.dry_run)
    elif args.command == "balance":
        balance_command()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
