#!/usr/bin/env python3
"""
Profit Optimizer - Estrategias avanzadas para maximizar ganancias
Implementa múltiples estrategias de optimización de retornos
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

class ProfitStrategy(Enum):
    """Estrategias de toma de ganancias"""
    FIXED_TP = "fixed_take_profit"           # TP fijo
    TRAILING_STOP = "trailing_stop"          # Trailing stop clásico
    PARTIAL_TRAILING = "partial_trailing"    # TP parcial + trailing
    SCALPING = "scalping"                    # Scalping rápido
    SWING = "swing"                          # Swing trading
    MULTI_TIMEFRAME = "multi_timeframe"      # Estrategia multi-timeframe

@dataclass
class OptimizationConfig:
    """Configuración de optimización de ganancias"""
    
    # Estrategia principal
    primary_strategy: ProfitStrategy = ProfitStrategy.PARTIAL_TRAILING
    
    # Take Profit parcial
    partial_take_profits: List[Tuple[float, float]] = field(default_factory=lambda: [
        (0.03, 0.50),   # 50% en +3%
        (0.05, 0.25),   # 25% en +5%
        (0.08, 0.25)    # 25% con trailing desde +8%
    ])
    
    # Trailing stop config
    trailing_activation: float = 0.02        # Activar trailing al 2%
    trailing_distance: str = "atr_1.5"       # 1.5x ATR
    min_trailing_distance: float = 0.005     # Mínimo 0.5%
    
    # Scalping config
    scalp_profit_target: float = 0.015       # 1.5% target
    scalp_stop_loss: float = 0.008           # 0.8% stop
    scalp_max_duration: int = 300            # 5 minutos máximo
    
    # Swing trading
    swing_profit_target: float = 0.05        # 5% target
    swing_stop_loss: float = 0.02            # 2% stop
    swing_min_duration: int = 900            # 15 minutos mínimo
    
    # Multi-timeframe
    timeframe_weights: Dict[str, float] = field(default_factory=lambda: {
        "1m": 0.20,
        "5m": 0.30,
        "15m": 0.35,
        "1h": 0.15
    })
    
    # Position sizing adaptativo
    max_position_size: float = 0.15          # Máximo 15% del capital
    base_position_size: float = 0.10         # Base 10%
    confidence_multiplier: Dict[float, float] = field(default_factory=lambda: {
        0.6: 0.5,    # 60% confianza -> 50% tamaño
        0.7: 0.8,    # 70% confianza -> 80% tamaño
        0.8: 1.0,    # 80% confianza -> 100% tamaño
        0.9: 1.3,    # 90% confianza -> 130% tamaño
        0.95: 1.5    # 95% confianza -> 150% tamaño
    })
    
    # Compounding
    enable_compounding: bool = True
    compound_threshold: float = 0.02         # Reinvertir después de 2% profit
    compound_percentage: float = 0.50        # Reinvertir 50% de ganancias
    
    # Arbitrage
    enable_arbitrage: bool = True
    min_arbitrage_profit: float = 0.003      # Mínimo 0.3% para arbitrage
    arbitrage_timeout: int = 30              # 30 segundos timeout
    
    # Market making
    enable_market_making: bool = False
    mm_spread_percentage: float = 0.002      # Spread del 0.2%
    mm_min_liquidity: float = 10000          # $10k mínima liquidez

class ProfitOptimizer:
    """Optimizador de ganancias con estrategias avanzadas"""
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.active_strategies: Dict[str, Any] = {}
        self.performance_metrics = {
            "total_trades": 0,
            "profitable_trades": 0,
            "total_profit_usd": 0.0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "sharpe_ratio": 0.0,
            "profit_factor": 0.0
        }
        
        logger.info(f"ProfitOptimizer inicializado con estrategia: {self.config.primary_strategy.value}")
    
    def calculate_adaptive_position_size(self, 
                                       balance: float, 
                                       confidence: float, 
                                       volatility: float,
                                       rsi: float = 50.0) -> Tuple[float, Dict[str, float]]:
        """
        Calcula tamaño de posición adaptativo basado en múltiples factores
        
        Returns:
            Tuple (tamaño_posición, factores_aplicados)
        """
        # Tamaño base
        size = balance * self.config.base_position_size
        
        # Multiplicador por confianza ML
        confidence_mult = 1.0
        for conf_threshold, multiplier in sorted(self.config.confidence_multiplier.items()):
            if confidence >= conf_threshold:
                confidence_mult = multiplier
        
        size *= confidence_mult
        
        # Ajuste por volatilidad (reducir en alta volatilidad)
        if volatility > 0.15:  # >15% volatilidad
            size *= 0.7
        elif volatility > 0.10:  # 10-15% volatilidad
            size *= 0.85
        elif volatility < 0.05:  # <5% volatilidad (muy estable)
            size *= 1.1
        
        # Ajuste por RSI (tendencia clara)
        if 40 < rsi < 60:  # RSI neutro, tendencia estable
            size *= 1.2
        elif rsi < 30 or rsi > 70:  # Sobrecompra/sobreventa extremas
            size *= 0.8
        
        # Ajuste por momento del día
        hour = datetime.now().hour
        if 2 <= hour <= 6:  # Horas bajas de trading (UTC)
            size *= 1.15  # Menos competencia, mejores precios
        elif 14 <= hour <= 18:  # Horas pico
            size *= 0.9  # Más competencia, spreads más amplios
        
        # Limitar tamaño máximo
        max_size = balance * self.config.max_position_size
        size = min(size, max_size)
        
        # Limitar tamaño mínimo (al menos $10)
        size = max(size, 10.0)
        
        factors = {
            "confidence_multiplier": confidence_mult,
            "volatility_adjustment": volatility,
            "rsi_adjustment": rsi,
            "time_adjustment": hour,
            "final_size_percent": (size / balance) * 100
        }
        
        return size, factors
    
    async def execute_partial_take_profit_strategy(self, 
                                                 position: Dict[str, Any],
                                                 current_price: float) -> List[Dict[str, Any]]:
        """
        Ejecuta estrategia de take profit parcial con trailing
        
        Returns:
            Lista de órdenes a ejecutar
        """
        orders = []
        entry_price = position["entry_price"]
        position_size = position["size_usd"]
        
        # Calcular ganancia actual
        current_profit_pct = (current_price - entry_price) / entry_price
        
        # Verificar cada nivel de TP parcial
        for target_pct, close_pct in self.config.partial_take_profits:
            if current_profit_pct >= target_pct:
                # Calcular cantidad a cerrar
                close_amount_usd = position_size * close_pct
                
                order = {
                    "type": "TAKE_PROFIT_PARTIAL",
                    "token": position["token"],
                    "amount_usd": close_amount_usd,
                    "target_price": entry_price * (1 + target_pct),
                    "actual_price": current_price,
                    "profit_percentage": target_pct,
                    "close_percentage": close_pct,
                    "reason": f"TP parcial @ {target_pct*100:.1f}%"
                }
                
                orders.append(order)
                logger.info(f"✅ TP parcial activado: {target_pct*100:.1f}% - Cerrar {close_pct*100:.0f}%")
        
        # Verificar trailing stop (solo si ya activado)
        if position.get("trailing_activated", False):
            trailing_price = position.get("trailing_stop_price")
            if trailing_price and current_price <= trailing_price:
                # Cerrar posición restante
                remaining_pct = 1.0 - sum(pct for _, pct in self.config.partial_take_profits)
                if remaining_pct > 0:
                    close_amount_usd = position_size * remaining_pct
                    
                    order = {
                        "type": "TRAILING_STOP",
                        "token": position["token"],
                        "amount_usd": close_amount_usd,
                        "stop_price": trailing_price,
                        "actual_price": current_price,
                        "profit_percentage": current_profit_pct,
                        "reason": "Trailing stop ejecutado"
                    }
                    
                    orders.append(order)
                    logger.info(f"🚨 Trailing stop ejecutado: {current_profit_pct*100:.2f}% profit")
        
        return orders
    
    async def execute_scalping_strategy(self, 
                                      position: Dict[str, Any],
                                      market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Estrategia de scalping para ganancias rápidas
        """
        orders = []
        current_price = market_data["current_price"]
        entry_price = position["entry_price"]
        entry_time = position["entry_time"]
        
        # Calcular tiempo en posición
        time_in_position = (datetime.now() - entry_time).total_seconds()
        
        # Verificar profit target
        current_profit = (current_price - entry_price) / entry_price
        
        if current_profit >= self.config.scalp_profit_target:
            # TP completo
            order = {
                "type": "SCALP_TAKE_PROFIT",
                "token": position["token"],
                "amount_usd": position["size_usd"],
                "profit_percentage": current_profit,
                "duration_seconds": time_in_position,
                "reason": f"Scalp target alcanzado: {self.config.scalp_profit_target*100:.1f}%"
            }
            orders.append(order)
            
        # Verificar stop loss
        elif current_profit <= -self.config.scalp_stop_loss:
            order = {
                "type": "SCALP_STOP_LOSS",
                "token": position["token"],
                "amount_usd": position["size_usd"],
                "loss_percentage": abs(current_profit),
                "duration_seconds": time_in_position,
                "reason": f"Scalp stop loss: {self.config.scalp_stop_loss*100:.1f}%"
            }
            orders.append(order)
            
        # Verificar timeout
        elif time_in_position > self.config.scalp_max_duration:
            order = {
                "type": "SCALP_TIMEOUT",
                "token": position["token"],
                "amount_usd": position["size_usd"],
                "profit_percentage": current_profit,
                "duration_seconds": time_in_position,
                "reason": f"Scalp timeout después de {self.config.scalp_max_duration}s"
            }
            orders.append(order)
        
        return orders
    
    async def find_arbitrage_opportunities(self) -> List[Dict[str, Any]]:
        """
        Encuentra oportunidades de arbitrage entre DEXs
        """
        if not self.config.enable_arbitrage:
            return []
        
        opportunities = []
        
        # Pares comunes para arbitrage
        common_pairs = [
            ("SOL", "USDC"),
            ("USDC", "SOL"),
            ("ETH", "USDC"),
            ("USDC", "ETH"),
            ("SOL", "ETH")
        ]
        
        for base, quote in common_pairs:
            try:
                # Obtener precios de múltiples DEXs
                prices = await self._get_multi_dex_prices(base, quote, amount=1.0)
                
                if len(prices) >= 2:
                    # Encontrar mejor compra y mejor venta
                    best_buy = min(prices, key=lambda x: x["price"])
                    best_sell = max(prices, key=lambda x: x["price"])
                    
                    # Calcular spread de arbitrage
                    spread = (best_sell["price"] - best_buy["price"]) / best_buy["price"]
                    
                    if spread >= self.config.min_arbitrage_profit:
                        opportunity = {
                            "base": base,
                            "quote": quote,
                            "buy_dex": best_buy["dex"],
                            "buy_price": best_buy["price"],
                            "sell_dex": best_sell["dex"],
                            "sell_price": best_sell["price"],
                            "spread_percentage": spread * 100,
                            "estimated_profit_per_unit": best_sell["price"] - best_buy["price"],
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        opportunities.append(opportunity)
                        logger.info(f"🔍 Oportunidad arbitrage: {base}/{quote} - Spread: {spread*100:.2f}%")
                        
            except Exception as e:
                logger.debug(f"Error buscando arbitrage {base}/{quote}: {e}")
        
        return opportunities
    
    async def _get_multi_dex_prices(self, base: str, quote: str, amount: float) -> List[Dict[str, Any]]:
        """Obtiene precios de múltiples DEXs"""
        # En producción, esto consultaría APIs reales
        dexes = ["orca", "raydium", "jupiter", "serum"]
        prices = []
        
        for dex in dexes:
            # Simular precios con pequeñas diferencias
            base_price = 100.0 if base == "SOL" else 1.0
            spread = np.random.uniform(-0.002, 0.002)  # ±0.2%
            
            price = {
                "dex": dex,
                "price": base_price * (1 + spread),
                "liquidity": np.random.uniform(50000, 500000),
                "slippage": np.random.uniform(0.001, 0.005)
            }
            
            prices.append(price)
        
        return prices
    
    def calculate_dynamic_stop_loss(self,
                                  entry_price: float,
                                  volatility: float,
                                  atr: float = None) -> Dict[str, float]:
        """
        Calcula stop loss dinámico basado en múltiples factores
        """
        # Método 1: Porcentaje fijo basado en volatilidad
        if volatility < 0.05:
            sl_percent = 0.015  # 1.5% para baja volatilidad
        elif volatility < 0.10:
            sl_percent = 0.02   # 2% para volatilidad media
        else:
            sl_percent = 0.025  # 2.5% para alta volatilidad
        
        # Método 2: Basado en ATR (Average True Range)
        if atr and atr > 0:
            atr_sl = entry_price - (atr * 1.5)
            atr_percent = (entry_price - atr_sl) / entry_price
            sl_percent = max(sl_percent, atr_percent)
        
        # Método 3: Basado en soporte cercano (simulado)
        support_level = entry_price * 0.98  # 2% abajo
        support_percent = 0.02
        
        # Tomar el más conservador
        final_sl_percent = max(sl_percent, support_percent)
        stop_loss_price = entry_price * (1 - final_sl_percent)
        
        return {
            "stop_loss_price": stop_loss_price,
            "stop_loss_percent": final_sl_percent,
            "method_used": "dynamic_volatility_atr",
            "volatility": volatility,
            "atr": atr
        }
    
    def calculate_dynamic_take_profit(self,
                                    entry_price: float,
                                    volatility: float,
                                    resistance_levels: List[float] = None) -> Dict[str, Any]:
        """
        Calcula take profit dinámico con múltiples objetivos
        """
        # TP1: Objetivo rápido (scalp)
        tp1_percent = min(0.03, volatility * 0.5)  # 3% o 50% de la volatilidad
        tp1_price = entry_price * (1 + tp1_percent)
        
        # TP2: Objetivo principal
        tp2_percent = volatility * 0.8  # 80% de la volatilidad
        tp2_price = entry_price * (1 + tp2_percent)
        
        # TP3: Objetivo agresivo
        tp3_percent = volatility * 1.2  # 120% de la volatilidad
        tp3_price = entry_price * (1 + tp3_percent)
        
        # Ajustar con niveles de resistencia
        if resistance_levels:
            # Encontrar resistencia más cercana
            closest_resistance = min(resistance_levels, 
                                   key=lambda x: abs(x - entry_price))
            if closest_resistance > entry_price:
                tp2_price = min(tp2_price, closest_resistance * 0.98)  # 2% antes de resistencia
        
        return {
            "take_profit_1": {
                "price": tp1_price,
                "percentage": tp1_percent,
                "description": "Scalp target"
            },
            "take_profit_2": {
                "price": tp2_price,
                "percentage": tp2_percent,
                "description": "Main target"
            },
            "take_profit_3": {
                "price": tp3_price,
                "percentage": tp3_percent,
                "description": "Aggressive target"
            },
            "recommended_strategy": "partial_take_profits" if volatility > 0.08 else "single_take_profit"
        }
    
    async def optimize_entry_timing(self,
                                  token: str,
                                  market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimiza el timing de entrada basado en múltiples factores
        """
        recommendations = []
        
        # 1. Análisis de volumen
        current_volume = market_data.get("volume_24h", 0)
        avg_volume = market_data.get("avg_volume_30d", current_volume)
        
        if current_volume > avg_volume * 1.5:
            recommendations.append({
                "factor": "volume_spike",
                "score": 0.8,
                "message": "Volumen 50%+ sobre promedio - Buena señal"
            })
        elif current_volume < avg_volume * 0.7:
            recommendations.append({
                "factor": "low_volume",
                "score": 0.4,
                "message": "Volumen bajo - Esperar confirmación"
            })
        
        # 2. Análisis de momento del día
        current_hour = datetime.now().hour
        if 2 <= current_hour <= 6:  # UTC horas bajas
            recommendations.append({
                "factor": "low_activity_hours",
                "score": 0.7,
                "message": "Horas de baja actividad - Mejores spreads"
            })
        elif 14 <= current_hour <= 18:  # UTC horas pico
            recommendations.append({
                "factor": "peak_hours",
                "score": 0.5,
                "message": "Horas pico - Más competencia"
            })
        
        # 3. Análisis de sentimiento del mercado
        market_sentiment = market_data.get("sentiment", "neutral")
        sentiment_scores = {
            "very_bullish": 0.9,
            "bullish": 0.7,
            "neutral": 0.5,
            "bearish": 0.3,
            "very_bearish": 0.1
        }
        
        if market_sentiment in sentiment_scores:
            recommendations.append({
                "factor": "market_sentiment",
                "score": sentiment_scores[market_sentiment],
                "message": f"Sentimiento del mercado: {market_sentiment}"
            })
        
        # Calcular score total
        if recommendations:
            total_score = sum(r["score"] for r in recommendations) / len(recommendations)
        else:
            total_score = 0.5
        
        # Recomendación final
        if total_score >= 0.7:
            action = "ENTER_NOW"
            confidence = "HIGH"
        elif total_score >= 0.5:
            action = "WAIT_FOR_CONFIRMATION"
            confidence = "MEDIUM"
        else:
            action = "AVOID_OR_SHORT"
            confidence = "LOW"
        
        return {
            "token": token,
            "overall_score": total_score,
            "action": action,
            "confidence": confidence,
            "recommendations": recommendations,
            "optimal_entry_time": self._calculate_optimal_entry_time(total_score),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_optimal_entry_time(self, score: float) -> datetime:
        """Calcula tiempo óptimo de entrada"""
        now = datetime.now()
        
        if score >= 0.7:
            # Entrar ahora
            return now
        elif score >= 0.5:
            # Esperar 5-15 minutos
            wait_minutes = np.random.randint(5, 16)
            return now + timedelta(minutes=wait_minutes)
        else:
            # Esperar 30+ minutos o siguiente día
            return now + timedelta(hours=1)
    
    async def compound_profits(self, 
                             profits_usd: float, 
                             total_balance: float) -> Dict[str, Any]:
        """
        Estrategia de compounding de ganancias
        """
        if not self.config.enable_compounding:
            return {"action": "NO_COMPOUNDING", "amount": 0.0}
        
        # Calcular porcentaje a reinvertir
        if profits_usd / total_balance >= self.config.compound_threshold:
            reinvest_amount = profits_usd * self.config.compound_percentage
            
            return {
                "action": "REINVEST",
                "reinvest_amount_usd": reinvest_amount,
                "reinvest_percentage": self.config.compound_percentage * 100,
                "remaining_profits_usd": profits_usd - reinvest_amount,
                "new_total_balance": total_balance + reinvest_amount,
                "reason": f"Profits alcanzaron threshold del {self.config.compound_threshold*100:.1f}%"
            }
        else:
            return {
                "action": "HOLD_CASH",
                "reinvest_amount_usd": 0.0,
                "reason": f"Profits ({profits_usd/total_balance*100:.1f}%) bajo threshold"
            }
    
    def update_performance_metrics(self, 
                                 trade_result: Dict[str, Any]) -> None:
        """Actualiza métricas de performance"""
        self.performance_metrics["total_trades"] += 1
        
        if trade_result.get("profit_usd", 0) > 0:
            self.performance_metrics["profitable_trades"] += 1
        
        self.performance_metrics["total_profit_usd"] += trade_result.get("profit_usd", 0)
        
        # Calcular Sharpe Ratio (simplificado)
        if self.performance_metrics["total_trades"] > 10:
            avg_return = self.performance_metrics["total_profit_usd"] / self.performance_metrics["total_trades"]
            # En producción, calcularías desviación estándar real
            self.performance_metrics["sharpe_ratio"] = avg_return * np.sqrt(365) / 0.1  # Asumiendo 10% volatilidad
        
        # Calcular Profit Factor
        total_wins = sum(1 for _ in range(self.performance_metrics["profitable_trades"]))
        total_losses = self.performance_metrics["total_trades"] - total_wins
        
        if total_losses > 0:
            self.performance_metrics["profit_factor"] = (
                self.performance_metrics["total_profit_usd"] / 
                (total_losses * 100)  # Asumiendo pérdida promedio de $100
            )
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Genera recomendaciones de optimización basadas en performance"""
        win_rate = (self.performance_metrics["profitable_trades"] / 
                   max(1, self.performance_metrics["total_trades"]))
        
        recommendations = []
        
        if win_rate < 0.5:
            recommendations.append({
                "area": "entry_timing",
                "action": "AUMENTAR_UMBRAL_CONFIANZA",
                "current_value": "60%",
                "recommended_value": "70%",
                "reason": f"Win rate baja ({win_rate*100:.1f}%)"
            })
            
            recommendations.append({
                "area": "position_sizing",
                "action": "REDUCIR_TAMAÑO_POSICIÓN",
                "current_value": "10%",
                "recommended_value": "7%",
                "reason": "Protección de capital durante racha negativa"
            })
        
        if self.performance_metrics["profit_factor"] < 1.2:
            recommendations.append({
                "area": "risk_management",
                "action": "AJUSTAR_STOP_LOSS",
                "current_value": "2%",
                "recommended_value": "1.5%",
                "reason": f"Profit factor bajo ({self.performance_metrics['profit_factor']:.2f})"
            })
        
        if self.performance_metrics["sharpe_ratio"] < 1.5:
            recommendations.append({
                "area": "strategy_diversification",
                "action": "AÑADIR_ESTRATEGIA_ARBITRAJE",
                "reason": f"Sharpe ratio bajo ({self.performance_metrics['sharpe_ratio']:.2f})"
            })
        
        return {
            "current_performance": self.performance_metrics,
            "recommendations": recommendations,
            "estimated_impact": "10-30% mejora en retornos",
            "implementation_time": "1-2 horas"
        }

# Instancia global
profit_optimizer = ProfitOptimizer()