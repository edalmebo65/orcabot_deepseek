# core/trading/signal_generator.py
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class SignalStrength(Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class TradingSignal:
    """Señal de trading"""
    type: SignalType
    strength: SignalStrength
    confidence: float  # 0-1
    price: Decimal
    timestamp: str
    indicators: Dict
    timeframe: str
    reason: str
    
    @property
    def is_buy(self) -> bool:
        return self.type == SignalType.BUY
    
    @property
    def is_sell(self) -> bool:
        return self.type == SignalType.SELL

class SignalGenerator:
    """Generador de señales de trading"""
    
    def __init__(self, config):
        self.config = config
        
        # Umbrales de señal
        self.thresholds = {
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "macd_signal_crossover": 0.0001,
            "bbands_position": 0.2,  # 20% desde el borde
            "volume_spike": 2.0,  # 2x volumen promedio
            "min_confidence": 0.65
        }
        
        # Pesos para combinación de señales
        self.weights = {
            "rsi": 0.15,
            "macd": 0.20,
            "bbands": 0.15,
            "volume": 0.10,
            "trend": 0.20,
            "support_resistance": 0.20
        }
    
    def generate_signal(self, 
                       indicators: Dict,
                       price_data: Dict) -> TradingSignal:
        """
        Genera señal de trading basada en indicadores
        """
        # Analizar cada indicador
        signals = []
        confidence_scores = []
        
        # 1. RSI Analysis
        rsi_signal, rsi_confidence = self._analyze_rsi(indicators.get('rsi'))
        signals.append(rsi_signal)
        confidence_scores.append(rsi_confidence * self.weights["rsi"])
        
        # 2. MACD Analysis
        macd_signal, macd_confidence = self._analyze_macd(
            indicators.get('macd'),
            indicators.get('macd_signal')
        )
        signals.append(macd_signal)
        confidence_scores.append(macd_confidence * self.weights["macd"])
        
        # 3. Bollinger Bands Analysis
        bbands_signal, bbands_confidence = self._analyze_bbands(
            indicators.get('bb_position'),
            indicators.get('bb_width')
        )
        signals.append(bbands_signal)
        confidence_scores.append(bbbands_confidence * self.weights["bbands"])
        
        # 4. Volume Analysis
        volume_signal, volume_confidence = self._analyze_volume(
            indicators.get('volume_ratio'),
            indicators.get('volume_trend')
        )
        signals.append(volume_signal)
        confidence_scores.append(volume_confidence * self.weights["volume"])
        
        # 5. Trend Analysis
        trend_signal, trend_confidence = self._analyze_trend(
            indicators.get('trend_direction'),
            indicators.get('trend_strength')
        )
        signals.append(trend_signal)
        confidence_scores.append(trend_confidence * self.weights["trend"])
        
        # 6. Support/Resistance Analysis
        sr_signal, sr_confidence = self._analyze_support_resistance(
            price_data.get('current_price'),
            price_data.get('support_level'),
            price_data.get('resistance_level')
        )
        signals.append(sr_signal)
        confidence_scores.append(sr_confidence * self.weights["support_resistance"])
        
        # Combinar señales
        final_signal, final_confidence = self._combine_signals(signals, confidence_scores)
        
        # Determinar fuerza de la señal
        strength = self._determine_strength(final_confidence)
        
        # Crear señal final
        signal = TradingSignal(
            type=final_signal,
            strength=strength,
            confidence=final_confidence,
            price=Decimal(str(price_data.get('current_price', 0))),
            timestamp=price_data.get('timestamp', ''),
            indicators=indicators,
            timeframe=price_data.get('timeframe', ''),
            reason=self._generate_reason(signals, strength)
        )
        
        return signal
    
    def _analyze_rsi(self, rsi_value: float) -> Tuple[SignalType, float]:
        """Analiza señal RSI"""
        if rsi_value is None:
            return SignalType.HOLD, 0.0
        
        confidence = 0.0
        signal = SignalType.HOLD
        
        if rsi_value < self.thresholds["rsi_oversold"]:
            signal = SignalType.BUY
            confidence = (self.thresholds["rsi_oversold"] - rsi_value) / self.thresholds["rsi_oversold"]
        elif rsi_value > self.thresholds["rsi_overbought"]:
            signal = SignalType.SELL
            confidence = (rsi_value - self.thresholds["rsi_overbought"]) / (100 - self.thresholds["rsi_overbought"])
        
        return signal, min(confidence, 1.0)
    
    def _analyze_macd(self, macd: float, signal: float) -> Tuple[SignalType, float]:
        """Analiza señal MACD"""
        if macd is None or signal is None:
            return SignalType.HOLD, 0.0
        
        diff = macd - signal
        confidence = abs(diff) / self.thresholds["macd_signal_crossover"]
        
        if diff > self.thresholds["macd_signal_crossover"]:
            return SignalType.BUY, min(confidence, 1.0)
        elif diff < -self.thresholds["macd_signal_crossover"]:
            return SignalType.SELL, min(confidence, 1.0)
        
        return SignalType.HOLD, 0.0
    
    def _analyze_bbands(self, bb_position: float, bb_width: float) -> Tuple[SignalType, float]:
        """Analiza Bollinger Bands"""
        if bb_position is None or bb_width is None:
            return SignalType.HOLD, 0.0
        
        confidence = 0.0
        signal = SignalType.HOLD
        
        # Precio cerca del borde inferior (sobreventa)
        if bb_position < self.thresholds["bbands_position"]:
            signal = SignalType.BUY
            confidence = (self.thresholds["bbands_position"] - bb_position) / self.thresholds["bbands_position"]
        
        # Precio cerca del borde superior (sobrecompra)
        elif bb_position > (1 - self.thresholds["bbands_position"]):
            signal = SignalType.SELL
            confidence = (bb_position - (1 - self.thresholds["bbands_position"])) / self.thresholds["bbands_position"]
        
        # Bandas estrechas (breakout inminente)
        elif bb_width < 0.5:  # Bandas muy estrechas
            # Señal neutral pero con atención
            signal = SignalType.HOLD
            confidence = 0.3
        
        return signal, min(confidence, 1.0)
    
    def _analyze_volume(self, volume_ratio: float, volume_trend: str) -> Tuple[SignalType, float]:
        """Analiza volumen"""
        if volume_ratio is None:
            return SignalType.HOLD, 0.0
        
        confidence = 0.0
        signal = SignalType.HOLD
        
        # Spike de volumen (posible movimiento fuerte)
        if volume_ratio > self.thresholds["volume_spike"]:
            confidence = min((volume_ratio - 1) / (self.thresholds["volume_spike"] - 1), 1.0)
            
            if volume_trend == "increasing":
                signal = SignalType.BUY
            elif volume_trend == "decreasing":
                signal = SignalType.SELL
            else:
                signal = SignalType.HOLD
        
        return signal, confidence
    
    def _analyze_trend(self, trend_direction: str, trend_strength: float) -> Tuple[SignalType, float]:
        """Analiza tendencia"""
        if trend_direction is None or trend_strength is None:
            return SignalType.HOLD, 0.0
        
        confidence = trend_strength
        
        if trend_direction == "up":
            return SignalType.BUY, confidence
        elif trend_direction == "down":
            return SignalType.SELL, confidence
        
        return SignalType.HOLD, 0.0
    
    def _analyze_support_resistance(self, 
                                  current_price: float,
                                  support: float,
                                  resistance: float) -> Tuple[SignalType, float]:
        """Analiza soporte y resistencia"""
        if current_price is None or support is None or resistance is None:
            return SignalType.HOLD, 0.0
        
        # Calcular distancia a soporte/resistencia
        distance_to_support = abs(current_price - support) / current_price
        distance_to_resistance = abs(current_price - resistance) / current_price
        
        confidence = 0.0
        signal = SignalType.HOLD
        
        # Cerca del soporte (potencial rebote)
        if distance_to_support < 0.02:  # 2% del soporte
            signal = SignalType.BUY
            confidence = 1 - (distance_to_support / 0.02)
        
        # Cerca de la resistencia (potencial rechazo)
        elif distance_to_resistance < 0.02:  # 2% de la resistencia
            signal = SignalType.SELL
            confidence = 1 - (distance_to_resistance / 0.02)
        
        return signal, confidence
    
    def _combine_signals(self, 
                        signals: List[SignalType],
                        confidences: List[float]) -> Tuple[SignalType, float]:
        """Combina múltiples señales"""
        # Contar señales de cada tipo
        buy_count = sum(1 for s in signals if s == SignalType.BUY)
        sell_count = sum(1 for s in signals if s == SignalType.SELL)
        hold_count = sum(1 for s in signals if s == SignalType.HOLD)
        
        # Calcular confidencias ponderadas
        buy_confidence = sum(c for s, c in zip(signals, confidences) if s == SignalType.BUY)
        sell_confidence = sum(c for s, c in zip(signals, confidences) if s == SignalType.SELL)
        
        # Determinar señal final
        if buy_count > sell_count and buy_count > hold_count:
            final_signal = SignalType.BUY
            final_confidence = buy_confidence / buy_count if buy_count > 0 else 0
        elif sell_count > buy_count and sell_count > hold_count:
            final_signal = SignalType.SELL
            final_confidence = sell_confidence / sell_count if sell_count > 0 else 0
        else:
            final_signal = SignalType.HOLD
            final_confidence = 0.5  # Neutral
        
        # Ajustar por consenso
        total_signals = len(signals)
        consensus = max(buy_count, sell_count, hold_count) / total_signals
        
        final_confidence *= consensus
        
        return final_signal, min(final_confidence, 1.0)
    
    def _determine_strength(self, confidence: float) -> SignalStrength:
        """Determina fuerza de la señal basada en confianza"""
        if confidence >= 0.8:
            return SignalStrength.VERY_STRONG
        elif confidence >= 0.65:
            return SignalStrength.STRONG
        elif confidence >= 0.5:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _generate_reason(self, signals: List[SignalType], strength: SignalStrength) -> str:
        """Genera razón para la señal"""
        reasons = []
        
        for i, signal in enumerate(signals):
            if signal == SignalType.BUY:
                reasons.append(f"Indicator {i+1}: Bullish")
            elif signal == SignalType.SELL:
                reasons.append(f"Indicator {i+1}: Bearish")
        
        if not reasons:
            reasons.append("Mixed or neutral signals")
        
        strength_text = strength.value.replace('_', ' ').title()
        return f"{strength_text} signal. Reasons: {', '.join(reasons[:3])}"
    
    def filter_signals_by_confidence(self,
                                   signals: List[TradingSignal],
                                   min_confidence: float = None) -> List[TradingSignal]:
        """Filtra señales por confianza mínima"""
        if min_confidence is None:
            min_confidence = self.thresholds["min_confidence"]
        
        return [s for s in signals if s.confidence >= min_confidence]
    
    def rank_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Rankea señales por confianza y fuerza"""
        # Ponderar confianza por fuerza
        strength_weights = {
            SignalStrength.VERY_STRONG: 1.2,
            SignalStrength.STRONG: 1.1,
            SignalStrength.MODERATE: 1.0,
            SignalStrength.WEAK: 0.8
        }
        
        def score_signal(signal: TradingSignal) -> float:
            base_score = signal.confidence
            strength_weight = strength_weights.get(signal.strength, 1.0)
            return base_score * strength_weight
        
        return sorted(signals, key=score_signal, reverse=True)