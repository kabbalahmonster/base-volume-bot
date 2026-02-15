# Testing Guide

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### Specific Test File
```bash
pytest tests/test_wallet.py -v
```

### With Coverage
```bash
pytest tests/ -v --cov=. --cov-report=html
```

### Integration Tests Only
```bash
pytest tests/ -v -m integration
```

### Unit Tests Only
```bash
pytest tests/ -v -m unit
```

## Test Structure

```
tests/
├── test_wallet.py      # Wallet and encryption tests
├── test_config.py      # Configuration tests
├── test_dex_router.py  # DEX routing tests
├── test_zerox.py       # 0x aggregator tests
└── conftest.py         # Shared fixtures
```

## Writing Tests

### Unit Test Template
```python
def test_feature_name(self):
    """Test description."""
    # Arrange
    input_data = "test"
    
    # Act
    result = function(input_data)
    
    # Assert
    assert result == expected
```

### Integration Test Template
```python
@pytest.mark.integration
def test_live_feature():
    """Test requiring network."""
    # This test requires live RPC
    pass
```

## Coverage Goals

- Wallet: 90%+
- Config: 90%+
- Routers: 70%+
- Bot: 60%+

## CI/CD

Tests run automatically on:
- Push to main
- Pull requests
- Nightly builds
