#!/usr/bin/env python3
"""
Swarm Wallet CLI - Command Line Interface for Swarm Operations
==============================================================

Provides an interactive CLI for:
- Creating and managing swarm wallets
- Funding wallets from main wallet
- Executing trades across the swarm
- Reclaiming funds to main wallet
- Monitoring swarm status

Usage:
    python swarm_cli.py create --count 10
    python swarm_cli.py fund --main-key 0x... --amount 0.02
    python swarm_cli.py run --password mypassword
    python swarm_cli.py reclaim --main-address 0x... --password mypassword
    python swarm_cli.py status

Author: Cult of the Shell
"""

import os
import sys
import json
import argparse
import getpass
from pathlib import Path
from typing import Optional

from web3 import Web3
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import swarm modules
from swarm_wallet import (
    SecureSwarmManager,
    SwarmWalletConfig,
    RotationMode,
    SwarmWallet
)
from swarm_trader import SwarmTrader, SwarmBatchOperations
from config import Config, ConfigManager

console = Console()


def print_banner():
    """Print the CLI banner."""
    banner = """
    🦑 $COMPUTE Swarm Wallet Manager 🦑
    ═══════════════════════════════════
    Multi-wallet volume generation system
    """
    console.print(Panel(banner, style="bold cyan", box=box.DOUBLE))


def get_password(prompt: str = "Enter swarm password: ") -> str:
    """Securely get password from user."""
    console.print(f"[yellow]{prompt}[/yellow]")
    password = getpass.getpass("> ")
    
    if len(password) < 8:
        console.print("[red]Password must be at least 8 characters[/red]")
        sys.exit(1)
    
    return password


def get_main_wallet_key() -> str:
    """Securely get main wallet private key."""
    console.print("[yellow]Enter main wallet private key (with 0x prefix):[/yellow]")
    key = getpass.getpass("> ")
    
    if not key.startswith("0x"):
        console.print("[red]Private key must start with 0x[/red]")
        sys.exit(1)
    
    return key


def create_swarm_command(args):
    """Handle create command - generate new swarm wallets."""
    print_banner()
    
    console.print(f"\n[bold cyan]Creating {args.count} swarm wallets...[/bold cyan]\n")
    
    # Get password
    password = get_password("Create encryption password: ")
    console.print("[yellow]Confirm password:[/yellow]")
    confirm = getpass.getpass("> ")
    
    if password != confirm:
        console.print("[red]Passwords don't match![/red]")
        return
    
    # Setup config
    config = SwarmWalletConfig(
        num_wallets=args.count,
        key_file=args.key_file,
        audit_log=args.audit_log,
        dry_run=args.dry_run
    )
    
    # Connect to Base
    web3 = Web3(Web3.HTTPProvider(args.rpc))
    if not web3.is_connected():
        console.print("[red]Failed to connect to Base network[/red]")
        return
    
    # Create swarm manager
    manager = SecureSwarmManager(config, web3)
    
    # Create wallets
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating wallets...", total=None)
        
        wallets = manager.create_swarm(password, args.count)
        progress.update(task, completed=True)
    
    # Display results
    table = Table(title=f"Created {len(wallets)} Swarm Wallets", box=box.ROUNDED)
    table.add_column("Index", style="cyan")
    table.add_column("Address", style="green")
    table.add_column("Created", style="dim")
    
    for wallet in wallets:
        table.add_row(
            str(wallet.index),
            wallet.address,
            wallet.created_at[:19]
        )
    
    console.print(table)
    console.print(f"\n[green]✓ Swarm wallets saved to: {args.key_file}[/green]")
    console.print(f"[dim]  Keep this file secure - it contains encrypted keys[/dim]")
    
    # Show funding command
    console.print(f"\n[bold]Next step:[/bold] Fund the swarm")
    console.print(f"  python swarm_cli.py fund --main-key <KEY> --amount 0.02")


