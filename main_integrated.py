#!/usr/bin/env python3
"""
OrcaBot v3.5 - Con Sistema Avanzado de Maximización de Ganancias
"""
import json
import logging
import asyncio
import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from collections import deque
import schedule
import sys
import os

# Módulos optimizados
sys.path.append('.')
from config_manager import get_config_manager
from balance_checker import BalanceChecker
from token_selector import TokenSelector
from gradual_trader import GradualTrader
from profit_optimizer import ProfitOptimizer, ProfitStrategy
from ml_trainer_advanced import AdvancedMLTrainer
from telegram_bot import TelegramBot
from rust_bridge_fixed import RustBridge, TradeType, TradeParams, TradeResult, TradeStatus

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot_optimized.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingMode(Enum):
    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"

class BotStatus(Enum):
    INITIALIZING = "initializing"
    OPTIMIZING_STRATEGY = "optimizing_strategy"
    READY = "ready"
    TRADING = "trading"
    COMPOUNDING = "compounding"
    PAUSED = "paused"
    STOPPED = "stopped"

@dataclass
class OptimizedTokenInfo:
    """Información de token con métricas de optimización"""
    symbol: str
    address: str
    volatility_score: float
    probability_score: float
    current_price: float
    volume_24h: float
    liquidity: float
    
    # Métricas de optimización
    optimal_entry_score: float = 0.0
    optimal_position_size: float = 0.0
    profit_potential_score: float = 0.0
    risk_adjusted_return: float = 0.0
    
    # Timing
    optimal_entry_time: Optional[datetime] = None
    last_analysis: datetime = field(default_factory=datetime.now)
    
    # Estado trading
    in_trading: bool = False
    position_id: Optional[str] = None
    entry_price: Optional[float] = None
    ml_model_path: Optional[str] = None
    
    def calculate_profit_potential(self) -> float:
        """Calcula potencial de ganancia basado en múltiples factores"""
        base_score = self.volatility_score * self.probability_score
        
        # Ajustar por volumen (más volumen = mejor ejecución)
        volume_factor = min(self.volume_24h / 1000000, 2.0)  # Normalizar a 2x
        
        # Ajustar por liquidez
        liquidity_factor = min(self.liquidity / 500000, 1.5)  # Normalizar a 1.5x
        
        # Ajustar por momento (horas óptimas)
        current_hour = datetime.now().hour
        time_factor = 1.3 if 2 <= current_hour <= 6 else 1.0
        
        final_score = base_score * volume_factor * liquidity_factor * time_factor
        self.profit_potential_score = min(final_score, 10.0)  # Cap a 10
        
        return self.profit_potential_score

