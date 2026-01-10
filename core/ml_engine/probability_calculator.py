# core/ml_engine/probability_calculator.py
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from decimal import Decimal
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

@dataclass
class ProbabilityDistribution:
    """Distribución de probabilidad"""
    mean: float
    std: float
    confidence: float
    percentiles: Dict[str, float]
    
    @property
    def coefficient_of_variation(self) -> float:
        """Coeficiente de variación"""
        return self.std / self.mean if self.mean != 0 else 0

class ProbabilityCalculator:
    """Calculador de probabilidades para trading"""
    
    def __init__(self, config):
        self.config = config
        
        # Modelos de probabilidad
        self.models = {}
        
        # Historial de predicciones
        self.prediction_history = []
        self.max_history = 1000
        
    def calculate_buy_probability(self,
                                features: np.ndarray,
                                model = None) -> Dict[str, float]:
        """
        Calcula probabilidad de compra
        """
        if model is None:
            # Fallback a modelo simple si no hay modelo
            return self._calculate_simple_probability(features)
        
        try:
            # Predecir con modelo
            if len(features.shape) == 1:
                features = features.reshape(1, -1)
            
            # Obtener predicciones
            predictions = model.predict_proba(features)
            
            # Probabilidad de clase positiva (compra)
            buy_probability = float(predictions[0, 1])
            
            # Calcular confianza
            confidence = self._calculate_prediction_confidence(predictions[0])
            
            # Calcular distribución
            distribution = self._estimate_probability_distribution(
                predictions, 
                features
            )
            
            result = {
                "buy_probability": buy_probability,
                "confidence": confidence,
                "distribution_mean": distribution.mean,
                "distribution_std": distribution.std,
                "percentile_25": distribution.percentiles.get("25", 0),
                "percentile_75": distribution.percentiles.get("75", 0),
                "coefficient_of_variation": distribution.coefficient_of_variation,
                "signal_strength": self._calculate_signal_strength(buy_probability, confidence)
            }
            
            # Guardar en historial
            self._save_prediction(result)
            
            return result
            
        except Exception as e:
            self.config.logger.error(f"Error calculating probability: {e}")
            return self._calculate_simple_probability(features)
    
    def _calculate_simple_probability(self, features: np.ndarray) -> Dict[str, float]:
        """Cálculo simple de probabilidad (fallback)"""
        # Extraer características relevantes
        if len(features) > 0:
            # Usar RSI si está disponible (posición 0 en características técnicas)
            rsi_value = features[0] if len(features) > 0 else 50
            
            # Convertir RSI a probabilidad
            if rsi_value < 30:
                prob = 0.8  # Sobreventa - alta probabilidad de compra
            elif rsi_value > 70:
                prob = 0.2  # Sobrecompra - baja probabilidad de compra
            else:
                prob = 0.5  # Neutral
        else:
            prob = 0.5
        
        return {
            "buy_probability": prob,
            "confidence": 0.5,
            "distribution_mean": prob,
            "distribution_std": 0.1,
            "signal_strength": "NEUTRAL"
        }
    
    def _calculate_prediction_confidence(self, probabilities: np.ndarray) -> float:
        """Calcula confianza de la predicción"""
        # Confianza basada en la diferencia entre las probabilidades
        if len(probabilities) >= 2:
            max_prob = np.max(probabilities)
            second_max = np.partition(probabilities.flatten(), -2)[-2]
            confidence = max_prob - second_max
        else:
            confidence = 0.0
        
        return float(confidence)
    
    def _estimate_probability_distribution(self,
                                         predictions: np.ndarray,
                                         features: np.ndarray) -> ProbabilityDistribution:
        """Estima distribución de probabilidad"""
        # Calcular estadísticas básicas
        mean_prob = float(np.mean(predictions[:, 1]))  # Probabilidad de compra
        std_prob = float(np.std(predictions[:, 1]))
        
        # Calcular percentiles
        percentiles = {}
        for p in [10, 25, 50, 75, 90]:
            percentiles[str(p)] = float(np.percentile(predictions[:, 1], p))
        
        # Calcular confianza basada en consistencia
        confidence = 1.0 - min(std_prob / mean_prob if mean_prob > 0 else 1.0, 1.0)
        
        return ProbabilityDistribution(
            mean=mean_prob,
            std=std_prob,
            confidence=confidence,
            percentiles=percentiles
        )
    
    def _calculate_signal_strength(self, probability: float, confidence: float) -> str:
        """Calcula fuerza de la señal"""
        score = probability * confidence
        
        if score >= 0.7:
            return "VERY_STRONG"
        elif score >= 0.6:
            return "STRONG"
        elif score >= 0.5:
            return "MODERATE"
        else:
            return "WEAK"
    
    def calculate_risk_adjusted_probability(self,
                                          base_probability: float,
                                          risk_factors: Dict[str, float]) -> float:
        """
        Ajusta probabilidad basada en factores de riesgo
        """
        adjusted_prob = base_probability
        
        # Ajustar por volatilidad
        volatility = risk_factors.get('volatility', 0.0)
        if volatility > 0.05:  # Alta volatilidad
            adjusted_prob *= 0.8  # Reducir probabilidad
        elif volatility < 0.01:  # Baja volatilidad
            adjusted_prob *= 1.1  # Aumentar probabilidad
        
        # Ajustar por liquidez
        liquidity = risk_factors.get('liquidity', 1.0)
        if liquidity < 0.5:  # Baja liquidez
            adjusted_prob *= 0.7  # Reducir significativamente
        
        # Ajustar por tendencia del mercado
        market_trend = risk_factors.get('market_trend', 0.0)
        adjusted_prob *= (1 + market_trend * 0.2)  # ±20% ajuste
        
        # Ajustar por volumen
        volume_ratio = risk_factors.get('volume_ratio', 1.0)
        if volume_ratio > 2.0:  # Alto volumen
            adjusted_prob *= 1.15  # Aumentar probabilidad
        elif volume_ratio < 0.5:  # Bajo volumen
            adjusted_prob *= 0.85  # Reducir probabilidad
        
        # Limitar entre 0 y 1
        return max(0.0, min(1.0, adjusted_prob))
    
    def calculate_conditional_probability(self,
                                        event_a: str,
                                        event_b: str,
                                        historical_data: Dict) -> float:
        """
        Calcula probabilidad condicional P(A|B)
        """
        # Contar ocurrencias
        count_a_and_b = historical_data.get(f'{event_a}_and_{event_b}', 0)
        count_b = historical_data.get(event_b, 1)  # Evitar división por cero
        
        if count_b == 0:
            return 0.0
        
        return count_a_and_b / count_b
    
    def bayesian_update(self,
                       prior_prob: float,
                       likelihood: float,
                       evidence: float) -> float:
        """
        Actualización bayesiana de probabilidad
        P(A|B) = P(B|A) * P(A) / P(B)
        """
        if evidence == 0:
            return prior_prob
        
        posterior = (likelihood * prior_prob) / evidence
        
        # Limitar entre 0 y 1
        return max(0.0, min(1.0, posterior))
    
    def calculate_expected_value(self,
                               probability: float,
                               win_amount: float,
                               loss_amount: float) -> float:
        """
        Calcula valor esperado
        EV = (probability * win_amount) - ((1 - probability) * loss_amount)
        """
        return (probability * win_amount) - ((1 - probability) * loss_amount)
    
    def calculate_kelly_criterion(self,
                                probability: float,
                                win_loss_ratio: float) -> float:
        """
        Calcula fracción de Kelly
        f* = p - (1-p)/b
        donde b = win/loss ratio
        """
        if win_loss_ratio <= 0:
            return 0.0
        
        kelly = probability - ((1 - probability) / win_loss_ratio)
        
        # Fracción fraccional de Kelly (más conservadora)
        fractional_kelly = kelly * 0.5  # Usar 50% de Kelly
        
        return max(0.0, fractional_kelly)
    
    def _save_prediction(self, prediction: Dict):
        """Guarda predicción en historial"""
        self.prediction_history.append({
            **prediction,
            "timestamp": np.datetime64('now')
        })
        
        # Mantener tamaño limitado
        if len(self.prediction_history) > self.max_history:
            self.prediction_history = self.prediction_history[-self.max_history:]
    
    def get_prediction_accuracy(self, window: int = 100) -> Dict:
        """Calcula precisión de predicciones históricas"""
        if len(self.prediction_history) < 10:
            return {"error": "Insufficient historical data"}
        
        # Tomar últimas N predicciones
        recent = self.prediction_history[-min(window, len(self.prediction_history)):]
        
        # Calcular métricas
        probabilities = [p["buy_probability"] for p in recent]
        confidences = [p["confidence"] for p in recent]
        
        # Calcular precisión teórica (asumiendo que probabilidades > 0.5 deberían ser correctas)
        # En implementación real, necesitaríamos ground truth
        
        return {
            "avg_probability": float(np.mean(probabilities)),
            "std_probability": float(np.std(probabilities)),
            "avg_confidence": float(np.mean(confidences)),
            "num_predictions": len(recent),
            "probability_trend": self._calculate_trend(probabilities),
            "confidence_trend": self._calculate_trend(confidences)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calcula tendencia de una serie"""
        if len(values) < 2:
            return "STABLE"
        
        # Regresión lineal simple
        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        
        if abs(slope) < 0.01:
            return "STABLE"
        elif slope > 0:
            return "INCREASING"
        else:
            return "DECREASING"