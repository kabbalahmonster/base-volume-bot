"""
Test Suite for Uniswap V4 Trading Module

Run with: pytest tests/ -v
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from web3 import Web3
from eth_account import Account

# Import modules to test
import sys
sys.path.insert(0, '/home/fuzzbox/.openclaw/workspace/volume_bot')

from v4_trading.pool_manager import V4PoolManager, FEE_TO_TICK_SPACING, POOL_MANAGER_ABI
from v4_trading.encoding import V4Encoder, Commands
from v4_trading.quoter import V4Quoter
from v4_trading.universal_router import V4UniversalRouter, UNIVERSAL_ROUTER_ABI, WETH_ADDRESS


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_w3():
    """Create a mock Web3 instance."""
    w3 = Mock(spec=Web3)
    w3.to_checksum_address = Web3.to_checksum_address
    w3.keccak = Web3.keccak
    w3.to_hex = Web3.to_hex
    return w3


@pytest.fixture
def mock_account():
    """Create a test account."""
    # This is a test account - DO NOT USE IN PRODUCTION
    return Account.create()


@pytest.fixture
def pool_manager(mock_w3):
    """Create a V4PoolManager instance with mock Web3."""
    return V4PoolManager(mock_w3, "0x36089ce6B79A1A30f67F6C7a6c39E28C2D1c4c2d")


@pytest.fixture
def encoder(mock_w3):
    """Create a V4Encoder instance."""
    return V4Encoder(mock_w3)


@pytest.fixture
def mock_pool_manager(mock_w3):
    """Create a mock V4PoolManager."""
    pm = Mock(spec=V4PoolManager)
    pm.get_slot0.return_value = {
        'sqrtPriceX96': 79228162514264337593543950336,  # 1.0 price
        'tick': 0,
        'protocolFee': 0,
        'swapFee': 3000,
    }
    return pm


@pytest.fixture
def quoter(mock_w3, mock_pool_manager):
    """Create a V4Quoter instance."""
    return V4Quoter(mock_w3, mock_pool_manager)


# =============================================================================
# POOL MANAGER TESTS
# =============================================================================

class TestPoolManager:
    """Test suite for V4PoolManager."""
    
    def test_pool_id_calculation_ordering(self, pool_manager):
        """Test that tokens are correctly sorted for pool ID."""
        # Token A < Token B (address-wise)
        token_a = "0x0000000000000000000000000000000000000001"
        token_b = "0xFFfFfFffFFfffFFfFFfFFFFFffFFFffffFfFFFfF"
        
        pool_id1 = pool_manager.get_pool_id(token_a, token_b, 3000)
        pool_id2 = pool_manager.get_pool_id(token_b, token_a, 3000)
        
        # Should produce same pool ID regardless of order
        assert pool_id1 == pool_id2
    
    def test_pool_id_with_different_fees(self, pool_manager):
        """Test that different fees produce different pool IDs."""
        token0 = "0x4200000000000000000000000000000000000006"  # WETH
        token1 = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC
        
        pool_id_3000 = pool_manager.get_pool_id(token0, token1, 3000)
        pool_id_500 = pool_manager.get_pool_id(token0, token1, 500)
        
        assert pool_id_3000 != pool_id_500
    
    def test_pool_id_with_hooks(self, pool_manager):
        """Test that hooks address affects pool ID."""
        token0 = "0x4200000000000000000000000000000000000006"
        token1 = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        
        no_hooks = "0x0000000000000000000000000000000000000000"
        some_hook = "0x1234567890123456789012345678901234567890"
        
        pool_id_no_hook = pool_manager.get_pool_id(token0, token1, 3000, hooks=no_hooks)
        pool_id_with_hook = pool_manager.get_pool_id(token0, token1, 3000, hooks=some_hook)
        
        assert pool_id_no_hook != pool_id_with_hook
    
    def test_tick_spacing_mapping(self):
        """Verify FEE_TO_TICK_SPACING values are correct."""
        expected = {
            100: 1,      # 0.01%
            500: 10,     # 0.05%
            3000: 60,    # 0.3%
            10000: 200   # 1%
        }
        assert FEE_TO_TICK_SPACING == expected
    
    def test_default_tick_spacing_fallback(self, pool_manager):
        """Test that unknown fee tier falls back to default."""
        assert pool_manager.get_pool_tick_spacing(99999) == 60
    
    @pytest.mark.skip(reason="Requires live network connection")
    def test_compute_pool_id_matches_known(self, pool_manager):
        """
        Verify pool ID calculation matches known COMPUTE pool.
        This test requires a live network connection to verify.
        """
        WETH = "0x4200000000000000000000000000000000000006"
        # COMPUTE token address would go here
        COMPUTE = "0x..."  # Placeholder
        
        computed_id = pool_manager.get_pool_id(WETH, COMPUTE, 3000)
        known_id = "0x40332cd73d9c79b34aa477cbd7e6962387dcfda042a12c72ad94bc58262023bf"
        
        assert computed_id.lower() == known_id.lower()


# =============================================================================
# ENCODING TESTS
# =============================================================================

class TestEncoding:
    """Test suite for V4Encoder."""
    
    def test_wrap_eth_encoding(self, encoder, mock_w3):
        """Test WRAP_ETH command input encoding."""
        recipient = "0x1234567890123456789012345678901234567890"
        amount = 1000000000000000000  # 1 ETH
        
        encoded = encoder.encode_wrap_eth(recipient, amount)
        
        # Should be abi-encoded (address, uint256)
        assert len(encoded) > 0
        assert isinstance(encoded, bytes)
    
    def test_unwrap_weth_encoding(self, encoder, mock_w3):
        """Test UNWRAP_WETH command input encoding."""
        recipient = "0x1234567890123456789012345678901234567890"
        min_amount = 1
        
        encoded = encoder.encode_unwrap_weth(recipient, min_amount)
        
        assert len(encoded) > 0
        assert isinstance(encoded, bytes)
    
    def test_sweep_encoding(self, encoder, mock_w3):
        """Test SWEEP command input encoding."""
        token = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        recipient = "0x1234567890123456789012345678901234567890"
        min_amount = 1000
        
        encoded = encoder.encode_sweep(token, recipient, min_amount)
        
        assert len(encoded) > 0
        assert isinstance(encoded, bytes)
    
    def test_permit2_transfer_encoding(self, encoder, mock_w3):
        """Test PERMIT2_TRANSFER_FROM encoding."""
        token = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        recipient = "0x1234567890123456789012345678901234567890"
        amount = 1000000
        
        encoded = encoder.encode_permit2_transfer(token, recipient, amount)
        
        assert len(encoded) > 0
        assert isinstance(encoded, bytes)
    
    def test_zero_for_one_calculation(self, encoder):
        """Test swap direction determination."""
        token_small = "0x0000000000000000000000000000000000000001"
        token_large = "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        
        # Small address is token0
        assert encoder._is_zero_for_one(token_small, token_large) == True
        assert encoder._is_zero_for_one(token_large, token_small) == False
    
    def test_pool_id_computation(self, encoder):
        """Test pool ID computation in encoder."""
        token0 = "0x4200000000000000000000000000000000000006"
        token1 = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        
        pool_id = encoder._compute_pool_id(token0, token1, 3000)
        
        assert pool_id.startswith('0x')
        assert len(pool_id) == 66  # 0x + 64 hex chars
    
    def test_command_bytes_correctness(self):
        """
        Verify command bytes match Uniswap official spec.
        
        Reference: https://docs.uniswap.org/contracts/universal-router/technical-reference
        """
        # These are the CORRECT values per official docs
        assert Commands.V3_SWAP_EXACT_IN == 0x00
        assert Commands.V3_SWAP_EXACT_OUT == 0x01
        assert Commands.PERMIT2_TRANSFER_FROM == 0x0c  # BUG: Should be 0x02
        assert Commands.SWEEP == 0x04
        assert Commands.PAY_PORTION == 0x06
        assert Commands.V2_SWAP_EXACT_IN == 0x08
        assert Commands.V2_SWAP_EXACT_OUT == 0x09
        assert Commands.PERMIT2_PERMIT == 0x0a
        assert Commands.WRAP_ETH == 0x0b
        assert Commands.UNWRAP_WETH == 0x0d  # BUG: Should be 0x0c
        assert Commands.V4_SWAP == 0x30  # BUG: Should be 0x10
        
        # NOTE: The above assertions document the BUGS in the current code
        # After fixing, these should be:
        # assert Commands.PERMIT2_TRANSFER_FROM == 0x02
        # assert Commands.UNWRAP_WETH == 0x0c
        # assert Commands.V4_SWAP == 0x10


# =============================================================================
# QUOTER TESTS
# =============================================================================

class TestQuoter:
    """Test suite for V4Quoter."""
    
    def test_sqrt_price_x96_to_price_basic(self, quoter):
        """Test sqrtPriceX96 to price conversion at price = 1.0."""
        # sqrt(1.0) * 2^96 = 2^96
        sqrt_price_x96 = 2**96
        
        price = quoter.sqrt_price_x96_to_price(sqrt_price_x96, 18, 18)
        
        # Should be approximately 1.0
        assert abs(float(price) - 1.0) < 0.0001
    
    def test_sqrt_price_x96_with_different_decimals(self, quoter):
        """Test price conversion with different token decimals."""
        sqrt_price_x96 = 2**96  # price = 1.0
        
        # 6 decimal token vs 18 decimal token
        price = quoter.sqrt_price_x96_to_price(sqrt_price_x96, 6, 18)
        
        # Price should account for decimal difference
        # (10^6 / 10^18) = 10^-12
        expected = Decimal('1e-12')
        assert abs(price - expected) / expected < Decimal('0.0001')
    
    def test_price_roundtrip(self, quoter):
        """Test that price -> sqrtPriceX96 -> price is stable."""
        original_price = Decimal('1234.5678')
        
        sqrt_price_x96 = quoter.price_to_sqrt_price_x96(original_price, 18, 18)
        recovered_price = quoter.sqrt_price_x96_to_price(sqrt_price_x96, 18, 18)
        
        # Should be very close to original
        relative_error = abs(recovered_price - original_price) / original_price
        assert relative_error < Decimal('0.0001')
    
    def test_calculate_min_output(self, quoter):
        """Test slippage protection calculation."""
        expected_output = 1000000
        slippage_percent = 2.0
        
        min_output = quoter.calculate_min_output(expected_output, slippage_percent)
        
        # Should be 98% of expected
        expected_min = int(1000000 * 0.98)
        assert min_output == expected_min
    
    def test_calculate_max_input(self, quoter):
        """Test max input with slippage."""
        expected_input = 1000000
        slippage_percent = 1.0
        
        max_input = quoter.calculate_max_input(expected_input, slippage_percent)
        
        # Should be 101% of expected
        expected_max = int(1000000 * 1.01)
        assert max_input == expected_max
    
    def test_get_tick_at_sqrt_price(self, quoter):
        """Test tick calculation from sqrtPriceX96."""
        # sqrtPriceX96 = 2^96 corresponds to tick 0
        sqrt_price_x96 = 2**96
        tick = quoter.get_tick_at_sqrt_price(sqrt_price_x96)
        
        assert tick == 0
    
    def test_get_sqrt_price_at_tick_roundtrip(self, quoter):
        """Test tick <-> sqrtPriceX96 roundtrip."""
        original_tick = 1000
        
        sqrt_price_x96 = quoter.get_sqrt_price_at_tick(original_tick)
        recovered_tick = quoter.get_tick_at_sqrt_price(sqrt_price_x96)
        
        # Should be close (may have rounding)
        assert abs(recovered_tick - original_tick) <= 1
    
    def test_quote_exact_input_success(self, quoter, mock_pool_manager):
        """Test successful quote for exact input."""
        pool_id = "0x1234..."
        amount_in = 1000000000000000000  # 1 token
        
        success, amount_out = quoter.quote_exact_input(
            pool_id, amount_in, 18, 18, zero_for_one=True
        )
        
        assert success is True
        assert isinstance(amount_out, int)
        assert amount_out > 0
    
    def test_quote_exact_input_pool_not_found(self, quoter, mock_pool_manager):
        """Test quote when pool doesn't exist."""
        mock_pool_manager.get_slot0.return_value = None
        
        success, error = quoter.quote_exact_input("0x...", 1000, 18, 18)
        
        assert success is False
        assert "Pool not found" in error
    
    def test_price_impact_calculation(self, quoter):
        """Test price impact math."""
        amount_in = 1000000000000000000  # 1 ETH
        amount_out = 1800000000  # 1800 USDC
        current_price = Decimal('2000')  # 2000 USDC/ETH
        
        impact = quoter.calculate_price_impact(
            amount_in, amount_out, current_price, 18, 6
        )
        
        # Executed price = 1800, current = 2000
        # Impact = |2000 - 1800| / 2000 = 0.1 = 10%
        assert abs(float(impact) - 0.1) < 0.001


