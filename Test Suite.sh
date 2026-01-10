# Run all tests
python -m pytest tests/

# Test blockchain connection
python scripts/test_blockchain.py

# Test ML pipeline
python tests/test_ml.py

# Test trading logic
python tests/test_trading.py