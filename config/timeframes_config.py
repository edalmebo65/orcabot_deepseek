# config/timeframes_config.py
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum

class TimeframeUnit(Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"

@dataclass
class TimeframeConfig:
    """Configuración de un timeframe específico"""
    value: int
    unit: TimeframeUnit
    enabled: bool = True
    priority: int = 1  # 1 = más importante
    min_samples: int = 1000
    max_samples: int = 10000
    
    @property
    def seconds(self) -> int:
        """Convierte a segundos"""
        multipliers = {
            TimeframeUnit.MINUTE: 60,
            TimeframeUnit.HOUR: 3600,
            TimeframeUnit.DAY: 86400,
            TimeframeUnit.WEEK: 604800
        }
        return self.value * multipliers[self.unit]
    
    @property
    def label(self) -> str:
        """Etiqueta legible"""
        return f"{self.value}{self.unit.value[0]}"

class TimeframesConfig:
    """Gestor de configuración de timeframes"""
    
    def __init__(self):
        # Timeframes por defecto
        self.timeframes = [
            TimeframeConfig(1, TimeframeUnit.MINUTE, enabled=True, priority=5),
            TimeframeConfig(5, TimeframeUnit.MINUTE, enabled=True, priority=4),
            TimeframeConfig(15, TimeframeUnit.MINUTE, enabled=True, priority=3),
            TimeframeConfig(60, TimeframeUnit.MINUTE, enabled=True, priority=2),
            TimeframeConfig(240, TimeframeUnit.MINUTE, enabled=False, priority=1),
            TimeframeConfig(1440, TimeframeUnit.MINUTE, enabled=False, priority=1),
        ]
        
        # Configuración de análisis
        self.primary_timeframe = TimeframeConfig(15, TimeframeUnit.MINUTE)
        self.confirmation_timeframes = 2  # Número de timeframes para confirmación
        
        # Configuración de datos
        self.history_days = 30
        self.update_frequency_seconds = 60
        self.max_data_points = 10000
        
        # Configuración de resample
        self.allow_resample = True
        self.resample_method = "ohlc4"  # (open+high+low+close)/4
        
    def get_enabled_timeframes(self) -> List[TimeframeConfig]:
        """Obtiene timeframes habilitados ordenados por prioridad"""
        enabled = [tf for tf in self.timeframes if tf.enabled]
        return sorted(enabled, key=lambda x: x.priority, reverse=True)
    
    def get_timeframe_by_label(self, label: str) -> TimeframeConfig:
        """Obtiene timeframe por etiqueta"""
        for tf in self.timeframes:
            if tf.label == label:
                return tf
        raise ValueError(f"Timeframe {label} not found")
    
    def get_optimal_timeframes(self, count: int = 3) -> List[TimeframeConfig]:
        """Obtiene timeframes óptimos para análisis múltiple"""
        enabled = self.get_enabled_timeframes()
        return enabled[:min(count, len(enabled))]
    
    def validate_timeframe_combination(self, timeframes: List[str]) -> bool:
        """Valida combinación de timeframes"""
        if len(timeframes) < 2:
            return False
        
        # Verificar que sean múltiplos
        tf_values = []
        for label in timeframes:
            tf = self.get_timeframe_by_label(label)
            tf_values.append(tf.seconds)
        
        # Ordenar de menor a mayor
        tf_values.sort()
        
        # Verificar relación
        for i in range(1, len(tf_values)):
            if tf_values[i] % tf_values[i-1] != 0:
                return False
        
        return True