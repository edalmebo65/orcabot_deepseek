# core/trading/capital_manager.py
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

@dataclass
class Operation:
    """Representa una operación activa"""
    id: str
    asset_pair: str  # Ej: "SOL/USDC"
    entry_price: Decimal
    entry_time: datetime
    position_size_usdc: Decimal
    stop_loss_price: Decimal
    take_profit_price: Decimal
    current_price: Decimal
    trailing_stop_price: Optional[Decimal] = None
    risk_zero_price: Optional[Decimal] = None
    status: str = "ACTIVE"  # ACTIVE, CLOSED, STOPPED, PROFIT_TAKEN
    
    @property
    def current_pnl_pct(self) -> Decimal:
        """Calcula P&L actual en porcentaje"""
        if self.entry_price == Decimal('0'):
            return Decimal('0')
        return ((self.current_price - self.entry_price) / self.entry_price) * Decimal('100')
    
    @property
    def current_pnl_usdc(self) -> Decimal:
        """Calcula P&L actual en USDC"""
        return self.position_size_usdc * (self.current_pnl_pct / Decimal('100'))
    
    def update_price(self, new_price: Decimal):
        """Actualiza precio actual y calcula trailing stop"""
        self.current_price = new_price
        
        # Actualizar trailing stop si aplica
        if self.trailing_stop_price:
            # Solo mover hacia arriba
            if new_price > self.trailing_stop_price:
                new_trailing = new_price * (Decimal('1') - self.trailing_stop_distance)
                self.trailing_stop_price = max(self.trailing_stop_price, new_trailing)
    
    def is_risk_zero(self) -> bool:
        """Verifica si la operación alcanzó riesgo cero"""
        if not self.risk_zero_price:
            return False
        return self.current_price >= self.risk_zero_price

