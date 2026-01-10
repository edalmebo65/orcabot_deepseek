# security/anomaly_detector.py
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

class AnomalyType(Enum):
    PRICE_MANIPULATION = "price_manipulation"
    VOLUME_SPIKE = "volume_spike"
    WASH_TRADING = "wash_trading"
    FRONT_RUNNING = "front_running"
    FLASH_CRASH = "flash_crash"
    UNUSUAL_PATTERN = "unusual_pattern"

@dataclass
class AnomalyAlert:
    """Alerta de anomalía detectada"""
    type: AnomalyType
    confidence: float
    timestamp: datetime
    details: Dict
    asset_pair: str
    severity: str
    
    @property
    def is_critical(self) -> bool:
        return self.severity in ["HIGH", "CRITICAL"]

class AnomalyDetector:
    """Detector de anomalías en tiempo real"""
    
    def __init__(self, config):
        self.config = config
        self.history: Dict[str, List] = {}
        self.max_history = 1000
        
        # Umbrales de detección
        self.thresholds = {
            'price_change_1m': 0.05,      # 5% cambio en 1 minuto
            'volume_spike_ratio': 3.0,    # 3x volumen normal
            'trade_frequency': 10,        # 10 trades por minuto
            'same_address_trades': 5,     # 5 trades misma dirección
            'flash_crash_pct': 0.10,      # 10% caída en 1 minuto
        }
        
        # Estadísticas
        self.stats = {
            'anomalies_detected': 0,
            'false_positives': 0,
            'by_type': {},
            'last_detection': None
        }
    
    def detect_price_manipulation(self, 
                                 price_history: List[float],
                                 volume_history: List[float]) -> Optional[AnomalyAlert]:
        """
        Detecta posibles manipulaciones de precio
        """
        if len(price_history) < 10:
            return None
        
        # Calcular estadísticas
        prices = np.array(price_history)
        returns = np.diff(prices) / prices[:-1]
        
        # Detectar cambios abruptos
        max_change = np.max(np.abs(returns[-5:]))  # Últimos 5 cambios
        if max_change > self.thresholds['price_change_1m']:
            # Verificar si hay volumen anormal
            volumes = np.array(volume_history[-5:])
            avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[0]
            
            if volumes[-1] > avg_volume * self.thresholds['volume_spike_ratio']:
                confidence = min(max_change / 0.10, 1.0)  # Normalizar a 10%
                
                return AnomalyAlert(
                    type=AnomalyType.PRICE_MANIPULATION,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    details={
                        'price_change': float(max_change),
                        'volume_spike': float(volumes[-1] / avg_volume),
                        'current_price': float(prices[-1]),
                        'avg_price': float(np.mean(prices))
                    },
                    asset_pair="UNKNOWN",
                    severity="HIGH" if confidence > 0.7 else "MEDIUM"
                )
        
        return None
    
    def detect_wash_trading(self,
                          trades: List[Dict]) -> Optional[AnomalyAlert]:
        """
        Detecta posibles wash trading
        """
        if len(trades) < 20:
            return None
        
        # Agrupar por dirección
        address_counts = {}
        for trade in trades[-100:]:  # Últimos 100 trades
            address = trade.get('address', 'unknown')
            address_counts[address] = address_counts.get(address, 0) + 1
        
        # Verificar direcciones con muchos trades
        suspicious_addresses = []
        for address, count in address_counts.items():
            if count > self.thresholds['same_address_trades']:
                suspicious_addresses.append(address)
        
        if suspicious_addresses:
            # Calcular métricas
            total_trades = len(trades)
            suspicious_trades = sum(address_counts[addr] for addr in suspicious_addresses)
            suspicious_ratio = suspicious_trades / total_trades
            
            if suspicious_ratio > 0.3:  # 30% de trades sospechosos
                confidence = min(suspicious_ratio, 1.0)
                
                return AnomalyAlert(
                    type=AnomalyType.WASH_TRADING,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    details={
                        'suspicious_addresses': suspicious_addresses,
                        'suspicious_trades': suspicious_trades,
                        'total_trades': total_trades,
                        'suspicious_ratio': suspicious_ratio
                    },
                    asset_pair="UNKNOWN",
                    severity="HIGH" if confidence > 0.5 else "MEDIUM"
                )
        
        return None
    
    def detect_flash_crash(self,
                          price_history: List[float],
                          timeframe_minutes: int = 1) -> Optional[AnomalyAlert]:
        """
        Detecta flash crashes
        """
        if len(price_history) < timeframe_minutes * 2:
            return None
        
        # Calcular caída máxima en el timeframe
        recent_prices = price_history[-(timeframe_minutes * 2):]
        max_price = np.max(recent_prices)
        min_price = np.min(recent_prices)
        
        crash_pct = (max_price - min_price) / max_price
        
        if crash_pct > self.thresholds['flash_crash_pct']:
            # Verificar recuperación
            current_price = price_history[-1]
            recovery_pct = (current_price - min_price) / min_price
            
            confidence = min(crash_pct / 0.20, 1.0)  # Normalizar a 20%
            
            return AnomalyAlert(
                type=AnomalyType.FLASH_CRASH,
                confidence=confidence,
                timestamp=datetime.now(),
                details={
                    'crash_percentage': float(crash_pct),
                    'recovery_percentage': float(recovery_pct),
                    'max_price': float(max_price),
                    'min_price': float(min_price),
                    'current_price': float(current_price)
                },
                asset_pair="UNKNOWN",
                severity="CRITICAL" if crash_pct > 0.15 else "HIGH"
            )
        
        return None
    
    def detect_unusual_patterns(self,
                               market_data: Dict) -> List[AnomalyAlert]:
        """
        Detecta patrones inusuales en múltiples dimensiones
        """
        alerts = []
        
        # 1. Patrón de volumen
        if 'volume' in market_data and 'avg_volume' in market_data:
            volume_ratio = market_data['volume'] / market_data['avg_volume']
            if volume_ratio > self.thresholds['volume_spike_ratio']:
                alerts.append(
                    AnomalyAlert(
                        type=AnomalyType.VOLUME_SPIKE,
                        confidence=min((volume_ratio - 1) / 2, 1.0),
                        timestamp=datetime.now(),
                        details={
                            'volume_ratio': float(volume_ratio),
                            'current_volume': market_data['volume'],
                            'avg_volume': market_data['avg_volume']
                        },
                        asset_pair=market_data.get('asset_pair', 'UNKNOWN'),
                        severity="MEDIUM"
                    )
                )
        
        # 2. Frecuencia de trades
        if 'trades_per_minute' in market_data:
            trade_freq = market_data['trades_per_minute']
            if trade_freq > self.thresholds['trade_frequency']:
                alerts.append(
                    AnomalyAlert(
                        type=AnomalyType.UNUSUAL_PATTERN,
                        confidence=min(trade_freq / 20, 1.0),
                        timestamp=datetime.now(),
                        details={
                            'trades_per_minute': trade_freq,
                            'threshold': self.thresholds['trade_frequency']
                        },
                        asset_pair=market_data.get('asset_pair', 'UNKNOWN'),
                        severity="LOW"
                    )
                )
        
        # 3. Spread anormal
        if 'bid_ask_spread' in market_data and 'avg_spread' in market_data:
            spread_ratio = market_data['bid_ask_spread'] / market_data['avg_spread']
            if spread_ratio > 2.0:  # Spread 2x mayor que promedio
                alerts.append(
                    AnomalyAlert(
                        type=AnomalyType.UNUSUAL_PATTERN,
                        confidence=min((spread_ratio - 1) / 2, 1.0),
                        timestamp=datetime.now(),
                        details={
                            'spread_ratio': float(spread_ratio),
                            'current_spread': market_data['bid_ask_spread'],
                            'avg_spread': market_data['avg_spread']
                        },
                        asset_pair=market_data.get('asset_pair', 'UNKNOWN'),
                        severity="MEDIUM"
                    )
                )
        
        return alerts
    
    def analyze_market_data(self,
                          asset_pair: str,
                          market_data: Dict) -> List[AnomalyAlert]:
        """
        Analiza datos de mercado para detectar anomalías
        """
        alerts = []
        
        # Guardar en historial
        if asset_pair not in self.history:
            self.history[asset_pair] = []
        
        self.history[asset_pair].append({
            'timestamp': datetime.now(),
            'data': market_data
        })
        
        # Mantener historial limitado
        if len(self.history[asset_pair]) > self.max_history:
            self.history[asset_pair] = self.history[asset_pair][-self.max_history:]
        
        # Ejecutar detecciones
        if 'price_history' in market_data and 'volume_history' in market_data:
            # Precio manipulación
            price_alert = self.detect_price_manipulation(
                market_data['price_history'],
                market_data['volume_history']
            )
            if price_alert:
                price_alert.asset_pair = asset_pair
                alerts.append(price_alert)
            
            # Flash crash
            flash_alert = self.detect_flash_crash(market_data['price_history'])
            if flash_alert:
                flash_alert.asset_pair = asset_pair
                alerts.append(flash_alert)
        
        # Wash trading
        if 'recent_trades' in market_data:
            wash_alert = self.detect_wash_trading(market_data['recent_trades'])
            if wash_alert:
                wash_alert.asset_pair = asset_pair
                alerts.append(wash_alert)
        
        # Patrones inusuales
        unusual_alerts = self.detect_unusual_patterns(market_data)
        for alert in unusual_alerts:
            alert.asset_pair = asset_pair
            alerts.append(alert)
        
        # Actualizar estadísticas
        if alerts:
            self.stats['anomalies_detected'] += len(alerts)
            self.stats['last_detection'] = datetime.now()
            
            for alert in alerts:
                anomaly_type = alert.type.value
                self.stats['by_type'][anomaly_type] = self.stats['by_type'].get(anomaly_type, 0) + 1
        
        return alerts
    
    def should_pause_trading(self, alerts: List[AnomalyAlert]) -> bool:
        """
        Determina si se debe pausar trading basado en anomalías
        """
        critical_count = sum(1 for alert in alerts if alert.is_critical)
        
        # Pausar si hay más de 2 anomalías críticas
        if critical_count >= 2:
            self.config.logger.warning(f"Pausing trading due to {critical_count} critical anomalies")
            return True
        
        # Pausar si hay anomalía CRITICAL
        for alert in alerts:
            if alert.severity == "CRITICAL":
                self.config.logger.warning(f"Pausing trading due to CRITICAL anomaly: {alert.type.value}")
                return True
        
        return False
    
    def get_detection_stats(self) -> Dict:
        """Obtiene estadísticas de detección"""
        stats = self.stats.copy()
        
        # Agregar información de historial
        stats['history_size'] = sum(len(h) for h in self.history.values())
        stats['monitored_pairs'] = len(self.history)
        
        # Calcular tasa de detección
        if stats['anomalies_detected'] > 0:
            stats['detection_rate'] = stats['anomalies_detected'] / stats['history_size'] * 100
        else:
            stats['detection_rate'] = 0
        
        return stats
    
    def reset_stats(self):
        """Reinicia estadísticas"""
        self.stats = {
            'anomalies_detected': 0,
            'false_positives': 0,
            'by_type': {},
            'last_detection': None
        }