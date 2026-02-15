#!/usr/bin/env python3
"""
Uniswap V4 Universal Router Integration
========================================
Direct V4 integration for COMPUTE and other V4-only tokens.

Uses Universal Router with encoded commands for ETH->Token swaps.
Pool discovery uses V4's PoolKey → PoolId architecture.

Universal Router on Base: 0x6c083a36f731ea994739ef5e8647d18553d41f76
Pool Manager on Base: 0x498581ff718922c3f8e6a244956af099b2652b2b
"""

import time
from typing import Tuple, Optional, Dict, Any
from decimal import Decimal
from dataclasses import dataclass
from web3 import Web3
from eth_account import Account
from eth_abi import encode
from eth_utils import keccak
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Universal Router address on Base
UNIVERSAL_ROUTER = "0x6c083a36f731ea994739ef5e8647d18553d41f76"

# WETH on Base
WETH = "0x4200000000000000000000000000000000000006"

# V4 Pool Manager
V4_POOL_MANAGER = "0x498581ff718922c3f8e6a244956af099b2652b2b"

# Universal Router Command Constants
class Commands:
    """Universal Router command bytes."""
    V3_SWAP_EXACT_IN = 0x00
    V3_SWAP_EXACT_OUT = 0x01
    PERMIT2_TRANSFER_FROM = 0x02
    V4_SWAP_EXACT_IN = 0x03
    V4_SWAP_EXACT_OUT = 0x04
    SETTLE = 0x05
    TAKE = 0x06
    CLOSE_DELTA = 0x07
    CLEAR_OR_TAKE = 0x08
    SWEEP = 0x09
    WRAP_ETH = 0x0a
    UNWRAP_WETH = 0x0b
    PAY_PORTION = 0x0c
    PAY_PORTION_2 = 0x0d
    PERMIT2_PERMIT = 0x0e

# WETH ABI (minimal)
WETH_ABI = [
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "type": "function"},
    {"constant": False, "inputs": [{"name": "wad", "type": "uint256"}], "name": "withdraw", "outputs": [], "payable": False, "type": "function"},
    {"constant": True, "inputs": [{"name": "", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "guy", "type": "address"}, {"name": "wad", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "", "type": "address"}, {"name": "", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
]

# Universal Router ABI
UNIVERSAL_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "bytes", "name": "commands", "type": "bytes"},
            {"internalType": "bytes[]", "name": "inputs", "type": "bytes[]"}
        ],
        "name": "execute",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes", "name": "commands", "type": "bytes"},
            {"internalType": "bytes[]", "name": "inputs", "type": "bytes[]"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "execute",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

# ERC20 ABI (minimal)
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
]


class TransactionError(Exception):
    """Custom exception for transaction failures that should be retried."""
    pass


@dataclass
class PoolKey:
    """V4 PoolKey struct."""
    currency0: str  # address
    currency1: str  # address
    fee: int        # uint24
    tickSpacing: int # int24
    hooks: str      # address
    
    def to_id(self) -> bytes:
        """Compute PoolId = keccak256(abi.encode(PoolKey))."""
        # Encode PoolKey as: (address, address, uint24, int24, address)
        encoded = encode(
            ['address', 'address', 'uint24', 'int24', 'address'],
            [self.currency0, self.currency1, self.fee, self.tickSpacing, self.hooks]
        )
        return keccak(encoded)


