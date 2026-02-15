"""
Uniswap V4 Trading Module
==========================

A reusable, token-agnostic trading module for Uniswap V4 on Base.

This module provides a simple API for interacting with Uniswap V4 pools,
handling all the complexity of V4's new architecture internally.

V4 Architecture:
- PoolManager: 0x36089ce6B79A1A30f67F6C7a6c39E28C2D1c4c2d (Base)
- UniversalRouter: 0x6c083a36f731ea994739ef5e8647d18553d41f76 (Base)

Usage:
    from v4_trading import V4Trader
    
    trader = V4Trader(w3, account)
    
    # Buy tokens with ETH
    success, tx_hash = trader.buy(token_address, amount_eth=0.1)
    
    # Sell tokens for ETH
    success, tx_hash = trader.sell(token_address, amount_tokens=100)

Author: OpenClaw
License: MIT
"""

from typing import Tuple, Optional, Union
from decimal import Decimal
from web3 import Web3
from eth_account import Account

from .pool_manager import V4PoolManager
from .universal_router import V4UniversalRouter
from .quoter import V4Quoter

# Constants
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"
POOL_MANAGER_ADDRESS = "0x36089ce6B79A1A30f67F6C7a6c39E28C2D1c4c2d"
UNIVERSAL_ROUTER_ADDRESS = "0x6c083a36f731ea994739ef5e8647d18553d41f76"

DEFAULT_FEE_TIER = 3000  # 0.3% - most common
DEFAULT_SLIPPAGE = 2.0   # 2% default slippage


