# tests/test_ml.py
import pytest
import numpy as np
import pandas as pd
from decimal import Decimal
from unittest.mock import Mock

from core.ml_engine.lstm_predictor import LSTMPredictor
from core.ml_engine.feature_extractor import FeatureExtractor
from core.ml_engine.probability_calculator import ProbabilityCalculator

@pytest.fixture
def mock_ml_config():
    config = Mock()
    config.ml_confidence_threshold = 0.75
    config.ml_sequence_length = 60
    config.base_dir = "test_dir"
    config.models_dir = "test_dir/models"
    config.logger = Mock()
    return config

def test_feature_extractor_initialization(mock_ml_config):
    """Test inicialización de extractor de características"""
    extractor = FeatureExtractor(mock_ml_config)
    
    assert extractor.config == mock_ml_config
    assert 'technical' in extractor.feature_config
    assert 'temporal' in extractor.feature_config
    assert 'volume' in extractor.feature_config
    assert 'market' in extractor.feature_config

def test_feature_extraction():
    """Test extracción de características básicas"""
    config = Mock()
    extractor = FeatureExtractor(config)
    
    # Crear datos de prueba
    dates = pd.date_range('2024-01-01', periods=100, freq='1min')
    data = pd.DataFrame({
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 101,
        'low': np.random.randn(100).cumsum() + 99,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    # Extraer características
    feature_set = extractor.extract_features(data)
    
    # Verificar que se extrajeron características
    assert feature_set.technical.shape[1] > 0
    assert feature_set.temporal.shape[1] > 0
    assert feature_set.volume.shape[1] > 0
    assert feature_set.market.shape[1] > 0
    assert len(feature_set.labels) == len(data)

def test_probability_calculator(mock_ml_config):
    """Test calculador de probabilidades"""
    calculator = ProbabilityCalculator(mock_ml_config)
    
    # Test cálculo simple
    features = np.random.randn(50)
    result = calculator.calculate_buy_probability(features)
    
    assert 'buy_probability' in result
    assert 'confidence' in result
    assert 'signal_strength' in result
    assert 0 <= result['buy_probability'] <= 1
    assert 0 <= result['confidence'] <= 1
    
    # Test cálculo de valor esperado
    ev = calculator.calculate_expected_value(
        probability=0.7,
        win_amount=100,
        loss_amount=50
    )
    assert isinstance(ev, float)
    
    # Test fracción de Kelly
    kelly = calculator.calculate_kelly_criterion(
        probability=0.6,
        win_loss_ratio=2.0
    )
    assert 0 <= kelly <= 1

def test_lstm_predictor_initialization(mock_ml_config):
    """Test inicialización de predictor LSTM"""
    predictor = LSTMPredictor(mock_ml_config)
    
    assert predictor.config == mock_ml_config
    assert predictor.device in ['cpu', 'cuda']
    
    # Test preparación de características
    ohlcv_data = {
        '5m': pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100, 101, 102],
            'volume': [1000, 2000, 3000]
        })
    }
    
    features = predictor.prepare_features(ohlcv_data)
    assert isinstance(features, list)

@pytest.mark.asyncio
async def test_training_pipeline(mock_ml_config):
    """Test pipeline de entrenamiento"""
    from core.ml_engine.training_pipeline import TrainingPipeline
    
    pipeline = TrainingPipeline(mock_ml_config)
    
    # Verificar configuración
    assert pipeline.training_config['test_size'] == 0.2
    assert pipeline.training_config['epochs'] == 50
    assert pipeline.training_config['learning_rate'] == 0.001
    
    # Test preparación de datos
    feature_sets = [{
        'features': np.random.randn(100, 10),
        'labels': np.random.randint(0, 2, 100)
    }]
    
    training_data = pipeline.prepare_training_data(feature_sets)
    
    assert 'X_train' in training_data
    assert 'X_val' in training_data
    assert 'X_test' in training_data
    assert 'y_train' in training_data
    assert 'y_val' in training_data
    assert 'y_test' in training_data
    assert training_data['data_stats']['train_samples'] > 0