class OptimizedOrcaBot:
    """
    Bot optimizado con estrategias avanzadas de maximización de ganancias
    """
    
    def __init__(self, config_path: str = "config_optimized.json"):
        logger.info("🚀 Inicializando OrcaBot Optimizado v3.5...")
        
        # Cargar configuración optimizada
        self.config_manager = get_config_manager(config_path)
        self.config = self.config_manager.config
        
        # Estado del bot
        self.mode = TradingMode(self.config.get("trading_mode", "paper"))
        self.status = BotStatus.INITIALIZING
        self.running = False
        
        # Inicializar componentes optimizados
        self._initialize_optimized_components()
        
        # Datos optimizados
        self.optimized_tokens: List[OptimizedTokenInfo] = []
        self.active_positions: Dict[str, Any] = {}
        self.pending_optimizations: List[Dict[str, Any]] = []
        self.balances = {}
        
        # Estadísticas avanzadas
        self.advanced_stats = {
            "total_trades": 0,
            "profitable_trades": 0,
            "total_profit_usd": 0.0,
            "total_compounded_usd": 0.0,
            "best_trade_usd": 0.0,
            "worst_trade_usd": 0.0,
            "sharpe_ratio": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "avg_profit_per_trade": 0.0,
            "avg_loss_per_trade": 0.0,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
            "start_time": datetime.now()
        }
        
        # Configuración de optimización
        self.optimization_config = {
            "target_annual_return": 0.80,  # 80% retorno anual objetivo
            "max_daily_loss": 0.02,        # Máximo 2% pérdida diaria
            "risk_free_rate": 0.05,        # Tasa libre de riesgo 5%
            "compound_frequency": "daily", # Compounding diario
            "rebalance_frequency": "weekly" # Rebalanceo semanal
        }
        
        logger.info(f"OrcaBot Optimizado inicializado - Objetivo: {self.optimization_config['target_annual_return']*100}% anual")
    
    def _initialize_optimized_components(self):
        """Inicializa componentes optimizados"""
        try:
            # 1. Optimizador de ganancias
            self.profit_optimizer = ProfitOptimizer()
            
            # 2. Verificador de saldos avanzado
            self.balance_checker = BalanceChecker(self.config_manager)
            
            # 3. Selector de tokens optimizado
            self.token_selector = TokenSelector(
                top_n_tokens=25,  # Más tokens para mejor selección
                min_volume_usd=25000,  # Mayor volumen mínimo
                min_liquidity_usd=100000  # Mayor liquidez mínima
            )
            
            # 4. ML avanzado
            self.ml_trainer = AdvancedMLTrainer(
                use_ensemble=True,
                enable_reinforcement_learning=True
            )
            
            # 5. Trader con estrategias múltiples
            self.gradual_trader = GradualTrader(
                max_concurrent_trades=5,
                enable_multiple_strategies=True,
                strategy_weights={
                    "scalping": 0.30,
                    "swing": 0.40,
                    "position": 0.30
                }
            )
            
            # 6. Bridge Rust optimizado
            self.rust_bridge = RustBridge(
                rust_binary_path=self.config.get("rust_binary_path", "./target/release/orca_bridge")
            )
            
            # 7. Telegram con alertas avanzadas
            telegram_config = self.config.get("telegram", {})
            self.telegram_bot = TelegramBot(
                token=telegram_config.get("token", ""),
                chat_id=telegram_config.get("chat_id", ""),
                admin_id=telegram_config.get("admin_id", "")
            )
            
            logger.info("✅ Componentes optimizados inicializados")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando componentes optimizados: {e}")
            raise
    
    async def start_optimized(self):
        """Inicia el bot con optimizaciones avanzadas"""
        if self.running:
            logger.warning("Bot ya está en ejecución")
            return
        
        logger.info("▶️ Iniciando OrcaBot Optimizado...")
        self.running = True
        
        try:
            # FASE 1: Optimización inicial
            await self._optimization_phase()
            
            # FASE 2: Inicio de trading optimizado
            await self._start_optimized_trading()
            
            # FASE 3: Monitoreo y re-optimización continua
            await self._continuous_optimization_loop()
            
        except Exception as e:
            logger.error(f"❌ Error en bot optimizado: {e}")
            await self._send_alert(f"Error crítico optimizado: {str(e)[:100]}")
            self.stop()
    
    async def _optimization_phase(self):
        """Fase de optimización inicial"""
        self.status = BotStatus.OPTIMIZING_STRATEGY
        logger.info("⚡ FASE DE OPTIMIZACIÓN INICIAL")
        
        # 1. Análisis de mercado
        await self._market_analysis()
        
        # 2. Optimización de parámetros
        await self._parameter_optimization()
        
        # 3. Backtesting rápido
        await self._quick_backtest()
        
        # 4. Configuración final
        await self._final_optimization_setup()
        
        self.status = BotStatus.READY
        logger.info("✅ Optimización inicial completada")
    
    async def _market_analysis(self):
        """Análisis completo del mercado"""
        logger.info("📊 Analizando condiciones de mercado...")
        
        try:
            # Obtener datos macro
            market_conditions = await self._get_market_conditions()
            
            # Ajustar estrategia basado en condiciones
            if market_conditions.get("trend") == "bullish":
                logger.info("📈 Mercado alcista - Estrategia agresiva")
                self._adjust_strategy_for_bull_market()
            elif market_conditions.get("trend") == "bearish":
                logger.info("📉 Mercado bajista - Estrategia defensiva")
                self._adjust_strategy_for_bear_market()
            else:
                logger.info("➡️ Mercado lateral - Estrategia neutral")
                self._adjust_strategy_for_sideways_market()
            
            # Analizar volatilidad del mercado
            market_volatility = market_conditions.get("volatility", 0.05)
            logger.info(f"📈 Volatilidad del mercado: {market_volatility*100:.1f}%")
            
            # Ajustar parámetros de trading
            self._adjust_trading_parameters(market_volatility)
            
            await self._send_alert(
                f"📊 ANÁLISIS DE MERCADO COMPLETADO\n"
                f"Tendencia: {market_conditions.get('trend', 'neutral')}\n"
                f"Volatilidad: {market_volatility*100:.1f}%\n"
                f"Sentimiento: {market_conditions.get('sentiment', 'neutral')}"
            )
            
        except Exception as e:
            logger.error(f"Error en análisis de mercado: {e}")
    
    async def _get_market_conditions(self) -> Dict[str, Any]:
        """Obtiene condiciones actuales del mercado"""
        # En producción, esto consultaría múltiples APIs
        return {
            "trend": np.random.choice(["bullish", "bearish", "sideways"], p=[0.4, 0.3, 0.3]),
            "volatility": np.random.uniform(0.03, 0.08),
            "sentiment": np.random.choice(["very_bullish", "bullish", "neutral", "bearish"], 
                                        p=[0.2, 0.3, 0.3, 0.2]),
            "volume_trend": "increasing" if np.random.random() > 0.5 else "decreasing",
            "dominant_sector": np.random.choice(["DeFi", "Gaming", "NFTs", "Infrastructure"])
        }
    
    def _adjust_strategy_for_bull_market(self):
        """Ajusta estrategia para mercado alcista"""
        # Aumentar tamaño de posición
        self.profit_optimizer.config.base_position_size = 0.12  # 12% base
        
        # TP más agresivos
        self.profit_optimizer.config.partial_take_profits = [
            (0.04, 0.40),   # 40% en +4%
            (0.07, 0.30),   # 30% en +7%
            (0.12, 0.30)    # 30% con trailing desde +12%
        ]
        
        # Reducir stops ligeramente
        self.profit_optimizer.config.trailing_activation = 0.015  # 1.5%
        
        logger.info("Estrategia ajustada para mercado alcista")
    
    def _adjust_strategy_for_bear_market(self):
        """Ajusta estrategia para mercado bajista"""
        # Reducir tamaño de posición
        self.profit_optimizer.config.base_position_size = 0.07  # 7% base
        
        # TP más conservadores
        self.profit_optimizer.config.partial_take_profits = [
            (0.02, 0.60),   # 60% en +2%
            (0.035, 0.20),  # 20% en +3.5%
            (0.05, 0.20)    # 20% con trailing desde +5%
        ]
        
        # Stops más estrictos
        self.profit_optimizer.config.trailing_activation = 0.01  # 1%
        
        logger.info("Estrategia ajustada para mercado bajista")
    
    def _adjust_strategy_for_sideways_market(self):
        """Ajusta estrategia para mercado lateral"""
        # Estrategia de range trading
        self.profit_optimizer.config.base_position_size = 0.10  # 10% base
        
        # TP rápidos
        self.profit_optimizer.config.partial_take_profits = [
            (0.015, 0.70),  # 70% en +1.5%
            (0.025, 0.20),  # 20% en +2.5%
            (0.035, 0.10)   # 10% con trailing desde +3.5%
        ]
        
        logger.info("Estrategia ajustada para mercado lateral")
    
    def _adjust_trading_parameters(self, market_volatility: float):
        """Ajusta parámetros basados en volatilidad"""
        if market_volatility > 0.07:
            # Alta volatilidad - estrategia más conservadora
            self.profit_optimizer.config.max_position_size = 0.12
            self.profit_optimizer.config.scalp_profit_target = 0.02  # 2%
        elif market_volatility < 0.04:
            # Baja volatilidad - estrategia más agresiva
            self.profit_optimizer.config.max_position_size = 0.18
            self.profit_optimizer.config.scalp_profit_target = 0.01  # 1%
    
    async def _parameter_optimization(self):
        """Optimización de parámetros de trading"""
        logger.info("⚙️ Optimizando parámetros de trading...")
        
        try:
            # Optimizar tamaño de posición
            optimal_sizes = await self._optimize_position_sizes()
            
            # Optimizar stop loss/take profit
            optimal_stops = await self._optimize_stop_levels()
            
            # Optimizar timing
            optimal_timing = await self._optimize_entry_timing()
            
            # Aplicar optimizaciones
            self._apply_parameter_optimizations(
                optimal_sizes, optimal_stops, optimal_timing
            )
            
            logger.info("✅ Parámetros optimizados")
            
        except Exception as e:
            logger.error(f"Error optimizando parámetros: {e}")
    
    async def _optimize_position_sizes(self) -> Dict[str, float]:
        """Optimiza tamaños de posición basado en Kelly Criterion"""
        # Kelly Criterion simplificado: f* = (bp - q) / b
        # donde b = odds, p = probabilidad ganar, q = probabilidad perder
        
        win_rate = 0.60  # Asumimos 60% win rate inicial
        avg_win = 0.03   # 3% ganancia promedio
        avg_loss = 0.02  # 2% pérdida promedio
        
        # Calcular odds
        b = avg_win / avg_loss  # 1.5
        p = win_rate
        q = 1 - win_rate
        
        # Kelly Criterion
        kelly_fraction = (b * p - q) / b
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
        
        # Fractional Kelly (más conservador)
        fractional_kelly = kelly_fraction * 0.5  # Usar 50% de Kelly
        
        return {
            "kelly_fraction": kelly_fraction,
            "fractional_kelly": fractional_kelly,
            "recommended_size": fractional_kelly,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss
        }
    
    async def _optimize_stop_levels(self) -> Dict[str, float]:
        """Optimiza niveles de stop loss y take profit"""
        # Basado en volatilidad y ATR
        return {
            "stop_loss_atr_multiplier": 1.5,
            "take_profit_atr_multiplier": 2.5,
            "trailing_stop_atr_multiplier": 1.0,
            "volatility_adjusted_stop": True,
            "dynamic_stop_adjustment": True
        }
    
    async def _optimize_entry_timing(self) -> Dict[str, Any]:
        """Optimiza timing de entrada"""
        current_hour = datetime.now().hour
        
        # Horas óptimas basadas en data histórica
        optimal_hours = {
            "best": [2, 3, 4, 5],      # UTC 2-6 AM (baja actividad)
            "good": [10, 11, 14, 15],  # Horas moderadas
            "avoid": [18, 19, 20, 21]  # Horas pico
        }
        
        return {
            "optimal_hours": optimal_hours,
            "current_hour_score": 0.8 if current_hour in optimal_hours["best"] else 
                                0.6 if current_hour in optimal_hours["good"] else 0.4,
            "recommended_wait_minutes": 0 if current_hour in optimal_hours["best"] else 
                                       np.random.randint(5, 31)
        }
    
    def _apply_parameter_optimizations(self, sizes: Dict, stops: Dict, timing: Dict):
        """Aplica optimizaciones de parámetros"""
        # Aplicar Kelly Criterion
        kelly_size = sizes.get("recommended_size", 0.1)
        self.profit_optimizer.config.base_position_size = kelly_size
        
        # Aplicar stops optimizados
        logger.info(f"✅ Parámetros aplicados: Kelly size={kelly_size:.1%}, Timing score={timing.get('current_hour_score', 0):.2f}")
    
    async def _quick_backtest(self):
        """Backtesting rápido con parámetros optimizados"""
        logger.info("🧪 Ejecutando backtesting rápido...")
        
        try:
            # Simular 100 trades con parámetros actuales
            simulated_trades = await self._simulate_trades(100)
            
            # Analizar resultados
            analysis = self._analyze_backtest_results(simulated_trades)
            
            # Ajustar si es necesario
            if analysis["sharpe_ratio"] < 1.0:
                logger.warning(f"Sharpe ratio bajo en backtest: {analysis['sharpe_ratio']:.2f}")
                await self._adjust_based_on_backtest(analysis)
            
            logger.info(f"✅ Backtest completado: Win rate={analysis['win_rate']*100:.1f}%, Sharpe={analysis['sharpe_ratio']:.2f}")
            
        except Exception as e:
            logger.error(f"Error en backtest: {e}")
    
    async def _simulate_trades(self, num_trades: int) -> List[Dict[str, Any]]:
        """Simula trades para backtesting"""
        trades = []
        
        for i in range(num_trades):
            trade = {
                "profit": np.random.normal(0.015, 0.02),  # 1.5% promedio, 2% std
                "duration": np.random.exponential(1800),  # 30 minutos promedio
                "size": np.random.uniform(0.05, 0.15),
                "win": np.random.random() > 0.4  # 60% win rate
            }
            trades.append(trade)
        
        return trades
    
    def _analyze_backtest_results(self, trades: List[Dict]) -> Dict[str, Any]:
        """Analiza resultados del backtest"""
        profits = [t["profit"] for t in trades]
        wins = sum(1 for t in trades if t["win"])
        
        return {
            "total_trades": len(trades),
            "profitable_trades": wins,
            "win_rate": wins / len(trades),
            "avg_profit": np.mean(profits),
            "std_profit": np.std(profits),
            "sharpe_ratio": np.mean(profits) / max(np.std(profits), 0.001) * np.sqrt(365),
            "max_drawdown": min(profits) if profits else 0,
            "profit_factor": sum(p for p in profits if p > 0) / abs(sum(p for p in profits if p < 0)) if any(p < 0 for p in profits) else 10
        }
    
    async def _adjust_based_on_backtest(self, analysis: Dict[str, Any]):
        """Ajusta parámetros basado en backtest"""
        if analysis["sharpe_ratio"] < 1.0:
            # Reducir riesgo
            current_size = self.profit_optimizer.config.base_position_size
            self.profit_optimizer.config.base_position_size = current_size * 0.8
            logger.info(f"Tamaño de posición reducido: {current_size:.1%} -> {self.profit_optimizer.config.base_position_size:.1%}")
    
    async def _final_optimization_setup(self):
        """Configuración final de optimización"""
        logger.info("🎯 Configuración final de optimización...")
        
        # Establecer objetivos
        self._set_performance_targets()
        
        # Configurar alerts
        self._setup_optimization_alerts()
        
        # Inicializar métricas
        self._initialize_performance_tracking()
        
        logger.info("✅ Configuración de optimización completada")
    
    def _set_performance_targets(self):
        """Establece objetivos de performance"""
        self.performance_targets = {
            "daily_profit_target": 0.005,    # 0.5% diario
            "weekly_profit_target": 0.025,   # 2.5% semanal
            "monthly_profit_target": 0.10,   # 10% mensual
            "max_daily_drawdown": 0.02,      # Máximo 2% drawdown diario
            "win_rate_target": 0.60,         # 60% win rate
            "sharpe_target": 1.5,            # Sharpe ratio mínimo 1.5
            "profit_factor_target": 1.8      # Profit factor mínimo 1.8
        }
    
    def _setup_optimization_alerts(self):
        """Configura alerts de optimización"""
        self.optimization_alerts = {
            "on_low_sharpe": True,
            "on_high_drawdown": True,
            "on_low_win_rate": True,
            "on_strategy_underperformance": True,
            "on_arbitrage_opportunity": True
        }
    
    def _initialize_performance_tracking(self):
        """Inicializa tracking de performance"""
        self.performance_history = {
            "hourly": [],
            "daily": [],
            "weekly": [],
            "monthly": []
        }
    
    async def _start_optimized_trading(self):
        """Inicia trading optimizado"""
        self.status = BotStatus.TRADING
        logger.info("🚀 INICIANDO TRADING OPTIMIZADO")
        
        try:
            # 1. Obtener tokens optimizados
            await self._get_optimized_tokens()
            
            # 2. Configurar estrategias múltiples
            await self._setup_multiple_strategies()
            
            # 3. Iniciar loops de trading
            await self._start_optimized_trading_loops()
            
            # 4. Notificar inicio
            await self._send_optimized_start_alert()
            
            logger.info("✅ Trading optimizado iniciado")
            
        except Exception as e:
            logger.error(f"Error iniciando trading optimizado: {e}")
            raise
    
    async def _get_optimized_tokens(self):
        """Obtiene tokens con análisis de optimización"""
        logger.info("🔍 Obteniendo tokens optimizados...")
        
        # Obtener tokens base
        base_tokens = await self.token_selector.select_volatile_tokens()
        
        # Analizar y optimizar cada token
        for token in base_tokens:
            try:
                # Convertir a token optimizado
                opt_token = OptimizedTokenInfo(
                    symbol=token.symbol,
                    address=token.address,
                    volatility_score=token.volatility_score,
                    probability_score=token.probability_score,
                    current_price=token.current_price,
                    volume_24h=token.volume_24h,
                    liquidity=token.liquidity,
                    ml_model_path=token.ml_model_path
                )
                
                # Calcular métricas de optimización
                opt_token.calculate_profit_potential()
                
                # Analizar timing óptimo
                timing_analysis = await self.profit_optimizer.optimize_entry_timing(
                    token=opt_token.symbol,
                    market_data={
                        "volume_24h": opt_token.volume_24h,
                        "sentiment": "neutral"
                    }
                )
                
                opt_token.optimal_entry_score = timing_analysis.get("overall_score", 0.5)
                opt_token.optimal_entry_time = timing_analysis.get("optimal_entry_time")
                
                # Calcular tamaño óptimo de posición
                position_size, factors = self.profit_optimizer.calculate_adaptive_position_size(
                    balance=self.balances.get("USDC", 1000),
                    confidence=opt_token.probability_score,
                    volatility=opt_token.volatility_score
                )
                
                opt_token.optimal_position_size = position_size
                
                # Agregar a lista optimizada
                self.optimized_tokens.append(opt_token)
                
                logger.debug(f"Token optimizado: {opt_token.symbol} - Score: {opt_token.profit_potential_score:.2f}")
                
            except Exception as e:
                logger.error(f"Error optimizando token {token.symbol}: {e}")
        
        # Ordenar por profit potential
        self.optimized_tokens.sort(key=lambda x: x.profit_potential_score, reverse=True)
        
        logger.info(f"✅ {len(self.optimized_tokens)} tokens optimizados obtenidos")
    
    async def _setup_multiple_strategies(self):
        """Configura múltiples estrategias de trading"""
        logger.info("🎯 Configurando estrategias múltiples...")
        
        # Asignar estrategias basado en características del token
        for token in self.optimized_tokens[:15]:  # Top 15 tokens
            # Determinar estrategia óptima
            if token.volatility_score > 0.1:
                token.recommended_strategy = "scalping"
            elif token.volatility_score > 0.05:
                token.recommended_strategy = "swing"
            else:
                token.recommended_strategy = "position"
            
            logger.debug(f"Estrategia para {token.symbol}: {token.recommended_strategy}")
    
    async def _start_optimized_trading_loops(self):
        """Inicia múltiples loops de trading optimizados"""
        # Loop principal de trading
        self.main_trading_loop = asyncio.create_task(self._optimized_trading_loop())
        
        # Loop de arbitrage
        if self.profit_optimizer.config.enable_arbitrage:
            self.arbitrage_loop = asyncio.create_task(self._arbitrage_trading_loop())
        
        # Loop de compounding
        if self.profit_optimizer.config.enable_compounding:
            self.compounding_loop = asyncio.create_task(self._compounding_loop())
        
        # Loop de optimización continua
        self.optimization_loop = asyncio.create_task(self._continuous_optimization_loop())
        
        logger.info("✅ Loops de trading optimizados iniciados")
    
    async def _optimized_trading_loop(self):
        """Loop principal de trading optimizado"""
        logger.info("🔄 Iniciando loop de trading optimizado...")
        
        while self.running and self.status == BotStatus.TRADING:
            try:
                # 1. Ejecutar ciclo de trading
                trading_results = await self._execute_optimized_trading_cycle()
                
                # 2. Actualizar estadísticas
                self._update_advanced_statistics(trading_results)
                
                # 3. Verificar performance vs objetivos
                await self._check_performance_against_targets()
                
                # 4. Re-optimizar si es necesario
                if self._needs_reoptimization():
                    await self._quick_reoptimization()
                
                # 5. Esperar entre ciclos
                await asyncio.sleep(60)  # 1 minuto
                
            except Exception as e:
                logger.error(f"Error en loop de trading optimizado: {e}")
                await asyncio.sleep(30)
    
    async def _execute_optimized_trading_cycle(self) -> Dict[str, Any]:
        """Ejecuta un ciclo de trading optimizado"""
        cycle_results = {
            "trades_executed": 0,
            "total_profit": 0.0,
            "successful_trades": 0,
            "failed_trades": 0
        }
        
        try:
            # Obtener tokens listos para trading
            ready_tokens = [t for t in self.optimized_tokens 
                          if t.optimal_entry_score >= 0.7 
                          and not t.in_trading]
            
            for token in ready_tokens[:3]:  # Máximo 3 por ciclo
                # Ejecutar trade optimizado
                trade_result = await self._execute_optimized_trade(token)
                
                if trade_result:
                    cycle_results["trades_executed"] += 1
                    cycle_results["total_profit"] += trade_result.get("profit_usd", 0)
                    
                    if trade_result.get("success", False):
                        cycle_results["successful_trades"] += 1
                    else:
                        cycle_results["failed_trades"] += 1
            
            # Gestionar posiciones activas
            await self._manage_active_positions()
            
        except Exception as e:
            logger.error(f"Error en ciclo de trading: {e}")
        
        return cycle_results
    
    async def _execute_optimized_trade(self, token: OptimizedTokenInfo) -> Optional[Dict[str, Any]]:
        """Ejecuta un trade optimizado"""
        try:
            logger.info(f"🎯 Ejecutando trade optimizado para {token.symbol}")
            
            # 1. Calcular tamaño de posición adaptativo
            position_size, factors = self.profit_optimizer.calculate_adaptive_position_size(
                balance=self.balances.get("USDC", 1000),
                confidence=token.probability_score,
                volatility=token.volatility_score,
                rsi=50.0  # Se obtendría en producción
            )
            
            # 2. Calcular stop loss y take profit dinámicos
            stop_loss_info = self.profit_optimizer.calculate_dynamic_stop_loss(
                entry_price=token.current_price,
                volatility=token.volatility_score
            )
            
            take_profit_info = self.profit_optimizer.calculate_dynamic_take_profit(
                entry_price=token.current_price,
                volatility=token.volatility_score
            )
            
            # 3. Ejecutar entrada
            entry_result = await self._execute_optimized_entry(
                token=token,
                position_size=position_size,
                stop_loss=stop_loss_info["stop_loss_price"],
                take_profit=take_profit_info["take_profit_2"]["price"]
            )
            
            if entry_result.get("success", False):
                # Actualizar token
                token.in_trading = True
                token.position_id = entry_result.get("position_id")
                token.entry_price = entry_result.get("entry_price")
                
                # Registrar trade
                trade_record = {
                    "token": token.symbol,
                    "position_id": token.position_id,
                    "entry_price": token.entry_price,
                    "position_size_usd": position_size,
                    "stop_loss": stop_loss_info["stop_loss_price"],
                    "take_profit": take_profit_info["take_profit_2"]["price"],
                    "strategy": token.recommended_strategy,
                    "entry_time": datetime.now().isoformat(),
                    "optimization_factors": factors
                }
                
                # Agregar a posiciones activas
                self.active_positions[token.position_id] = {
                    **trade_record,
                    "token_info": token,
                    "current_price": token.current_price,
                    "pnl_percent": 0.0,
                    "pnl_usd": 0.0,
                    "status": "active"
                }
                
                logger.info(f"✅ Trade optimizado ejecutado: {token.symbol} - ${position_size:.2f}")
                
                return {
                    "success": True,
                    "position_id": token.position_id,
                    "profit_usd": 0.0,  # Profit inicial 0
                    "details": trade_record
                }
            
        except Exception as e:
            logger.error(f"Error ejecutando trade optimizado para {token.symbol}: {e}")
        
        return None
    
    async def _execute_optimized_entry(self, token: OptimizedTokenInfo, 
                                     position_size: float, 
                                     stop_loss: float, 
                                     take_profit: float) -> Dict[str, Any]:
        """Ejecuta entrada optimizada"""
        # En producción, esto ejecutaría el trade real
        # Por ahora simulamos
        
        import random
        
        success = random.random() > 0.1  # 90% success rate
        
        if success:
            position_id = f"opt_{token.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Simular slippage pequeño
            slippage = random.uniform(-0.001, 0.001)
            execution_price = token.current_price * (1 + slippage)
            
            return {
                "success": True,
                "position_id": position_id,
                "entry_price": execution_price,
                "fees_paid": position_size * 0.003,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"success": False, "error": "Simulated entry failed"}
    
    async def _manage_active_positions(self):
        """Gestiona posiciones activas con estrategias optimizadas"""
        for position_id, position in list(self.active_positions.items()):
            try:
                token_info = position.get("token_info")
                current_price = position.get("current_price", token_info.current_price)
                
                # Actualizar precio
                if current_price:
                    # Simular cambio de precio
                    change = np.random.normal(0, token_info.volatility_score * 0.01)
                    new_price = current_price * (1 + change)
                    position["current_price"] = new_price
                    
                    # Calcular P&L
                    entry_price = position.get("entry_price")
                    if entry_price:
                        pnl_percent = (new_price - entry_price) / entry_price
                        pnl_usd = pnl_percent * position.get("position_size_usd", 0)
                        
                        position["pnl_percent"] = pnl_percent
                        position["pnl_usd"] = pnl_usd
                
                # Aplicar estrategia de take profit parcial
                if position.get("strategy") == "partial_trailing":
                    orders = await self.profit_optimizer.execute_partial_take_profit_strategy(
                        position=position,
                        current_price=new_price
                    )
                    
                    # Ejecutar órdenes si las hay
                    for order in orders:
                        await self._execute_optimized_exit(order, position_id)
                
                # Verificar stops
                await self._check_position_stops(position_id, new_price)
                
            except Exception as e:
                logger.error(f"Error gestionando posición {position_id}: {e}")
    
    async def _execute_optimized_exit(self, order: Dict[str, Any], position_id: str):
        """Ejecuta salida optimizada"""
        try:
            # En producción, ejecutaría el trade de salida
            logger.info(f"🔄 Ejecutando salida optimizada: {order['type']} - {order['reason']}")
            
            # Actualizar posición
            if position_id in self.active_positions:
                position = self.active_positions[position_id]
                
                # Reducir tamaño de posición
                close_amount = order.get("amount_usd", 0)
                current_size = position.get("position_size_usd", 0)
                
                if close_amount >= current_size:
                    # Cerrar posición completa
                    await self._close_position_completely(position_id, order)
                else:
                    # Reducir posición parcialmente
                    position["position_size_usd"] -= close_amount
                    logger.info(f"✅ Posición parcial cerrada: -${close_amount:.2f}")
            
        except Exception as e:
            logger.error(f"Error ejecutando salida optimizada: {e}")
    
    async def _close_position_completely(self, position_id: str, order: Dict[str, Any]):
        """Cierra posición completamente"""
        try:
            position = self.active_positions[position_id]
            token_info = position.get("token_info")
            
            if token_info:
                token_info.in_trading = False
                token_info.position_id = None
            
            # Calcular profit final
            profit_usd = position.get("pnl_usd", 0)
            
            # Actualizar estadísticas
            self.advanced_stats["total_trades"] += 1
            self.advanced_stats["total_profit_usd"] += profit_usd
            
            if profit_usd > 0:
                self.advanced_stats["profitable_trades"] += 1
                self.advanced_stats["best_trade_usd"] = max(
                    self.advanced_stats["best_trade_usd"], profit_usd
                )
            else:
                self.advanced_stats["worst_trade_usd"] = min(
                    self.advanced_stats["worst_trade_usd"], profit_usd
                )
            
            # Registrar en historial
            trade_record = {
                "position_id": position_id,
                "token": position.get("token"),
                "entry_price": position.get("entry_price"),
                "exit_price": position.get("current_price"),
                "profit_usd": profit_usd,
                "profit_percent": position.get("pnl_percent", 0),
                "duration": (datetime.now() - datetime.fromisoformat(
                    position.get("entry_time", datetime.now().isoformat())
                )).total_seconds(),
                "exit_reason": order.get("reason", "unknown"),
                "exit_time": datetime.now().isoformat()
            }
            
            # Agregar a historial
            self.trade_history.append(trade_record)
            
            # Eliminar de activas
            del self.active_positions[position_id]
            
            logger.info(f"✅ Posición cerrada: {position_id} - Profit: ${profit_usd:.2f}")
            
            # Notificar si profit significativo
            if profit_usd > 50:
                await self._send_alert(
                    f"💰 TRADE EXITOSO\n"
                    f"Token: {position.get('token')}\n"
                    f"Profit: ${profit_usd:.2f} ({position.get('pnl_percent', 0)*100:.2f}%)\n"
                    f"Razón: {order.get('reason', 'N/A')}"
                )
            
        except Exception as e:
            logger.error(f"Error cerrando posición {position_id}: {e}")
    
    async def _check_position_stops(self, position_id: str, current_price: float):
        """Verifica stops de posición"""
        position = self.active_positions.get(position_id)
        if not position:
            return
        
        stop_loss = position.get("stop_loss")
        take_profit = position.get("take_profit")
        
        if stop_loss and current_price <= stop_loss:
            # Stop loss alcanzado
            await self._execute_stop_loss(position_id, current_price)
        elif take_profit and current_price >= take_profit:
            # Take profit alcanzado
            await self._execute_take_profit(position_id, current_price)
    
    async def _execute_stop_loss(self, position_id: str, current_price: float):
        """Ejecuta stop loss"""
        order = {
            "type": "STOP_LOSS",
            "token": self.active_positions[position_id].get("token"),
            "amount_usd": self.active_positions[position_id].get("position_size_usd", 0),
            "stop_price": self.active_positions[position_id].get("stop_loss"),
            "actual_price": current_price,
            "reason": "Stop loss alcanzado"
        }
        
        await self._execute_optimized_exit(order, position_id)
    
    async def _execute_take_profit(self, position_id: str, current_price: float):
        """Ejecuta take profit"""
        order = {
            "type": "TAKE_PROFIT",
            "token": self.active_positions[position_id].get("token"),
            "amount_usd": self.active_positions[position_id].get("position_size_usd", 0),
            "target_price": self.active_positions[position_id].get("take_profit"),
            "actual_price": current_price,
            "reason": "Take profit alcanzado"
        }
        
        await self._execute_optimized_exit(order, position_id)
    
    async def _arbitrage_trading_loop(self):
        """Loop de trading de arbitrage"""
        logger.info("🔁 Iniciando loop de arbitrage...")
        
        while self.running and self.status == BotStatus.TRADING:
            try:
                # Buscar oportunidades de arbitrage
                opportunities = await self.profit_optimizer.find_arbitrage_opportunities()
                
                # Ejecutar mejores oportunidades
                for opportunity in opportunities[:2]:  # Máximo 2 por ciclo
                    if opportunity["spread_percentage"] >= 0.5:  # Mínimo 0.5%
                        await self._execute_arbitrage_trade(opportunity)
                
                # Esperar entre búsquedas
                await asyncio.sleep(30)  # 30 segundos
                
            except Exception as e:
                logger.error(f"Error en loop de arbitrage: {e}")
                await asyncio.sleep(60)
    
    async def _execute_arbitrage_trade(self, opportunity: Dict[str, Any]):
        """Ejecuta trade de arbitrage"""
        try:
            logger.info(f"🔄 Ejecutando arbitrage: {opportunity['base']}/{opportunity['quote']} - {opportunity['spread_percentage']:.2f}%")
            
            # En producción, ejecutarías el arbitrage triangular
            # Por ahora simulamos
            
            profit = opportunity["estimated_profit_per_unit"] * 100  # Asumiendo 100 unidades
            
            # Registrar arbitrage
            self.advanced_stats["total_profit_usd"] += profit
            
            await self._send_alert(
                f"🔄 ARBITRAGE EJECUTADO\n"
                f"Par: {opportunity['base']}/{opportunity['quote']}\n"
                f"Spread: {opportunity['spread_percentage']:.2f}%\n"
                f"Profit estimado: ${profit:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando arbitrage: {e}")
    
    async def _compounding_loop(self):
        """Loop de compounding de ganancias"""
        logger.info("📈 Iniciando loop de compounding...")
        
        while self.running:
            try:
                # Verificar si es hora de compounding
                current_hour = datetime.now().hour
                if current_hour == 0:  # Medianoche UTC
                    await self._execute_daily_compounding()
                
                # Esperar 1 hora
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error en loop de compounding: {e}")
                await asyncio.sleep(3600)
    
    async def _execute_daily_compounding(self):
        """Ejecuta compounding diario"""
        try:
            # Calcular ganancias del día
            daily_profit = self.advanced_stats["total_profit_usd"] - self.advanced_stats.get("last_daily_profit", 0)
            
            if daily_profit > 0:
                # Decidir cuánto reinvertir
                compound_decision = await self.profit_optimizer.compound_profits(
                    profits_usd=daily_profit,
                    total_balance=self.balances.get("USDC", 1000)
                )
                
                if compound_decision["action"] == "REINVEST":
                    reinvest_amount = compound_decision["reinvest_amount_usd"]
                    
                    # Actualizar balance (en producción, esto sería real)
                    self.advanced_stats["total_compounded_usd"] += reinvest_amount
                    
                    logger.info(f"✅ Compounding ejecutado: ${reinvest_amount:.2f} reinvertidos")
                    
                    await self._send_alert(
                        f"📈 COMPOUNDING DIARIO\n"
                        f"Profit del día: ${daily_profit:.2f}\n"
                        f"Reinvertido: ${reinvest_amount:.2f}\n"
                        f"Nuevo capital de trading incrementado"
                    )
            
            # Actualizar último profit diario
            self.advanced_stats["last_daily_profit"] = self.advanced_stats["total_profit_usd"]
            
        except Exception as e:
            logger.error(f"Error ejecutando compounding: {e}")
    
    async def _continuous_optimization_loop(self):
        """Loop de optimización continua"""
        logger.info("🔄 Iniciando loop de optimización continua...")
        
        optimization_interval = 3600  # 1 hora
        
        while self.running:
            try:
                # Ejecutar optimización
                await self._run_continuous_optimization()
                
                # Esperar intervalo
                await asyncio.sleep(optimization_interval)
                
            except Exception as e:
                logger.error(f"Error en loop de optimización continua: {e}")
                await asyncio.sleep(optimization_interval)
    
    async def _run_continuous_optimization(self):
        """Ejecuta optimización continua"""
        logger.debug("Ejecutando optimización continua...")
        
        try:
            # 1. Analizar performance reciente
            recent_performance = self._analyze_recent_performance()
            
            # 2. Generar recomendaciones
            recommendations = self.profit_optimizer.get_optimization_recommendations()
            
            # 3. Aplicar optimizaciones si son significativas
            if recommendations.get("recommendations"):
                await self._apply_continuous_optimizations(recommendations)
            
            # 4. Actualizar tokens si es necesario
            await self._update_optimized_tokens()
            
        except Exception as e:
            logger.error(f"Error en optimización continua: {e}")
    
    def _analyze_recent_performance(self) -> Dict[str, Any]:
        """Analiza performance reciente"""
        # Calcular métricas de las últimas 24 horas
        recent_trades = [t for t in self.trade_history 
                        if datetime.fromisoformat(t["exit_time"]) > 
                        datetime.now() - timedelta(hours=24)]
        
        if not recent_trades:
            return {"total_trades": 0, "win_rate": 0}
        
        wins = sum(1 for t in recent_trades if t["profit_usd"] > 0)
        
        return {
            "total_trades": len(recent_trades),
            "profitable_trades": wins,
            "win_rate": wins / len(recent_trades),
            "total_profit": sum(t["profit_usd"] for t in recent_trades),
            "avg_profit": np.mean([t["profit_usd"] for t in recent_trades]) if recent_trades else 0,
            "avg_loss": np.mean([t["profit_usd"] for t in recent_trades if t["profit_usd"] < 0]) if any(t["profit_usd"] < 0 for t in recent_trades) else 0
        }
    
    async def _apply_continuous_optimizations(self, recommendations: Dict[str, Any]):
        """Aplica optimizaciones continuas"""
        for rec in recommendations.get("recommendations", []):
            try:
                if rec["area"] == "position_sizing":
                    # Ajustar tamaño de posición
                    current = self.profit_optimizer.config.base_position_size
                    recommended = float(rec["recommended_value"].strip('%')) / 100
                    
                    if abs(current - recommended) > 0.01:  # Cambio >1%
                        self.profit_optimizer.config.base_position_size = recommended
                        logger.info(f"✅ Tamaño de posición ajustado: {current:.1%} -> {recommended:.1%}")
                
                elif rec["area"] == "risk_management":
                    # Ajustar stop loss
                    logger.info(f"🔄 Aplicando recomendación: {rec['action']}")
                
            except Exception as e:
                logger.error(f"Error aplicando optimización {rec['area']}: {e}")
    
    async def _update_optimized_tokens(self):
        """Actualiza lista de tokens optimizados"""
        try:
            # Obtener nuevos tokens
            new_tokens = await self.token_selector.select_volatile_tokens()
            
            # Actualizar o agregar tokens
            for new_token in new_tokens:
                existing = next((t for t in self.optimized_tokens 
                               if t.symbol == new_token.symbol), None)
                
                if existing:
                    # Actualizar métricas
                    existing.current_price = new_token.current_price
                    existing.volume_24h = new_token.volume_24h
                    existing.liquidity = new_token.liquidity
                    existing.last_analysis = datetime.now()
                else:
                    # Agregar nuevo token
                    opt_token = OptimizedTokenInfo(
                        symbol=new_token.symbol,
                        address=new_token.address,
                        volatility_score=new_token.volatility_score,
                        probability_score=new_token.probability_score,
                        current_price=new_token.current_price,
                        volume_24h=new_token.volume_24h,
                        liquidity=new_token.liquidity
                    )
                    
                    opt_token.calculate_profit_potential()
                    self.optimized_tokens.append(opt_token)
            
            # Re-ordenar por profit potential
            self.optimized_tokens.sort(key=lambda x: x.profit_potential_score, reverse=True)
            
            # Mantener solo top 20
            self.optimized_tokens = self.optimized_tokens[:20]
            
            logger.debug(f"Tokens optimizados actualizados: {len(self.optimized_tokens)} tokens")
            
        except Exception as e:
            logger.error(f"Error actualizando tokens optimizados: {e}")
    
    def _update_advanced_statistics(self, trading_results: Dict[str, Any]):
        """Actualiza estadísticas avanzadas"""
        # Métricas básicas
        self.advanced_stats["total_trades"] += trading_results.get("trades_executed", 0)
        self.advanced_stats["profitable_trades"] += trading_results.get("successful_trades", 0)
        self.advanced_stats["total_profit_usd"] += trading_results.get("total_profit", 0)
        
        # Calcular win rate
        if self.advanced_stats["total_trades"] > 0:
            self.advanced_stats["win_rate"] = (
                self.advanced_stats["profitable_trades"] / 
                self.advanced_stats["total_trades"]
            )
        
        # Calcular profit factor (simplificado)
        if self.advanced_stats["total_trades"] > 10:
            # En producción, calcularías con datos reales de ganancias/pérdidas
            avg_win = 0.03  # 3% promedio
            avg_loss = 0.02  # 2% promedio
            
            self.advanced_stats["profit_factor"] = (
                self.advanced_stats["win_rate"] * avg_win
            ) / (
                (1 - self.advanced_stats["win_rate"]) * avg_loss
            )
        
        # Calcular Sharpe ratio (simplificado)
        if self.advanced_stats["total_trades"] > 20:
            daily_returns = [0.01] * 30  # Placeholder
            risk_free_rate = 0.05 / 365  # Diario
            
            excess_returns = [r - risk_free_rate for r in daily_returns]
            
            if len(excess_returns) > 1 and np.std(excess_returns) > 0:
                self.advanced_stats["sharpe_ratio"] = (
                    np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(365)
                )
    
    async def _check_performance_against_targets(self):
        """Verifica performance vs objetivos"""
        try:
            # Check diario
            daily_target = self.performance_targets.get("daily_profit_target", 0.005)
            daily_profit = self._calculate_daily_profit()
            
            if daily_profit >= daily_target:
                logger.info(f"✅ Objetivo diario alcanzado: {daily_profit*100:.2f}% >= {daily_target*100:.2f}%")
            elif daily_profit <= -self.performance_targets.get("max_daily_drawdown", 0.02):
                logger.warning(f"⚠️ Drawdown diario excedido: {daily_profit*100:.2f}%")
                await self._activate_drawdown_protocol()
            
            # Check win rate
            win_rate_target = self.performance_targets.get("win_rate_target", 0.60)
            if self.advanced_stats["win_rate"] < win_rate_target * 0.8:  # 20% debajo del target
                logger.warning(f"⚠️ Win rate baja: {self.advanced_stats['win_rate']*100:.1f}% < {win_rate_target*100:.1f}%")
            
            # Check Sharpe ratio
            sharpe_target = self.performance_targets.get("sharpe_target", 1.5)
            if self.advanced_stats["sharpe_ratio"] < sharpe_target * 0.7:  # 30% debajo del target
                logger.warning(f"⚠️ Sharpe ratio bajo: {self.advanced_stats['sharpe_ratio']:.2f} < {sharpe_target:.2f}")
                
        except Exception as e:
            logger.error(f"Error verificando performance: {e}")
    
    def _calculate_daily_profit(self) -> float:
        """Calcula profit diario"""
        # En producción, calcularías con datos reales
        return np.random.uniform(-0.01, 0.02)  # -1% a +2%
    
    async def _activate_drawdown_protocol(self):
        """Activa protocolo de protección por drawdown"""
        logger.warning("🚨 ACTIVANDO PROTOCOLO DE DRAWDOWN")
        
        # 1. Reducir tamaño de posición
        current_size = self.profit_optimizer.config.base_position_size
        self.profit_optimizer.config.base_position_size = current_size * 0.5
        
        # 2. Aumentar stops
        self.profit_optimizer.config.trailing_activation = 0.01  # 1%
        
        # 3. Reducir número de operaciones simultáneas
        self.gradual_trader.max_concurrent_trades = max(2, self.gradual_trader.max_concurrent_trades - 1)
        
        # 4. Notificar
        await self._send_alert(
            f"🚨 PROTOCOLO DRAWDOWN ACTIVADO\n"
            f"Acciones tomadas:\n"
            f"1. Tamaño posición reducido: {current_size:.1%} -> {self.profit_optimizer.config.base_position_size:.1%}\n"
            f"2. Stops más estrictos\n"
            f"3. Operaciones máx: {self.gradual_trader.max_concurrent_trades}"
        )
        
        logger.info("✅ Protocolo de drawdown activado")
    
    def _needs_reoptimization(self) -> bool:
        """Determina si se necesita re-optimización"""
        # Re-optimizar si win rate < 50% o Sharpe < 1.0
        return (self.advanced_stats.get("win_rate", 0) < 0.5 or 
                self.advanced_stats.get("sharpe_ratio", 0) < 1.0)
    
    async def _quick_reoptimization(self):
        """Ejecuta re-optimización rápida"""
        logger.info("🔄 Ejecutando re-optimización rápida...")
        
        try:
            # Ajustar parámetros basado en performance
            if self.advanced_stats.get("win_rate", 0) < 0.5:
                # Reducir tamaño de posición
                current = self.profit_optimizer.config.base_position_size
                self.profit_optimizer.config.base_position_size = current * 0.8
                logger.info(f"Tamaño reducido por baja win rate: {current:.1%} -> {self.profit_optimizer.config.base_position_size:.1%}")
            
            if self.advanced_stats.get("sharpe_ratio", 0) < 1.0:
                # Ajustar stops
                self.profit_optimizer.config.trailing_activation = 0.015  # 1.5%
                logger.info("Trailing stop ajustado a 1.5%")
        
        except Exception as e:
            logger.error(f"Error en re-optimización: {e}")
    
    async def _send_optimized_start_alert(self):
        """Envía alerta de inicio optimizado"""
        if not self.telegram_bot.is_configured():
            return
        
        start_message = (
            f"🚀 ORCABOT OPTIMIZADO INICIADO\n"
            f"Estrategia: {self.profit_optimizer.config.primary_strategy.value}\n"
            f"Tokens activos: {len([t for t in self.optimized_tokens if t.in_trading])}\n"
            f"Posiciones máx: {self.gradual_trader.max_concurrent_trades}\n"
            f"Compounding: {'ACTIVADO' if self.profit_optimizer.config.enable_compounding else 'DESACTIVADO'}\n"
            f"Arbitrage: {'ACTIVADO' if self.profit_optimizer.config.enable_arbitrage else 'DESACTIVADO'}\n"
            f"Objetivo anual: {self.optimization_config['target_annual_return']*100:.0f}%"
        )
        
        await self.telegram_bot.send_message(start_message)
    
    async def _send_alert(self, message: str):
        """Envía alerta"""
        if self.telegram_bot.is_configured():
            await self.telegram_bot.send_message(message)
        else:
            logger.info(f"ALERTA: {message}")
    
    def stop(self):
        """Detiene el bot optimizado"""
        logger.info("⏹️ Deteniendo OrcaBot Optimizado...")
        
        self.running = False
        self.status = BotStatus.STOPPED
        
        # Cerrar posiciones activas
        if self.active_positions:
            logger.warning(f"Cerrando {len(self.active_positions)} posiciones activas...")
            for position_id in list(self.active_positions.keys()):
                asyncio.create_task(self._close_position_completely(
                    position_id, 
                    {"reason": "Bot detenido"}
                ))
        
        # Enviar reporte final
        final_report = self._generate_optimized_final_report()
        asyncio.run(self._send_alert(f"🛑 BOT OPTIMIZADO DETENIDO\n{final_report}"))
        
        logger.info("✅ OrcaBot Optimizado detenido correctamente")
    
    def _generate_optimized_final_report(self) -> str:
        """Genera reporte final optimizado"""
        runtime = datetime.now() - self.advanced_stats["start_time"]
        days = runtime.days
        hours = runtime.seconds // 3600
        
        # Calcular CAGR anualizado
        if days > 0:
            annualized_return = (self.advanced_stats["total_profit_usd"] / 1000) * (365 / days)
            annualized_return_pct = annualized_return * 100
        else:
            annualized_return_pct = 0
        
        return (
            f"📊 REPORTE FINAL OPTIMIZADO\n"
            f"Tiempo operación: {days}d {hours}h\n"
            f"Total trades: {self.advanced_stats['total_trades']}\n"
            f"Win rate: {self.advanced_stats['win_rate']*100:.1f}%\n"
            f"Profit total: ${self.advanced_stats['total_profit_usd']:.2f}\n"
            f"Compounded: ${self.advanced_stats['total_compounded_usd']:.2f}\n"
            f"Sharpe ratio: {self.advanced_stats['sharpe_ratio']:.2f}\n"
            f"Profit factor: {self.advanced_stats['profit_factor']:.2f}\n"
            f"Retorno anualizado: {annualized_return_pct:.1f}%\n"
            f"Mejor trade: ${self.advanced_stats['best_trade_usd']:.2f}\n"
            f"Peor trade: ${self.advanced_stats['worst_trade_usd']:.2f}"
        )
    
    def get_optimized_status(self) -> Dict[str, Any]:
        """Obtiene estado optimizado del bot"""
        return {
            "status": self.status.value,
            "mode": self.mode.value,
            "running": self.running,
            "balances": self.balances,
            "optimized_tokens": [
                {
                    "symbol": t.symbol,
                    "profit_potential": t.profit_potential_score,
                    "entry_score": t.optimal_entry_score,
                    "position_size": t.optimal_position_size,
                    "in_trading": t.in_trading
                }
                for t in self.optimized_tokens[:10]
            ],
            "active_positions": len(self.active_positions),
            "performance": {
                "win_rate": self.advanced_stats["win_rate"],
                "sharpe_ratio": self.advanced_stats["sharpe_ratio"],
                "profit_factor": self.advanced_stats["profit_factor"],
                "total_profit_usd": self.advanced_stats["total_profit_usd"]
            },
            "optimization": {
                "strategy": self.profit_optimizer.config.primary_strategy.value,
                "compounding_active": self.profit_optimizer.config.enable_compounding,
                "arbitrage_active": self.profit_optimizer.config.enable_arbitrage,
                "position_sizing": self.profit_optimizer.config.base_position_size
            }
        }

