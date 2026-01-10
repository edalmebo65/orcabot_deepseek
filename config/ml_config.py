# config/ml_config.py
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict, Optional
from enum import Enum

class MLModelType(Enum):
    LSTM = "lstm"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    ENSEMBLE = "ensemble"

class FeatureGroup(Enum):
    TECHNICAL = "technical"
    TEMPORAL = "temporal"
    VOLUME = "volume"
    MARKET = "market"
    SENTIMENT = "sentiment"

@dataclass
class ModelConfig:
    """Configuración de modelo ML"""
    model_type: MLModelType
    sequence_length: int
    hidden_size: int
    num_layers: int
    dropout_rate: float
    learning_rate: float
    batch_size: int
    epochs: int
    
    @property
    def model_params(self) -> Dict:
        return {
            "type": self.model_type.value,
            "sequence_length": self.sequence_length,
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "dropout_rate": self.dropout_rate,
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "epochs": self.epochs
        }

@dataclass
class FeatureConfig:
    """Configuración de características"""
    enabled_groups: List[FeatureGroup]
    technical_indicators: List[str]
    temporal_features: List[str]
    volume_features: List[str]
    market_features: List[str]
    
    @property
    def total_features(self) -> int:
        return (
            len(self.technical_indicators) +
            len(self.temporal_features) +
            len(self.volume_features) +
            len(self.market_features)
        )

class MLConfig:
    """Configuración completa de Machine Learning"""
    
    def __init__(self):
        # Modelo principal
        self.primary_model = ModelConfig(
            model_type=MLModelType.LSTM,
            sequence_length=60,
            hidden_size=128,
            num_layers=3,
            dropout_rate=0.2,
            learning_rate=0.001,
            batch_size=32,
            epochs=50
        )
        
        # Modelos de respaldo
        self.backup_models = [
            ModelConfig(
                model_type=MLModelType.RANDOM_FOREST,
                sequence_length=1,
                hidden_size=0,
                num_layers=0,
                dropout_rate=0.0,
                learning_rate=0.0,
                batch_size=1,
                epochs=1
            )
        ]
        
        # Características
        self.features = FeatureConfig(
            enabled_groups=[
                FeatureGroup.TECHNICAL,
                FeatureGroup.TEMPORAL,
                FeatureGroup.VOLUME,
                FeatureGroup.MARKET
            ],
            technical_indicators=[
                "rsi", "macd", "stoch", "bbands", "atr",
                "adx", "cci", "mfi", "obv", "volume_ratio"
            ],
            temporal_features=[
                "hour_sin", "hour_cos", "day_sin", "day_cos",
                "month_sin", "month_cos", "is_weekend"
            ],
            volume_features=[
                "volume_ratio", "obv", "volume_zscore",
                "volume_trend", "volume_volatility"
            ],
            market_features=[
                "volatility_20", "volatility_50", "daily_spread",
                "liquidity_ratio", "trend_strength", "market_regime"
            ]
        )
        
        # Umbrales y parámetros
        self.confidence_threshold = 0.75
        self.min_samples_training = 1000
        self.retrain_interval_hours = 6
        self.validation_split = 0.2
        self.test_split = 0.1
        
        # Data handling
        self.history_days = 30
        self.update_frequency_minutes = 5
        self.max_data_points = 10000
        
        # Performance
        self.enable_incremental_training = True
        self.enable_model_ensemble = False
        self.model_ensemble_weights = [0.7, 0.3]  # [primary, backup]
        
        # Monitoring
        self.monitor_accuracy = True
        self.accuracy_threshold = 0.65
        self.auto_switch_on_low_accuracy = True
    
    def get_model_config(self, model_type: MLModelType = None) -> ModelConfig:
        """Obtiene configuración de modelo"""
        if model_type is None:
            return self.primary_model
        
        if model_type == self.primary_model.model_type:
            return self.primary_model
        
        for model in self.backup_models:
            if model.model_type == model_type:
                return model
        
        return self.primary_model
    
    def get_enabled_features(self) -> List[str]:
        """Obtiene lista de características habilitadas"""
        features = []
        
        if FeatureGroup.TECHNICAL in self.features.enabled_groups:
            features.extend(self.features.technical_indicators)
        
        if FeatureGroup.TEMPORAL in self.features.enabled_groups:
            features.extend(self.features.temporal_features)
        
        if FeatureGroup.VOLUME in self.features.enabled_groups:
            features.extend(self.features.volume_features)
        
        if FeatureGroup.MARKET in self.features.enabled_groups:
            features.extend(self.features.market_features)
        
        return features
    
    def validate(self) -> List[str]:
        """Valida configuración ML"""
        errors = []
        
        if self.confidence_threshold < 0.5 or self.confidence_threshold > 0.95:
            errors.append("Confidence threshold must be between 0.5 and 0.95")
        
        if self.primary_model.sequence_length < 10:
            errors.append("Sequence length too short (min 10)")
        
        if self.primary_model.sequence_length > 200:
            errors.append("Sequence length too long (max 200)")
        
        if len(self.features.enabled_groups) == 0:
            errors.append("At least one feature group must be enabled")
        
        if self.features.total_features == 0:
            errors.append("No features configured")
        
        if self.features.total_features > 100:
            errors.append(f"Too many features ({self.features.total_features}), max 100")
        
        if sum(self.model_ensemble_weights) != 1.0:
            errors.append("Model ensemble weights must sum to 1.0")
        
        return errors
    
    def get_training_params(self) -> Dict:
        """Obtiene parámetros de entrenamiento"""
        return {
            "model": self.primary_model.model_params,
            "features": {
                "total": self.features.total_features,
                "groups": [g.value for g in self.features.enabled_groups]
            },
            "thresholds": {
                "confidence": self.confidence_threshold,
                "accuracy": self.accuracy_threshold
            },
            "training": {
                "min_samples": self.min_samples_training,
                "retrain_hours": self.retrain_interval_hours,
                "validation_split": self.validation_split,
                "test_split": self.test_split,
                "incremental": self.enable_incremental_training,
                "ensemble": self.enable_model_ensemble
            }
        }