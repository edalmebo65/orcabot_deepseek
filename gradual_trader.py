#!/usr/bin/env python3
"""
Gestor de trading gradual para OrcaBot
Maneja hasta 5 operaciones simultáneas con entrada gradual
basada en punto de inicio + costos + ganancia 0.2%
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)

class PositionStatus(Enum):
    PENDING_ENTRY = "pending_entry"
    ACTIVE = "active"
    TRAILING_STOP = "trailing_stop"
    STOPPED_OUT = "stopped_out"
    TAKE_PROFIT = "take_profit"
    CLOSED = "closed"

@dataclass
class GradualPosition:
    """Posición con gestión gradual"""
    position_id: str
    token_symbol: str
    token_address: str
    entry_price_target: float  # Precio objetivo de entrada
    entry_price_actual: Optional[float] = None  # Precio real de entrada
    position_size_usd: float = 0.0
    position_size_tokens: float = 0.0
    status: PositionStatus = PositionStatus.PENDING_ENTRY
    ml_confidence: float = 0.0
    volatility_score: float = 0.0
    
    # Niveles de gestión
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_activated: bool = False
    trailing_stop_price: Optional[float] = None
    
    # Tiempos
    created_at: datetime = field(default_factory=datetime.now)
    entered_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None
    
    # Resultados
    pnl_usd: float = 0.0
    pnl_percent: float = 0.0
    fees_paid_sol: float = 0.0
    
    # Metadata
    ml_model_path: Optional[str] = None
    current_price: Optional[float] = None
    highest_price: Optional[float] = None
    
    def calculate_entry_target(self, current_price: float, fee_estimate: float = 0.003) -> float:
        """
        Calcula precio objetivo de entrada considerando:
        - Precio actual
        - Fees estimados (0.3%)
        - Ganancia mínima requerida (0.2%)
        """
        # Costo total = precio + fees + spread
        total_cost_factor = 1 + fee_estimate + 0.001  # 0.3% fees + 0.1% spread
        
        # Precio necesario para ganar 0.2% después de costs
        required_profit_factor = 1 + 0.002  # 0.2% profit
        
        # Precio objetivo = precio actual * costos * ganancia
        target_price = current_price * total_cost_factor * required_profit_factor
        
        # Redondear a 6 decimales
        return round(target_price, 6)
    
    def update_trailing_stop(self, current_price: float, activation_percent: float = 0.002):
        """
        Actualiza trailing stop cuando se activa
        
        Args:
            current_price: Precio actual
            activation_percent: Porcentaje para activar trailing (0.2%)
        """
        if self.entry_price_actual is None:
            return
        
        # Calcular ganancia actual
        current_gain = (current_price - self.entry_price_actual) / self.entry_price_actual
        
        # Activar trailing stop si se alcanza ganancia mínima
        if current_gain >= activation_percent and not self.trailing_stop_activated:
            self.trailing_stop_activated = True
            self.trailing_stop_price = self.entry_price_actual * (1 + activation_percent * 0.5)
            logger.info(f"Trailing stop activado para {self.token_symbol} @ {current_price}")
        
        # Actualizar trailing stop si el precio sube
        if self.trailing_stop_activated:
            # Mantener trailing stop a 0.1% del precio más alto
            if self.highest_price is None or current_price > self.highest_price:
                self.highest_price = current_price
                self.trailing_stop_price = current_price * 0.999  # 0.1% below highest
            
            # Verificar si el precio cayó por debajo del trailing stop
            if current_price < self.trailing_stop_price:
                self.status = PositionStatus.STOPPED_OUT
                logger.info(f"Trailing stop ejecutado para {self.token_symbol}")

class GradualTrader:
    """Gestiona operaciones de trading graduales"""
    
    def __init__(self, max_concurrent_trades: int = 5, 
                 min_profit_margin: float = 0.002,
                 check_interval_minutes: int = 5):
        
        self.max_concurrent_trades = max_concurrent_trades
        self.min_profit_margin = min_profit_margin
        self.check_interval = check_interval_minutes
        
        self.active_positions: Dict[str, GradualPosition] = {}
        self.pending_positions: List[GradualPosition] = []
        self.position_history: List[GradualPosition] = []
        
        # Componentes externos
        self.balance_checker = None
        self.rust_bridge = None
        self.ml_trainer = None
        self.token_selector = None
        
        # Estadísticas
        self.statistics = {
            "total_trades": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "total_pnl_usd": 0.0,
            "total_volume_usd": 0.0,
            "current_concurrent": 0,
            "max_concurrent_reached": 0
        }
        
        logger.info(f"GradualTrader inicializado: máximo {max_concurrent_trades} operaciones simultáneas")
    
    async def initialize(self, tokens: List[Any], balance_checker, rust_bridge, ml_trainer):
        """Inicializa el trader con componentes externos"""
        self.balance_checker = balance_checker
        self.rust_bridge = rust_bridge
        self.ml_trainer = ml_trainer
        
        # Crear posiciones pendientes para los tokens top
        await self._create_pending_positions(tokens)
        
        logger.info(f"Creadas {len(self.pending_positions)} posiciones pendientes")
    
    async def _create_pending_positions(self, tokens: List[Any]):
        """Crea posiciones pendientes para los tokens seleccionados"""
        # Ordenar tokens por score (mejores primero)
        sorted_tokens = sorted(
            tokens, 
            key=lambda t: t.volatility_score * t.probability_score,
            reverse=True
        )
        
        # Crear posiciones para top tokens (hasta 2x el máximo concurrente)
        max_pending = self.max_concurrent_trades * 2
        
        for token in sorted_tokens[:max_pending]:
            # Obtener precio actual
            current_price = token.current_price
            
            if current_price and current_price > 0:
                # Crear posición
                position = GradualPosition(
                    position_id=f"pos_{token.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    token_symbol=token.symbol,
                    token_address=token.address,
                    ml_confidence=token.probability_score,
                    volatility_score=token.volatility_score,
                    ml_model_path=token.ml_model_path,
                    current_price=current_price
                )
                
                # Calcular precio objetivo de entrada
                position.entry_price_target = position.calculate_entry_target(
                    current_price=current_price
                )
                
                self.pending_positions.append(position)
                
                logger.info(f"Posición pendiente creada para {token.symbol}: "
                          f"actual=${current_price:.4f}, objetivo=${position.entry_price_target:.4f}")
    
    async def trading_cycle(self):
        """Ejecuta un ciclo completo de trading"""
        try:
            logger.debug("Iniciando ciclo de trading...")
            
            # 1. Actualizar precios de posiciones activas
            await self._update_active_positions()
            
            # 2. Verificar stops y toma de ganancias
            await self._check_position_triggers()
            
            # 3. Intentar nuevas entradas si hay slots disponibles
            await self._attempt_new_entries()
            
            # 4. Actualizar estadísticas
            self._update_statistics()
            
            # 5. Limpiar posiciones cerradas
            self._cleanup_closed_positions()
            
            logger.debug(f"Ciclo completado: {len(self.active_positions)} activas, "
                        f"{len(self.pending_positions)} pendientes")
            
        except Exception as e:
            logger.error(f"Error en ciclo de trading: {e}")
    
    async def _update_active_positions(self):
        """Actualiza precios de posiciones activas"""
        for position_id, position in list(self.active_positions.items()):
            try:
                # Obtener precio actual (simulado por ahora)
                # En producción, esto consultaría una API
                if position.current_price:
                    # Simular cambio de precio
                    change = np.random.normal(0, position.volatility_score * 0.01)
                    new_price = position.current_price * (1 + change)
                    position.current_price = max(new_price, 0.000001)
                    
                    # Actualizar highest price
                    if position.highest_price is None or position.current_price > position.highest_price:
                        position.highest_price = position.current_price
                    
                    # Actualizar trailing stop
                    if position.status == PositionStatus.ACTIVE:
                        position.update_trailing_stop(
                            current_price=position.current_price,
                            activation_percent=self.min_profit_margin
                        )
                    
                    # Calcular P&L actual
                    if position.entry_price_actual:
                        position.pnl_percent = (
                            (position.current_price - position.entry_price_actual) / 
                            position.entry_price_actual
                        )
                        position.pnl_usd = position.pnl_percent * position.position_size_usd
                
            except Exception as e:
                logger.error(f"Error actualizando posición {position_id}: {e}")
    
    async def _check_position_triggers(self):
        """Verifica triggers para posiciones activas"""
        positions_to_close = []
        
        for position_id, position in list(self.active_positions.items()):
            try:
                if position.status == PositionStatus.ACTIVE and position.current_price:
                    
                    # Verificar stop loss
                    if position.stop_loss_price and position.current_price <= position.stop_loss_price:
                        logger.info(f"Stop loss alcanzado para {position.token_symbol}: "
                                  f"{position.current_price:.6f} <= {position.stop_loss_price:.6f}")
                        position.status = PositionStatus.STOPPED_OUT
                        positions_to_close.append(position_id)
                    
                    # Verificar take profit
                    elif position.take_profit_price and position.current_price >= position.take_profit_price:
                        logger.info(f"Take profit alcanzado para {position.token_symbol}: "
                                  f"{position.current_price:.6f} >= {position.take_profit_price:.6f}")
                        position.status = PositionStatus.TAKE_PROFIT
                        positions_to_close.append(position_id)
                    
                    # Verificar trailing stop
                    elif position.status == PositionStatus.STOPPED_OUT:
                        positions_to_close.append(position_id)
            
            except Exception as e:
                logger.error(f"Error verificando triggers para {position_id}: {e}")
        
        # Cerrar posiciones que alcanzaron triggers
        for position_id in positions_to_close:
            await self.close_position(position_id)
    
    async def _attempt_new_entries(self):
        """Intenta nuevas entradas si hay capacidad"""
        # Verificar cuántas posiciones activas hay
        active_count = len(self.active_positions)
        
        if active_count >= self.max_concurrent_trades:
            logger.debug(f"Máximo de operaciones alcanzado: {active_count}/{self.max_concurrent_trades}")
            return
        
        # Calcular slots disponibles
        available_slots = self.max_concurrent_trades - active_count
        
        # Ordenar posiciones pendientes por prioridad
        self.pending_positions.sort(
            key=lambda p: p.ml_confidence * p.volatility_score,
            reverse=True
        )
        
        # Intentar entrar en posiciones pendientes
        entries_made = 0
        
        for position in list(self.pending_positions):
            if entries_made >= available_slots:
                break
            
            # Verificar condiciones de entrada
            if await self._check_entry_conditions(position):
                # Ejecutar entrada
                if await self._execute_entry(position):
                    entries_made += 1
                    self.pending_positions.remove(position)
        
        if entries_made > 0:
            logger.info(f"Realizadas {entries_made} nuevas entradas")
    
    async def _check_entry_conditions(self, position: GradualPosition) -> bool:
        """Verifica condiciones para entrar en una posición"""
        try:
            # 1. Verificar que haya precio actual
            if not position.current_price or position.current_price <= 0:
                return False
            
            # 2. Verificar que el precio alcance el objetivo
            if position.current_price < position.entry_price_target:
                logger.debug(f"{position.token_symbol}: Precio actual ({position.current_price:.6f}) "
                           f"< objetivo ({position.entry_price_target:.6f})")
                return False
            
            # 3. Verificar confianza ML
            if position.ml_confidence < 0.65:  # Umbral mínimo
                logger.debug(f"{position.token_symbol}: Confianza ML baja ({position.ml_confidence:.3f})")
                return False
            
            # 4. Verificar saldos disponibles
            if self.balance_checker:
                # Calcular tamaño de posición (10% del balance USDC o $100, lo que sea menor)
                balance_info = await self.balance_checker.get_current_balances()
                usdc_balance = balance_info.get("USDC", 0)
                
                position_size = min(usdc_balance * 0.1, 100)  # 10% o $100
                
                if position_size < 10:  # Mínimo $10
                    logger.debug(f"{position.token_symbol}: Tamaño de posición muy pequeño ({position_size:.2f})")
                    return False
                
                # Verificar factibilidad
                feasible, message = await self.balance_checker.check_transaction_feasibility(
                    usdc_amount=position_size
                )
                
                if not feasible:
                    logger.debug(f"{position.token_symbol}: No factible - {message}")
                    return False
            
            # 5. Obtener predicción ML actualizada
            if self.ml_trainer and position.ml_model_path:
                prediction = await self.ml_trainer.predict(
                    model_path=position.ml_model_path,
                    current_price=position.current_price
                )
                
                if prediction and prediction.get("confidence", 0) < 0.7:
                    logger.debug(f"{position.token_symbol}: Predicción ML baja")
                    return False
            
            logger.info(f"✅ Condiciones de entrada OK para {position.token_symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error verificando condiciones para {position.token_symbol}: {e}")
            return False
    
    async def _execute_entry(self, position: GradualPosition) -> bool:
        """Ejecuta entrada en una posición"""
        try:
            logger.info(f"🔔 EJECUTANDO ENTRADA para {position.token_symbol}")
            
            # 1. Calcular tamaño de posición
            balance_info = await self.balance_checker.get_current_balances()
            usdc_balance = balance_info.get("USDC", 0)
            
            position_size_usd = min(usdc_balance * 0.1, 100)  # 10% o $100
            position.position_size_usd = position_size_usd
            
            # Calcular cantidad de tokens
            token_amount = position_size_usd / position.current_price
            position.position_size_tokens = token_amount
            
            # 2. Reservar fondos
            reserved = await self.balance_checker.reserve_funds(position_size_usd)
            if not reserved:
                logger.error(f"No se pudieron reservar fondos para {position.token_symbol}")
                return False
            
            # 3. Ejecutar trade (simulado por ahora)
            if self.rust_bridge:
                # En producción, esto ejecutaría el trade real
                trade_result = await self._execute_simulated_trade(position)
                
                if trade_result.get("status") != "completed":
                    logger.error(f"Trade falló para {position.token_symbol}")
                    await self.balance_checker.release_funds(position_size_usd)
                    return False
                
                position.entry_price_actual = trade_result.get("execution_price", position.current_price)
                position.fees_paid_sol = trade_result.get("fees_sol", 0.0001)
            
            else:
                # Modo simulación
                position.entry_price_actual = position.current_price
                position.fees_paid_sol = 0.0001
            
            # 4. Configurar gestión de riesgo
            position.status = PositionStatus.ACTIVE
            position.entered_at = datetime.now()
            
            # Stop loss a -2%
            position.stop_loss_price = position.entry_price_actual * 0.98
            
            # Take profit a +5%
            position.take_profit_price = position.entry_price_actual * 1.05
            
            # 5. Agregar a posiciones activas
            self.active_positions[position.position_id] = position
            
            # 6. Enviar notificación
            if hasattr(self, 'telegram_bot'):
                await self.telegram_bot.send_message(
                    f"📈 ENTRADA EJECUTADA\n"
                    f"Token: {position.token_symbol}\n"
                    f"Precio: ${position.entry_price_actual:.6f}\n"
                    f"Monto: ${position.position_size_usd:.2f}\n"
                    f"Stop Loss: ${position.stop_loss_price:.6f}\n"
                    f"Take Profit: ${position.take_profit_price:.6f}"
                )
            
            logger.info(f"✅ Entrada exitosa para {position.token_symbol}: "
                       f"${position.position_size_usd:.2f} @ ${position.entry_price_actual:.6f}")
            
            self.statistics["total_trades"] += 1
            self.statistics["current_concurrent"] = len(self.active_positions)
            self.statistics["max_concurrent_reached"] = max(
                self.statistics["max_concurrent_reached"],
                len(self.active_positions)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando entrada para {position.token_symbol}: {e}")
            
            # Liberar fondos reservados
            if self.balance_checker and position.position_size_usd > 0:
                await self.balance_checker.release_funds(position.position_size_usd)
            
            return False
    
    async def _execute_simulated_trade(self, position: GradualPosition) -> Dict:
        """Ejecuta trade simulado (para desarrollo)"""
        # Simular ejecución con pequeño slippage
        import random
        
        slippage = random.uniform(-0.001, 0.001)  # ±0.1%
        execution_price = position.current_price * (1 + slippage)
        
        return {
            "status": "completed",
            "execution_price": execution_price,
            "fees_sol": 0.0001,
            "tx_hash": f"simulated_tx_{position.position_id}",
            "timestamp": datetime.now().isoformat()
        }
    
    async def close_position(self, position_id: str) -> bool:
        """Cierra una posición activa"""
        try:
            if position_id not in self.active_positions:
                logger.warning(f"Posición {position_id} no encontrada")
                return False
            
            position = self.active_positions[position_id]
            
            logger.info(f"CERRANDO posición {position.token_symbol} - {position.status.value}")
            
            # 1. Ejecutar cierre (simulado)
            if self.rust_bridge:
                # En producción, ejecutar trade de cierre
                close_result = await self._execute_simulated_close(position)
            else:
                close_result = {"status": "completed", "execution_price": position.current_price}
            
            # 2. Calcular P&L final
            if position.entry_price_actual and position.current_price:
                position.pnl_percent = (
                    (position.current_price - position.entry_price_actual) / 
                    position.entry_price_actual
                )
                position.pnl_usd = position.pnl_percent * position.position_size_usd
            
            # 3. Actualizar estado
            position.exited_at = datetime.now()
            position.status = PositionStatus.CLOSED
            
            # 4. Liberar fondos y agregar P&L
            if self.balance_checker:
                # En realidad, el balance se actualizaría con la transacción de cierre
                # Por ahora solo actualizamos estadísticas
                pass
            
            # 5. Actualizar estadísticas
            if position.pnl_usd > 0:
                self.statistics["successful_trades"] += 1
            else:
                self.statistics["failed_trades"] += 1
            
            self.statistics["total_pnl_usd"] += position.pnl_usd
            self.statistics["total_volume_usd"] += position.position_size_usd
            
            # 6. Mover a historial
            self.position_history.append(position)
            del self.active_positions[position_id]
            
            # 7. Enviar notificación
            pnl_sign = "📈" if position.pnl_usd > 0 else "📉"
            if hasattr(self, 'telegram_bot'):
                await self.telegram_bot.send_message(
                    f"{pnl_sign} POSICIÓN CERRADA\n"
                    f"Token: {position.token_symbol}\n"
                    f"Razón: {position.status.value}\n"
                    f"P&L: ${position.pnl_usd:.2f} ({position.pnl_percent*100:.2f}%)\n"
                    f"Duración: {position.exited_at - position.entered_at}"
                )
            
            logger.info(f"✅ Posición {position.token_symbol} cerrada: "
                       f"${position.pnl_usd:.2f} ({position.pnl_percent*100:.2f}%)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cerrando posición {position_id}: {e}")
            return False
    
    async def _execute_simulated_close(self, position: GradualPosition) -> Dict:
        """Ejecuta cierre simulado"""
        import random
        
        # Pequeño slippage en cierre
        slippage = random.uniform(-0.001, 0.001)
        execution_price = position.current_price * (1 + slippage)
        
        return {
            "status": "completed",
            "execution_price": execution_price,
            "fees_sol": 0.00005,
            "tx_hash": f"simulated_close_{position.position_id}",
            "timestamp": datetime.now().isoformat()
        }
    
    def _update_statistics(self):
        """Actualiza estadísticas del trader"""
        self.statistics["current_concurrent"] = len(self.active_positions)
    
    def _cleanup_closed_positions(self):
        """Limpia posiciones del historial muy antiguas"""
        # Mantener solo posiciones de los últimos 7 días
        cutoff = datetime.now() - timedelta(days=7)
        self.position_history = [
            p for p in self.position_history 
            if p.exited_at and p.exited_at > cutoff
        ]
    
    async def get_state(self) -> Dict[str, Any]:
        """Obtiene estado actual del trader"""
        active_positions_info = {}
        
        for pos_id, position in self.active_positions.items():
            active_positions_info[pos_id] = {
                "token": position.token_symbol,
                "status": position.status.value,
                "entry_price": position.entry_price_actual,
                "current_price": position.current_price,
                "pnl_percent": position.pnl_percent,
                "pnl_usd": position.pnl_usd,
                "size_usd": position.position_size_usd,
                "stop_loss": position.stop_loss_price,
                "take_profit": position.take_profit_price,
                "trailing_active": position.trailing_stop_activated
            }
        
        return {
            "active_positions": active_positions_info,
            "pending_positions": len(self.pending_positions),
            "total_trades": self.statistics["total_trades"],
            "successful_trades": self.statistics["successful_trades"],
            "failed_trades": self.statistics["failed_trades"],
            "total_pnl_usd": self.statistics["total_pnl_usd"],
            "total_volume_usd": self.statistics["total_volume_usd"],
            "current_concurrent": self.statistics["current_concurrent"],
            "max_concurrent_reached": self.statistics["max_concurrent_reached"]
        }
    
    def stop(self):
        """Detiene el trader de manera segura"""
        logger.info("Deteniendo GradualTrader...")
        
        # Cerrar todas las posiciones activas
        for position_id in list(self.active_positions.keys()):
            asyncio.create_task(self.close_position(position_id))
        
        logger.info("GradualTrader detenido")