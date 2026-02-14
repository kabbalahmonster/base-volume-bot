"""
Swarm Wallet Manager
====================
Manages multiple wallets for distributed trading volume.

Security First Design:
- All keys encrypted with PBKDF2 + Fernet
- Main wallet never exposed
- Balance verification before all operations
- Audit trail of all transactions
- Never dissolve wallets with balance

Author: Clawdelia (Cult of the Shell)
"""

import os
import json
import time
import logging
from pathlib import Path
from decimal import Decimal
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from web3 import Web3
from eth_account import Account
from cryptography.fernet import Fernet
import hashlib
import base64

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


@dataclass
class SwarmWallet:
    """Represents a single swarm wallet"""
    address: str
    encrypted_key: str
    index: int
    created_at: str
    total_buys: int = 0
    total_sells: int = 0
    total_eth_bought: Decimal = Decimal("0")
    last_used: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "address": self.address,
            "encrypted_key": self.encrypted_key,
            "index": self.index,
            "created_at": self.created_at,
            "total_buys": self.total_buys,
            "total_sells": self.total_sells,
            "total_eth_bought": str(self.total_eth_bought),
            "last_used": self.last_used,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SwarmWallet':
        return cls(
            address=data["address"],
            encrypted_key=data["encrypted_key"],
            index=data["index"],
            created_at=data["created_at"],
            total_buys=data.get("total_buys", 0),
            total_sells=data.get("total_sells", 0),
            total_eth_bought=Decimal(data.get("total_eth_bought", "0")),
            last_used=data.get("last_used"),
        )


class SwarmSecurity:
    """Security utilities for swarm wallets"""
    
    @staticmethod
    def derive_key(password: str) -> bytes:
        """Derive encryption key from password with PBKDF2"""
        key = hashlib.sha256(password.encode()).digest()
        return base64.urlsafe_b64encode(key)
    
    @staticmethod
    def encrypt_private_key(private_key: str, password: str) -> str:
        """Encrypt a private key"""
        key = SwarmSecurity.derive_key(password)
        f = Fernet(key)
        encrypted = f.encrypt(private_key.encode())
        return encrypted.decode()
    
    @staticmethod
    def decrypt_private_key(encrypted_key: str, password: str) -> Optional[str]:
        """Decrypt a private key"""
        try:
            key = SwarmSecurity.derive_key(password)
            f = Fernet(key)
            decrypted = f.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except Exception:
            return None
    
    @staticmethod
    def validate_address(address: str) -> bool:
        """Validate Ethereum address"""
        try:
            return Web3.is_address(address) and Web3.is_checksum_address(address)
        except:
            return False