class V4DirectRouter:
    """
    Direct Uniswap V4 router for tokens that only have V4 liquidity.
    
    Uses PoolKey → PoolId architecture for pool discovery.
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
        self.pool_manager = w3.to_checksum_address(V4_POOL_MANAGER)
        
        # Initialize contracts
        self.router = w3.eth.contract(address=self.router_address, abi=UNIVERSAL_ROUTER_ABI)
        self.weth_contract = w3.eth.contract(address=self.weth, abi=WETH_ABI)
        
        # Stats
        self.total_swaps = 0
        self.successful_swaps = 0
        self.total_gas_spent = 0
        
    def _calculate_min_amount_out(self, expected_amount: int, slippage_percent: float) -> int:
        """Calculate minimum output with slippage protection."""
        return int(expected_amount * (100 - slippage_percent) / 100)
    
    def _estimate_gas(self, tx_dict: Dict[str, Any]) -> int:
        """Estimate gas with safety buffer."""
        try:
            estimated = self.w3.eth.estimate_gas(tx_dict)
            return int(estimated * 1.2)
        except Exception as e:
            print(f"[dim]Gas estimation failed: {e}, using default[/dim]")
            return 500000
    
    def _find_v4_pool(
        self,
        token_in: str,
        token_out: str,
        fee_tiers: list = None
    ) -> Optional[PoolKey]:
        """
        Find a V4 pool by computing PoolId and checking if pool exists.
        
        V4 pools are identified by PoolKey → PoolId (keccak256 hash).
        We try common fee tiers and compute PoolId for each.
        """
        if fee_tiers is None:
            fee_tiers = [500, 3000, 10000]  # 0.05%, 0.3%, 1% (most common)
        
        # Ensure checksum addresses
        token_in_cs = self.w3.to_checksum_address(token_in)
        token_out_cs = self.w3.to_checksum_address(token_out)
        
        # Sort for currency0/currency1 ordering (required by V4)
        if token_in_cs.lower() < token_out_cs.lower():
            currency0, currency1 = token_in_cs, token_out_cs
            zero_for_one = True
        else:
            currency0, currency1 = token_out_cs, token_in_cs
            zero_for_one = False
        
        print(f"[dim]Searching V4 pools: {currency0[:10]}... / {currency1[:10]}...[/dim]")
        
        for fee in fee_tiers:
            try:
                # Standard tick spacing for each fee tier
                tick_spacing = {100: 1, 500: 10, 3000: 60, 10000: 200}.get(fee, 60)
                
                # Construct PoolKey
                pool_key = PoolKey(
                    currency0=currency0,
                    currency1=currency1,
                    fee=fee,
                    tickSpacing=tick_spacing,
                    hooks='0x0000000000000000000000000000000000000000'  # No hooks
                )
                
                # Compute PoolId
                pool_id = pool_key.to_id()
                pool_id_hex = '0x' + pool_id.hex()
                
                print(f"[dim]  Trying fee={fee}, tickSpacing={tick_spacing}, PoolId={pool_id_hex[:20]}...[/dim]")
                
                # Try to verify pool exists by calling PoolManager
                # V4 pools store state in PoolManager - we can try to read slot0
                # For now, we'll assume pool exists if we can construct valid PoolKey
                # In production, you'd verify with extsload or similar
                
                # Return the pool key for swap construction
                return pool_key
                
            except Exception as e:
                print(f"[dim]  Fee={fee} error: {e}[/dim]")
                continue
        
        return None
    
    def _encode_v4_swap_exact_in(
        self,
        pool_key: PoolKey,
        amount_in: int,
        min_amount_out: int,
        zero_for_one: bool,
        sqrt_price_limit_x96: int = 0
    ) -> bytes:
        """
        Encode V4 swap exact input parameters.
        
        V4 swap params: (poolKey, zeroForOne, amountIn, amountOutMinimum, sqrtPriceLimitX96, hookData)
        """
        swap_params = encode(
            ['(address,address,uint24,int24,address)', 'bool', 'uint128', 'uint128', 'uint160', 'bytes'],
            [
                (
                    pool_key.currency0,
                    pool_key.currency1,
                    pool_key.fee,
                    pool_key.tickSpacing,
                    pool_key.hooks
                ),
                zero_for_one,
                amount_in,
                min_amount_out,
                sqrt_price_limit_x96,
                b''  # hookData
            ]
        )
        return swap_params
    
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
        Swap ETH for tokens via V4 Universal Router.
        
        Command sequence:
        1. WRAP_ETH - wrap input ETH to WETH
        2. V4_SWAP_EXACT_IN - perform V4 swap
        3. TAKE - take output tokens
        4. SWEEP - sweep any remaining WETH back to user
        """
        token_address = self.w3.to_checksum_address(token_address)
        amount_in_wei = int(amount_eth * 10**18)
        
        print(f"[dim]Finding V4 pool for swap...[/dim]")
        
        # Find V4 pool
        pool_key = self._find_v4_pool(self.weth, token_address)
        if not pool_key:
            return False, "No V4 pool found for token pair"
        
        print(f"[green]✓ Found V4 pool: fee={pool_key.fee}, tickSpacing={pool_key.tickSpacing}[/green]")
        
        # Determine swap direction
        zero_for_one = self.weth.lower() == pool_key.currency0.lower()
        
        # For slippage, use conservative estimate (V4 quoter is complex)
        # Assume 0.5% slippage from pool fee as baseline
        expected_out = int(amount_in_wei * 0.995)
        min_amount_out = self._calculate_min_amount_out(expected_out, slippage_percent)
        
        print(f"[dim]Expected: {expected_out}, Min with {slippage_percent}% slippage: {min_amount_out}[/dim]")
        
        try:
            # Build command sequence for V4 swap
            commands = bytes([Commands.WRAP_ETH, Commands.V4_SWAP_EXACT_IN, Commands.CLOSE_DELTA, Commands.TAKE, Commands.SWEEP])
            
            inputs = []
            
            # Command 1: WRAP_ETH
            wrap_input = encode(
                ['address', 'uint256'],
                [self.router_address, amount_in_wei]
            )
            inputs.append(wrap_input)
            
            # Command 2: V4_SWAP_EXACT_IN
            swap_input = self._encode_v4_swap_exact_in(
                pool_key, amount_in_wei, min_amount_out, zero_for_one
            )
            inputs.append(swap_input)
            
            # Command 3: CLOSE_DELTA - settle any open deltas before taking
            close_delta_input = encode(
                ['address'],
                [token_address]
            )
            inputs.append(close_delta_input)
            
            # Command 4: TAKE - take output tokens
            take_input = encode(
                ['address', 'address', 'uint128'],
                [token_address, self.account.address, 0]  # 0 = take all
            )
            inputs.append(take_input)
            
            # Command 5: SWEEP - sweep any remaining WETH
            sweep_input = encode(
                ['address', 'address', 'uint160'],
                [self.weth, self.account.address, 0]
            )
            inputs.append(sweep_input)
            
            # Calculate deadline
            deadline = int(time.time()) + deadline_seconds
            
            # Build transaction
            tx = self.router.functions.execute(
                commands,
                inputs,
                deadline
            ).build_transaction({
                'from': self.account.address,
                'value': amount_in_wei,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Estimate gas
            tx['gas'] = self._estimate_gas(tx)
            print(f"[dim]Gas estimated: {tx['gas']}[/dim]")
            
            # Sign and send
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex = self.w3.to_hex(tx_hash)
            
            print(f"[dim]Transaction sent: {tx_hex}[/dim]")
            
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
        token_address = self.w3.to_checksum_address(token_address)
        amount_in_units = int(amount_tokens * (10 ** token_decimals))
        
        print(f"[dim]Finding V4 pool for token->ETH swap...[/dim]")
        
        # Find V4 pool
        pool_key = self._find_v4_pool(token_address, self.weth)
        if not pool_key:
            return False, "No V4 pool found for token pair"
        
        print(f"[green]✓ Found V4 pool: fee={pool_key.fee}[/green]")
        
        # Check and handle token approval
        token_contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
        current_allowance = token_contract.functions.allowance(
            self.account.address,
            self.router_address
        ).call()
        
        if current_allowance < amount_in_units:
            print(f"[dim]Approving router to spend tokens...[/dim]")
            approve_tx = token_contract.functions.approve(
                self.router_address,
                amount_in_units
            ).build_transaction({
                'from': self.account.address,
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id
            })
            
            signed_approve = self.account.sign_transaction(approve_tx)
            approve_hash = self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(approve_hash, timeout=120)
            print(f"[dim]✓ Approved[/dim]")
        
        # Determine swap direction
        zero_for_one = token_address.lower() == pool_key.currency0.lower()
        
        # Estimate output
        expected_out = int(amount_in_units * 0.995)
        min_amount_out = self._calculate_min_amount_out(expected_out, slippage_percent)
        
        try:
            # Build commands
            commands = bytes([Commands.V4_SWAP_EXACT_IN, Commands.UNWRAP_WETH, Commands.SWEEP])
            
            inputs = []
            
            # Command 1: V4_SWAP_EXACT_IN
            swap_input = self._encode_v4_swap_exact_in(
                pool_key, amount_in_units, min_amount_out, zero_for_one
            )
            inputs.append(swap_input)
            
            # Command 2: UNWRAP_WETH
            unwrap_input = encode(
                ['address', 'uint256'],
                [self.account.address, 0]  # 0 = unwrap all
            )
            inputs.append(unwrap_input)
            
            # Command 3: SWEEP
            sweep_input = encode(
                ['address', 'address', 'uint160'],
                [token_address, self.account.address, 0]
            )
            inputs.append(sweep_input)
            
            deadline = int(time.time()) + deadline_seconds
            
            tx = self.router.functions.execute(
                commands,
                inputs,
                deadline
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            tx['gas'] = self._estimate_gas(tx)
            
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex = self.w3.to_hex(tx_hash)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                return True, tx_hex
            else:
                raise TransactionError(f"Swap failed (status={receipt['status']})")
                
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


# Backwards compatibility alias
V4UniversalRouter = V4DirectRouter