def fund_swarm_command(args):
    """Handle fund command - fund swarm from main wallet."""
    print_banner()
    
    console.print(f"\n[bold cyan]Funding swarm wallets...[/bold cyan]\n")
    
    # Get main wallet key
    if not args.main_key:
        main_key = get_main_wallet_key()
    else:
        main_key = args.main_key
    
    # Setup config
    config = SwarmWalletConfig(
        key_file=args.key_file,
        audit_log=args.audit_log,
        dry_run=args.dry_run
    )
    
    # Connect to Base
    web3 = Web3(Web3.HTTPProvider(args.rpc))
    if not web3.is_connected():
        console.print("[red]Failed to connect to Base network[/red]")
        return
    
    # Create manager
    manager = SecureSwarmManager(config, web3)
    
    if not manager.wallets:
        console.print("[red]No swarm wallets found. Run 'create' first.[/red]")
        return
    
    # Check main wallet balance
    from eth_account import Account
    main_account = Account.from_key(main_key)
    balance = web3.eth.get_balance(main_account.address)
    balance_eth = float(web3.from_wei(balance, 'ether'))
    
    total_needed = args.amount * len(manager.wallets)
    
    console.print(f"Main wallet: {main_account.address}")
    console.print(f"Balance: {balance_eth:.4f} ETH")
    console.print(f"Wallets to fund: {len(manager.wallets)}")
    console.print(f"Amount per wallet: {args.amount} ETH")
    console.print(f"Total needed: {total_needed:.4f} ETH")
    console.print(f"Gas reserve: ~0.01 ETH")
    
    if balance_eth < total_needed + 0.01:
        console.print(f"\n[red]Insufficient balance! Need {total_needed + 0.01:.4f} ETH[/red]")
        return
    
    if args.dry_run:
        console.print(f"\n[yellow][DRY RUN] Would fund {len(manager.wallets)} wallets[/yellow]")
        return
    
    # Confirm
    console.print(f"\n[yellow]This will send {total_needed:.4f} ETH to {len(manager.wallets)} wallets[/yellow]")
    confirm = input("Type 'FUND' to confirm: ")
    
    if confirm != "FUND":
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    # Fund wallets
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Funding wallets...", total=len(manager.wallets))
        
        results = manager.fund_swarm(main_key, args.amount)
        
        for i, result in enumerate(results):
            progress.update(task, advance=1)
    
    # Display results
    table = Table(title="Funding Results", box=box.ROUNDED)
    table.add_column("Wallet", style="cyan")
    table.add_column("Address", style="dim")
    table.add_column("Amount", style="green")
    table.add_column("Status", style="white")
    
    success_count = 0
    for i, result in enumerate(results):
        wallet = manager.wallets[i]
        status = "[green]✓[/green]" if result.status == "SUCCESS" else "[red]✗[/red]"
        if result.status == "SUCCESS":
            success_count += 1
        
        table.add_row(
            str(i),
            wallet.address[:20] + "...",
            f"{args.amount} ETH",
            status
        )
    
    console.print(table)
    console.print(f"\n[green]✓ Successfully funded {success_count}/{len(results)} wallets[/green]")


def status_command(args):
    """Handle status command - show swarm status."""
    print_banner()
    
    # Setup config
    config = SwarmWalletConfig(
        key_file=args.key_file,
        audit_log=args.audit_log
    )
    
    # Connect to Base
    web3 = Web3(Web3.HTTPProvider(args.rpc))
    if not web3.is_connected():
        console.print("[red]Failed to connect to Base network[/red]")
        return
    
    # Create manager
    manager = SecureSwarmManager(config, web3)
    
    if not manager.wallets:
        console.print("[yellow]No swarm wallets found. Run 'create' first.[/yellow]")
        return
    
    # Get status
    status = manager.get_swarm_status()
    
    # Display summary
    summary = Panel(
        f"Total Wallets: {status['total_wallets']}\n"
        f"Active Wallets: {status['active_wallets']}\n"
        f"Total ETH: {status['total_eth']:.6f}\n"
        f"Total COMPUTE: {status['total_compute']:.2f}\n"
        f"Rotation Mode: {status['rotation_mode']}",
        title="Swarm Summary",
        border_style="cyan"
    )
    console.print(summary)
    
    # Display wallet table
    table = Table(title="Wallet Details", box=box.ROUNDED)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Address", style="dim")
    table.add_column("ETH", style="green", justify="right")
    table.add_column("COMPUTE", style="yellow", justify="right")
    table.add_column("TXs", style="blue", justify="right")
    table.add_column("Active", style="white", width=6)
    
    for wallet_data in status['wallets']:
        idx = wallet_data['index']
        addr = wallet_data['address'][:16] + "..." + wallet_data['address'][-8:]
        eth = f"{wallet_data['eth_balance']:.6f}"
        comp = f"{wallet_data['compute_balance']:.2f}"
        txs = str(wallet_data['tx_count'])
        active = "🟢" if wallet_data['is_active'] else "🔴"
        
        table.add_row(str(idx), addr, eth, comp, txs, active)
    
    console.print(table)
    
    # Show audit trail if requested
    if args.show_audit:
        console.print("\n[bold]Recent Audit Trail:[/bold]")
        audit_records = manager.get_audit_trail(limit=10)
        
        audit_table = Table(box=box.ROUNDED)
        audit_table.add_column("Time", style="dim")
        audit_table.add_column("Action", style="cyan")
        audit_table.add_column("Wallet", style="white")
        audit_table.add_column("Status", style="green")
        
        for record in audit_records:
            time_str = record.timestamp[11:19] if len(record.timestamp) > 19 else record.timestamp
            wallet_idx = str(record.wallet_index) if record.wallet_index is not None else "-"
            status = "[green]✓[/green]" if record.status == "SUCCESS" else "[red]✗[/red]"
            
            audit_table.add_row(time_str, record.action, wallet_idx, status)
        
        console.print(audit_table)


