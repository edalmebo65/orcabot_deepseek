# core/ml_engine/data_pipeline.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
import aiohttp
from dataclasses import dataclass
import talib
from pathlib import Path
import pickle

@dataclass
class OHLCVData:
    """Datos OHLCV estructurados"""
    timestamp: pd.DatetimeIndex
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convierte a DataFrame"""
        return pd.DataFrame({
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }, index=self.timestamp)

class DataPipeline:
    """Pipeline de datos para ML"""
    
    def __init__(self, config):
        self.config = config
        self.data_cache = {}
        self.cache_expiry = {}
        
        # Fuentes de datos
        self.data_sources = {
            'birdeye': 'https://public-api.birdeye.so/public',
            'jupiter': 'https://api.jup.ag',
            'pyth': 'https://api.pyth.network'
        }
    
    async def fetch_ohlcv(self, 
                         pool_address: str,
                         timeframe: str,
                         limit: int = 1000) -> Optional[OHLCVData]:
        """
        Obtiene datos OHLCV para un pool
        """
        cache_key = f"{pool_address}_{timeframe}_{limit}"
        
        # Verificar cache
        if cache_key in self.data_cache:
            expiry = self.cache_expiry.get(cache_key)
            if expiry and datetime.now() < expiry:
                return self.data_cache[cache_key]
        
        try:
            # Intentar múltiples fuentes
            data = await self._try_birdeye(pool_address, timeframe, limit)
            if data is None:
                data = await self._try_jupiter(pool_address, timeframe, limit)
            
            if data:
                # Cachear por 5 minutos
                self.data_cache[cache_key] = data
                self.cache_expiry[cache_key] = datetime.now() + timedelta(minutes=5)
                return data
            
        except Exception as e:
            self.config.logger.error(f"Error fetching OHLCV for {pool_address}: {e}")
        
        return None
    
    async def _try_birdeye(self, pool_address: str, timeframe: str, limit: int) -> Optional[OHLCVData]:
        """Intenta obtener datos de Birdeye"""
        try:
            async with aiohttp.ClientSession() as session:
                # Convertir timeframe a resolución de Birdeye
                resolution = self._timeframe_to_resolution(timeframe)
                
                url = f"{self.data_sources['birdeye']}/ohlcv/{pool_address}"
                params = {
                    'address': pool_address,
                    'type': resolution,
                    'time_from': int((datetime.now() - timedelta(days=30)).timestamp()),
                    'time_to': int(datetime.now().timestamp()),
                    'limit': limit
                }
                
                headers = {
                    'X-API-KEY': self.config.HELIUS_API_KEY
                }
                
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_birdeye_data(data)
        
        except Exception as e:
            self.config.logger.debug(f"Birdeye failed for {pool_address}: {e}")
        
        return None
    
    def _timeframe_to_resolution(self, timeframe: str) -> str:
        """Convierte timeframe a resolución de API"""
        mapping = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '1h': '1H',
            '4h': '4H',
            '1d': '1D'
        }
        return mapping.get(timeframe, '15m')
    
    def _parse_birdeye_data(self, data: Dict) -> Optional[OHLCVData]:
        """Parsea datos de Birdeye"""
        try:
            items = data.get('data', {}).get('items', [])
            
            timestamps = []
            opens, highs, lows, closes, volumes = [], [], [], [], []
            
            for item in items:
                timestamps.append(datetime.fromtimestamp(item['unixTime']))
                opens.append(float(item['o']))
                highs.append(float(item['h']))
                lows.append(float(item['l']))
                closes.append(float(item['c']))
                volumes.append(float(item.get('v', 0)))
            
            return OHLCVData(
                timestamp=pd.DatetimeIndex(timestamps),
                open=np.array(opens),
                high=np.array(highs),
                low=np.array(lows),
                close=np.array(closes),
                volume=np.array(volumes)
            )
        
        except Exception as e:
            self.config.logger.error(f"Error parsing Birdeye data: {e}")
            return None
    
    async def _try_jupiter(self, pool_address: str, timeframe: str, limit: int) -> Optional[OHLCVData]:
        """Intenta obtener datos de Jupiter (fallback)"""
        # Jupiter no tiene OHLCV directo, necesitaríamos otra fuente
        # Por ahora retornar None
        return None
    
    def calculate_technical_indicators(self, ohlcv: OHLCVData) -> pd.DataFrame:
        """
        Calcula todos los indicadores técnicos
        """
        df = ohlcv.to_dataframe()
        
        # 1. Momentum Indicators
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['close'], 
            fastperiod=12, 
            slowperiod=26, 
            signalperiod=9
        )
        df['stoch_k'], df['stoch_d'] = talib.STOCH(
            df['high'], df['low'], df['close'],
            fastk_period=14, slowk_period=3, slowd_period=3
        )
        
        # 2. Volatility Indicators
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(
            df['close'], 
            timeperiod=20, 
            nbdevup=2, 
            nbdevdn=2
        )
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
        # 3. Volume Indicators
        df['obv'] = talib.OBV(df['close'], df['volume'])
        df['volume_sma'] = talib.SMA(df['volume'], timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # 4. Trend Indicators
        df['sma_20'] = talib.SMA(df['close'], timeperiod=20)
        df['sma_50'] = talib.SMA(df['close'], timeperiod=50)
        df['ema_12'] = talib.EMA(df['close'], timeperiod=12)
        df['ema_26'] = talib.EMA(df['close'], timeperiod=26)
        
        # 5. Custom Indicators
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['price_acceleration'] = df['returns'].diff()
        
        # 6. Support and Resistance
        df['support'], df['resistance'] = self._calculate_support_resistance(df)
        
        # 7. Market Structure
        df['higher_high'] = (df['high'] > df['high'].shift(1)) & (df['high'].shift(1) > df['high'].shift(2))
        df['lower_low'] = (df['low'] < df['low'].shift(1)) & (df['low'].shift(1) < df['low'].shift(2))
        
        return df.dropna()
    
    def _calculate_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Tuple[pd.Series, pd.Series]:
        """Calcula niveles de soporte y resistencia"""
        support = df['low'].rolling(window=window, center=True).min()
        resistance = df['high'].rolling(window=window, center=True).max()
        return support, resistance
    
    def create_sequences(self, 
                        data: pd.DataFrame, 
                        sequence_length: int = 60,
                        target_col: str = 'returns') -> Tuple[np.ndarray, np.ndarray]:
        """
        Crea secuencias para LSTM
        """
        features = data.drop(columns=[target_col] if target_col in data.columns else [])
        targets = data[target_col] if target_col in data.columns else np.zeros(len(data))
        
        X, y = [], []
        
        for i in range(len(features) - sequence_length):
            X.append(features.iloc[i:i+sequence_length].values)
            y.append(targets.iloc[i+sequence_length])
        
        return np.array(X), np.array(y)
    
    def save_training_data(self, 
                          asset_id: str,
                          timeframe: str,
                          data: pd.DataFrame):
        """
        Guarda datos de entrenamiento
        """
        data_dir = self.config.base_dir / "data" / "training"
        data_dir.mkdir(exist_ok=True)
        
        filename = data_dir / f"{asset_id}_{timeframe}_{datetime.now().strftime('%Y%m%d')}.pkl"
        
        with open(filename, 'wb') as f:
            pickle.dump({
                'asset_id': asset_id,
                'timeframe': timeframe,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }, f)
    
    def load_training_data(self, 
                          asset_id: str,
                          timeframe: str,
                          days_back: int = 30) -> Optional[pd.DataFrame]:
        """
        Carga datos históricos de entrenamiento
        """
        data_dir = self.config.base_dir / "data" / "training"
        
        if not data_dir.exists():
            return None
        
        all_data = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for file in data_dir.glob(f"{asset_id}_{timeframe}_*.pkl"):
            try:
                with open(file, 'rb') as f:
                    file_data = pickle.load(f)
                    file_date = datetime.fromisoformat(file_data['timestamp'])
                    
                    if file_date >= cutoff_date:
                        all_data.append(file_data['data'])
            except:
                continue
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        
        return None