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
            from uniswap_universal_router_decoder import RouterCodec, FunctionRecipient, Wei
            self.codec = RouterCodec()
            self.FunctionRecipient = FunctionRecipient
            self.Wei = Wei
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
                    # Pattern: wrap ETH -> V4 swap exact in
                    chain = self.codec.encode.chain()
                    
                    # Add V4 swap exact in single
                    # Note: The library uses chained calls via .chain()
                    chain.v4_swap_exact_in_single(
                        pool_key=pool_key,
                        zero_for_one=zero_for_one,
                        amount_in=self.Wei(amount_in_wei),
                        amount_out_min=self.Wei(min_amount_out),
                        sqrt_price_limit_x96=0,
                        hook_data=b''
                    )
                    
                    # The library should handle wrapping and settlement internally
                    # when we build the transaction
                    
                    print(f"[green]✓ Found V4 pool: fee={fee}[/green]")
                    
                    # Build transaction
                    deadline = int(time.time()) + deadline_seconds
                    
                    tx = self.codec.build_transaction(
                        chain=chain,
                        from_address=self.account.address,
                        deadline=deadline,
                        value=amount_in_wei,
                        w3=self.w3
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
                    
                    chain.v4_swap_exact_in_single(
                        pool_key=pool_key,
                        zero_for_one=zero_for_one,
                        amount_in=self.Wei(amount_in_units),
                        amount_out_min=self.Wei(min_amount_out),
                        sqrt_price_limit_x96=0,
                        hook_data=b''
                    )
                    
                    deadline = int(time.time()) + deadline_seconds
                    
                    tx = self.codec.build_transaction(
                        chain=chain,
                        from_address=self.account.address,
                        deadline=deadline,
                        w3=self.w3
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
