# core/ml_engine/feature_extractor.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass
from decimal import Decimal
import talib

@dataclass
class FeatureSet:
    """Conjunto de características para ML"""
    technical: np.ndarray
    temporal: np.ndarray
    volume: np.ndarray
    market: np.ndarray
    labels: np.ndarray
    
    @property
    def combined(self) -> np.ndarray:
        """Combina todas las características"""
        return np.concatenate([
            self.technical,
            self.temporal,
            self.volume,
            self.market
        ], axis=1) if self.technical.ndim > 1 else np.concatenate([
            self.technical,
            self.temporal,
            self.volume,
            self.market
        ])

class FeatureExtractor:
    """Extractor de características para ML"""
    
    def __init__(self, config):
        self.config = config
        
        # Configuración de características
        self.feature_config = {
            'technical': ['rsi', 'macd', 'bb_position', 'atr', 'stoch'],
            'temporal': ['hour', 'day_of_week', 'month', 'seasonality'],
            'volume': ['volume_ratio', 'obv', 'volume_profile'],
            'market': ['volatility', 'spread', 'liquidity_ratio']
        }
        
        # Normalización
        self.scalers = {}
        self.is_fitted = False
    
    def extract_features(self, 
                        data: pd.DataFrame,
                        target_column: str = 'returns') -> FeatureSet:
        """
        Extrae características de datos OHLCV
        """
        if data.empty or len(data) < 50:
            raise ValueError("Insufficient data for feature extraction")
        
        # 1. Características técnicas
        technical_features = self._extract_technical_features(data)
        
        # 2. Características temporales
        temporal_features = self._extract_temporal_features(data)
        
        # 3. Características de volumen
        volume_features = self._extract_volume_features(data)
        
        # 4. Características de mercado
        market_features = self._extract_market_features(data)
        
        # 5. Labels (target)
        labels = self._create_labels(data, target_column)
        
        return FeatureSet(
            technical=technical_features,
            temporal=temporal_features,
            volume=volume_features,
            market=market_features,
            labels=labels
        )
    
    def _extract_technical_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extrae características técnicas"""
        features = []
        
        # RSI
        rsi = talib.RSI(data['close'].values, timeperiod=14)
        features.append(rsi[:, np.newaxis])
        
        # MACD
        macd, macd_signal, macd_hist = talib.MACD(
            data['close'].values,
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )
        features.extend([macd[:, np.newaxis], macd_signal[:, np.newaxis], macd_hist[:, np.newaxis]])
        
        # Bollinger Bands position
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            data['close'].values,
            timeperiod=20,
            nbdevup=2,
            nbdevdn=2
        )
        bb_position = (data['close'].values - bb_lower) / (bb_upper - bb_lower)
        features.append(bb_position[:, np.newaxis])
        
        # ATR (Average True Range)
        atr = talib.ATR(
            data['high'].values,
            data['low'].values,
            data['close'].values,
            timeperiod=14
        )
        features.append(atr[:, np.newaxis])
        
        # Stochastic
        slowk, slowd = talib.STOCH(
            data['high'].values,
            data['low'].values,
            data['close'].values,
            fastk_period=14,
            slowk_period=3,
            slowd_period=3
        )
        features.extend([slowk[:, np.newaxis], slowd[:, np.newaxis]])
        
        # ADX (Average Directional Index)
        adx = talib.ADX(
            data['high'].values,
            data['low'].values,
            data['close'].values,
            timeperiod=14
        )
        features.append(adx[:, np.newaxis])
        
        # CCI (Commodity Channel Index)
        cci = talib.CCI(
            data['high'].values,
            data['low'].values,
            data['close'].values,
            timeperiod=20
        )
        features.append(cci[:, np.newaxis])
        
        # Combinar todas las características técnicas
        technical_features = np.concatenate(features, axis=1)
        
        # Reemplazar NaNs
        technical_features = np.nan_to_num(technical_features, nan=0.0)
        
        return technical_features
    
    def _extract_temporal_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extrae características temporales"""
        features = []
        
        # Extraer componentes de tiempo del índice
        if hasattr(data.index, 'hour'):
            hour_sin = np.sin(2 * np.pi * data.index.hour / 24)
            hour_cos = np.cos(2 * np.pi * data.index.hour / 24)
            features.extend([hour_sin.values[:, np.newaxis], hour_cos.values[:, np.newaxis]])
        
        if hasattr(data.index, 'dayofweek'):
            day_sin = np.sin(2 * np.pi * data.index.dayofweek / 7)
            day_cos = np.cos(2 * np.pi * data.index.dayofweek / 7)
            features.extend([day_sin.values[:, np.newaxis], day_cos.values[:, np.newaxis]])
        
        if hasattr(data.index, 'month'):
            month_sin = np.sin(2 * np.pi * data.index.month / 12)
            month_cos = np.cos(2 * np.pi * data.index.month / 12)
            features.extend([month_sin.values[:, np.newaxis], month_cos.values[:, np.newaxis]])
        
        # Estacionalidad (por ejemplo, trimestre)
        if hasattr(data.index, 'quarter'):
            quarter = data.index.quarter.values[:, np.newaxis] / 4
            features.append(quarter)
        
        # Weekend flag
        if hasattr(data.index, 'dayofweek'):
            is_weekend = (data.index.dayofweek >= 5).values[:, np.newaxis].astype(float)
            features.append(is_weekend)
        
        if features:
            temporal_features = np.concatenate(features, axis=1)
        else:
            temporal_features = np.zeros((len(data), 1))
        
        return temporal_features
    
    def _extract_volume_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extrae características de volumen"""
        features = []
        
        # Volume ratio (vs. moving average)
        volume_ma = data['volume'].rolling(window=20).mean()
        volume_ratio = data['volume'] / volume_ma
        features.append(volume_ratio.fillna(1).values[:, np.newaxis])
        
        # OBV (On-Balance Volume)
        obv = talib.OBV(data['close'].values, data['volume'].values)
        features.append(obv[:, np.newaxis])
        
        # Volume profile (high/low volume periods)
        volume_std = data['volume'].rolling(window=20).std()
        volume_zscore = (data['volume'] - volume_ma) / volume_std
        features.append(volume_zscore.fillna(0).values[:, np.newaxis])
        
        # Volume trend
        volume_trend = data['volume'].diff().rolling(window=5).mean()
        features.append(volume_trend.fillna(0).values[:, np.newaxis])
        
        # Volume volatility
        volume_volatility = data['volume'].rolling(window=20).std() / volume_ma
        features.append(volume_volatility.fillna(0).values[:, np.newaxis])
        
        volume_features = np.concatenate(features, axis=1)
        volume_features = np.nan_to_num(volume_features, nan=0.0)
        
        return volume_features
    
    def _extract_market_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extrae características de mercado"""
        features = []
        
        # Volatilidad histórica
        returns = data['close'].pct_change().fillna(0)
        volatility_20 = returns.rolling(window=20).std()
        volatility_50 = returns.rolling(window=50).std()
        features.extend([
            volatility_20.values[:, np.newaxis],
            volatility_50.values[:, np.newaxis]
        ])
        
        # Spread (high-low range)
        daily_spread = (data['high'] - data['low']) / data['close']
        features.append(daily_spread.values[:, np.newaxis])
        
        # Liquidity ratio (volume/volatility)
        liquidity_ratio = data['volume'] / (volatility_20 * data['close'])
        features.append(liquidity_ratio.fillna(0).values[:, np.newaxis])
        
        # Trend strength
        sma_20 = data['close'].rolling(window=20).mean()
        sma_50 = data['close'].rolling(window=50).mean()
        trend_strength = abs(sma_20 - sma_50) / data['close']
        features.append(trend_strength.fillna(0).values[:, np.newaxis])
        
        # Market regime (bullish/bearish)
        market_regime = (sma_20 > sma_50).astype(float)
        features.append(market_regime.values[:, np.newaxis])
        
        market_features = np.concatenate(features, axis=1)
        market_features = np.nan_to_num(market_features, nan=0.0)
        
        return market_features
    
    def _create_labels(self, data: pd.DataFrame, target_column: str) -> np.ndarray:
        """Crea labels para entrenamiento"""
        if target_column in data.columns:
            # Usar columna existente
            labels = data[target_column].values
        else:
            # Crear labels binarias basadas en retornos futuros
            future_returns = data['close'].pct_change(5).shift(-5)  # Retornos a 5 periodos
            labels = (future_returns > 0).astype(float)  # 1 si positivo, 0 si negativo
        
        # Reemplazar NaNs
        labels = np.nan_to_num(labels, nan=0.0)
        
        return labels
    
    def normalize_features(self, 
                          feature_set: FeatureSet,
                          fit: bool = False) -> FeatureSet:
        """Normaliza características"""
        from sklearn.preprocessing import StandardScaler
        
        normalized_set = FeatureSet(
            technical=np.zeros_like(feature_set.technical),
            temporal=np.zeros_like(feature_set.temporal),
            volume=np.zeros_like(feature_set.volume),
            market=np.zeros_like(feature_set.market),
            labels=feature_set.labels
        )
        
        # Normalizar cada tipo de característica por separado
        feature_types = ['technical', 'temporal', 'volume', 'market']
        
        for feature_type in feature_types:
            features = getattr(feature_set, feature_type)
            
            if fit or feature_type not in self.scalers:
                scaler = StandardScaler()
                scaled_features = scaler.fit_transform(features)
                self.scalers[feature_type] = scaler
                self.is_fitted = True
            else:
                scaler = self.scalers[feature_type]
                scaled_features = scaler.transform(features)
            
            setattr(normalized_set, feature_type, scaled_features)
        
        return normalized_set
    
    def create_sequences(self, 
                        feature_set: FeatureSet,
                        sequence_length: int = 60) -> Tuple[np.ndarray, np.ndarray]:
        """
        Crea secuencias para modelos de series temporales
        """
        # Combinar todas las características
        X_combined = feature_set.combined
        
        # Crear secuencias
        X_seq, y_seq = [], []
        
        for i in range(len(X_combined) - sequence_length):
            X_seq.append(X_combined[i:i+sequence_length])
            y_seq.append(feature_set.labels[i+sequence_length])
        
        return np.array(X_seq), np.array(y_seq)
    
    def get_feature_importance(self, model) -> Dict[str, float]:
        """Obtiene importancia de características (si el modelo lo soporta)"""
        try:
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
                
                # Nombres de características (simplificado)
                feature_names = []
                for feature_type in ['technical', 'temporal', 'volume', 'market']:
                    n_features = getattr(self, f'_get_{feature_type}_count')()
                    feature_names.extend([f"{feature_type}_{i}" for i in range(n_features)])
                
                return dict(zip(feature_names, importances))
        except:
            pass
        
        return {}
    
    def _get_technical_count(self) -> int:
        """Número de características técnicas"""
        return 10  # RSI, MACD(3), BB, ATR, Stochastic(2), ADX, CCI
    
    def _get_temporal_count(self) -> int:
        """Número de características temporales"""
        return 8  # hour(2), day(2), month(2), quarter, weekend
    
    def _get_volume_count(self) -> int:
        """Número de características de volumen"""
        return 5  # volume_ratio, OBV, zscore, trend, volatility
    
    def _get_market_count(self) -> int:
        """Número de características de mercado"""
        return 6  # volatility(2), spread, liquidity, trend_strength, regime