"""
V4 Quoter Module
================

Handles price quoting and calculations for Uniswap V4 pools.

V4 uses the same pricing mechanics as V3 (concentrated liquidity),
but pool identification works differently (pool IDs vs addresses).
"""

from typing import Tuple, Optional, Union
from decimal import Decimal, ROUND_HALF_UP
from web3 import Web3

from .pool_manager import V4PoolManager


class V4Quoter:
    """
    Price quoting for V4 pools.
    
    Provides functions to:
    - Get current prices from pools
    - Calculate expected output amounts
    - Convert between sqrtPriceX96 and human-readable prices
    
    Example:
        >>> quoter = V4Quoter(w3, pool_manager)
        >>> price = quoter.get_price_in_eth(USDC, pool_id)
        >>> amount_out = quoter.quote_exact_input(pool_id, 1000, 6, 18)
    """
    
    # Q96 constant for price calculations
    Q96 = 2**96
    
    def __init__(self, w3: Web3, pool_manager: V4PoolManager):
        """
        Initialize quoter.
        
        Args:
            w3: Web3 instance
            pool_manager: V4PoolManager instance
        """
        self.w3 = w3
        self.pool_manager = pool_manager
    
    def sqrt_price_x96_to_price(self, sqrt_price_x96: int, token0_decimals: int, token1_decimals: int) -> Decimal:
        """
        Convert sqrtPriceX96 to human-readable price.
        
        Price = (sqrtPriceX96 / Q96)^2 * 10^(token0_decimals - token1_decimals)
        
        Args:
            sqrt_price_x96: sqrt(price) * Q96 from pool
            token0_decimals: Decimals of token0
            token1_decimals: Decimals of token1
            
        Returns:
            Price as Decimal (token1 per token0)
        """
        # Calculate price = (sqrtPriceX96 / Q96) ^ 2
        sqrt_price = Decimal(sqrt_price_x96) / Decimal(self.Q96)
        price = sqrt_price ** 2
        
        # Adjust for decimals: price = price * 10^(token0_decimals - token1_decimals)
        decimal_adjustment = Decimal(10) ** (token0_decimals - token1_decimals)
        price = price * decimal_adjustment
        
        return price
    
    def price_to_sqrt_price_x96(self, price: Decimal, token0_decimals: int, token1_decimals: int) -> int:
        """
        Convert human-readable price to sqrtPriceX96.
        
        Args:
            price: Human-readable price (token1 per token0)
            token0_decimals: Decimals of token0
            token1_decimals: Decimals of token1
            
        Returns:
            sqrtPriceX96 value
        """
        # Adjust for decimals
        decimal_adjustment = Decimal(10) ** (token0_decimals - token1_decimals)
        adjusted_price = price / decimal_adjustment
        
        # sqrtPriceX96 = sqrt(price) * Q96
        sqrt_price = adjusted_price.sqrt()
        sqrt_price_x96 = int(sqrt_price * Decimal(self.Q96))
        
        return sqrt_price_x96
    
    def get_price_in_eth(
        self,
        token_address: str,
        pool_id: str,
        token_decimals: int = 18
    ) -> Tuple[bool, Union[Decimal, str]]:
        """
        Get token price in ETH.
        
        Args:
            token_address: Token address
            pool_id: Pool ID (ETH/Token pool)
            token_decimals: Token decimals
            
        Returns:
            Tuple of (success, price_or_error)
        """
        try:
            slot0 = self.pool_manager.get_slot0(pool_id)
            
            if not slot0:
                return False, "Pool not found"
            
            sqrt_price_x96 = slot0['sqrtPriceX96']
            
            # Determine which token is ETH (WETH)
            # For WETH/TOKEN pool, we need to know which is token0
            # This is a simplified version - in production, you'd store this info
            
            # Assume token is token1, ETH is token0 for calculation
            # Price = token price in ETH
            price = self.sqrt_price_x96_to_price(sqrt_price_x96, 18, token_decimals)
            
            return True, price
            
        except Exception as e:
            return False, f"Price calculation error: {e}"
    
    def get_price_in_usd(
        self,
        token_address: str,
        pool_id: str,
        eth_price_usd: Decimal,
        token_decimals: int = 18
    ) -> Tuple[bool, Union[Decimal, str]]:
        """
        Get token price in USD.
        
        Args:
            token_address: Token address
            pool_id: Pool ID (ETH/Token pool)
            eth_price_usd: Current ETH price in USD
            token_decimals: Token decimals
            
        Returns:
            Tuple of (success, price_or_error)
        """
        success, price_in_eth = self.get_price_in_eth(token_address, pool_id, token_decimals)
        
        if not success:
            return False, price_in_eth
        
        try:
            price_in_usd = price_in_eth * eth_price_usd
            return True, price_in_usd
        except Exception as e:
            return False, f"USD price calculation error: {e}"
    
    def quote_exact_input(
        self,
        pool_id: str,
        amount_in: int,
        token_in_decimals: int,
        token_out_decimals: int,
        zero_for_one: bool = True
    ) -> Tuple[bool, Union[int, str]]:
        """
        Quote expected output for exact input swap.
        
        Note: This is a simplified calculation. For production use,
        you'd want to simulate the swap through the actual pool math
        or use an on-chain quoter.
        
        Args:
            pool_id: Pool ID
            amount_in: Input amount (in token units)
            token_in_decimals: Input token decimals
            token_out_decimals: Output token decimals
            zero_for_one: Direction of swap
            
        Returns:
            Tuple of (success, amount_out_or_error)
        """
        try:
            slot0 = self.pool_manager.get_slot0(pool_id)
            
            if not slot0:
                return False, "Pool not found"
            
            sqrt_price_x96 = slot0['sqrtPriceX96']
            
            # Get current price
            price = self.sqrt_price_x96_to_price(
                sqrt_price_x96,
                token_in_decimals if zero_for_one else token_out_decimals,
                token_out_decimals if zero_for_one else token_in_decimals
            )
            
            # Simple quote: output = input * price * (1 - fee)
            # This is a rough estimate - real V4 quoting is more complex
            amount_in_decimal = Decimal(amount_in) / Decimal(10 ** token_in_decimals)
            
            # Get fee from slot0
            fee = slot0.get('swapFee', 3000) / 1_000_000  # Convert to decimal
            
            # Calculate output with fee
            amount_out_decimal = amount_in_decimal * price * (1 - Decimal(fee))
            amount_out = int(amount_out_decimal * Decimal(10 ** token_out_decimals))
            
            return True, amount_out
            
        except Exception as e:
            return False, f"Quote error: {e}"
    
    def quote_exact_output(
        self,
        pool_id: str,
        amount_out: int,
        token_in_decimals: int,
        token_out_decimals: int,
        zero_for_one: bool = True
    ) -> Tuple[bool, Union[int, str]]:
        """
        Quote required input for exact output swap.
        
        Args:
            pool_id: Pool ID
            amount_out: Output amount (in token units)
            token_in_decimals: Input token decimals
            token_out_decimals: Output token decimals
            zero_for_one: Direction of swap
            
        Returns:
            Tuple of (success, amount_in_or_error)
        """
        try:
            slot0 = self.pool_manager.get_slot0(pool_id)
            
            if not slot0:
                return False, "Pool not found"
            
            sqrt_price_x96 = slot0['sqrtPriceX96']
            
            # Get current price
            price = self.sqrt_price_x96_to_price(
                sqrt_price_x96,
                token_in_decimals if zero_for_one else token_out_decimals,
                token_out_decimals if zero_for_one else token_in_decimals
            )
            
            # Calculate required input
            amount_out_decimal = Decimal(amount_out) / Decimal(10 ** token_out_decimals)
            
            # Get fee from slot0
            fee = slot0.get('swapFee', 3000) / 1_000_000
            
            # input = output / price / (1 - fee)
            amount_in_decimal = amount_out_decimal / price / (1 - Decimal(fee))
            amount_in = int(amount_in_decimal * Decimal(10 ** token_in_decimals))
            
            return True, amount_in
            
        except Exception as e:
            return False, f"Quote error: {e}"
    
    def calculate_min_output(
        self,
        expected_output: int,
        slippage_percent: float
    ) -> int:
        """
        Calculate minimum output with slippage protection.
        
        Args:
            expected_output: Expected output amount
            slippage_percent: Slippage tolerance (%)
            
        Returns:
            Minimum acceptable output
        """
        slippage_decimal = Decimal(slippage_percent) / Decimal(100)
        min_output = int(Decimal(expected_output) * (Decimal(1) - slippage_decimal))
        return min_output
    
    def calculate_max_input(
        self,
        expected_input: int,
        slippage_percent: float
    ) -> int:
        """
        Calculate maximum input with slippage protection.
        
        Args:
            expected_input: Expected input amount
            slippage_percent: Slippage tolerance (%)
            
        Returns:
            Maximum acceptable input
        """
        slippage_decimal = Decimal(slippage_percent) / Decimal(100)
        max_input = int(Decimal(expected_input) * (Decimal(1) + slippage_decimal))
        return max_input
    
    def get_tick_at_sqrt_price(self, sqrt_price_x96: int) -> int:
        """
        Get the tick corresponding to a sqrtPriceX96.
        
        This is useful for understanding the current price position.
        
        Args:
            sqrt_price_x96: sqrt(price) * Q96
            
        Returns:
            Tick (log base 1.0001 of price)
        """
        import math
        
        # price = (sqrtPriceX96 / Q96)^2
        # tick = log(price) / log(1.0001)
        price = (Decimal(sqrt_price_x96) / Decimal(self.Q96)) ** 2
        tick = int(math.log(float(price), 1.0001))
        
        return tick
    
    def get_sqrt_price_at_tick(self, tick: int) -> int:
        """
        Get the sqrtPriceX96 at a given tick.
        
        Args:
            tick: Tick value
            
        Returns:
            sqrtPriceX96
        """
        # sqrt(price) = 1.0001^(tick/2)
        # sqrtPriceX96 = sqrt(price) * Q96
        sqrt_price = Decimal(1.0001) ** (Decimal(tick) / Decimal(2))
        sqrt_price_x96 = int(sqrt_price * Decimal(self.Q96))
        
        return sqrt_price_x96
    
    def calculate_price_impact(
        self,
        amount_in: int,
        amount_out: int,
        current_price: Decimal,
        token_in_decimals: int,
        token_out_decimals: int
    ) -> Decimal:
        """
        Calculate price impact of a swap.
        
        Args:
            amount_in: Input amount
            amount_out: Output amount
            current_price: Price before swap
            token_in_decimals: Input token decimals
            token_out_decimals: Output token decimals
            
        Returns:
            Price impact as decimal (e.g., 0.01 = 1%)
        """
        # Convert to decimal
        amount_in_dec = Decimal(amount_in) / Decimal(10 ** token_in_decimals)
        amount_out_dec = Decimal(amount_out) / Decimal(10 ** token_out_decimals)
        
        # Executed price
        executed_price = amount_out_dec / amount_in_dec
        
        # Price impact
        price_impact = abs(current_price - executed_price) / current_price
        
        return price_impact
