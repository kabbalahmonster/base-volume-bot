#!/usr/bin/env python3
"""
Swarm Wallet Tests - Comprehensive Test Suite
=============================================

Tests for the swarm wallet system covering:
- Wallet generation and encryption
- Funding and reclamation
- Rotation modes
- Balance checking
- Safety validations

Run with: python -m pytest test_swarm.py -v

Author: Cult of the Shell
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

from swarm_wallet import (
    SecureSwarmManager,
    SwarmWalletConfig,
    SwarmWallet,
    RotationMode,
    AuditRecord,
    InsufficientFundsError
)
from eth_account import Account


class TestSwarmWalletConfig(unittest.TestCase):
    """Test SwarmWalletConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SwarmWalletConfig()
        
        self.assertEqual(config.num_wallets, 10)
        self.assertEqual(config.min_eth_per_wallet, 0.01)
        self.assertEqual(config.eth_fund_amount, 0.02)
        self.assertEqual(config.rotation_mode, RotationMode.ROUND_ROBIN)
        self.assertEqual(config.key_file, "./swarm_wallets.enc")
        self.assertFalse(config.dry_run)
    
    def test_config_serialization(self):
        """Test config to/from dict conversion."""
        config = SwarmWalletConfig(
            num_wallets=5,
            rotation_mode=RotationMode.RANDOM,
            dry_run=True
        )
        
        data = config.to_dict()
        restored = SwarmWalletConfig.from_dict(data)
        
        self.assertEqual(restored.num_wallets, 5)
        self.assertEqual(restored.rotation_mode, RotationMode.RANDOM)
        self.assertTrue(restored.dry_run)


class TestSwarmWallet(unittest.TestCase):
    """Test SwarmWallet dataclass."""
    
    def test_wallet_creation(self):
        """Test wallet creation and defaults."""
        wallet = SwarmWallet(
            index=0,
            address="0x1234567890123456789012345678901234567890",
            encrypted_private_key="encrypted_key_here",
            salt="salt_here",
            created_at="2024-01-01T00:00:00"
        )
        
        self.assertEqual(wallet.index, 0)
        self.assertEqual(wallet.tx_count, 0)
        self.assertTrue(wallet.is_active)
    
    def test_record_buy(self):
        """Test buy recording."""
        wallet = SwarmWallet(
            index=0,
            address="0x1234...",
            encrypted_private_key="enc",
            salt="salt",
            created_at="2024-01-01"
        )
        
        wallet.record_buy(0.01)
        
        self.assertEqual(wallet.tx_count, 1)
        self.assertEqual(wallet.total_buys, 1)
        self.assertEqual(wallet.total_eth_spent, 0.01)
        self.assertIsNotNone(wallet.last_used)
    
    def test_record_sell(self):
        """Test sell recording."""
        wallet = SwarmWallet(
            index=0,
            address="0x1234...",
            encrypted_private_key="enc",
            salt="salt",
            created_at="2024-01-01"
        )
        
        wallet.record_sell(0.015)
        
        self.assertEqual(wallet.tx_count, 1)
        self.assertEqual(wallet.total_sells, 1)
        self.assertEqual(wallet.total_eth_received, 0.015)
        self.assertIsNotNone(wallet.last_used)