class V4Trader:
    """
    Main trading interface for Uniswap V4.
    
    Provides a simple, token-agnostic API for buying and selling tokens
    through Uniswap V4 pools on Base.
    
    Example:
        >>> trader = V4Trader(w3, account)
        >>> success, result = trader.buy(token, amount_eth=0.5)
        >>> if success:
        ...     print(f"Bought! TX: {result}")
    """
    
    def __init__(
        self,
        w3: Web3,
        account: Account,
        pool_manager_address: str = POOL_MANAGER_ADDRESS,
        universal_router_address: str = UNIVERSAL_ROUTER_ADDRESS,
        default_slippage: float = DEFAULT_SLIPPAGE,
        default_fee_tier: int = DEFAULT_FEE_TIER
    ):
        """
        Initialize V4 trader.
        
        Args:
            w3: Web3 instance connected to Base
            account: Account for signing transactions
            pool_manager_address: PoolManager contract address
            universal_router_address: UniversalRouter contract address
            default_slippage: Default slippage tolerance (%)
            default_fee_tier: Default pool fee tier (100, 500, 3000, 10000)
        """
        self.w3 = w3
        self.account = account
        self.default_slippage = default_slippage
        self.default_fee_tier = default_fee_tier
        
        # Initialize components
        self.pool_manager = V4PoolManager(w3, pool_manager_address)
        self.router = V4UniversalRouter(w3, account, universal_router_address)
        self.quoter = V4Quoter(w3, self.pool_manager)
        
        # Cache for token info
        self._token_cache = {}
    
    def _get_token_decimals(self, token_address: str) -> int:
        """Get token decimals (with caching)."""
        token_address = self.w3.to_checksum_address(token_address)
        if token_address not in self._token_cache:
            token_contract = self.w3.eth.contract(
                address=token_address,
                abi=[
                    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
                    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
                ]
            )
            try:
                decimals = token_contract.functions.decimals().call()
                symbol = token_contract.functions.symbol().call()
                self._token_cache[token_address] = {'decimals': decimals, 'symbol': symbol}
            except Exception as e:
                # Fallback for non-standard tokens
                self._token_cache[token_address] = {'decimals': 18, 'symbol': 'UNKNOWN'}
        return self._token_cache[token_address]['decimals']
    
    def buy(
        self,
        token_address: str,
        amount_eth: Union[Decimal, float],
        slippage_percent: Optional[float] = None,
        fee_tier: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Buy tokens with ETH (swap ETH -> Token).
        
        Args:
            token_address: Token to buy
            amount_eth: Amount of ETH to spend
            slippage_percent: Max slippage allowed (uses default if not set)
            fee_tier: Pool fee tier (uses default if not set)
            
        Returns:
            Tuple of (success: bool, tx_hash_or_error: str)
        """
        token_address = self.w3.to_checksum_address(token_address)
        amount_eth = Decimal(str(amount_eth))
        slippage = slippage_percent if slippage_percent is not None else self.default_slippage
        fee = fee_tier if fee_tier is not None else self.default_fee_tier
        
        print(f"[V4Trader] Buying {token_address} with {amount_eth} ETH (fee={fee})...")
        
        try:
            # Get token decimals
            token_decimals = self._get_token_decimals(token_address)
            
            # Get quote first
            pool_id = self.pool_manager.get_pool_id(WETH_ADDRESS, token_address, fee)
            slot0 = self.pool_manager.get_slot0(pool_id)
            
            if not slot0:
                return False, f"No pool found for {token_address} with fee {fee}"
            
            # Execute swap via UniversalRouter
            return self.router.swap_exact_in(
                token_in=WETH_ADDRESS,
                token_out=token_address,
                amount_in_eth=amount_eth,
                slippage_percent=slippage,
                fee_tier=fee
            )
            
        except Exception as e:
            return False, f"Buy error: {e}"
    
    def sell(
        self,
        token_address: str,
        amount_tokens: Union[Decimal, float],
        slippage_percent: Optional[float] = None,
        fee_tier: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Sell tokens for ETH (swap Token -> ETH).
        
        Args:
            token_address: Token to sell
            amount_tokens: Amount of tokens to sell
            slippage_percent: Max slippage allowed (uses default if not set)
            fee_tier: Pool fee tier (uses default if not set)
            
        Returns:
            Tuple of (success: bool, tx_hash_or_error: str)
        """
        token_address = self.w3.to_checksum_address(token_address)
        slippage = slippage_percent if slippage_percent is not None else self.default_slippage
        fee = fee_tier if fee_tier is not None else self.default_fee_tier
        
        print(f"[V4Trader] Selling {amount_tokens} tokens for ETH (fee={fee})...")
        
        try:
            # Get token decimals
            token_decimals = self._get_token_decimals(token_address)
            amount_in_wei = int(Decimal(str(amount_tokens)) * (10 ** token_decimals))
            
            # Check pool exists
            pool_id = self.pool_manager.get_pool_id(token_address, WETH_ADDRESS, fee)
            slot0 = self.pool_manager.get_slot0(pool_id)
            
            if not slot0:
                return False, f"No pool found for {token_address} with fee {fee}"
            
            # Execute swap via UniversalRouter
            return self.router.swap_exact_out(
                token_in=token_address,
                token_out=WETH_ADDRESS,
                amount_in_tokens=amount_tokens,
                token_decimals=token_decimals,
                slippage_percent=slippage,
                fee_tier=fee
            )
            
        except Exception as e:
            return False, f"Sell error: {e}"
    
    def get_price(
        self,
        token_address: str,
        fee_tier: Optional[int] = None
    ) -> Tuple[bool, Union[Decimal, str]]:
        """
        Get current token price in ETH.
        
        Args:
            token_address: Token address
            fee_tier: Pool fee tier
            
        Returns:
            Tuple of (success: bool, price_or_error: str/Decimal)
        """
        token_address = self.w3.to_checksum_address(token_address)
        fee = fee_tier if fee_tier is not None else self.default_fee_tier
        
        try:
            pool_id = self.pool_manager.get_pool_id(WETH_ADDRESS, token_address, fee)
            return self.quoter.get_price_in_eth(token_address, pool_id)
        except Exception as e:
            return False, f"Price error: {e}"
    
    def get_pool_info(
        self,
        token0: str,
        token1: str,
        fee_tier: Optional[int] = None
    ) -> dict:
        """
        Get information about a V4 pool.
        
        Args:
            token0: First token address
            token1: Second token address
            fee_tier: Pool fee tier
            
        Returns:
            Dictionary with pool info
        """
        token0 = self.w3.to_checksum_address(token0)
        token1 = self.w3.to_checksum_address(token1)
        fee = fee_tier if fee_tier is not None else self.default_fee_tier
        
        pool_id = self.pool_manager.get_pool_id(token0, token1, fee)
        slot0 = self.pool_manager.get_slot0(pool_id)
        
        return {
            'pool_id': pool_id,
            'token0': token0,
            'token1': token1,
            'fee': fee,
            'sqrtPriceX96': slot0.get('sqrtPriceX96') if slot0 else None,
            'tick': slot0.get('tick') if slot0 else None,
            'liquidity': slot0.get('liquidity') if slot0 else None,
        }


__all__ = [
    'V4Trader',
    'V4PoolManager',
    'V4UniversalRouter',
    'V4Quoter',
    'WETH_ADDRESS',
    'POOL_MANAGER_ADDRESS',
    'UNIVERSAL_ROUTER_ADDRESS',
]
