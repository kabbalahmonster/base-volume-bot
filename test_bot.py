#!/usr/bin/env python3
"""
Test Suite for $COMPUTE Volume Bot

Run with: python -m pytest tests/ -v
Or: python test_bot.py
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, ConfigManager
from utils import (
    format_wei, 
    format_eth, 
    format_duration, 
    format_address,
    validate_private_key,
    validate_address,
    calculate_slippage
)


class TestConfig(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
    
    def tearDown(self):
        if self.config_path.exists():
            self.config_path.unlink()
        os.rmdir(self.temp_dir)
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = Config()
        self.assertEqual(config.chain_id, 8453)
        self.assertEqual(config.buy_amount_eth, 0.002)
        self.assertEqual(config.sell_after_buys, 10)
    
    def test_config_encryption_decryption(self):
        """Test private key encryption and decryption."""
        manager = ConfigManager(self.config_path)
        
        config_data = {
            "rpc_url": "https://test.base.org",
            "chain_id": 8453,
        }
        
        private_key = "0x" + "a" * 64
        password = "test_password_123"
        
        # Create config
        config = manager.create_config(config_data, private_key, password)
        self.assertIsNotNone(config.encrypted_private_key)
        
        # Load and decrypt
        loaded_config = manager.load_config(password)
        self.assertEqual(loaded_config.encrypted_private_key, private_key)
    
    def test_config_password_rotation(self):
        """Test password rotation."""
        manager = ConfigManager(self.config_path)
        
        config_data = {"chain_id": 8453}
        private_key = "0x" + "b" * 64
        old_password = "old_pass"
        new_password = "new_pass"
        
        manager.create_config(config_data, private_key, old_password)
        manager.rotate_password(old_password, new_password)
        
        # Should be able to load with new password
        loaded = manager.load_config(new_password)
        self.assertEqual(loaded.encrypted_private_key, private_key)


class TestUtils(unittest.TestCase):
    """Test utility functions."""
    
    def test_format_wei(self):
        """Test wei formatting."""
        self.assertEqual(format_wei(0), "0")
        self.assertEqual(format_wei(10**18), "1.0000")
        self.assertEqual(format_wei(5 * 10**17), "0.50000000")
    
    def test_format_eth(self):
        """Test ETH formatting."""
        self.assertEqual(format_eth(0.5), "0.5000 ETH")
        self.assertEqual(format_eth(0.0005), "0.000500 ETH")
        self.assertEqual(format_eth(5), "5.00 ETH")
    
    def test_format_duration(self):
        """Test duration formatting."""
        self.assertEqual(format_duration(30), "30s")
        self.assertEqual(format_duration(90), "1m 30s")
        self.assertEqual(format_duration(3600), "1h 0m")
        self.assertEqual(format_duration(3665), "1h 1m")
    
    def test_format_address(self):
        """Test address formatting."""
        addr = "0x1234567890123456789012345678901234567890"
        formatted = format_address(addr, 4)
        self.assertEqual(formatted, "0x12...7890")
    
    def test_validate_private_key(self):
        """Test private key validation."""
        self.assertTrue(validate_private_key("0x" + "a" * 64))
        self.assertTrue(validate_private_key("b" * 64))
        self.assertFalse(validate_private_key("0x" + "a" * 63))  # Too short
        self.assertFalse(validate_private_key(""))
        self.assertFalse(validate_private_key("not_hex" * 10))
    
    def test_validate_address(self):
        """Test address validation."""
        valid = "0x696381f39F17cAD67032f5f52A4924ce84e51BA3"
        self.assertTrue(validate_address(valid))
        self.assertFalse(validate_address(""))
        self.assertFalse(validate_address("0x123"))
        self.assertFalse(validate_address("not_an_address"))
    
    def test_calculate_slippage(self):
        """Test slippage calculation."""
        self.assertEqual(calculate_slippage(100, 95), 5.0)
        self.assertEqual(calculate_slippage(100, 100), 0.0)
        self.assertEqual(calculate_slippage(100, 105), 5.0)


class TestWallet(unittest.TestCase):
    """Test wallet functionality (mocked)."""
    
    @patch('wallet.Web3')
    def test_wallet_initialization(self, mock_web3):
        """Test wallet initialization."""
        # Setup mocks
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 8453
        mock_web3.return_value = mock_w3
        
        config = Config(
            encrypted_private_key="0x" + "c" * 64,
            chain_id=8453
        )
        
        # Would need actual private key for full test
        # This tests the structure
        self.assertEqual(config.chain_id, 8453)


class TestTrader(unittest.TestCase):
    """Test trader functionality (mocked)."""
    
    def test_trade_result_structure(self):
        """Test trade result dataclass."""
        from trader import TradeResult
        
        result = TradeResult(
            success=True,
            tx_hash="0x123...",
            amount_in=0.1,
            amount_out=95.5,
            gas_used=150000
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.gas_used, 150000)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestWallet))
    suite.addTests(loader.loadTestsFromTestCase(TestTrader))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("🧪 Running $COMPUTE Volume Bot Tests\n")
    success = run_tests()
    sys.exit(0 if success else 1)
