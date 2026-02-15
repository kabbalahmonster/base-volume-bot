#!/usr/bin/env python3
"""
Uniswap V4 Universal Router Integration
========================================
Direct V4 integration using uniswap-universal-router-decoder library.

This library handles the complex V4 encoding properly:
- V4_SWAP command with embedded actions
- Proper SETTLE/TAKE/SETTLE_ALL/TAKE_ALL encoding
- Pool Key encoding

Install: pip install uniswap-universal-router-decoder
Docs: https://github.com/Elnaril/uniswap-universal-router-decoder
"""

import time
from typing import Tuple, Optional, Dict, Any
from decimal import Decimal
from dataclasses import dataclass
from web3 import Web3
from eth_account import Account
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Universal Router address on Base
UNIVERSAL_ROUTER = "0x6c083a36f731ea994739ef5e8647d18553d41f76"

# WETH on Base
WETH = "0x4200000000000000000000000000000000000006"

# ERC20 ABI (minimal)
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]


class TransactionError(Exception):
    """Custom exception for transaction failures that should be retried."""
    pass


class V4DirectRouter:
    """
    Direct Uniswap V4 router using uniswap-universal-router-decoder library.
    
    Uses the library's encode.chain() API for building swap transactions.
    """
    
    def __init__(self, w3: Web3, account: Account, max_retries: int = 3, 
                 retry_delay_base: float = 2.0, chain_id: int = 8453):
        self.w3 = w3
        self.account = account
        self.chain_id = chain_id
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        
        self.weth = w3.to_checksum_address(WETH)
        self.router_address = w3.to_checksum_address(UNIVERSAL_ROUTER)
        
        # Stats
        self.total_swaps = 0
        self.successful_swaps = 0
        self.total_gas_spent = 0
        
        # Try to import the library
        try:
            from uniswap_universal_router_decoder import RouterCodec, FunctionRecipient
            self.codec = RouterCodec(w3=w3)
            self.FunctionRecipient = FunctionRecipient
            self.has_library = True
            print("[green]✓ uniswap-universal-router-decoder library loaded[/green]")
        except ImportError as e:
            self.has_library = False
            print(f"[yellow]⚠ uniswap-universal-router-decoder not installed: {e}[/yellow]")
    
    def _calculate_min_amount_out(self, expected_amount: int, slippage_percent: float) -> int:
        """Calculate minimum output with slippage protection."""
        return int(expected_amount * (100 - slippage_percent) / 100)
    
    def _build_v4_pool_key(self, token_a: str, token_b: str, fee: int) -> Dict:
        """Build V4 PoolKey struct."""
        # Sort currencies for V4 (currency0 < currency1)
        if token_a.lower() < token_b.lower():
            currency0, currency1 = token_a, token_b
        else:
            currency0, currency1 = token_b, token_a
        
        tick_spacing = {100: 1, 500: 10, 3000: 60, 10000: 200}.get(fee, 60)
        
        return {
            'currency0': currency0,
            'currency1': currency1,
            'fee': fee,
            'tickSpacing': tick_spacing,
            'hooks': '0x0000000000000000000000000000000000000000'
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(TransactionError),
        reraise=True
    )
    def swap_eth_for_tokens(
        self,
        token_address: str,
        amount_eth: Decimal,
        slippage_percent: float = 2.0,
        deadline_seconds: int = 300
    ) -> Tuple[bool, str]:
        """
        Swap ETH for tokens via V4 Universal Router using the decoder library.
        """
        if not self.has_library:
            return False, "uniswap-universal-router-decoder library not installed. Run: pip install uniswap-universal-router-decoder"
        
        token_address = self.w3.to_checksum_address(token_address)
        amount_in_wei = int(amount_eth * 10**18)
        
        print(f"[dim]Building V4 swap with library...[/dim]")
        
        try:
            # Try common fee tiers
            fee_tiers = [500, 3000, 10000]
            
            for fee in fee_tiers:
                try:
                    print(f"[dim]  Trying fee={fee}...[/dim]")
                    
                    # Build PoolKey
                    pool_key = self._build_v4_pool_key(self.weth, token_address, fee)
                    
                    # Determine swap direction
                    zero_for_one = self.weth.lower() == pool_key['currency0'].lower()
                    
                    # Estimate expected output (conservative)
                    expected_out = int(amount_in_wei * 0.995)
                    min_amount_out = self._calculate_min_amount_out(expected_out, slippage_percent)
                    
                    # Build swap using library's encode.chain() API
                    # Pattern: wrap ETH -> V4 swap exact in -> take tokens
                    chain = self.codec.encode.chain()
                    
                    # 1. Wrap ETH to WETH (command 0x0a)
                    chain.wrap_eth(self.FunctionRecipient.ROUTER, amount_in_wei)
                    
                    print(f"[dim]  Added WRAP_ETH command[/dim]")
                    
                    # 2. Add V4 swap exact in single (command 0x10)
                    # chain.v4_swap() returns a builder object
                    v4_swap = chain.v4_swap()
                    v4_swap.swap_exact_in_single(
                        pool_key=pool_key,
                        zero_for_one=zero_for_one,
                        amount_in=amount_in_wei,
                        amount_out_min=min_amount_out,
                        hook_data=b''
                    )
                    # Take the output tokens to wallet
                    # take(currency, recipient, amount) - specify exact recipient
                    v4_swap.take(currency=token_address, recipient=self.account.address, amount=min_amount_out)
                    
                    # CRITICAL: Build v4 swap to commit commands to chain
                    chain = v4_swap.build_v4_swap()
                    
                    print(f"[green]✓ Found V4 pool: fee={fee}[/green]")
                    
                    # Build transaction with Base UR address (checksummed)
                    deadline = int(time.time()) + deadline_seconds
                    base_ur = self.w3.to_checksum_address(UNIVERSAL_ROUTER)
                    
                    tx = chain.build_transaction(
                        sender=self.account.address,
                        value=amount_in_wei,
                        deadline=deadline,
                        ur_address=base_ur
                    )
                    
                    print(f"[dim]Transaction built, sending...[/dim]")
                    
                    # Sign and send
                    signed = self.account.sign_transaction(tx)
                    tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                    tx_hex = self.w3.to_hex(tx_hash)
                    
                    print(f"[dim]TX: {tx_hex}[/dim]")
                    
                    # Wait for receipt
                    receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    
                    self.total_swaps += 1
                    self.total_gas_spent += receipt['gasUsed']
                    
                    if receipt['status'] == 1:
                        self.successful_swaps += 1
                        print(f"[green]✓ V4 swap successful! Gas used: {receipt['gasUsed']}[/green]")
                        return True, tx_hex
                    else:
                        error_msg = f"V4 swap failed (status={receipt['status']}) - TX: {tx_hex}"
                        print(f"[red]✗ {error_msg}[/red]")
                        raise TransactionError(error_msg)
                    
                except Exception as e:
                    if "Fee=" in str(e):
                        print(f"[dim]  Fee={fee} not available, trying next...[/dim]")
                        continue
                    raise
            
            return False, "No V4 pool found for token pair"
                
        except TransactionError:
            raise
        except Exception as e:
            error_msg = f"V4 swap error: {e}"
            print(f"[red]✗ {error_msg}[/red]")
            raise TransactionError(error_msg)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(TransactionError),
        reraise=True
    )
    def swap_tokens_for_eth(
        self,
        token_address: str,
        amount_tokens: Decimal,
        token_decimals: int = 18,
        slippage_percent: float = 2.0,
        deadline_seconds: int = 300
    ) -> Tuple[bool, str]:
        """Swap tokens for ETH via V4 Universal Router."""
        if not self.has_library:
            return False, "uniswap-universal-router-decoder library not installed"
        
        token_address = self.w3.to_checksum_address(token_address)
        amount_in_units = int(amount_tokens * (10 ** token_decimals))
        
        print(f"[dim]Building V4 token->ETH swap...[/dim]")
        
        try:
            # Try fee tiers
            fee_tiers = [500, 3000, 10000]
            
            for fee in fee_tiers:
                try:
                    print(f"[dim]  Trying fee={fee}...[/dim]")
                    
                    pool_key = self._build_v4_pool_key(token_address, self.weth, fee)
                    zero_for_one = token_address.lower() == pool_key['currency0'].lower()
                    
                    expected_out = int(amount_in_units * 0.995)
                    min_amount_out = self._calculate_min_amount_out(expected_out, slippage_percent)
                    
                    chain = self.codec.encode.chain()
                    
                    # V4 swap builder pattern
                    v4_swap = chain.v4_swap()
                    v4_swap.swap_exact_in_single(
                        pool_key=pool_key,
                        zero_for_one=zero_for_one,
                        amount_in=amount_in_units,
                        amount_out_min=min_amount_out,
                        hook_data=b''
                    )
                    # Take WETH output to wallet
                    v4_swap.take(currency=self.weth, recipient=self.account.address, amount=min_amount_out)
                    
                    # CRITICAL: Build v4 swap to commit commands to chain
                    chain = v4_swap.build_v4_swap()
                    
                    deadline = int(time.time()) + deadline_seconds
                    base_ur = self.w3.to_checksum_address(UNIVERSAL_ROUTER)
                    
                    tx = chain.build_transaction(
                        sender=self.account.address,
                        deadline=deadline,
                        ur_address=base_ur
                    )
                    
                    signed = self.account.sign_transaction(tx)
                    tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                    tx_hex = self.w3.to_hex(tx_hash)
                    
                    receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    
                    if receipt['status'] == 1:
                        return True, tx_hex
                    else:
                        raise TransactionError(f"Swap failed (status={receipt['status']})")
                    
                except Exception as e:
                    if "Fee=" in str(e):
                        continue
                    raise
            
            return False, "No V4 pool found"
                
        except TransactionError:
            raise
        except Exception as e:
            raise TransactionError(f"Swap error: {e}")
    
    def recover_eth_from_router(self) -> Tuple[bool, str]:
        """
        ⚠️  IMPORTANT LIMITATION ⚠️
        
        This function CANNOT recover ETH that was accidentally sent to the Universal Router
        contract via empty execute() calls. That ETH is effectively stuck/donated.
        
        The Universal Router does not have a function to arbitrarily withdraw its ETH balance.
        SWEEP only works for ETH that is part of the current execution context, not for
        previously sent donations.
        
        This function is kept for documentation purposes but will likely not recover
        funds from failed V4 test transactions.
        
        Returns:
            (success, tx_hash or error message)
        """
        if not self.has_library:
            return False, "Library not installed"
        
        print(f"[yellow]⚠️  WARNING: ETH sent to Universal Router is likely unrecoverable[/yellow]")
        print(f"[dim]Attempting sweep (may not work for stuck ETH)...[/dim]")
        
        try:
            chain = self.codec.encode.chain()
            
            # Sweep ETH (address(0) represents native ETH)
            # NOTE: This only sweeps ETH from current execution, not previously stuck ETH
            chain.sweep(
                function_recipient=self.FunctionRecipient.SENDER,
                token_address="0x0000000000000000000000000000000000000000",  # ETH
                amount_min=0,  # Sweep all
            )
            
            base_ur = self.w3.to_checksum_address(UNIVERSAL_ROUTER)
            
            tx = chain.build_transaction(
                sender=self.account.address,
                deadline=int(time.time()) + 300,
                ur_address=base_ur
            )
            
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex = self.w3.to_hex(tx_hash)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"[yellow]⚠️  TX succeeded but ETH may not be recoverable[/yellow]")
                print(f"[dim]TX: {tx_hex[:20]}...[/dim]")
                return True, tx_hex
            else:
                return False, f"Sweep failed (status={receipt['status']})"
                
        except Exception as e:
            return False, f"Recovery error: {e}"
    
    def unwrap_weth(self, amount: Optional[int] = None) -> Tuple[bool, str]:
        """
        Unwrap WETH to ETH.
        
        Args:
            amount: Amount to unwrap (None = unwrap all)
            
        Returns:
            (success, tx_hash or error message)
        """
        if not self.has_library:
            return False, "Library not installed"
        
        print(f"[dim]Unwrapping WETH...[/dim]")
        
        try:
            if amount is None:
                # Get balance
                weth_contract = self.w3.eth.contract(address=self.weth, abi=ERC20_ABI)
                amount = weth_contract.functions.balanceOf(self.account.address).call()
            
            if amount == 0:
                return False, "No WETH to unwrap"
            
            chain = self.codec.encode.chain()
            
            # Unwrap WETH
            chain.unwrap_weth(
                function_recipient=self.FunctionRecipient.SENDER,
                amount=amount
            )
            
            base_ur = self.w3.to_checksum_address(UNIVERSAL_ROUTER)
            
            tx = chain.build_transaction(
                sender=self.account.address,
                deadline=int(time.time()) + 300,
                ur_address=base_ur
            )
            
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex = self.w3.to_hex(tx_hash)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"[green]✓ WETH unwrapped! TX: {tx_hex[:20]}...[/green]")
                return True, tx_hex
            else:
                return False, f"Unwrap failed (status={receipt['status']})"
                
        except Exception as e:
            return False, f"Unwrap error: {e}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            'total_swaps': self.total_swaps,
            'successful_swaps': self.successful_swaps,
            'failed_swaps': self.total_swaps - self.successful_swaps,
            'success_rate': self.successful_swaps / self.total_swaps if self.total_swaps > 0 else 0,
            'total_gas_spent': self.total_gas_spent,
            'avg_gas_per_swap': self.total_gas_spent / self.total_swaps if self.total_swaps > 0 else 0
        }


# Backwards compatibility
V4UniversalRouter = V4DirectRouter
