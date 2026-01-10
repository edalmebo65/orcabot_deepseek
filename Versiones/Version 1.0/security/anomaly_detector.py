# security/anomaly_detector.py
import numpy as np
from sklearn.ensemble import IsolationForest
from dataclasses import dataclass
from typing import List, Dict
import asyncio

@dataclass
class AnomalyConfig:
    price_change_threshold: float = 0.05  # 5% cambio abrupto
    volume_spike_threshold: float = 3.0   # 3x volumen normal
    frequency_threshold: int = 10         # 10 operaciones/minuto

class AnomalyDetector:
    def __init__(self):
        self.config = AnomalyConfig()
        self.isolation_forest = IsolationForest(contamination=0.1)
        self.is_trained = False
        
    async def detect_market_anomalies(self, 
                                     market_data: Dict) -> List[str]:
        """
        Detecta anomalías en tiempo real
        """
        anomalies = []
        
        # 1. Detección de cambios abruptos de precio
        if self._detect_abrupt_price_change(market_data):
            anomalies.append("PRICE_SPIKE")
        
        # 2. Detección de volumen anómalo
        if self._detect_volume_spike(market_data):
            anomalies.append("VOLUME_SPIKE")
        
        # 3. Detección de patrones sospechosos
        if self._detect_wash_trading_pattern(market_data):
            anomalies.append("WASH_TRADING_SUSPECTED")
        
        # 4. Detección de flash crash
        if self._detect_flash_crash(market_data):
            anomalies.append("FLASH_CRASH_DETECTED")
        
        return anomalies
    
    def _detect_wash_trading_pattern(self, market_data: Dict) -> bool:
        """
        Detecta patrones de wash trading
        """
        trades = market_data.get('recent_trades', [])
        
        if len(trades) < 20:
            return False
        
        # Analizar patrones de trading circular
        addresses = [t['address'] for t in trades]
        unique_addresses = len(set(addresses))
        
        # Ratio sospechoso si pocas direcciones hacen muchas transacciones
        if len(trades) / max(unique_addresses, 1) > 5:
            return True
        
        return False