# core/trading/risk_manager.py
from dataclasses import dataclass
from typing import Optional
import numpy as np
from enum import Enum

class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"

@dataclass
class RiskParameters:
    max_position_size: float = 0.1  # 10% del portfolio
    max_daily_loss: float = 0.02   # 2% pérdida máxima diaria
    min_profit_margin: float = 0.002  # 0.2% mínimo
    trailing_stop_activation: float = 0.005  # 0.5% para activar
    trailing_stop_distance: float = 0.002   # 0.2% distancia

class RiskManager:
    def __init__(self, config):
        self.config = config
        self.risk_params = RiskParameters()
        self.daily_pnl = 0
        
    def calculate_support_resistance(self, prices: np.ndarray) -> Tuple[float, float]:
        """
        Calcula soporte y resistencia dinámicos
        """
        # Método de pivot points
        high = np.max(prices[-20:])
        low = np.min(prices[-20:])
        close = prices[-1]
        
        pivot = (high + low + close) / 3
        resistance = 2 * pivot - low
        support = 2 * pivot - high
        
        return support, resistance
    
    def determine_stop_loss_take_profit(self, 
                                       entry_price: float,
                                       transaction_cost: float,
                                       support: float,
                                       resistance: float) -> Tuple[float, float]:
        """
        Calcula SL y TP basados en soporte/resistencia
        """
        # Stop Loss: debajo del soporte con margen
        stop_loss = support * 0.995  # 0.5% debajo del soporte
        
        # Take Profit: múltiplos de riesgo
        risk = abs(entry_price - stop_loss)
        take_profit = entry_price + (2.5 * risk)  # Ratio riesgo:beneficio 1:2.5
        
        # Ajustar por costos de transacción
        min_profit = entry_price * (1 + self.risk_params.min_profit_margin + transaction_cost)
        take_profit = max(take_profit, min_profit)
        
        return stop_loss, take_profit
    
    def calculate_trailing_stop(self, 
                               current_price: float, 
                               entry_price: float,
                               highest_price: float) -> float:
        """
        Calcula trailing stop dinámico
        """
        profit = (current_price - entry_price) / entry_price
        
        if profit > self.risk_params.trailing_stop_activation:
            # Calcular distancia desde el máximo
            distance_from_high = (highest_price - current_price) / highest_price
            
            if distance_from_high <= self.risk_params.trailing_stop_distance:
                trailing_stop = highest_price * (1 - self.risk_params.trailing_stop_distance)
                return trailing_stop
        
        return None