#!/usr/bin/env python3
"""
Módulo propio de indicadores técnicos - Reemplazo para pandas-ta
Implementa los indicadores esenciales para trading
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Implementación propia de indicadores técnicos"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula Relative Strength Index (RSI)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(prices: pd.Series, 
                      fast: int = 12, 
                      slow: int = 26, 
                      signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula MACD (Moving Average Convergence Divergence)"""
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, 
                                 period: int = 20, 
                                 std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula Bollinger Bands"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, sma, lower_band
    
    @staticmethod
    def calculate_atr(high: pd.Series, 
                     low: pd.Series, 
                     close: pd.Series, 
                     period: int = 14) -> pd.Series:
        """Calcula Average True Range (ATR)"""
        high_low = high - low
        high_close = abs(high - close.shift())
        low_close = abs(low - close.shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, 
                           low: pd.Series, 
                           close: pd.Series, 
                           k_period: int = 14, 
                           d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calcula Stochastic Oscillator"""
        low_min = low.rolling(window=k_period).min()
        high_max = high.rolling(window=k_period).max()
        
        k = 100 * ((close - low_min) / (high_max - low_min))
        d = k.rolling(window=d_period).mean()
        return k, d
    
    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calcula On-Balance Volume (OBV)"""
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        return obv
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
        """Calcula Exponential Moving Average (EMA)"""
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
        """Calcula Simple Moving Average (SMA)"""
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def calculate_vwap(high: pd.Series, 
                      low: pd.Series, 
                      close: pd.Series, 
                      volume: pd.Series) -> pd.Series:
        """Calcula Volume Weighted Average Price (VWAP)"""
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap
    
    @staticmethod
    def calculate_adx(high: pd.Series, 
                     low: pd.Series, 
                     close: pd.Series, 
                     period: int = 14) -> pd.Series:
        """Calcula Average Directional Index (ADX)"""
        # True Range
        high_low = high - low
        high_close = abs(high - close.shift())
        low_close = abs(low - close.shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Directional Movement
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Smooth the DMs
        plus_dm_smooth = pd.Series(plus_dm).rolling(window=period).mean()
        minus_dm_smooth = pd.Series(minus_dm).rolling(window=period).mean()
        
        # Directional Indicators
        plus_di = 100 * (plus_dm_smooth / tr.rolling(window=period).mean())
        minus_di = 100 * (minus_dm_smooth / tr.rolling(window=period).mean())
        
        # DX and ADX
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    @staticmethod
    def calculate_cci(high: pd.Series, 
                     low: pd.Series, 
                     close: pd.Series, 
                     period: int = 20) -> pd.Series:
        """Calcula Commodity Channel Index (CCI)"""
        typical_price = (high + low + close) / 3
        sma = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean()
        )
        cci = (typical_price - sma) / (0.015 * mad)
        return cci
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula todos los indicadores técnicos para un DataFrame OHLCV
        
        Args:
            df: DataFrame con columnas ['open', 'high', 'low', 'close', 'volume']
            
        Returns:
            DataFrame con indicadores añadidos
        """
        result = df.copy()
        
        try:
            # RSI
            result['rsi'] = TechnicalIndicators.calculate_rsi(result['close'], 14)
            
            # MACD
            macd, signal, hist = TechnicalIndicators.calculate_macd(result['close'])
            result['macd'] = macd
            result['macd_signal'] = signal
            result['macd_hist'] = hist
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(result['close'])
            result['bb_upper'] = bb_upper
            result['bb_middle'] = bb_middle
            result['bb_lower'] = bb_lower
            result['bb_width'] = (bb_upper - bb_lower) / bb_middle
            
            # ATR
            result['atr'] = TechnicalIndicators.calculate_atr(
                result['high'], result['low'], result['close']
            )
            
            # Stochastic
            stoch_k, stoch_d = TechnicalIndicators.calculate_stochastic(
                result['high'], result['low'], result['close']
            )
            result['stoch_k'] = stoch_k
            result['stoch_d'] = stoch_d
            
            # OBV
            result['obv'] = TechnicalIndicators.calculate_obv(result['close'], result['volume'])
            
            # EMAs
            result['ema_9'] = TechnicalIndicators.calculate_ema(result['close'], 9)
            result['ema_21'] = TechnicalIndicators.calculate_ema(result['close'], 21)
            result['ema_50'] = TechnicalIndicators.calculate_ema(result['close'], 50)
            result['ema_200'] = TechnicalIndicators.calculate_ema(result['close'], 200)
            
            # SMAs
            result['sma_20'] = TechnicalIndicators.calculate_sma(result['close'], 20)
            result['sma_50'] = TechnicalIndicators.calculate_sma(result['close'], 50)
            
            # VWAP
            result['vwap'] = TechnicalIndicators.calculate_vwap(
                result['high'], result['low'], result['close'], result['volume']
            )
            
            # ADX
            result['adx'] = TechnicalIndicators.calculate_adx(
                result['high'], result['low'], result['close']
            )
            
            # CCI
            result['cci'] = TechnicalIndicators.calculate_cci(
                result['high'], result['low'], result['close']
            )
            
            # Retornos
            result['returns'] = result['close'].pct_change()
            result['log_returns'] = np.log(result['close'] / result['close'].shift())
            
            # Volatilidad
            result['volatility_20'] = result['returns'].rolling(window=20).std()
            result['volatility_50'] = result['returns'].rolling(window=50).std()
            
            # Volume indicators
            result['volume_sma'] = result['volume'].rolling(window=20).mean()
            result['volume_ratio'] = result['volume'] / result['volume_sma']
            
            logger.info(f"✅ Calculados {len([c for c in result.columns if c not in df.columns])} indicadores técnicos")
            
        except Exception as e:
            logger.error(f"Error calculando indicadores: {e}")
        
        return result
    
    @staticmethod
    def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
        """
        Genera señales de trading basadas en indicadores técnicos
        
        Returns:
            DataFrame con señales: 1=buy, -1=sell, 0=hold
        """
        signals = pd.DataFrame(index=df.index)
        
        try:
            # Señal RSI
            signals['rsi_signal'] = 0
            signals.loc[df['rsi'] < 30, 'rsi_signal'] = 1  # Oversold -> Buy
            signals.loc[df['rsi'] > 70, 'rsi_signal'] = -1  # Overbought -> Sell
            
            # Señal MACD
            signals['macd_signal'] = 0
            signals.loc[(df['macd'] > df['macd_signal']) & 
                       (df['macd'].shift() <= df['macd_signal'].shift()), 'macd_signal'] = 1
            signals.loc[(df['macd'] < df['macd_signal']) & 
                       (df['macd'].shift() >= df['macd_signal'].shift()), 'macd_signal'] = -1
            
            # Señal Bollinger Bands
            signals['bb_signal'] = 0
            signals.loc[df['close'] < df['bb_lower'], 'bb_signal'] = 1  # Below lower band -> Buy
            signals.loc[df['close'] > df['bb_upper'], 'bb_signal'] = -1  # Above upper band -> Sell
            
            # Señal Stochastic
            signals['stoch_signal'] = 0
            signals.loc[(df['stoch_k'] < 20) & (df['stoch_d'] < 20), 'stoch_signal'] = 1
            signals.loc[(df['stoch_k'] > 80) & (df['stoch_d'] > 80), 'stoch_signal'] = -1
            
            # Señal EMA crossover
            signals['ema_signal'] = 0
            signals.loc[(df['ema_9'] > df['ema_21']) & 
                       (df['ema_9'].shift() <= df['ema_21'].shift()), 'ema_signal'] = 1
            signals.loc[(df['ema_9'] < df['ema_21']) & 
                       (df['ema_9'].shift() >= df['ema_21'].shift()), 'ema_signal'] = -1
            
            # Señal compuesta (suma ponderada)
            signals['composite_signal'] = (
                signals['rsi_signal'] * 0.2 +
                signals['macd_signal'] * 0.3 +
                signals['bb_signal'] * 0.15 +
                signals['stoch_signal'] * 0.15 +
                signals['ema_signal'] * 0.2
            )
            
            # Señal final (normalizada a -1, 0, 1)
            signals['final_signal'] = 0
            signals.loc[signals['composite_signal'] > 0.3, 'final_signal'] = 1
            signals.loc[signals['composite_signal'] < -0.3, 'final_signal'] = -1
            
            # Confianza de la señal
            signals['signal_confidence'] = abs(signals['composite_signal'])
            
            logger.info(f"✅ Señales generadas: {sum(signals['final_signal'] != 0)} señales no-neutrales")
            
        except Exception as e:
            logger.error(f"Error generando señales: {e}")
        
        return signals

# Instancia global
tech_indicators = TechnicalIndicators()