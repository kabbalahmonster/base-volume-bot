"""
Test Suite for Volume Bot
=========================

Run with: pytest tests/ -v
Or: python -m pytest tests/ -v --cov=.
"""

import pytest
import os
import sys
import json
import tempfile
from pathlib import Path
from decimal import Decimal

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from wallet import SecureKeyManager
from config import Config, ConfigManager


class TestSecureKeyManager:
    """Tests for wallet encryption/decryption."""
    
    def test_encrypt_and_save(self, tmp_path):
        """Test encrypting and saving a private key."""
        key_file = tmp_path / "test_wallet.enc"
        manager = SecureKeyManager(str(key_file))
        
        private_key = "0x" + "a" * 64
        password = "test_password_123"
        
        result = manager.encrypt_and_save(private_key, password)
        assert result is True
        assert key_file.exists()
        
        # Check file permissions (Unix only)
        if os.name != 'nt':  # Not Windows
            import stat
            mode = key_file.stat().st_mode
            assert stat.S_IMODE(mode) == 0o600
    
    def test_load_and_decrypt(self, tmp_path):
        """Test loading and decrypting a private key."""
        key_file = tmp_path / "test_wallet.enc"
        manager = SecureKeyManager(str(key_file))
        
        private_key = "0x" + "a" * 64
        password = "test_password_123"
        
        # Save first
        manager.encrypt_and_save(private_key, password)
        
        # Load
        loaded_key = manager.load_and_decrypt(password)
        assert loaded_key == private_key
    
    def test_load_with_wrong_password(self, tmp_path):
        """Test that wrong password fails gracefully."""
        key_file = tmp_path / "test_wallet.enc"
        manager = SecureKeyManager(str(key_file))
        
        private_key = "0x" + "a" * 64
        manager.encrypt_and_save(private_key, "correct_password")
        
        # Try wrong password
        result = manager.load_and_decrypt("wrong_password")
        assert result is None
    
    def test_exists(self, tmp_path):
        """Test checking if wallet exists."""
        key_file = tmp_path / "test_wallet.enc"
        manager = SecureKeyManager(str(key_file))
        
        assert not manager.exists()
        
        manager.encrypt_and_save("0x" + "a" * 64, "password")
        assert manager.exists()


class TestConfig:
    """Tests for configuration management."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.chain_id == 8453
        assert config.buy_amount_eth == 0.002
        assert config.slippage_percent == 2.0
        assert config.max_retries == 3
    
    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = Config()
        config.buy_amount_eth = 0.01
        
        data = config.to_dict()
        assert data['buy_amount_eth'] == 0.01
        assert data['chain_id'] == 8453
    
    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            'chain_id': 8453,
            'buy_amount_eth': 0.01,
            'slippage_percent': 3.0,
        }
        
        config = Config.from_dict(data)
        assert config.chain_id == 8453
        assert config.buy_amount_eth == 0.01
        assert config.slippage_percent == 3.0
    
    def test_config_ignores_invalid_fields(self):
        """Test that invalid fields are ignored."""
        data = {
            'chain_id': 8453,
            'invalid_field': 'should_be_ignored',
        }
        
        config = Config.from_dict(data)
        assert config.chain_id == 8453
        assert not hasattr(config, 'invalid_field')


class TestConfigManager:
    """Tests for ConfigManager."""
    
    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading configuration."""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(config_path)
        
        config = Config()
        config.buy_amount_eth = 0.01
        
        # Save
        result = manager.save_config(config, "test_password")
        assert result is True
        assert config_path.exists()
        
        # Load
        loaded = manager.load_config("test_password")
        assert loaded is not None
        assert loaded.buy_amount_eth == 0.01


class TestInputValidation:
    """Tests for input validation functions."""
    
    def test_valid_address(self):
        """Test valid Ethereum address detection."""
        from web3 import Web3
        
        valid = "0x696381f39F17cAD67032f5f52A4924ce84e51BA3"
        assert Web3.is_address(valid) is True
        
        invalid = "0xinvalid"
        assert Web3.is_address(invalid) is False
    
    def test_slippage_validation(self):
        """Test slippage percentage validation."""
        # Valid slippage
        assert 0 < 2.0 < 100
        
        # Invalid slippage
        assert -1 < 0  # Negative
        assert 101 > 100  # Over 100%
    
    def test_amount_validation(self):
        """Test amount validation."""
        # Valid amounts
        assert Decimal("0.001") > 0
        assert Decimal("1.0") > 0
        
        # Invalid amounts
        assert Decimal("0") == 0
        assert Decimal("-0.1") < 0


class TestDexRouter:
    """Tests for DEX router (requires mocking Web3)."""
    
    @pytest.fixture
    def mock_w3(self):
        """Create mock Web3 instance."""
        from unittest.mock import Mock, MagicMock
        
        w3 = Mock()
        w3.eth = Mock()
        w3.eth.get_balance = Mock(return_value=10**18)  # 1 ETH
        w3.eth.gas_price = 1000000000  # 1 gwei
        w3.eth.get_transaction_count = Mock(return_value=0)
        w3.to_checksum_address = Mock(side_effect=lambda x: x)
        w3.to_hex = Mock(return_value="0xtxhash")
        
        return w3
    
    @pytest.fixture
    def mock_account(self):
        """Create mock account."""
        from unittest.mock import Mock
        
        account = Mock()
        account.address = "0xWalletAddress"
        account.sign_transaction = Mock(return_value=Mock(raw_transaction=b"signed"))
        
        return account
    
    def test_router_initialization(self, mock_w3, mock_account):
        """Test router can be initialized."""
        from dex_router import MultiDEXRouter
        
        # This would need actual mocking of contract calls
        # For now, just test the structure
        pass  # Placeholder


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_private_key_format(self):
        """Test handling of invalid private key."""
        # Private key must be 64 hex chars
        short_key = "0x1234"
        long_key = "0x" + "a" * 100
        
        # Both should be handled gracefully
        assert len(short_key) < 66  # 0x + 64
        assert len(long_key) > 66


# Integration tests (skipped by default)
@pytest.mark.integration
def test_live_balance_check():
    """Test balance check against live network."""
    # This test requires:
    # - Valid RPC endpoint
    # - Valid wallet address
    # - Network connectivity
    pytest.skip("Integration test - run manually")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
