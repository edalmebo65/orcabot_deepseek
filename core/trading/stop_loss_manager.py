# core/trading/stop_loss_manager.py
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class StopLossType(Enum):
    FIXED = "fixed"
    TRAILING = "trailing"
    VOLATILITY = "volatility"
    TIME_BASED = "time_based"

@dataclass
class StopLossConfig:
    """Configuración de stop loss"""
    type: StopLossType
    value: Decimal  # Porcentaje o valor absoluto
    activation_price: Optional[Decimal] = None  # Para trailing
    min_distance_pct: Decimal = Decimal('0.001')  # 0.1% distancia mínima
    
    @property
    def is_trailing(self) -> bool:
        return self.type == StopLossType.TRAILING

class StopLossManager:
    """Gestor avanzado de stop loss"""
    
    def __init__(self, config):
        self.config = config
        self.stop_losses: Dict[str, StopLossConfig] = {}
        
        # Configuración por defecto
        self.default_stop_loss_pct = config.trading.capital.stop_loss_pct
        self.trailing_activation_pct = config.trading.capital.trailing_stop_activation_pct
        self.trailing_distance_pct = config.trading.capital.trailing_stop_distance_pct
    
    def create_fixed_stop_loss(self,
                             entry_price: Decimal,
                             stop_loss_pct: Decimal = None) -> Decimal:
        """
        Crea stop loss fijo
        """
        if stop_loss_pct is None:
            stop_loss_pct = self.default_stop_loss_pct
        
        stop_loss_price = entry_price * (Decimal('1') - stop_loss_pct)
        
        # Redondear
        stop_loss_price = stop_loss_price.quantize(
            Decimal('0.0001'),
            rounding=ROUND_DOWN
        )
        
        return stop_loss_price
    
    def create_trailing_stop_loss(self,
                                entry_price: Decimal,
                                current_price: Decimal,
                                activation_pct: Decimal = None,
                                distance_pct: Decimal = None) -> Optional[Decimal]:
        """
        Crea o actualiza stop loss trailing
        """
        if activation_pct is None:
            activation_pct = self.trailing_activation_pct
        
        if distance_pct is None:
            distance_pct = self.trailing_distance_pct
        
        # Calcular ganancia actual
        profit_pct = (current_price - entry_price) / entry_price
        
        # Verificar si se activa el trailing
        if profit_pct >= activation_pct:
            # Calcular trailing stop
            trailing_stop = current_price * (Decimal('1') - distance_pct)
            return trailing_stop.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
        
        return None
    
    def create_volatility_stop_loss(self,
                                  entry_price: Decimal,
                                  volatility_pct: Decimal,
                                  multiplier: Decimal = Decimal('2.0')) -> Decimal:
        """
        Crea stop loss basado en volatilidad
        """
        # Stop loss = entry_price - (volatility * multiplier)
        stop_loss_distance = volatility_pct * multiplier
        stop_loss_price = entry_price * (Decimal('1') - stop_loss_distance)
        
        # Asegurar mínimo
        min_stop_loss_pct = Decimal('0.005')  # 0.5% mínimo
        max_stop_loss_pct = Decimal('0.10')   # 10% máximo
        
        actual_distance = Decimal('1') - (stop_loss_price / entry_price)
        
        if actual_distance < min_stop_loss_pct:
            stop_loss_price = entry_price * (Decimal('1') - min_stop_loss_pct)
        elif actual_distance > max_stop_loss_pct:
            stop_loss_price = entry_price * (Decimal('1') - max_stop_loss_pct)
        
        return stop_loss_price.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
    
    def calculate_optimal_stop_loss(self,
                                  entry_price: Decimal,
                                  asset_volatility: Decimal,
                                  atr: Decimal,
                                  support_level: Decimal) -> Tuple[Decimal, Dict]:
        """
        Calcula stop loss óptimo usando múltiples métodos
        """
        # 1. Stop loss fijo (configuración base)
        fixed_sl = self.create_fixed_stop_loss(entry_price)
        
        # 2. Stop loss por volatilidad (ATR)
        atr_sl = entry_price - (atr * Decimal('1.5'))
        
        # 3. Stop loss por soporte técnico
        support_sl = support_level * Decimal('0.99')  # 1% debajo del soporte
        
        # 4. Seleccionar el más conservativo (más alto para longs)
        candidate_stops = [fixed_sl, atr_sl, support_sl]
        optimal_sl = max(candidate_stops)
        
        # 5. Validar distancia mínima
        min_distance_pct = Decimal('0.005')  # 0.5% mínimo
        max_distance_pct = Decimal('0.05')   # 5% máximo
        
        distance_pct = (entry_price - optimal_sl) / entry_price
        
        if distance_pct < min_distance_pct:
            optimal_sl = entry_price * (Decimal('1') - min_distance_pct)
        elif distance_pct > max_distance_pct:
            optimal_sl = entry_price * (Decimal('1') - max_distance_pct)
        
        details = {
            "entry_price": float(entry_price),
            "fixed_stop_loss": float(fixed_sl),
            "atr_stop_loss": float(atr_sl),
            "support_stop_loss": float(support_sl),
            "optimal_stop_loss": float(optimal_sl),
            "distance_pct": float(distance_pct),
            "distance_amount": float(entry_price - optimal_sl)
        }
        
        return optimal_sl, details
    
    def update_trailing_stop(self,
                           operation_id: str,
                           current_price: Decimal,
                           current_trailing: Optional[Decimal]) -> Optional[Decimal]:
        """
        Actualiza stop loss trailing
        """
        if operation_id not in self.stop_losses:
            return current_trailing
        
        config = self.stop_losses[operation_id]
        
        if not config.is_trailing or config.activation_price is None:
            return current_trailing
        
        # Solo mover hacia arriba (para longs)
        if current_price > config.activation_price:
            new_trailing = current_price * (Decimal('1') - config.value)
            
            if current_trailing is None or new_trailing > current_trailing:
                return new_trailing.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
        
        return current_trailing
    
    def should_trigger_stop_loss(self,
                               current_price: Decimal,
                               stop_loss_price: Decimal,
                               operation_side: str) -> bool:
        """
        Verifica si se debe activar el stop loss
        """
        if operation_side == "BUY":
            return current_price <= stop_loss_price
        else:  # SELL (short)
            return current_price >= stop_loss_price
    
    def calculate_risk_reward_ratio(self,
                                  entry_price: Decimal,
                                  stop_loss_price: Decimal,
                                  take_profit_price: Decimal) -> Decimal:
        """
        Calcula ratio riesgo/beneficio
        """
        risk = abs(entry_price - stop_loss_price)
        reward = abs(take_profit_price - entry_price)
        
        if risk == Decimal('0'):
            return Decimal('0')
        
        return reward / risk
    
    def get_stop_loss_recommendation(self,
                                   asset_metrics: Dict) -> Dict:
        """
        Genera recomendación de stop loss basada en métricas
        """
        entry_price = Decimal(str(asset_metrics.get('current_price', 0)))
        volatility = Decimal(str(asset_metrics.get('volatility_24h', 0.01)))
        atr = Decimal(str(asset_metrics.get('atr', 0)))
        support = Decimal(str(asset_metrics.get('support_level', entry_price * Decimal('0.95'))))
        
        # Calcular stop loss óptimo
        optimal_sl, details = self.calculate_optimal_stop_loss(
            entry_price, volatility, atr, support
        )
        
        # Calcular take profit basado en risk/reward
        risk = entry_price - optimal_sl
        reward_targets = {
            "1:1": entry_price + risk,
            "1:2": entry_price + (risk * Decimal('2')),
            "1:3": entry_price + (risk * Decimal('3'))
        }
        
        recommendation = {
            "entry_price": float(entry_price),
            "recommended_stop_loss": float(optimal_sl),
            "risk_amount": float(risk),
            "risk_pct": float(risk / entry_price * Decimal('100')),
            "reward_targets": {k: float(v) for k, v in reward_targets.items()},
            "risk_reward_ratios": {k: float((v - entry_price) / risk) for k, v in reward_targets.items()},
            "calculation_details": details
        }
        
        return recommendation