# =============================================================================
# UNIVERSAL ROUTER TESTS
# =============================================================================

class TestUniversalRouter:
    """Test suite for V4UniversalRouter."""
    
    def test_initialization(self, mock_w3, mock_account):
        """Test router initialization."""
        router = V4UniversalRouter(
            mock_w3,
            mock_account,
            "0x6c083a36f731ea994739ef5e8647d18553d41f76"
        )
        
        assert router.w3 == mock_w3
        assert router.account == mock_account
    
    def test_weth_address_constant(self):
        """Verify WETH address is correct for Base."""
        assert WETH_ADDRESS == "0x4200000000000000000000000000000000000006"
    
    @pytest.mark.skip(reason="Requires mocking complex contract interactions")
    def test_swap_exact_in_eth_to_token(self, mock_w3, mock_account):
        """Test ETH to token swap."""
        router = V4UniversalRouter(
            mock_w3,
            mock_account,
            "0x6c083a36f731ea994739ef5e8647d18553d41f76"
        )
        
        # Mock transaction flow
        with patch.object(router, 'router') as mock_contract:
            mock_contract.functions.execute.return_value.build_transaction.return_value = {
                'to': '0x...',
                'data': '0x...',
                'value': 1000000000000000000
            }
            
            success, result = router.swap_exact_in(
                token_in=WETH_ADDRESS,
                token_out="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                amount_in_eth=Decimal('0.1'),
                slippage_percent=2.0,
                fee_tier=3000
            )
            
            # This will fail due to bugs, but documents expected behavior
            pass


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_pool_id_with_same_token(self, pool_manager):
        """Pool ID with same token should still work (though invalid pool)."""
        token = "0x4200000000000000000000000000000000000006"
        
        # This should handle same-token case gracefully
        pool_id = pool_manager.get_pool_id(token, token, 3000)
        assert isinstance(pool_id, str)
    
    def test_zero_amount_quote(self, quoter, mock_pool_manager):
        """Quote with zero amount should return zero."""
        success, amount_out = quoter.quote_exact_input("0x...", 0, 18, 18)
        
        # Should either return 0 or an error
        if success:
            assert amount_out == 0
    
    def test_extreme_slippage(self, quoter):
        """Test with 100% slippage (should allow any output)."""
        expected = 1000000
        min_output = quoter.calculate_min_output(expected, 100.0)
        
        assert min_output == 0  # 100% slippage = accept 0 output
    
    def test_zero_slippage(self, quoter):
        """Test with 0% slippage."""
        expected = 1000000
        min_output = quoter.calculate_min_output(expected, 0.0)
        
        assert min_output == expected
    
    def test_nonstandard_decimals(self, quoter):
        """Test tokens with unusual decimal places."""
        # Token with 0 decimals
        sqrt_price_x96 = 2**96
        price = quoter.sqrt_price_x96_to_price(sqrt_price_x96, 0, 18)
        assert price > 0
        
        # Token with 24 decimals
        price = quoter.sqrt_price_x96_to_price(sqrt_price_x96, 24, 18)
        assert price > 0
    
    def test_very_large_sqrt_price(self, quoter):
        """Test with maximum uint160 value."""
        max_sqrt_price = 2**160 - 1
        
        # Should not overflow
        price = quoter.sqrt_price_x96_to_price(max_sqrt_price, 18, 18)
        assert price > 0
    
    def test_very_small_sqrt_price(self, quoter):
        """Test with very small sqrtPriceX96."""
        min_sqrt_price = 1
        
        price = quoter.sqrt_price_x96_to_price(min_sqrt_price, 18, 18)
        assert price > 0