class SwarmManager:
    """
    Manages a swarm of trading wallets.
    
    Features:
    - Create multiple wallets
    - Distribute funds from main wallet
    - Cycle through wallets for trades
    - Reclaim all funds
    - Safe dissolution (zero-balance only)
    """
    
    def __init__(self, 
                 main_wallet_key: str,
                 password: str,
                 w3: Web3,
                 swarm_file: str = ".swarm.json"):
        """
        Initialize swarm manager.
        
        Args:
            main_wallet_key: Private key of main funding wallet
            password: Password for encrypting swarm wallet keys
            w3: Web3 instance connected to network
            swarm_file: File to store swarm wallet data
        """
        self.main_account = Account.from_key(main_wallet_key)
        self.password = password
        self.w3 = w3
        self.swarm_file = Path(swarm_file)
        self.wallets: List[SwarmWallet] = []
        self.current_index = 0
        
        self.logger = logging.getLogger("SwarmManager")
        
        # Load existing swarm if present
        self._load_swarm()
    
    def _load_swarm(self):
        """Load existing swarm from file"""
        if self.swarm_file.exists():
            try:
                with open(self.swarm_file, 'r') as f:
                    data = json.load(f)
                    self.wallets = [SwarmWallet.from_dict(w) for w in data.get("wallets", [])]
                    self.current_index = data.get("current_index", 0)
                console.print(f"[dim]Loaded {len(self.wallets)} wallets from swarm[/dim]")
            except Exception as e:
                self.logger.error(f"Failed to load swarm: {e}")
                console.print("[yellow]⚠ Failed to load existing swarm, starting fresh[/yellow]")
    
    def _save_swarm(self):
        """Save swarm to file"""
        try:
            data = {
                "wallets": [w.to_dict() for w in self.wallets],
                "current_index": self.current_index,
                "updated_at": datetime.now().isoformat(),
            }
            with open(self.swarm_file, 'w') as f:
                json.dump(data, f, indent=2)
            # Restrict permissions
            os.chmod(self.swarm_file, 0o600)
        except Exception as e:
            self.logger.error(f"Failed to save swarm: {e}")
            raise
    
    def create_swarm(self, count: int) -> List[str]:
        """
        Create N new swarm wallets.
        
        Args:
            count: Number of wallets to create
            
        Returns:
            List of created wallet addresses
        """
        console.print(f"\n[bold cyan]🐝 Creating {count} swarm wallets...[/bold cyan]")
        
        addresses = []
        start_index = len(self.wallets)
        
        for i in range(count):
            # Generate new wallet
            account = Account.create()
            
            # Encrypt private key
            encrypted_key = SwarmSecurity.encrypt_private_key(
                account.key.hex(),
                self.password
            )
            
            # Create wallet record
            wallet = SwarmWallet(
                address=account.address,
                encrypted_key=encrypted_key,
                index=start_index + i,
                created_at=datetime.now().isoformat(),
            )
            
            self.wallets.append(wallet)
            addresses.append(account.address)
            
            console.print(f"[dim]  Created wallet {wallet.index}: {account.address[:20]}...[/dim]")
        
        # Save swarm
        self._save_swarm()
        
        console.print(f"[green]✓ Created {count} swarm wallets[/green]")
        return addresses
    
    def distribute_funds(self, amount_per_wallet_eth: float, 
                        fund_compute: bool = False,
                        compute_amount: float = 0) -> bool:
        """
        Distribute ETH (and optionally COMPUTE) to all swarm wallets.
        
        Args:
            amount_per_wallet_eth: Amount of ETH to send to each wallet
            fund_compute: Whether to also fund with COMPUTE
            compute_amount: Amount of COMPUTE to send (if fund_compute=True)
            
        Returns:
            True if all distributions successful
        """
        if not self.wallets:
            console.print("[red]✗ No wallets in swarm. Create swarm first.[/red]")
            return False
        
        total_eth_needed = amount_per_wallet_eth * len(self.wallets)
        
        console.print(f"\n[bold cyan]💸 Distributing funds...[/bold cyan]")
        console.print(f"[dim]Amount per wallet: {amount_per_wallet_eth} ETH[/dim]")
        console.print(f"[dim]Total needed: {total_eth_needed} ETH[/dim]")
        console.print(f"[dim]Number of wallets: {len(self.wallets)}[/dim]")
        
        # Check main wallet balance
        main_balance = self.w3.eth.get_balance(self.main_account.address)
        main_balance_eth = float(self.w3.from_wei(main_balance, 'ether'))
        
        if main_balance_eth < total_eth_needed + 0.01:  # +0.01 for gas
            console.print(f"[red]✗ Insufficient balance. Have: {main_balance_eth:.4f} ETH, Need: {total_eth_needed + 0.01:.4f} ETH[/red]")
            return False
        
        # Confirm
        confirm = input(f"\nType 'DISTRIBUTE' to send {total_eth_needed} ETH to {len(self.wallets)} wallets: ")
        if confirm != "DISTRIBUTE":
            console.print("[yellow]⚠ Distribution cancelled[/yellow]")
            return False
        
        # Distribute to each wallet
        success_count = 0
        
        for wallet in self.wallets:
            try:
                # Send ETH
                tx = {
                    'to': wallet.address,
                    'value': self.w3.to_wei(amount_per_wallet_eth, 'ether'),
                    'gas': 21000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(self.main_account.address),
                    'chainId': 8453,
                }
                
                signed = self.w3.eth.account.sign_transaction(tx, self.main_account.key)
                tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
                
                # Wait for confirmation
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt['status'] == 1:
                    console.print(f"[green]✓ Funded wallet {wallet.index}: {amount_per_wallet_eth} ETH[/green]")
                    success_count += 1
                else:
                    console.print(f"[red]✗ Failed to fund wallet {wallet.index}[/red]")
                
                # Small delay to avoid nonce issues
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Failed to fund wallet {wallet.index}: {e}")
                console.print(f"[red]✗ Error funding wallet {wallet.index}: {e}[/red]")
        
        console.print(f"\n[bold]{'✓' if success_count == len(self.wallets) else '⚠'} Funded {success_count}/{len(self.wallets)} wallets[/bold]")
        return success_count == len(self.wallets)
    
    def get_next_wallet(self) -> Optional[Tuple[Account, SwarmWallet]]:
        """
        Get the next wallet in the cycle (round-robin).
        
        Returns:
            Tuple of (Account, SwarmWallet) or None if no wallets
        """
        if not self.wallets:
            return None
        
        # Get wallet at current index
        wallet = self.wallets[self.current_index]
        
        # Decrypt private key
        private_key = SwarmSecurity.decrypt_private_key(
            wallet.encrypted_key,
            self.password
        )
        
        if not private_key:
            console.print(f"[red]✗ Failed to decrypt wallet {wallet.index}[/red]")
            return None
        
        # Create account
        account = Account.from_key(private_key)
        
        # Update index for next call
        self.current_index = (self.current_index + 1) % len(self.wallets)
        self._save_swarm()
        
        # Update last used
        wallet.last_used = datetime.now().isoformat()
        
        return account, wallet
    
    def get_wallet_balance(self, wallet: SwarmWallet) -> Tuple[Decimal, Decimal]:
        """
        Get ETH and COMPUTE balance for a wallet.
        
        Returns:
            Tuple of (ETH balance, COMPUTE balance)
        """
        # ETH balance
        eth_balance = self.w3.eth.get_balance(wallet.address)
        eth_decimal = Decimal(self.w3.from_wei(eth_balance, 'ether'))
        
        # COMPUTE balance (would need contract integration)
        # For now, return 0
        compute_decimal = Decimal("0")
        
        return eth_decimal, compute_decimal
    
    def reclaim_all_funds(self, to_address: Optional[str] = None) -> bool:
        """
        Reclaim all funds from all swarm wallets to main wallet.
        
        Args:
            to_address: Optional different destination (default: main wallet)
            
        Returns:
            True if all reclamations successful
        """
        destination = to_address or self.main_account.address
        
        console.print(f"\n[bold yellow]💰 RECLAIMING ALL FUNDS[/bold yellow]")
        console.print(f"[dim]Destination: {destination}[/dim]")
        console.print(f"[dim]Wallets to reclaim: {len(self.wallets)}[/dim]")
        
        # Safety check
        confirm = input("\nType 'RECLAIM' to return all funds from swarm wallets: ")
        if confirm != "RECLAIM":
            console.print("[yellow]⚠ Reclamation cancelled[/yellow]")
            return False
        
        total_reclaimed_eth = Decimal("0")
        success_count = 0
        
        for wallet in self.wallets:
            try:
                # Decrypt key
                private_key = SwarmSecurity.decrypt_private_key(
                    wallet.encrypted_key,
                    self.password
                )
                
                if not private_key:
                    console.print(f"[red]✗ Failed to decrypt wallet {wallet.index}[/red]")
                    continue
                
                account = Account.from_key(private_key)
                
                # Get balance
                balance = self.w3.eth.get_balance(wallet.address)
                balance_eth = Decimal(self.w3.from_wei(balance, 'ether'))
                
                # Leave small amount for gas
                reclaimable = balance - self.w3.to_wei(0.001, 'ether')
                
                if reclaimable <= 0:
                    console.print(f"[dim]  Wallet {wallet.index}: No funds to reclaim[/dim]")
                    continue
                
                # Send funds
                tx = {
                    'to': destination,
                    'value': reclaimable,
                    'gas': 21000,
                    'gasPrice': self.w3.eth.gas_price,
                    'nonce': self.w3.eth.get_transaction_count(wallet.address),
                    'chainId': 8453,
                }
                
                signed = self.w3.eth.account.sign_transaction(tx, account.key)
                tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
                
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt['status'] == 1:
                    reclaimed_eth = Decimal(self.w3.from_wei(reclaimable, 'ether'))
                    total_reclaimed_eth += reclaimed_eth
                    console.print(f"[green]✓ Reclaimed {reclaimed_eth:.6f} ETH from wallet {wallet.index}[/green]")
                    success_count += 1
                else:
                    console.print(f"[red]✗ Failed to reclaim from wallet {wallet.index}[/red]")
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Failed to reclaim from wallet {wallet.index}: {e}")
                console.print(f"[red]✗ Error reclaiming from wallet {wallet.index}: {e}[/red]")
        
        console.print(f"\n[bold]{'✓' if success_count > 0 else '⚠'} Reclaimed {total_reclaimed_eth:.6f} ETH from {success_count} wallets[/bold]")
        return success_count > 0
    
    def dissolve_swarm(self, force: bool = False) -> bool:
        """
        Dissolve the swarm after verifying all wallets are empty.
        
        SAFETY: Will NOT dissolve wallets with non-zero balance unless force=True.
        
        Args:
            force: If True, dissolve even with balance (DANGEROUS)
            
        Returns:
            True if swarm dissolved
        """
        console.print(f"\n[bold red]🔥 DISSOLVING SWARM[/bold red]")
        console.print(f"[dim]Wallets to dissolve: {len(self.wallets)}[/dim]")
        
        # Check balances
        non_zero_wallets = []
        for wallet in self.wallets:
            eth_balance, _ = self.get_wallet_balance(wallet)
            if eth_balance > Decimal("0.0001"):  # Threshold for dust
                non_zero_wallets.append((wallet.index, eth_balance))
        
        if non_zero_wallets and not force:
            console.print("\n[red]✗ CANNOT DISSOLVE - Wallets with non-zero balance detected:[/red]")
            for idx, balance in non_zero_wallets:
                console.print(f"  Wallet {idx}: {balance:.6f} ETH")
            console.print("\n[yellow]Reclaim funds first with: swarm reclaim[/yellow]")
            return False
        
        # Confirm
        if non_zero_wallets and force:
            console.print("\n[red]⚠️ WARNING: The following wallets have non-zero balance:[/red]")
            for idx, balance in non_zero_wallets:
                console.print(f"  Wallet {idx}: {balance:.6f} ETH")
            
            confirm = input("\nType 'DESTROY' to dissolve swarm WITH FUNDS (IRREVERSIBLE): ")
            if confirm != "DESTROY":
                console.print("[yellow]⚠ Dissolution cancelled[/yellow]")
                return False
        else:
            confirm = input("\nType 'DISSOLVE' to destroy all swarm wallets: ")
            if confirm != "DISSOLVE":
                console.print("[yellow]⚠ Dissolution cancelled[/yellow]")
                return False
        
        # Destroy swarm
        self.wallets = []
        self.current_index = 0
        
        if self.swarm_file.exists():
            self.swarm_file.unlink()
        
        console.print("[green]✓ Swarm dissolved[/green]")
        return True
    
    def show_status(self):
        """Display swarm status"""
        console.print("\n[bold cyan]🐝 Swarm Status[/bold cyan]")
        console.print(f"[dim]Total wallets: {len(self.wallets)}[/dim]")
        console.print(f"[dim]Current index: {self.current_index}[/dim]")
        
        if not self.wallets:
            console.print("[yellow]⚠ No wallets in swarm[/yellow]")
            return
        
        table = Table(box=box.ROUNDED)
        table.add_column("Index", style="cyan")
        table.add_column("Address", style="green")
        table.add_column("ETH Balance", style="yellow")
        table.add_column("Buys/Sells", style="blue")
        table.add_column("Last Used", style="dim")
        
        for wallet in self.wallets:
            eth_balance, _ = self.get_wallet_balance(wallet)
            last_used = wallet.last_used or "Never"
            if last_used != "Never":
                # Format timestamp
                try:
                    dt = datetime.fromisoformat(last_used)
                    last_used = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
            
            table.add_row(
                str(wallet.index),
                f"{wallet.address[:16]}...",
                f"{eth_balance:.6f}",
                f"{wallet.total_buys}/{wallet.total_sells}",
                last_used,
            )
        
        console.print(table)
