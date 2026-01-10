# tests/test_trading.py
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock

from core.trading.capital_manager import CapitalManager, Operation
from core.trading.risk_zero_calculator import RiskZeroCalculator
from core.trading.stop_loss_manager import StopLossManager
from core.trading.signal_generator import SignalGenerator, TradingSignal, SignalType, SignalStrength

@pytest.fixture
def mock_trading_config():
    config = Mock()
    config.trading.capital.max_capital_per_trade_pct = Decimal('0.10')
    config.trading.capital.max_concurrent_operations = 5
    config.trading.capital.risk_zero_buffer_pct = Decimal('0.002')
    config.trading.capital.stop_loss_pct = Decimal('0.02')
    config.trading.capital.take_profit_pct = Decimal('0.05')
    config.trading.capital.trailing_stop_activation_pct = Decimal('0.005')
    config.trading.capital.trailing_stop_distance_pct = Decimal('0.002')
    config.trading.orca_fee_pct = Decimal('0.0025')
    config.current_capital_usdc = Decimal('10000')
    config.base_dir = "test_dir"
    config.logger = Mock()
    return config

def test_capital_manager_initialization(mock_trading_config):
    """Test inicialización de gestor de capital"""
    manager = CapitalManager(mock_trading_config)
    
    assert manager.config == mock_trading_config
    assert len(manager.operations) == 0
    assert len(manager.active_pairs) == 0
    assert manager.max_concurrent == 5
    
    # Test cálculo de posición
    position_size, details = manager.calculate_position_size(
        asset_price=Decimal('100'),
        confidence_score=0.8
    )
    
    assert position_size > 0
    assert 'final_position_size' in details

def test_risk_zero_calculator(mock_trading_config):
    """Test calculador de riesgo cero"""
    calculator = RiskZeroCalculator(mock_trading_config)
    
    # Test cálculo básico
    calculation = calculator.calculate_risk_zero(
        entry_price=Decimal('100'),
        position_size=Decimal('1000'),
        fees_pct=Decimal('0.005')
    )
    
    assert calculation.risk_zero_price > calculation.entry_price
    assert calculation.required_gain_pct > 0
    assert calculation.buffer_pct == Decimal('0.002')
    
    # Test verificación de riesgo cero alcanzable
    achieved, remaining, details = calculator.verify_risk_zero_achievable(
        entry_price=Decimal('100'),
        current_price=Decimal('102'),
        position_size=Decimal('1000'),
        fees_pct=Decimal('0.005')
    )
    
    assert 'already_achieved' in details
    assert 'required_gain_remaining_amount' in details

def test_stop_loss_manager(mock_trading_config):
    """Test gestor de stop loss"""
    manager = StopLossManager(mock_trading_config)
    
    # Test stop loss fijo
    fixed_sl = manager.create_fixed_stop_loss(
        entry_price=Decimal('100'),
        stop_loss_pct=Decimal('0.02')
    )
    
    assert fixed_sl == Decimal('98.0')  # 100 * (1 - 0.02)
    
    # Test trailing stop
    trailing_sl = manager.create_trailing_stop_loss(
        entry_price=Decimal('100'),
        current_price=Decimal('106'),  # 6% ganancia
        activation_pct=Decimal('0.005'),  # 0.5% activación
        distance_pct=Decimal('0.002')  # 0.2% distancia
    )
    
    assert trailing_sl is not None
    assert trailing_sl < Decimal('106')
    
    # Test verificación de trigger
    should_trigger = manager.should_trigger_stop_loss(
        current_price=Decimal('97'),
        stop_loss_price=Decimal('98'),
        operation_side="BUY"
    )
    
    assert should_trigger == True

def test_signal_generator(mock_trading_config):
    """Test generador de señales"""
    generator = SignalGenerator(mock_trading_config)
    
    # Test análisis RSI
    signal, confidence = generator._analyze_rsi(25)  # RSI sobreventa
    assert signal == SignalType.BUY
    assert confidence > 0
    
    signal, confidence = generator._analyze_rsi(75)  # RSI sobrecompra
    assert signal == SignalType.SELL
    assert confidence > 0
    
    # Test análisis MACD
    signal, confidence = generator._analyze_macd(0.001, 0.0005)  # MACD > señal
    assert signal == SignalType.BUY
    assert confidence > 0
    
    # Test generación de señal completa
    indicators = {
        'rsi': 30,
        'macd': 0.001,
        'macd_signal': 0.0005,
        'bb_position': 0.1,
        'bb_width': 0.5,
        'volume_ratio': 2.5,
        'volume_trend': 'increasing',
        'trend_direction': 'up',
        'trend_strength': 0.8
    }
    
    price_data = {
        'current_price': 100.0,
        'support_level': 95.0,
        'resistance_level': 105.0,
        'timestamp': datetime.now().isoformat(),
        'timeframe': '15m'
    }
    
    signal = generator.generate_signal(indicators, price_data)
    
    assert isinstance(signal, TradingSignal)
    assert signal.type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
    assert signal.confidence >= 0
    assert signal.strength in [SignalStrength.WEAK, SignalStrength.MODERATE, 
                              SignalStrength.STRONG, SignalStrength.VERY_STRONG]

def test_multi_operation_manager(mock_trading_config):
    """Test gestor multi-operación"""
    from core.trading.multi_operation_manager import MultiOperationManager
    
    capital_manager = Mock()
    manager = MultiOperationManager(mock_trading_config, capital_manager)
    
    # Verificar inicialización
    assert manager.max_concurrent == 5
    assert manager.stats['total_operations'] == 0
    assert manager.stats['active_operations'] == 0
    
    # Test verificación de apertura
    can_open = manager._can_open_operation("SOL/USDC")
    assert can_open == True  # Debería poder abrir inicialmente
    
    # Simular operaciones activas
    manager.stats['active_operations'] = 5
    can_open = manager._can_open_operation("SOL/USDC")
    assert can_open == False  # No debería poder abrir
    
    manager.stats['active_operations'] = 0
    manager.active_pairs.add("SOL/USDC")
    can_open = manager._can_open_operation("SOL/USDC")
    assert can_open == False  # Ya existe operación en este par