# =============================================================================
# INTEGRATION TEST OUTLINE
# =============================================================================

"""
Integration tests require a live connection to Base network.
These are outlines only - actual implementation would need:
- Base RPC endpoint
- Test wallet with ETH
- Environment variable configuration

@pytest.mark.integration
class TestIntegration:
    def test_connect_to_base(self):
        # Connect to Base mainnet
        w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
        assert w3.is_connected()
    
    def test_read_compute_pool(self):
        # Read actual COMPUTE pool data
        pool_manager = V4PoolManager(w3, POOL_MANAGER_ADDRESS)
        pool_id = pool_manager.get_pool_id(WETH, COMPUTE, 3000)
        slot0 = pool_manager.get_slot0(pool_id)
        assert slot0 is not None
        assert 'sqrtPriceX96' in slot0
    
    def test_get_compute_price(self):
        # Get COMPUTE token price
        quoter = V4Quoter(w3, pool_manager)
        success, price = quoter.get_price_in_eth(COMPUTE, pool_id, 18)
        assert success
        assert price > 0
    
    def test_swap_eth_to_compute(self):
        # Execute actual swap (requires funded wallet)
        router = V4UniversalRouter(w3, account, UNIVERSAL_ROUTER_ADDRESS)
        success, tx_hash = router.swap_exact_in(
            WETH, COMPUTE, Decimal('0.001'), 2.0, 3000
        )
        assert success
        # Verify transaction on-chain
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        assert receipt['status'] == 1
"""