class CapitalManager:
    """Gestor avanzado de capital y operaciones simultáneas"""
    
    def __init__(self, config):
        self.config = config
        self.operations: Dict[str, Operation] = {}
        self.operations_file = config.base_dir / "state" / "operations.json"
        self.load_operations()
        
        # Historial de trades
        self.trades_history = []
    
    def calculate_position_size(self, 
                               asset_price: Decimal,
                               confidence_score: float) -> Tuple[Decimal, Dict]:
        """
        Calcula tamaño de posición basado en reglas de capital
        Returns: (position_size_usdc, calculation_details)
        """
        # 1. Obtener capital disponible para trading
        total_capital = self.config.current_capital_usdc
        capital_for_trading = total_capital * (Decimal('1') - self.config.trading.capital.capital_reserve_pct)
        
        # 2. Calcular exposición actual
        current_exposure = sum(op.position_size_usdc for op in self.operations.values())
        
        # 3. Capital disponible para nueva operación
        available_capital = capital_for_trading - current_exposure
        
        # 4. Calcular máximo por Kelly Criterion ajustado
        kelly_fraction = Decimal(str(confidence_score)) * Decimal('0.5')  # 50% de Kelly máximo
        max_kelly_amount = available_capital * kelly_fraction
        
        # 5. Aplicar límite del 10% del capital total
        max_by_config = self.config.get_max_trade_amount_usdc()
        
        # 6. Tomar el mínimo de todas las restricciones
        position_size = min(max_kelly_amount, max_by_config, available_capital)
        
        # 7. Asegurar tamaño mínimo (ej: $10 USDC)
        min_position = Decimal('10')
        if position_size < min_position:
            return Decimal('0'), {"error": "Position size too small"}
        
        # 8. Redondear
        position_size = position_size.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        
        calculation_details = {
            "total_capital": float(total_capital),
            "capital_for_trading": float(capital_for_trading),
            "current_exposure": float(current_exposure),
            "available_capital": float(available_capital),
            "kelly_fraction": float(kelly_fraction),
            "max_kelly_amount": float(max_kelly_amount),
            "max_by_config": float(max_by_config),
            "final_position_size": float(position_size)
        }
        
        return position_size, calculation_details
    
    def calculate_risk_zero_price(self,
                                 entry_price: Decimal,
                                 position_size_usdc: Decimal,
                                 fees_pct: Decimal) -> Decimal:
        """
        Calcula precio de riesgo cero
        entrada + fees + 0.2% ganancia
        """
        total_cost_pct = fees_pct + self.config.trading.capital.risk_zero_buffer_pct
        risk_zero_price = entry_price * (Decimal('1') + total_cost_pct)
        
        return risk_zero_price.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
    
    def can_open_operation(self, 
                          asset_pair: str,
                          estimated_cost_usdc: Decimal,
                          confidence_score: float) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verifica si se puede abrir una nueva operación
        Returns: (can_open, message, position_details)
        """
        # 1. Verificar configuración global
        can_open_config, config_msg = self.config.can_open_new_operation(estimated_cost_usdc)
        if not can_open_config:
            return False, config_msg, None
        
        # 2. Verificar si ya hay operación abierta en este asset
        existing_ops = [op for op in self.operations.values() 
                       if op.asset_pair == asset_pair and op.status == "ACTIVE"]
        if existing_ops:
            return False, f"Ya existe operación activa para {asset_pair}", None
        
        # 3. Calcular tamaño de posición
        # Necesitamos el precio del asset para calcular posición
        # Esto se obtendrá del módulo de precios
        asset_price = self._get_asset_price(asset_pair)  # Método a implementar
        
        position_size, position_details = self.calculate_position_size(
            asset_price, 
            confidence_score
        )
        
        if position_size == Decimal('0'):
            return False, "Tamaño de posición calculado es cero", None
        
        # 4. Verificar cooldown para este asset
        if not self._check_cooldown(asset_pair):
            return False, f"Asset {asset_pair} en cooldown", None
        
        # 5. Verificar límite horario
        if not self._check_hourly_limit():
            return False, "Límite horario de operaciones alcanzado", None
        
        return True, "✅ Puede abrir operación", position_details
    
    def open_operation(self,
                      operation_id: str,
                      asset_pair: str,
                      entry_price: Decimal,
                      position_size_usdc: Decimal,
                      stop_loss_pct: Decimal = None,
                      take_profit_pct: Decimal = None) -> Operation:
        """
        Abre una nueva operación
        """
        # Calcular stop loss y take profit
        if stop_loss_pct is None:
            stop_loss_pct = self.config.trading.capital.stop_loss_pct
        if take_profit_pct is None:
            take_profit_pct = self.config.trading.capital.take_profit_pct
        
        stop_loss_price = entry_price * (Decimal('1') - stop_loss_pct)
        take_profit_price = entry_price * (Decimal('1') + take_profit_pct)
        
        # Calcular riesgo cero
        fees_pct = self.config.trading.orca_fee_pct * Decimal('2')  # Entrada y salida
        risk_zero_price = self.calculate_risk_zero_price(
            entry_price, 
            position_size_usdc, 
            fees_pct
        )
        
        # Crear operación
        operation = Operation(
            id=operation_id,
            asset_pair=asset_pair,
            entry_price=entry_price,
            entry_time=datetime.now(),
            position_size_usdc=position_size_usdc,
            stop_loss_price=stop_loss_price.quantize(Decimal('0.0001'), rounding=ROUND_DOWN),
            take_profit_price=take_profit_price.quantize(Decimal('0.0001'), rounding=ROUND_DOWN),
            current_price=entry_price,
            risk_zero_price=risk_zero_price,
            status="ACTIVE"
        )
        
        # Guardar operación
        self.operations[operation_id] = operation
        self.config.increment_active_operations()
        self.config.increment_daily_trades()
        
        # Actualizar exposición
        self._update_exposure()
        
        # Guardar estado
        self.save_operations()
        self.config._save_state()
        
        # Loggear
        self.config.trade_logger.info(
            f"Operación abierta: {operation_id} - {asset_pair} - "
            f"Tamaño: ${position_size_usdc} - Entry: ${entry_price} - "
            f"SL: ${stop_loss_price} - TP: ${take_profit_price}"
        )
        
        return operation
    
    def close_operation(self, 
                       operation_id: str,
                       exit_price: Decimal,
                       reason: str = "MANUAL") -> Dict:
        """
        Cierra una operación
        Returns: detalles del cierre
        """
        if operation_id not in self.operations:
            return {"error": "Operación no encontrada"}
        
        operation = self.operations[operation_id]
        
        # Calcular P&L
        pnl_pct = ((exit_price - operation.entry_price) / operation.entry_price) * Decimal('100')
        pnl_usdc = operation.position_size_usdc * (pnl_pct / Decimal('100'))
        
        # Actualizar operación
        operation.status = "CLOSED"
        operation.current_price = exit_price
        
        # Actualizar contadores
        self.config.decrement_active_operations()
        
        # Guardar en historial
        trade_record = {
            "operation_id": operation_id,
            "asset_pair": operation.asset_pair,
            "entry_price": float(operation.entry_price),
            "exit_price": float(exit_price),
            "position_size_usdc": float(operation.position_size_usdc),
            "pnl_pct": float(pnl_pct),
            "pnl_usdc": float(pnl_usdc),
            "entry_time": operation.entry_time.isoformat(),
            "exit_time": datetime.now().isoformat(),
            "duration_minutes": (datetime.now() - operation.entry_time).total_seconds() / 60,
            "close_reason": reason
        }
        
        self.trades_history.append(trade_record)
        
        # Guardar
        self.save_operations()
        self._save_trade_history(trade_record)
        
        # Loggear
        self.config.trade_logger.info(
            f"Operación cerrada: {operation_id} - {operation.asset_pair} - "
            f"P&L: {pnl_pct:.2f}% (${pnl_usdc:.2f}) - Razón: {reason}"
        )
        
        return trade_record
    
    def check_operation_triggers(self, 
                               operation_id: str,
                               current_price: Decimal) -> List[Dict]:
        """
        Verifica triggers de una operación (SL, TP, Trailing)
        Returns: lista de acciones a tomar
        """
        if operation_id not in self.operations:
            return []
        
        operation = self.operations[operation_id]
        operation.update_price(current_price)
        
        triggers = []
        
        # 1. Check Stop Loss
        if current_price <= operation.stop_loss_price:
            triggers.append({
                "type": "STOP_LOSS",
                "price": float(operation.stop_loss_price),
                "current_price": float(current_price),
                "action": "CLOSE",
                "reason": f"Stop loss alcanzado a ${operation.stop_loss_price}"
            })
        
        # 2. Check Take Profit
        elif current_price >= operation.take_profit_price:
            triggers.append({
                "type": "TAKE_PROFIT",
                "price": float(operation.take_profit_price),
                "current_price": float(current_price),
                "action": "CLOSE",
                "reason": f"Take profit alcanzado a ${operation.take_profit_price}"
            })
        
        # 3. Check Trailing Stop (si está activo)
        elif operation.trailing_stop_price and current_price <= operation.trailing_stop_price:
            triggers.append({
                "type": "TRAILING_STOP",
                "price": float(operation.trailing_stop_price),
                "current_price": float(current_price),
                "action": "CLOSE",
                "reason": f"Trailing stop alcanzado a ${operation.trailing_stop_price}"
            })
        
        # 4. Activar trailing stop si se alcanza el umbral
        elif (operation.current_pnl_pct >= self.config.trading.capital.trailing_stop_activation_pct * Decimal('100')
              and not operation.trailing_stop_price):
            # Activar trailing stop
            trailing_distance = self.config.trading.capital.trailing_stop_distance_pct * Decimal('100')
            operation.trailing_stop_price = current_price * (
                Decimal('1') - trailing_distance / Decimal('100')
            )
            
            triggers.append({
                "type": "TRAILING_STOP_ACTIVATED",
                "activation_price": float(current_price),
                "trailing_stop_price": float(operation.trailing_stop_price),
                "action": "UPDATE",
                "reason": f"Trailing stop activado a ${operation.trailing_stop_price}"
            })
        
        # 5. Check Risk Zero (información solo)
        if operation.is_risk_zero():
            triggers.append({
                "type": "RISK_ZERO_REACHED",
                "price": float(operation.risk_zero_price),
                "current_price": float(current_price),
                "action": "INFO",
                "reason": f"Riesgo cero alcanzado. Posición ahora libre de riesgo"
            })
        
        return triggers
    
    def get_available_capital_for_trading(self) -> Decimal:
        """Calcula capital disponible para nuevas operaciones"""
        total_capital = self.config.current_capital_usdc
        capital_for_trading = total_capital * (
            Decimal('1') - self.config.trading.capital.capital_reserve_pct
        )
        
        current_exposure = sum(
            op.position_size_usdc 
            for op in self.operations.values() 
            if op.status == "ACTIVE"
        )
        
        available = capital_for_trading - current_exposure
        return max(available, Decimal('0'))
    
    def save_operations(self):
        """Guarda operaciones a archivo"""
        ops_data = []
        for op in self.operations.values():
            op_dict = {
                "id": op.id,
                "asset_pair": op.asset_pair,
                "entry_price": str(op.entry_price),
                "entry_time": op.entry_time.isoformat(),
                "position_size_usdc": str(op.position_size_usdc),
                "stop_loss_price": str(op.stop_loss_price),
                "take_profit_price": str(op.take_profit_price),
                "current_price": str(op.current_price),
                "trailing_stop_price": str(op.trailing_stop_price) if op.trailing_stop_price else None,
                "risk_zero_price": str(op.risk_zero_price) if op.risk_zero_price else None,
                "status": op.status
            }
            ops_data.append(op_dict)
        
        with open(self.operations_file, 'w') as f:
            json.dump(ops_data, f, indent=2)
    
    def load_operations(self):
        """Carga operaciones desde archivo"""
        if not self.operations_file.exists():
            return
        
        with open(self.operations_file, 'r') as f:
            ops_data = json.load(f)
        
        for op_dict in ops_data:
            operation = Operation(
                id=op_dict["id"],
                asset_pair=op_dict["asset_pair"],
                entry_price=Decimal(op_dict["entry_price"]),
                entry_time=datetime.fromisoformat(op_dict["entry_time"]),
                position_size_usdc=Decimal(op_dict["position_size_usdc"]),
                stop_loss_price=Decimal(op_dict["stop_loss_price"]),
                take_profit_price=Decimal(op_dict["take_profit_price"]),
                current_price=Decimal(op_dict.get("current_price", op_dict["entry_price"])),
                trailing_stop_price=Decimal(op_dict["trailing_stop_price"]) if op_dict.get("trailing_stop_price") else None,
                risk_zero_price=Decimal(op_dict["risk_zero_price"]) if op_dict.get("risk_zero_price") else None,
                status=op_dict["status"]
            )
            self.operations[operation.id] = operation
    
    def _get_asset_price(self, asset_pair: str) -> Decimal:
        """Obtiene precio actual del asset (a implementar)"""
        # Esto se integrará con el módulo de precios
        # Por ahora retorna un placeholder
        return Decimal('100.0')
    
    def _check_cooldown(self, asset_pair: str) -> bool:
        """Verifica si el asset está en cooldown"""
        # Implementar lógica de cooldown
        return True
    
    def _check_hourly_limit(self) -> bool:
        """Verifica límite horario de operaciones"""
        # Contar operaciones en la última hora
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_ops = [
            op for op in self.trades_history
            if datetime.fromisoformat(op["exit_time"]) > one_hour_ago
        ]
        
        return len(recent_ops) < self.config.trading.max_trades_per_hour
    
    def _update_exposure(self):
        """Actualiza exposición del portfolio"""
        # Lógica para actualizar métricas de exposición
        pass
    
    def _save_trade_history(self, trade_record: Dict):
        """Guarda historial de trades"""
        history_file = self.config.base_dir / "state" / "trades_history.json"
        
        history = []
        if history_file.exists():
            with open(history_file, 'r') as f:
                history = json.load(f)
        
        history.append(trade_record)
        
        # Mantener solo últimos 1000 trades
        if len(history) > 1000:
            history = history[-1000:]
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)