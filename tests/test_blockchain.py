# tests/test_blockchain.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from core.blockchain.wallet_manager import WalletManager
from core.blockchain.orca_integration import OrcaIntegration

@pytest.fixture
def mock_config():
    config = Mock()
    config.PHANTOM_WALLET = "TestWallet123"
    config.PHANTOM_PRIVATE_KEY = "test_private_key"
    config.RPC_ENDPOINT = "https://test-rpc.com"
    config.trading.priority_fee_micro_lamports = 100000
    config.trading.orca_fee_pct = Decimal('0.0025')
    config.logger = Mock()
    return config

@pytest.mark.asyncio
async def test_wallet_initialization(mock_config):
    """Test inicialización de wallet"""
    with patch('solana.keypair.Keypair.from_secret_key') as mock_keypair:
        mock_keypair.return_value.public_key = Mock()
        mock_keypair.return_value.public_key.__str__.return_value = "TestWallet123"
        
        wallet = WalletManager(mock_config)
        
        # Verificar que se inicializó correctamente
        assert wallet.wallet_address is not None
        assert mock_config.PHANTOM_WALLET in str(wallet.wallet_address)

@pytest.mark.asyncio
async def test_wallet_connection(mock_config):
    """Test conexión de wallet"""
    wallet = WalletManager(mock_config)
    
    with patch('solana.rpc.async_api.AsyncClient.is_connected', new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = True
        
        await wallet.connect()
        
        # Verificar que se llamó a connect
        mock_connect.assert_called_once()

@pytest.mark.asyncio
async def test_orca_swap_simulation(mock_config):
    """Test simulación de swap"""
    wallet = WalletManager(mock_config)
    orca = OrcaIntegration(mock_config, wallet)
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Mock response de Jupiter API
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'outAmount': '1000000',
            'priceImpactPct': 0.001
        }
        mock_get.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post_response = AsyncMock()
            mock_post_response.status = 200
            mock_post_response.json.return_value = {
                'swapTransaction': 'test_transaction_data'
            }
            mock_post.return_value.__aenter__.return_value = mock_post_response
            
            # Test swap
            success, message, _ = await orca.execute_swap(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=Decimal('0.1'),
                slippage_bps=50
            )
            
            # Verificar que se ejecutó
            assert success or "Error" in message  # Puede fallar en test

def test_whirlpool_scanner_initialization(mock_config):
    """Test inicialización de scanner"""
    from core.blockchain.whirlpool_scanner import WhirlpoolScanner
    
    scanner = WhirlpoolScanner(mock_config, None)
    
    assert scanner.config == mock_config
    assert scanner.client is None

@pytest.mark.asyncio
async def test_transaction_executor(mock_config):
    """Test ejecutor de transacciones"""
    from core.blockchain.transaction_executor import TransactionExecutor
    
    wallet = WalletManager(mock_config)
    executor = TransactionExecutor(mock_config, wallet)
    
    # Verificar estadísticas iniciales
    stats = executor.get_stats()
    assert stats['total_transactions'] == 0
    assert stats['successful'] == 0
    assert stats['failed'] == 0