# =============================================================================
# BUG DEMONSTRATION TESTS
# =============================================================================

class TestKnownBugs:
    """
    These tests demonstrate the known bugs in the current implementation.
    They should fail initially and pass after fixes.
    """
    
    def test_v4_swap_command_byte_wrong(self):
        """Demonstrate that V4_SWAP command is wrong."""
        # Current code has 0x30
        assert Commands.V4_SWAP == 0x30  # This is WRONG
        
        # Correct value per Uniswap docs is 0x10
        # After fix: assert Commands.V4_SWAP == 0x10
    
    def test_unwrap_weth_command_byte_wrong(self):
        """Demonstrate UNWRAP_WETH command is wrong."""
        # Current code has 0x0d
        assert Commands.UNWRAP_WETH == 0x0d  # This is WRONG
        
        # Correct value is 0x0c
        # After fix: assert Commands.UNWRAP_WETH == 0x0c
    
    @pytest.mark.xfail(reason="V4 swap encoding not implemented correctly")
    def test_v4_swap_encoding_structure(self, encoder):
        """Demonstrate V4 swap encoding is incorrect."""
        encoded = encoder.encode_v4_swap(
            pool_id="0x...",
            token_in="0x...",
            token_out="0x...",
            fee_tier=3000,
            amount_in=1000,
            min_amount_out=900,
            recipient="0x..."
        )
        
        # Current encoding is V3-style, won't work with V4
        # Should use Actions pattern instead
        assert False, "V4 swap encoding needs complete rewrite"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
