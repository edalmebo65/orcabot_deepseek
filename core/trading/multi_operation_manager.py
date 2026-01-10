# core/trading/multi_operation_manager.py
import asyncio
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import json

@dataclass
class Operation:
    """Representa una operación de trading"""
    id: str
    asset_pair: str
    side: str  # "BUY" or "SELL"
    entry_price: Decimal
    current_price: Decimal
    position_size: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    trailing_stop: Optional[Decimal]
    risk_zero_price: Decimal
    status: str  # "OPEN", "CLOSED", "STOPPED", "PROFIT_TAKEN"
    open_time: datetime
    close_time: Optional[datetime]
    pnl: Decimal = Decimal('0')
    pnl_percentage: Decimal = Decimal('0')
    
    @property
    def is_active(self) -> bool:
        return self.status == "OPEN"
    
    @property
    def duration(self) -> Optional[timedelta]:
        if self.close_time:
            return self.close_time - self.open_time
        return datetime.now() - self.open_time

class MultiOperationManager:
    """Gestor de múltiples operaciones simultáneas"""
    
    def __init__(self, config, capital_manager):
        self.config = config
        self.capital_manager = capital_manager
        self.operations: Dict[str, Operation] = {}
        self.active_pairs: Set[str] = set()
        self.max_concurrent = config.trading.capital.max_concurrent_operations
        
        # Estadísticas
        self.stats = {
            "total_operations": 0,
            "active_operations": 0,
            "total_pnl": Decimal('0'),
            "winning_operations": 0,
            "losing_operations": 0
        }
        
        # Cooldown por asset
        self.cooldown_period = timedelta(minutes=5)
        self.last_trade_time: Dict[str, datetime] = {}
    
    async def open_operation(self,
                           asset_pair: str,
                           side: str,
                           entry_price: Decimal,
                           position_size: Decimal,
                           stop_loss_pct: Decimal = None,
                           take_profit_pct: Decimal = None) -> Optional[Operation]:
        """
        Abre una nueva operación
        """
        # 1. Verificar límites
        if not self._can_open_operation(asset_pair):
            return None
        
        # 2. Calcular stop loss y take profit
        if stop_loss_pct is None:
            stop_loss_pct = self.config.trading.capital.stop_loss_pct
        if take_profit_pct is None:
            take_profit_pct = self.config.trading.capital.take_profit_pct
        
        stop_loss = entry_price * (Decimal('1') - stop_loss_pct)
        take_profit = entry_price * (Decimal('1') + take_profit_pct)
        
        # 3. Calcular riesgo cero
        fees_pct = self.config.trading.orca_fee_pct * Decimal('2')
        risk_zero = self.capital_manager.calculate_risk_zero_price(
            entry_price, position_size, fees_pct
        )
        
        # 4. Crear operación
        operation_id = str(uuid.uuid4())[:8]
        operation = Operation(
            id=operation_id,
            asset_pair=asset_pair,
            side=side,
            entry_price=entry_price,
            current_price=entry_price,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=None,
            risk_zero_price=risk_zero,
            status="OPEN",
            open_time=datetime.now(),
            close_time=None
        )
        
        # 5. Registrar operación
        self.operations[operation_id] = operation
        self.active_pairs.add(asset_pair)
        self.last_trade_time[asset_pair] = datetime.now()
        
        # 6. Actualizar estadísticas
        self.stats["total_operations"] += 1
        self.stats["active_operations"] += 1
        
        # 7. Notificar
        self.config.logger.info(
            f"✅ Operación abierta: {operation_id} - {asset_pair} {side} "
            f"@ ${entry_price:.4f} (${position_size:.2f})"
        )
        
        return operation
    
    def _can_open_operation(self, asset_pair: str) -> bool:
        """
        Verifica si se puede abrir una operación
        """
        # 1. Verificar límite de operaciones simultáneas
        if self.stats["active_operations"] >= self.max_concurrent:
            self.config.logger.warning(
                f"Límite de operaciones alcanzado: {self.stats['active_operations']}/{self.max_concurrent}"
            )
            return False
        
        # 2. Verificar si ya hay operación en este par
        if asset_pair in self.active_pairs:
            self.config.logger.warning(f"Ya existe operación activa para {asset_pair}")
            return False
        
        # 3. Verificar cooldown
        if asset_pair in self.last_trade_time:
            time_since_last = datetime.now() - self.last_trade_time[asset_pair]
            if time_since_last < self.cooldown_period:
                self.config.logger.warning(
                    f"Asset {asset_pair} en cooldown: "
                    f"{time_since_last.seconds//60}m restantes"
                )
                return False
        
        return True
    
    async def update_operation_price(self,
                                  operation_id: str,
                                  current_price: Decimal) -> List[Dict]:
        """
        Actualiza precio de una operación y verifica triggers
        Returns: Lista de acciones requeridas
        """
        if operation_id not in self.operations:
            return []
        
        operation = self.operations[operation_id]
        operation.current_price = current_price
        
        # Calcular P&L actual
        if operation.side == "BUY":
            operation.pnl = (current_price - operation.entry_price) * operation.position_size
            operation.pnl_percentage = ((current_price - operation.entry_price) / operation.entry_price) * Decimal('100')
        else:  # SELL (short)
            operation.pnl = (operation.entry_price - current_price) * operation.position_size
            operation.pnl_percentage = ((operation.entry_price - current_price) / operation.entry_price) * Decimal('100')
        
        # Verificar triggers
        actions = []
        
        # 1. Stop Loss
        if (operation.side == "BUY" and current_price <= operation.stop_loss) or \
           (operation.side == "SELL" and current_price >= operation.stop_loss):
            actions.append({
                "type": "STOP_LOSS",
                "operation_id": operation_id,
                "price": current_price,
                "reason": f"Stop loss alcanzado @ ${current_price:.4f}"
            })
        
        # 2. Take Profit
        elif (operation.side == "BUY" and current_price >= operation.take_profit) or \
             (operation.side == "SELL" and current_price <= operation.take_profit):
            actions.append({
                "type": "TAKE_PROFIT",
                "operation_id": operation_id,
                "price": current_price,
                "reason": f"Take profit alcanzado @ ${current_price:.4f}"
            })
        
        # 3. Trailing Stop
        elif operation.trailing_stop:
            if (operation.side == "BUY" and current_price <= operation.trailing_stop) or \
               (operation.side == "SELL" and current_price >= operation.trailing_stop):
                actions.append({
                    "type": "TRAILING_STOP",
                    "operation_id": operation_id,
                    "price": current_price,
                    "reason": f"Trailing stop alcanzado @ ${current_price:.4f}"
                })
        
        # 4. Activar trailing stop si se alcanza umbral
        elif abs(operation.pnl_percentage) >= self.config.trading.capital.trailing_stop_activation_pct * Decimal('100'):
            # Calcular nuevo trailing stop
            if operation.side == "BUY":
                distance = self.config.trading.capital.trailing_stop_distance_pct * Decimal('100')
                operation.trailing_stop = current_price * (Decimal('1') - distance / Decimal('100'))
            else:
                distance = self.config.trading.capital.trailing_stop_distance_pct * Decimal('100')
                operation.trailing_stop = current_price * (Decimal('1') + distance / Decimal('100'))
            
            actions.append({
                "type": "TRAILING_STOP_ACTIVATED",
                "operation_id": operation_id,
                "trailing_stop": operation.trailing_stop,
                "reason": f"Trailing stop activado @ ${operation.trailing_stop:.4f}"
            })
        
        # 5. Riesgo cero alcanzado
        if (operation.side == "BUY" and current_price >= operation.risk_zero_price) or \
           (operation.side == "SELL" and current_price <= operation.risk_zero_price):
            actions.append({
                "type": "RISK_ZERO_REACHED",
                "operation_id": operation_id,
                "price": current_price,
                "reason": "✅ Riesgo cero alcanzado"
            })
        
        return actions
    
    async def close_operation(self,
                            operation_id: str,
                            close_price: Decimal,
                            reason: str) -> Dict:
        """
        Cierra una operación
        """
        if operation_id not in self.operations:
            return {"error": "Operación no encontrada"}
        
        operation = self.operations[operation_id]
        
        # Calcular P&L final
        if operation.side == "BUY":
            final_pnl = (close_price - operation.entry_price) * operation.position_size
            final_pnl_pct = ((close_price - operation.entry_price) / operation.entry_price) * Decimal('100')
        else:
            final_pnl = (operation.entry_price - close_price) * operation.position_size
            final_pnl_pct = ((operation.entry_price - close_price) / operation.entry_price) * Decimal('100')
        
        # Actualizar operación
        operation.status = "CLOSED"
        operation.close_time = datetime.now()
        operation.current_price = close_price
        operation.pnl = final_pnl
        operation.pnl_percentage = final_pnl_pct
        
        # Actualizar estadísticas
        self.stats["active_operations"] -= 1
        self.stats["total_pnl"] += final_pnl
        
        if final_pnl > 0:
            self.stats["winning_operations"] += 1
        else:
            self.stats["losing_operations"] += 1
        
        # Remover de pares activos
        self.active_pairs.discard(operation.asset_pair)
        
        # Crear registro
        record = {
            "operation_id": operation_id,
            "asset_pair": operation.asset_pair,
            "side": operation.side,
            "entry_price": float(operation.entry_price),
            "close_price": float(close_price),
            "position_size": float(operation.position_size),
            "pnl": float(final_pnl),
            "pnl_percentage": float(final_pnl_pct),
            "open_time": operation.open_time.isoformat(),
            "close_time": operation.close_time.isoformat(),
            "duration_seconds": operation.duration.total_seconds() if operation.duration else 0,
            "close_reason": reason
        }
        
        # Notificar
        self.config.logger.info(
            f"🔒 Operación cerrada: {operation_id} - {operation.asset_pair} "
            f"P&L: {final_pnl_pct:.2f}% (${final_pnl:.2f}) - Razón: {reason}"
        )
        
        return record
    
    def get_active_operations(self) -> List[Operation]:
        """Obtiene operaciones activas"""
        return [op for op in self.operations.values() if op.is_active]
    
    def get_operation_summary(self) -> Dict:
        """Obtiene resumen de operaciones"""
        active_ops = self.get_active_operations()
        
        total_exposure = sum(op.position_size for op in active_ops)
        total_unrealized_pnl = sum(op.pnl for op in active_ops)
        
        win_rate = 0
        if self.stats["total_operations"] > 0:
            win_rate = self.stats["winning_operations"] / self.stats["total_operations"]
        
        return {
            "active_operations": len(active_ops),
            "max_concurrent": self.max_concurrent,
            "total_exposure": float(total_exposure),
            "total_unrealized_pnl": float(total_unrealized_pnl),
            "total_realized_pnl": float(self.stats["total_pnl"]),
            "win_rate": float(win_rate),
            "total_operations": self.stats["total_operations"],
            "winning_operations": self.stats["winning_operations"],
            "losing_operations": self.stats["losing_operations"]
        }
    
    async def emergency_close_all(self) -> List[Dict]:
        """
        Cierra todas las operaciones de emergencia
        """
        records = []
        active_ops = self.get_active_operations()
        
        for operation in active_ops:
            # Obtener precio de mercado actual (simplificado)
            close_price = operation.current_price
            
            record = await self.close_operation(
                operation.id,
                close_price,
                "EMERGENCY_CLOSE"
            )
            
            if "error" not in record:
                records.append(record)
        
        return records