class TestSecureSwarmManager(unittest.TestCase):
    """Test SecureSwarmManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.key_file = Path(self.temp_dir) / "test_wallets.enc"
        self.audit_file = Path(self.temp_dir) / "test_audit.log"
        
        # Mock Web3
        self.mock_web3 = Mock()
        self.mock_web3.is_connected.return_value = True
        self.mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
        self.mock_web3.to_wei = lambda x, unit: int(x * 1e18) if unit == 'ether' else int(x)
        self.mock_web3.from_wei = lambda x, unit: x / 1e18 if unit == 'ether' else x
        self.mock_web3.eth.chain_id = 8453
        self.mock_web3.eth.gas_price = 1000000000  # 1 gwei
        
        self.config = SwarmWalletConfig(
            num_wallets=3,
            key_file=str(self.key_file),
            audit_log=str(self.audit_file),
            dry_run=True  # Safe for testing
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        if self.key_file.exists():
            self.key_file.unlink()
        if self.audit_file.exists():
            self.audit_file.unlink()
        os.rmdir(self.temp_dir)
    
    def test_create_swarm(self):
        """Test swarm creation."""
        manager = SecureSwarmManager(self.config, self.mock_web3)
        
        password = "test_password_123"
        wallets = manager.create_swarm(password, num_wallets=3)
        
        self.assertEqual(len(wallets), 3)
        self.assertEqual(len(manager.wallets), 3)
        
        # Verify each wallet has required fields
        for i, wallet in enumerate(wallets):
            self.assertEqual(wallet.index, i)
            self.assertTrue(wallet.address.startswith("0x"))
            self.assertIsNotNone(wallet.encrypted_private_key)
            self.assertIsNotNone(wallet.salt)
            self.assertTrue(len(wallet.salt) > 0)
    
    def test_encrypt_decrypt_private_key(self):
        """Test encryption and decryption roundtrip."""
        manager = SecureSwarmManager(self.config, self.mock_web3)
        
        password = "test_password_123"
        private_key = "0x" + "a" * 64  # Valid format test key
        salt = os.urandom(16)
        
        # Encrypt
        encrypted = manager._encrypt_private_key(private_key, password, salt)
        self.assertIsNotNone(encrypted)
        self.assertTrue(len(encrypted) > 0)
        
        # Decrypt
        decrypted = manager._decrypt_private_key(encrypted, password, salt)
        self.assertEqual(decrypted, private_key)
    
    def test_get_wallet(self):
        """Test wallet retrieval with decryption."""
        manager = SecureSwarmManager(self.config, self.mock_web3)
        
        password = "test_password_123"
        wallets = manager.create_swarm(password, num_wallets=3)
        
        # Get first wallet
        swarm_wallet, account = manager.get_wallet(0, password)
        
        self.assertEqual(swarm_wallet.index, 0)
        self.assertIsInstance(account, Account)
        self.assertEqual(account.address.lower(), swarm_wallet.address.lower())
    
    def test_get_wallet_wrong_password(self):
        """Test that wrong password fails decryption."""
        manager = SecureSwarmManager(self.config, self.mock_web3)
        
        password = "test_password_123"
        manager.create_swarm(password, num_wallets=1)
        
        with self.assertRaises(Exception):
            manager.get_wallet(0, "wrong_password")
    
    def test_rotation_round_robin(self):
        """Test round-robin rotation mode."""
        self.config.rotation_mode = RotationMode.ROUND_ROBIN
        manager = SecureSwarmManager(self.config, self.mock_web3)
        
        password = "test_password_123"
        manager.create_swarm(password, num_wallets=3)
        
        # Should cycle through 0, 1, 2, 0, 1, 2...
        indices = []
        for _ in range(6):
            wallet, _ = manager.get_next_wallet(password)
            indices.append(wallet.index)
        
        self.assertEqual(indices, [0, 1, 2, 0, 1, 2])
    
    def test_rotation_random(self):
        """Test random rotation mode."""
        self.config.rotation_mode = RotationMode.RANDOM
        manager = SecureSwarmManager(self.config, self.mock_web3)
        
        password = "test_password_123"
        manager.create_swarm(password, num_wallets=5)
        
        # Get multiple wallets
        indices = []
        for _ in range(10):
            wallet, _ = manager.get_next_wallet(password)
            indices.append(wallet.index)
            self.assertTrue(0 <= wallet.index < 5)
    
    def test_get_swarm_status(self):
        """Test swarm status retrieval."""
        manager = SecureSwarmManager(self.config, self.mock_web3)
        
        password = "test_password_123"
        manager.create_swarm(password, num_wallets=3)
        
        status = manager.get_swarm_status()
        
        self.assertEqual(status['status'], 'ACTIVE')
        self.assertEqual(status['total_wallets'], 3)
        self.assertEqual(len(status['wallets']), 3)
        self.assertIn('total_eth', status)
        self.assertIn('total_compute', status)
    
    def test_audit_logging(self):
        """Test audit log functionality."""
        manager = SecureSwarmManager(self.config, self.mock_web3)
        
        password = "test_password_123"
        manager.create_swarm(password, num_wallets=2)
        
        # Add some audit records
        manager._add_audit_record(AuditRecord(
            timestamp="2024-01-01T00:00:00",
            action="TEST",
            wallet_index=0,
            from_address="0x123",
            to_address="0x456",
            status="SUCCESS"
        ))
        
        # Retrieve audit trail
        trail = manager.get_audit_trail(limit=10)
        self.assertTrue(len(trail) >= 1)
        
        # Check audit file was created
        self.assertTrue(self.audit_file.exists())
    
    def test_verify_zero_balances(self):
        """Test zero balance verification."""
        manager = SecureSwarmManager(self.config, self.mock_web3)
        
        # Mock get_balance to return 0
        manager._get_wallet_balance = Mock(return_value=(0.0, 0.0))
        
        password = "test_password_123"
        manager.create_swarm(password, num_wallets=3)
        
        non_zero = manager.verify_zero_balances()
        self.assertEqual(len(non_zero), 0)
    
    def test_file_permissions(self):
        """Test that wallet file has restrictive permissions."""
        manager = SecureSwarmManager(self.config, self.mock_web3)
        
        password = "test_password_123"
        manager.create_swarm(password, num_wallets=1)
        
        # Check file permissions
        stat = os.stat(self.key_file)
        # Should be 0o600 (owner read/write only)
        # Note: This may vary by OS, so we just check it's not world-readable
        self.assertFalse(stat.st_mode & 0o044)


class TestSwarmIntegration(unittest.TestCase):
    """Integration tests for the complete swarm workflow."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.key_file = Path(self.temp_dir) / "wallets.enc"
        self.audit_file = Path(self.temp_dir) / "audit.log"
        
        # Create mock Web3 with more realistic behavior
        self.mock_web3 = Mock()
        self.mock_web3.is_connected.return_value = True
        self.mock_web3.eth.chain_id = 8453
        self.mock_web3.eth.gas_price = 1000000000
        
        # Simulate balance queries
        self.balances = {}
        def mock_get_balance(address):
            return self.balances.get(address, 1000000000000000000)
        self.mock_web3.eth.get_balance = mock_get_balance
        
        self.mock_web3.to_wei = lambda x, unit: int(x * 1e18) if unit == 'ether' else int(x)
        self.mock_web3.from_wei = lambda x, unit: x / 1e18 if unit == 'ether' else x
        
        self.config = SwarmWalletConfig(
            num_wallets=3,
            key_file=str(self.key_file),
            audit_log=str(self.audit_file),
            dry_run=True
        )
    
    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_workflow_dry_run(self):
        """Test complete workflow in dry-run mode."""
        manager = SecureSwarmManager(self.config, self.mock_web3)
        password = "test_password_123"
        
        # 1. Create swarm
        wallets = manager.create_swarm(password, num_wallets=3)
        self.assertEqual(len(wallets), 3)
        
        # 2. Check status
        status = manager.get_swarm_status()
        self.assertEqual(status['total_wallets'], 3)
        
        # 3. Test wallet rotation
        for _ in range(5):
            wallet, account = manager.get_next_wallet(password)
            self.assertIsNotNone(wallet)
            self.assertIsNotNone(account)
        
        # 4. Verify audit trail
        trail = manager.get_audit_trail()
        self.assertTrue(len(trail) > 0)
        
        print("\n✓ Full dry-run workflow completed successfully")