def reclaim_command(args):
    """Handle reclaim command - reclaim all funds to main wallet."""
    print_banner()
    
    console.print(f"\n[bold yellow]⚠️  RECLAIMING ALL FUNDS ⚠️[/bold yellow]\n")
    
    # Validate main address
    if not args.main_address or not Web3.is_address(args.main_address):
        console.print("[red]Invalid or missing main wallet address[/red]")
        return
    
    main_address = Web3.to_checksum_address(args.main_address)
    
    # Get password
    password = get_password()
    
    # Setup config
    config = SwarmWalletConfig(
        key_file=args.key_file,
        audit_log=args.audit_log,
        dry_run=args.dry_run
    )
    
    # Connect to Base
    web3 = Web3(Web3.HTTPProvider(args.rpc))
    if not web3.is_connected():
        console.print("[red]Failed to connect to Base network[/red]")
        return
    
    # Create manager
    manager = SecureSwarmManager(config, web3)
    
    if not manager.wallets:
        console.print("[red]No swarm wallets found.[/red]")
        return
    
    # Get current balances
    status = manager.get_swarm_status()
    
    console.print(f"[bold]Reclaim destination:[/bold] {main_address}")
    console.print(f"[bold]Wallets to reclaim:[/bold] {len(manager.wallets)}")
    console.print(f"[bold]Total ETH in swarm:[/bold] {status['total_eth']:.6f} ETH")
    console.print(f"[bold]Total COMPUTE in swarm:[/bold] {status['total_compute']:.2f}")
    
    if args.dry_run:
        console.print(f"\n[yellow][DRY RUN] Would reclaim all funds[/yellow]")
        return
    
    # Safety check: verify we can decrypt at least one wallet
    try:
        test_wallet, _ = manager.get_wallet(0, password)
        console.print("[green]✓ Password verified[/green]")
    except Exception as e:
        console.print(f"[red]Password verification failed: {e}[/red]")
        return
    
    # Multiple confirmations for safety
    console.print(f"\n[yellow]⚠️  This will transfer ALL funds from {len(manager.wallets)} wallets to {main_address}[/yellow]")
    console.print("[red]This action cannot be undone![/red]")
    
    confirm1 = input("\nType 'RECLAIM' to continue: ")
    if confirm1 != "RECLAIM":
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    # Reclaim funds
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Reclaiming funds...", total=len(manager.wallets))
        
        results = manager.reclaim_funds(main_address, password, args.compute)
        progress.update(task, completed=True)
    
    # Display results
    table = Table(title="Reclamation Results", box=box.ROUNDED)
    table.add_column("Wallet", style="cyan")
    table.add_column("Action", style="white")
    table.add_column("ETH", style="green")
    table.add_column("COMPUTE", style="yellow")
    table.add_column("Status", style="white")
    
    success_count = 0
    for result in results:
        status = "[green]✓[/green]" if result.status == "SUCCESS" else "[red]✗[/red]"
        if result.status == "SUCCESS":
            success_count += 1
        
        eth = f"{result.eth_amount:.6f}" if result.eth_amount else "-"
        comp = f"{result.compute_amount:.2f}" if result.compute_amount else "-"
        
        table.add_row(
            str(result.wallet_index) if result.wallet_index is not None else "-",
            result.action,
            eth,
            comp,
            status
        )
    
    console.print(table)
    console.print(f"\n[green]✓ Reclamation complete: {success_count}/{len(results)} operations successful[/green]")
    
    # Check for non-zero balances
    non_zero = manager.verify_zero_balances()
    if non_zero:
        console.print(f"\n[yellow]⚠️  Wallets with non-zero balances: {non_zero}[/yellow]")
        console.print("[dim]Run reclaim again or check manually[/dim]")


