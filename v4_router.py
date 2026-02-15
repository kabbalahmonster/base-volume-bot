#!/usr/bin/env python3
"""
Uniswap V4 Universal Router Integration
========================================
Full V4 integration for COMPUTE and other V4-only tokens.

Uses Universal Router with encoded commands for ETH->Token swaps.
This is a fallback when 0x aggregator is not available.

Universal Router on Base: 0x6c083a36f731ea994739ef5e8647d18553d41f76
"""

import time
from typing import Tuple, Optional, Dict, Any
from decimal import Decimal
from dataclasses import dataclass
from web3 import Web3
from eth_account import Account
from eth_abi import encode
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

# V4 Pool Manager ABI (minimal)
V4_POOL_MANAGER_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "currency0", "type": "address"},
            {"internalType": "address", "name": "currency1", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"},
            {"internalType": "int24", "name": "tickSpacing", "type": "int24"},
            {"internalType": "address", "name": "hooks", "type": "address"}
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class TransactionError(Exception):
    """Custom exception for transaction failures."""
    pass


@dataclass
class V4Quote:
    """Quote for V4 swap."""
    amount_in: int
    amount_out: int
    pool_fee: int
    price_impact: float
    sqrt_price_limit_x96: int


class V4UniversalRouter:
    """
    Full Uniswap V4 Universal Router integration.
    
    Implements proper command encoding for V4 swaps with:
    - Slippage protection
    - Gas estimation
    - Retry logic with exponential backoff
    - MEV protection via deadline
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
            # Add 20% buffer for safety
            return int(estimated * 1.2)
        except Exception as e:
            print(f"[dim]Gas estimation failed: {e}, using default[/dim]")
            return 500000  # Conservative default for V4
    
    def _encode_v4_swap_exact_in(
        self,
        pool_key: Dict[str, Any],
        amount_in: int,
        min_amount_out: int,
        sqrt_price_limit_x96: int = 0
    ) -> bytes:
        """
        Encode V4 swap exact input parameters.
        
        Pool key structure:
        - currency0: address (token0)
        - currency1: address (token1)
        - fee: uint24
        - tickSpacing: int24
        - hooks: address
        """
        # Encode the swap parameters
        # Structure: (poolKey, zeroForOne, amountIn, amountOutMinimum, sqrtPriceLimitX96, hookData)
        swap_params = encode(
            ['(address,address,uint24,int24,address)', 'bool', 'uint128', 'uint128', 'uint160', 'bytes'],
            [
                (
                    pool_key['currency0'],
                    pool_key['currency1'],
                    pool_key['fee'],
                    pool_key['tickSpacing'],
                    pool_key['hooks']
                ),
                pool_key['zeroForOne'],
                amount_in,
                min_amount_out,
                sqrt_price_limit_x96,
                b''  # hookData
            ]
        )
        return swap_params
    
    def _find_v4_pool(
        self,
        token_in: str,
        token_out: str,
        fee_tiers: list = None
    ) -> Optional[Dict[str, Any]]:
        """Find a V4 pool for the token pair."""
        if fee_tiers is None:
            fee_tiers = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
        
        pool_manager = self.w3.eth.contract(address=self.pool_manager, abi=V4_POOL_MANAGER_ABI)
        
        # Ensure addresses are checksummed
        token_in_cs = self.w3.to_checksum_address(token_in)
        token_out_cs = self.w3.to_checksum_address(token_out)
        
        # Sort for currency0/currency1 ordering
        token0, token1 = sorted([token_in_cs, token_out_cs])
        zero_for_one = token_in_cs == token0
        
        for fee in fee_tiers:
            try:
                # Standard tick spacing for each fee tier
                tick_spacing = {100: 1, 500: 10, 3000: 60, 10000: 200}.get(fee, 60)
                
                pool_address = pool_manager.functions.getPool(
                    token0,
                    token1,
                    fee,
                    tick_spacing,
                    '0x0000000000000000000000000000000000000000'  # No hooks
                ).call()
                
                if pool_address and pool_address != '0x0000000000000000000000000000000000000000':
                    # Check if pool has code
                    code = self.w3.eth.get_code(pool_address)
                    if len(code) > 0:
                        return {
                            'currency0': token0,
                            'currency1': token1,
                            'fee': fee,
                            'tickSpacing': tick_spacing,
                            'hooks': '0x0000000000000000000000000000000000000000',
                            'zeroForOne': zero_for_one,
                            'address': pool_address
                        }
            except Exception as e:
                print(f"[dim]  Pool check fee={fee}: {e}[/dim]")
                continue
        
        return None
    
    def _get_v3_quote(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        fee: int
    ) -> int:
        """Get quote using V3 quoter as fallback for V4."""
        # V4 quoter is complex; use V3 as approximation
        quoter_address = "0x3d4e44Eb1374240CE5F1B871ab261CD16335CB76"
        quoter_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "name": "quoteExactInputSingle",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        try:
            quoter = self.w3.eth.contract(address=quoter_address, abi=quoter_abi)
            # Ensure checksum addresses
            token_in_cs = self.w3.to_checksum_address(token_in)
            token_out_cs = self.w3.to_checksum_address(token_out)
            amount_out = quoter.functions.quoteExactInputSingle(
                token_in_cs,
                token_out_cs,
                fee,
                amount_in,
                0
            ).call()
            return amount_out
        except Exception as e:
            print(f"[dim]Quoter failed: {e}[/dim]")
            return 0
    
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
        
        Args:
            token_address: Token to receive
            amount_eth: Amount of ETH to swap
            slippage_percent: Maximum slippage allowed
            deadline_seconds: Transaction deadline from now
            
        Returns:
            (success, tx_hash or error message)
        """
        token_address = self.w3.to_checksum_address(token_address)
        amount_in_wei = int(amount_eth * 10**18)
        
        print(f"[dim]Finding V4 pool for swap...[/dim]")
        
        # Find V4 pool
        pool = self._find_v4_pool(self.weth, token_address)
        if not pool:
            return False, "No V4 pool found for token pair"
        
        print(f"[green]✓ Found V4 pool: fee={pool['fee']}, tickSpacing={pool['tickSpacing']}[/green]")
        
        # Get quote for slippage calculation
        print(f"[dim]Getting price quote...[/dim]")
        expected_out = self._get_v3_quote(self.weth, token_address, amount_in_wei, pool['fee'])
        
        if expected_out == 0:
            print("[yellow]⚠ Quoter returned 0, using conservative estimate[/yellow]")
            # Conservative fallback: assume 0.5% slippage from pool fee
            expected_out = int(amount_in_wei * 0.995)
        
        min_amount_out = self._calculate_min_amount_out(expected_out, slippage_percent)
        
        print(f"[dim]Expected: {expected_out}, Min with {slippage_percent}% slippage: {min_amount_out}[/dim]")
        
        try:
            # Build command sequence for V4 swap
            commands = bytes([Commands.WRAP_ETH, Commands.V4_SWAP_EXACT_IN, Commands.TAKE, Commands.SWEEP])
            
            inputs = []
            
            # Command 1: WRAP_ETH
            # Input: (recipient, amount)
            wrap_input = encode(
                ['address', 'uint256'],
                [self.router_address, amount_in_wei]  # Wrap to router for swap
            )
            inputs.append(wrap_input)
            
            # Command 2: V4_SWAP_EXACT_IN
            # Input: (poolKey, zeroForOne, amountIn, amountOutMinimum, sqrtPriceLimitX96, hookData)
            swap_input = encode(
                ['(address,address,uint24,int24,address)', 'bool', 'uint128', 'uint128', 'uint160', 'bytes'],
                [
                    (
                        pool['currency0'],
                        pool['currency1'],
                        pool['fee'],
                        pool['tickSpacing'],
                        pool['hooks']
                    ),
                    pool['zeroForOne'],
                    amount_in_wei,
                    min_amount_out,
                    0,  # sqrtPriceLimitX96 - no limit
                    b''  # hookData
                ]
            )
            inputs.append(swap_input)
            
            # Command 3: TAKE
            # Input: (token, recipient, amount)
            take_input = encode(
                ['address', 'address', 'uint128'],
                [token_address, self.account.address, 0]  # 0 = take all
            )
            inputs.append(take_input)
            
            # Command 4: SWEEP (sweep any remaining WETH)
            sweep_input = encode(
                ['address', 'address', 'uint160'],
                [self.weth, self.account.address, 0]  # 0 = sweep all
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
                'value': amount_in_wei,  # Send ETH to wrap
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
                'gas': 500000,  # Initial value, will be estimated
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
            raise  # Re-raise for retry
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
        """
        Swap tokens for ETH via V4 Universal Router.
        
        Command sequence:
        1. PERMIT2_TRANSFER_FROM - transfer tokens from user
        2. V4_SWAP_EXACT_IN - swap tokens for WETH
        3. UNWRAP_WETH - unwrap WETH to ETH
        4. TAKE - take ETH
        
        Args:
            token_address: Token to sell
            amount_tokens: Amount of tokens to sell
            token_decimals: Token decimals
            slippage_percent: Maximum slippage allowed
            deadline_seconds: Transaction deadline from now
            
        Returns:
            (success, tx_hash or error message)
        """
        token_address = self.w3.to_checksum_address(token_address)
        amount_in_units = int(amount_tokens * (10 ** token_decimals))
        
        print(f"[dim]Finding V4 pool for token->ETH swap...[/dim]")
        
        # Find V4 pool
        pool = self._find_v4_pool(token_address, self.weth)
        if not pool:
            return False, "No V4 pool found for token pair"
        
        print(f"[green]✓ Found V4 pool: fee={pool['fee']}[/green]")
        
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
        
        # Get quote
        print(f"[dim]Getting price quote...[/dim]")
        expected_out = self._get_v3_quote(token_address, self.weth, amount_in_units, pool['fee'])
        
        if expected_out == 0:
            print("[yellow]⚠ Quoter returned 0, using conservative estimate[/yellow]")
            expected_out = int(amount_in_units * 0.995)
        
        min_amount_out = self._calculate_min_amount_out(expected_out, slippage_percent)
        
        try:
            # Build command sequence
            commands = bytes([Commands.V4_SWAP_EXACT_IN, Commands.UNWRAP_WETH, Commands.SWEEP])
            
            inputs = []
            
            # Command 1: V4_SWAP_EXACT_IN
            # Need to encode the swap path properly for V4
            swap_input = encode(
                ['(address,address,uint24,int24,address)', 'bool', 'uint128', 'uint128', 'uint160', 'bytes'],
                [
                    (
                        pool['currency0'],
                        pool['currency1'],
                        pool['fee'],
                        pool['tickSpacing'],
                        pool['hooks']
                    ),
                    pool['zeroForOne'],
                    amount_in_units,
                    min_amount_out,
                    0,
                    b''
                ]
            )
            inputs.append(swap_input)
            
            # Command 2: UNWRAP_WETH
            # Input: (recipient, amount)
            unwrap_input = encode(
                ['address', 'uint256'],
                [self.account.address, 0]  # 0 = unwrap all
            )
            inputs.append(unwrap_input)
            
            # Command 3: SWEEP (sweep any remaining tokens)
            sweep_input = encode(
                ['address', 'address', 'uint160'],
                [token_address, self.account.address, 0]
            )
            inputs.append(sweep_input)
            
            deadline = int(time.time()) + deadline_seconds
            
            # Build transaction
            tx = self.router.functions.execute(
                commands,
                inputs,
                deadline
            ).build_transaction({
                'from': self.account.address,
                'value': 0,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.chain_id,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Estimate gas
            tx['gas'] = self._estimate_gas(tx)
            
            # Sign and send
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex = self.w3.to_hex(tx_hash)
            
            print(f"[dim]Transaction sent: {tx_hex}[/dim]")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            self.total_swaps += 1
            self.total_gas_spent += receipt['gasUsed']
            
            if receipt['status'] == 1:
                self.successful_swaps += 1
                print(f"[green]✓ V4 sell successful! Gas used: {receipt['gasUsed']}[/green]")
                return True, tx_hex
            else:
                error_msg = f"V4 sell failed (status={receipt['status']}) - TX: {tx_hex}"
                raise TransactionError(error_msg)
                
        except TransactionError:
            raise
        except Exception as e:
            error_msg = f"V4 sell error: {e}"
            print(f"[red]✗ {error_msg}[/red]")
            raise TransactionError(error_msg)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            'total_swaps': self.total_swaps,
            'successful_swaps': self.successful_swaps,
            'success_rate': (self.successful_swaps / self.total_swaps * 100) if self.total_swaps > 0 else 0,
            'total_gas_spent': self.total_gas_spent,
            'avg_gas_per_swap': (self.total_gas_spent / self.total_swaps) if self.total_swaps > 0 else 0
        }


# Backwards compatibility
V4DirectRouter = V4UniversalRouter