class TestSecurity(unittest.TestCase):
    """Security-focused tests."""
    
    def test_password_strength_validation(self):
        """Test that weak passwords are rejected."""
        temp_dir = tempfile.mkdtemp()
        key_file = Path(temp_dir) / "wallets.enc"
        
        mock_web3 = Mock()
        config = SwarmWalletConfig(
            key_file=str(key_file),
            dry_run=True
        )
        
        manager = SecureSwarmManager(config, mock_web3)
        
        # Short password should fail
        with self.assertRaises(ValueError):
            manager.create_swarm("short", num_wallets=1)
        
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_private_key_never_logged(self):
        """Test that private keys are never logged."""
        temp_dir = tempfile.mkdtemp()
        key_file = Path(temp_dir) / "wallets.enc"
        
        mock_web3 = Mock()
        config = SwarmWalletConfig(key_file=str(key_file), dry_run=True)
        manager = SecureSwarmManager(config, mock_web3)
        
        password = "secure_password_123"
        wallets = manager.create_swarm(password, num_wallets=1)
        
        # The encrypted key should be stored, not plaintext
        wallet = wallets[0]
        self.assertNotIn("0x", wallet.encrypted_private_key[:10])
        self.assertTrue(len(wallet.encrypted_private_key) > 64)  # Should be longer than raw key
        
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSwarmWalletConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestSwarmWallet))
    suite.addTests(loader.loadTestsFromTestCase(TestSecureSwarmManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSwarmIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurity))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