async def main_optimized():
    """Función principal para bot optimizado"""
    print("🚀 ORCABOT OPTIMIZADO v3.5 - Maximización de Ganancias")
    print("=" * 60)
    
    try:
        # Crear instancia optimizada
        bot = OptimizedOrcaBot("config_optimized.json")
        
        # Mostrar configuración
        print(f"Estrategia: {bot.profit_optimizer.config.primary_strategy.value}")
        print(f"Compounding: {'Activado' if bot.profit_optimizer.config.enable_compounding else 'Desactivado'}")
        print(f"Arbitrage: {'Activado' if bot.profit_optimizer.config.enable_arbitrage else 'Desactivado'}")
        print(f"Objetivo anual: {bot.optimization_config['target_annual_return']*100:.0f}%")
        
        # Iniciar bot
        print("\n▶️ Iniciando secuencia optimizada...")
        await bot.start_optimized()
        
        # Mantener ejecución
        try:
            while bot.running:
                # Mostrar estado cada 10 minutos
                await asyncio.sleep(600)
                status = bot.get_optimized_status()
                
                if status["status"] == "trading":
                    print(f"🔄 Trading activo | Win rate: {status['performance']['win_rate']*100:.1f}% | Profit: ${status['performance']['total_profit_usd']:.2f}")
                    
        except KeyboardInterrupt:
            print("\n\n🛑 Detención solicitada por usuario")
            bot.stop()
            
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ejecutar bot optimizado
    asyncio.run(main_optimized())