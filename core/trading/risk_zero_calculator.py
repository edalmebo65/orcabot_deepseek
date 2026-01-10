# core/trading/risk_zero_calculator.py
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Tuple
from dataclasses import dataclass

@dataclass
class RiskZeroCalculation:
    """Cálculo de riesgo cero"""
    entry_price: Decimal
    position_size: Decimal
    total_fees_pct: Decimal
    risk_zero_price: Decimal
    buffer_pct: Decimal
    required_gain_pct: Decimal
    
    @property
    def required_price_movement(self) -> Decimal:
        """Movimiento de precio requerido para riesgo cero"""
        return self.risk_zero_price - self.entry_price
    
    @property
    def required_gain_amount(self) -> Decimal:
        """Ganancia requerida en términos absolutos"""
        return self.position_size * self.required_gain_pct

class RiskZeroCalculator:
    """Calculador de precio de riesgo cero"""
    
    def __init__(self, config):
        self.config = config
        self.buffer_pct = config.trading.capital.risk_zero_buffer_pct
    
    def calculate_risk_zero(self,
                          entry_price: Decimal,
                          position_size: Decimal,
                          fees_pct: Decimal) -> RiskZeroCalculation:
        """
        Calcula precio de riesgo cero
        
        Fórmula: entrada + fees + 0.2% buffer
        """
        # Calcular fees totales (entrada + salida estimada)
        total_fees_pct = fees_pct * Decimal('2')  # Asumir misma fee para salida
        
        # Calcular ganancia requerida
        required_gain_pct = total_fees_pct + self.buffer_pct
        
        # Calcular precio de riesgo cero
        risk_zero_price = entry_price * (Decimal('1') + required_gain_pct)
        
        # Redondear a decimales apropiados
        risk_zero_price = risk_zero_price.quantize(
            Decimal('0.0001'), 
            rounding=ROUND_DOWN
        )
        
        return RiskZeroCalculation(
            entry_price=entry_price,
            position_size=position_size,
            total_fees_pct=total_fees_pct,
            risk_zero_price=risk_zero_price,
            buffer_pct=self.buffer_pct,
            required_gain_pct=required_gain_pct
        )
    
    def calculate_dynamic_buffer(self,
                               volatility_pct: Decimal,
                               market_condition: str = "normal") -> Decimal:
        """
        Calcula buffer dinámico basado en volatilidad
        """
        base_buffer = self.buffer_pct
        
        # Ajustar por volatilidad
        if volatility_pct > Decimal('0.05'):  # >5% volatilidad
            # Aumentar buffer en alta volatilidad
            buffer_multiplier = Decimal('1.5')
        elif volatility_pct < Decimal('0.01'):  # <1% volatilidad
            # Reducir buffer en baja volatilidad
            buffer_multiplier = Decimal('0.8')
        else:
            buffer_multiplier = Decimal('1.0')
        
        # Ajustar por condiciones de mercado
        if market_condition == "high_volatility":
            buffer_multiplier *= Decimal('1.3')
        elif market_condition == "low_volatility":
            buffer_multiplier *= Decimal('0.7')
        elif market_condition == "news_event":
            buffer_multiplier *= Decimal('2.0')
        
        dynamic_buffer = base_buffer * buffer_multiplier
        
        # Limites
        min_buffer = Decimal('0.001')  # 0.1%
        max_buffer = Decimal('0.01')   # 1.0%
        
        return max(min_buffer, min(dynamic_buffer, max_buffer))
    
    def calculate_position_size_for_risk_zero(self,
                                            available_capital: Decimal,
                                            entry_price: Decimal,
                                            stop_loss_pct: Decimal,
                                            risk_per_trade_pct: Decimal) -> Tuple[Decimal, Dict]:
        """
        Calcula tamaño de posición considerando riesgo cero
        """
        # 1. Calcular riesgo por trade en términos absolutos
        risk_amount = available_capital * risk_per_trade_pct
        
        # 2. Calcular distancia al stop loss
        stop_loss_distance_pct = stop_loss_pct
        
        # 3. Calcular tamaño de posición basado en riesgo
        position_size = risk_amount / (entry_price * stop_loss_distance_pct)
        
        # 4. Ajustar por límites de capital
        max_position = available_capital * Decimal('0.10')  # 10% del capital
        position_size = min(position_size, max_position)
        
        # 5. Calcular mínimo viable (considerando fees)
        min_fees = entry_price * position_size * self.config.trading.orca_fee_pct * Decimal('2')
        min_position = min_fees * Decimal('10')  # 10x las fees mínimas
        
        if position_size * entry_price < min_position:
            return Decimal('0'), {"error": "Position too small for fees"}
        
        # 6. Redondear
        position_size = position_size.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        
        calculation_details = {
            "available_capital": float(available_capital),
            "entry_price": float(entry_price),
            "stop_loss_pct": float(stop_loss_pct),
            "risk_per_trade_pct": float(risk_per_trade_pct),
            "risk_amount": float(risk_amount),
            "max_position": float(max_position),
            "min_position": float(min_position),
            "final_position_size": float(position_size),
            "position_value": float(position_size * entry_price)
        }
        
        return position_size, calculation_details
    
    def verify_risk_zero_achievable(self,
                                  entry_price: Decimal,
                                  current_price: Decimal,
                                  position_size: Decimal,
                                  fees_pct: Decimal) -> Tuple[bool, Decimal, Dict]:
        """
        Verifica si el riesgo cero es alcanzable desde el precio actual
        """
        # Calcular riesgo cero
        risk_zero_calc = self.calculate_risk_zero(
            entry_price, position_size, fees_pct
        )
        
        # Calcular ganancia actual
        if current_price > entry_price:
            current_gain_pct = (current_price - entry_price) / entry_price
            current_gain_amount = position_size * (current_price - entry_price)
        else:
            current_gain_pct = Decimal('0')
            current_gain_amount = Decimal('0')
        
        # Verificar si ya se alcanzó riesgo cero
        already_achieved = current_price >= risk_zero_calc.risk_zero_price
        
        # Calcular ganancia requerida restante
        if already_achieved:
            required_gain_remaining_pct = Decimal('0')
            required_gain_remaining_amount = Decimal('0')
        else:
            required_gain_remaining_pct = risk_zero_calc.required_gain_pct - current_gain_pct
            required_gain_remaining_amount = position_size * (risk_zero_calc.risk_zero_price - current_price)
        
        details = {
            "entry_price": float(entry_price),
            "current_price": float(current_price),
            "risk_zero_price": float(risk_zero_calc.risk_zero_price),
            "current_gain_pct": float(current_gain_pct),
            "current_gain_amount": float(current_gain_amount),
            "required_gain_remaining_pct": float(required_gain_remaining_pct),
            "required_gain_remaining_amount": float(required_gain_remaining_amount),
            "already_achieved": already_achieved,
            "distance_to_risk_zero_pct": float((risk_zero_calc.risk_zero_price - current_price) / current_price * Decimal('100')) if current_price > 0 else 0
        }
        
        return already_achieved, required_gain_remaining_amount, details