def rotate_mode_command(args):
    """Handle rotation mode command - set wallet rotation strategy."""
    print_banner()
    
    # Validate mode
    try:
        new_mode = RotationMode(args.mode)
    except ValueError:
        console.print(f"[red]Invalid rotation mode: {args.mode}[/red]")
        console.print(f"Valid modes: {[m.value for m in RotationMode]}")
        return
    
    # Setup config
    config = SwarmWalletConfig(
        key_file=args.key_file,
        audit_log=args.audit_log
    )
    
    # Connect to Base
    web3 = Web3(Web3.HTTPProvider(args.rpc))
    
    # Create manager
    manager = SecureSwarmManager(config, web3)
    
    # Update mode
    manager.config.rotation_mode = new_mode
    manager._save_wallets()
    
    console.print(f"[green]✓ Rotation mode set to: {new_mode.value}[/green]")
    
    # Show explanation
    explanations = {
        RotationMode.ROUND_ROBIN: "Wallets are used in sequence (0, 1, 2, ...)",
        RotationMode.RANDOM: "Wallets are selected randomly",
        RotationMode.LEAST_USED: "Wallet with fewest transactions is selected",
        RotationMode.BALANCE_BASED: "Wallet with highest ETH balance is selected"
    }
    console.print(f"[dim]{explanations[new_mode]}[/dim]")


def run_command(args):
    """Handle run command - run trading bot with swarm."""
    print_banner()
    
    console.print("\n[bold cyan]Starting Swarm Trading Bot...[/bold cyan]\n")
    
    # Get password
    password = get_password()
    
    # Load base config
    try:
        config_manager = ConfigManager(Path(args.config))
        # We need to decrypt to get the base config, but we don't have the password for that here
        # So we'll load raw and create a default config
        raw_config = config_manager.read_raw_config()
        base_config = Config.from_dict(raw_config)
    except Exception as e:
        console.print(f"[yellow]Could not load config file: {e}[/yellow]")
        console.print("[dim]Using default configuration[/dim]")
        base_config = Config()
    
    # Override dry run if specified
    if args.dry_run:
        base_config.dry_run = True
    
    # Setup swarm config
    swarm_config = SwarmWalletConfig(
        key_file=args.key_file,
        audit_log=args.audit_log,
        rotation_mode=RotationMode(args.rotation) if args.rotation else RotationMode.ROUND_ROBIN,
        dry_run=args.dry_run
    )
    
    # Connect to Base
    web3 = Web3(Web3.HTTPProvider(args.rpc))
    if not web3.is_connected():
        console.print("[red]Failed to connect to Base network[/red]")
        return
    
    # Create swarm manager to verify wallets exist
    swarm_manager = SecureSwarmManager(swarm_config, web3)
    
    if not swarm_manager.wallets:
        console.print("[red]No swarm wallets found. Run 'create' and 'fund' first.[/red]")
        return
    
    try:
        # Test decrypt first wallet
        test_wallet, _ = swarm_manager.get_wallet(0, password)
        console.print(f"[green]✓ Decrypted {len(swarm_manager.wallets)} wallets[/green]")
    except Exception as e:
        console.print(f"[red]Password verification failed: {e}[/red]")
        return
    
    # Create swarm trader
    try:
        swarm_trader = SwarmTrader(base_config, swarm_config, web3, password)
    except Exception as e:
        console.print(f"[red]Failed to initialize swarm trader: {e}[/red]")
        return
    
    console.print(f"[green]✓ Swarm trader initialized[/green]")
    console.print(f"[dim]Rotation mode: {swarm_config.rotation_mode.value}[/dim]")
    console.print(f"[dim]Dry run: {'Yes' if args.dry_run else 'No'}[/dim]")
    
    # Show initial status
    swarm_trader.print_summary()
    
    if args.dry_run:
        console.print("[yellow][DRY RUN MODE] No real transactions will be executed[/yellow]\n")
    
    # Run trading loop
    console.print("[bold green]Starting trading loop...[/bold green]")
    console.print("[dim]Press Ctrl+C to stop\n[/dim]")
    
    import asyncio
    
    async def trading_loop():
        import time
        
        try:
            while True:
                # Execute trading cycle
                result = await swarm_trader.run_trading_cycle()
                
                if result.success:
                    console.print(
                        f"[green]✓ {result.action} with wallet {result.wallet_index}: "
                        f"{result.tx_hash[:20]}...[/green]"
                    )
                else:
                    console.print(
                        f"[red]✗ {result.action} failed with wallet {result.wallet_index}: "
                        f"{result.error}[/red]"
                    )
                
                # Show stats periodically
                if swarm_trader.stats.total_trades % 5 == 0:
                    swarm_trader.print_summary()
                
                # Wait for next cycle
                console.print(f"[dim]Waiting {base_config.buy_interval_seconds} seconds...[/dim]")
                await asyncio.sleep(base_config.buy_interval_seconds)
                
        except asyncio.CancelledError:
            console.print("\n[yellow]Trading loop cancelled[/yellow]")
    
    try:
        asyncio.run(trading_loop())
    except KeyboardInterrupt:
        console.print("\n[yellow]Bot stopped by user[/yellow]")
        swarm_trader.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description="$COMPUTE Swarm Wallet CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create 10 swarm wallets
  python swarm_cli.py create --count 10
  
  # Fund swarm with 0.02 ETH per wallet
  python swarm_cli.py fund --main-key 0x... --amount 0.02
  
  # Check swarm status
  python swarm_cli.py status
  
  # Run trading bot
  python swarm_cli.py run --password mypassword
  
  # Reclaim all funds
  python swarm_cli.py reclaim --main-address 0x... --password mypassword
        """
    )
    
    # Global options
    parser.add_argument(
        '--rpc',
        default='https://mainnet.base.org',
        help='Base network RPC URL'
    )
    parser.add_argument(
        '--key-file',
        default='./swarm_wallets.enc',
        help='Path to encrypted wallet storage'
    )
    parser.add_argument(
        '--audit-log',
        default='./swarm_audit.log',
        help='Path to audit log file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate operations without executing transactions'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new swarm wallets')
    create_parser.add_argument('--count', type=int, default=10, help='Number of wallets to create')
    
    # Fund command
    fund_parser = subparsers.add_parser('fund', help='Fund swarm wallets from main wallet')
    fund_parser.add_argument('--main-key', help='Main wallet private key (or prompt)')
    fund_parser.add_argument('--amount', type=float, default=0.02, help='ETH amount per wallet')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show swarm status')
    status_parser.add_argument('--show-audit', action='store_true', help='Show recent audit trail')
    
    # Reclaim command
    reclaim_parser = subparsers.add_parser('reclaim', help='Reclaim all funds to main wallet')
    reclaim_parser.add_argument('--main-address', required=True, help='Main wallet address')
    reclaim_parser.add_argument('--compute', action='store_true', default=True, help='Also reclaim COMPUTE tokens')
    reclaim_parser.add_argument('--password', help='Swarm password (or prompt)')
    
    # Rotation mode command
    rotate_parser = subparsers.add_parser('rotate', help='Set wallet rotation mode')
    rotate_parser.add_argument('mode', choices=[m.value for m in RotationMode], help='Rotation mode')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run trading bot with swarm')
    run_parser.add_argument('--config', default='./bot_config.yaml', help='Path to bot config')
    run_parser.add_argument('--rotation', choices=[m.value for m in RotationMode], help='Rotation mode override')
    
    args = parser.parse_args()
    
    if args.command == 'create':
        create_swarm_command(args)
    elif args.command == 'fund':
        fund_swarm_command(args)
    elif args.command == 'status':
        status_command(args)
    elif args.command == 'reclaim':
        reclaim_command(args)
    elif args.command == 'rotate':
        rotate_mode_command(args)
    elif args.command == 'run':
        run_command(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
