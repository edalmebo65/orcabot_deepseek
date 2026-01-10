# core/scheduler/operation_scheduler.py
import asyncio
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import heapq

@dataclass
class ScheduledOperation:
    """Operación programada"""
    id: str
    asset_pair: str
    operation_type: str  # "BUY", "SELL", "STOP_LOSS", "TAKE_PROFIT"
    price: Decimal
    quantity: Decimal
    scheduled_time: datetime
    priority: int  # 1 = más alta
    status: str  # "PENDING", "EXECUTED", "CANCELLED", "FAILED"
    metadata: Dict
    
    @property
    def is_pending(self) -> bool:
        return self.status == "PENDING"
    
    @property
    def is_due(self) -> bool:
        return datetime.now() >= self.scheduled_time

class OperationScheduler:
    """Planificador de operaciones"""
    
    def __init__(self, config, trading_engine):
        self.config = config
        self.trading_engine = trading_engine
        
        # Cola de prioridad para operaciones programadas
        self.scheduled_operations: List[ScheduledOperation] = []
        self.operation_lookup: Dict[str, ScheduledOperation] = {}
        
        # Operaciones recurrentes
        self.recurring_operations: Dict[str, Dict] = {}
        
        # Configuración
        self.max_scheduled_ops = 100
        self.cleanup_interval = timedelta(hours=1)
        self.last_cleanup = datetime.now()
        
        # Estado
        self.is_running = False
    
    def schedule_operation(self,
                         asset_pair: str,
                         operation_type: str,
                         price: Decimal,
                         quantity: Decimal,
                         scheduled_time: datetime,
                         priority: int = 5,
                         metadata: Dict = None) -> Optional[str]:
        """
        Programa una operación
        """
        # Verificar límite
        if len(self.scheduled_operations) >= self.max_scheduled_ops:
            self.config.logger.warning("Maximum scheduled operations reached")
            return None
        
        # Crear ID único
        op_id = f"sched_{datetime.now().strftime('%Y%m%d%H%M%S')}_{asset_pair}"
        
        # Crear operación programada
        operation = ScheduledOperation(
            id=op_id,
            asset_pair=asset_pair,
            operation_type=operation_type,
            price=price,
            quantity=quantity,
            scheduled_time=scheduled_time,
            priority=priority,
            status="PENDING",
            metadata=metadata or {}
        )
        
        # Agregar a la cola de prioridad
        heapq.heappush(self.scheduled_operations, (priority, scheduled_time.timestamp(), operation))
        self.operation_lookup[op_id] = operation
        
        self.config.logger.info(
            f"📅 Scheduled {operation_type} operation for {asset_pair} "
            f"@ ${price:.4f} at {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return op_id
    
    def schedule_recurring_operation(self,
                                   asset_pair: str,
                                   operation_type: str,
                                   interval: timedelta,
                                   price_calculator,
                                   quantity_calculator,
                                   metadata: Dict = None) -> str:
        """
        Programa una operación recurrente
        """
        rec_id = f"recur_{asset_pair}_{operation_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Calcular primera ejecución (próxima hora completa)
        now = datetime.now()
        first_execution = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        # Guardar configuración recurrente
        self.recurring_operations[rec_id] = {
            'asset_pair': asset_pair,
            'operation_type': operation_type,
            'interval': interval,
            'price_calculator': price_calculator,
            'quantity_calculator': quantity_calculator,
            'last_execution': None,
            'next_execution': first_execution,
            'executions_count': 0,
            'metadata': metadata or {}
        }
        
        # Programar primera operación
        self._schedule_next_recurring(rec_id)
        
        self.config.logger.info(
            f"🔄 Scheduled recurring {operation_type} for {asset_pair} "
            f"every {interval.total_seconds()//3600}h"
        )
        
        return rec_id
    
    def _schedule_next_recurring(self, rec_id: str):
        """Programa siguiente ejecución recurrente"""
        if rec_id not in self.recurring_operations:
            return
        
        rec_config = self.recurring_operations[rec_id]
        
        # Calcular precio y cantidad
        try:
            price = rec_config['price_calculator']()
            quantity = rec_config['quantity_calculator']()
        except Exception as e:
            self.config.logger.error(f"Error calculating price/quantity for {rec_id}: {e}")
            return
        
        # Programar operación
        op_id = self.schedule_operation(
            asset_pair=rec_config['asset_pair'],
            operation_type=rec_config['operation_type'],
            price=price,
            quantity=quantity,
            scheduled_time=rec_config['next_execution'],
            priority=3,  # Prioridad media para recurrentes
            metadata={**rec_config['metadata'], 'recurring_id': rec_id}
        )
        
        if op_id:
            # Actualizar siguiente ejecución
            rec_config['next_execution'] = rec_config['next_execution'] + rec_config['interval']
    
    async def start(self):
        """Inicia el planificador"""
        self.is_running = True
        self.config.logger.info("🚀 Operation scheduler started")
        
        while self.is_running:
            try:
                # Ejecutar operaciones pendientes
                await self._execute_pending_operations()
                
                # Limpieza periódica
                await self._cleanup_old_operations()
                
                # Esperar antes de siguiente verificación
                await asyncio.sleep(1)
                
            except Exception as e:
                self.config.logger.error(f"Error in operation scheduler: {e}")
                await asyncio.sleep(5)
    
    async def _execute_pending_operations(self):
        """Ejecuta operaciones pendientes"""
        now = datetime.now()
        executed_ops = []
        
        # Obtener operaciones pendientes (sin modificar la heap)
        pending_ops = []
        temp_heap = self.scheduled_operations.copy()
        
        while temp_heap:
            priority, timestamp, operation = heapq.heappop(temp_heap)
            if operation.is_pending and operation.is_due:
                pending_ops.append(operation)
        
        # Ejecutar operaciones pendientes
        for operation in pending_ops:
            try:
                self.config.logger.info(
                    f"⚡ Executing scheduled {operation.operation_type} "
                    f"for {operation.asset_pair} @ ${operation.price:.4f}"
                )
                
                # Ejecutar operación a través del trading engine
                success = await self._execute_operation(operation)
                
                if success:
                    operation.status = "EXECUTED"
                    executed_ops.append(operation.id)
                    
                    # Si es recurrente, programar siguiente
                    if 'recurring_id' in operation.metadata:
                        rec_id = operation.metadata['recurring_id']
                        if rec_id in self.recurring_operations:
                            rec_config = self.recurring_operations[rec_id]
                            rec_config['last_execution'] = now
                            rec_config['executions_count'] += 1
                            self._schedule_next_recurring(rec_id)
                
                else:
                    operation.status = "FAILED"
                    self.config.logger.error(f"Failed to execute scheduled operation {operation.id}")
                    
            except Exception as e:
                operation.status = "FAILED"
                self.config.logger.error(f"Error executing scheduled operation {operation.id}: {e}")
        
        # Remover operaciones ejecutadas de la heap
        if executed_ops:
            new_heap = []
            for priority, timestamp, operation in self.scheduled_operations:
                if operation.id not in executed_ops:
                    heapq.heappush(new_heap, (priority, timestamp, operation))
                else:
                    # Remover del lookup
                    self.operation_lookup.pop(operation.id, None)
            
            self.scheduled_operations = new_heap
    
    async def _execute_operation(self, operation: ScheduledOperation) -> bool:
        """Ejecuta una operación específica"""
        try:
            # Aquí se integraría con el trading engine real
            # Por ahora, simulamos ejecución
            
            if operation.operation_type == "BUY":
                # Lógica de compra
                pass
            elif operation.operation_type == "SELL":
                # Lógica de venta
                pass
            elif operation.operation_type == "STOP_LOSS":
                # Lógica de stop loss
                pass
            elif operation.operation_type == "TAKE_PROFIT":
                # Lógica de take profit
                pass
            
            # Simular éxito
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            self.config.logger.error(f"Error in operation execution: {e}")
            return False
    
    async def _cleanup_old_operations(self):
        """Limpia operaciones antiguas"""
        now = datetime.now()
        
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # Remover operaciones ejecutadas o fallidas de más de 24 horas
        cutoff_time = now - timedelta(hours=24)
        removed_count = 0
        
        new_heap = []
        for priority, timestamp, operation in self.scheduled_operations:
            if (operation.status in ["EXECUTED", "FAILED", "CANCELLED"] and 
                operation.scheduled_time < cutoff_time):
                # Remover del lookup
                self.operation_lookup.pop(operation.id, None)
                removed_count += 1
            else:
                heapq.heappush(new_heap, (priority, timestamp, operation))
        
        self.scheduled_operations = new_heap
        
        if removed_count > 0:
            self.config.logger.debug(f"Cleaned up {removed_count} old operations")
        
        self.last_cleanup = now
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancela una operación programada"""
        if operation_id not in self.operation_lookup:
            return False
        
        operation = self.operation_lookup[operation_id]
        
        if operation.status != "PENDING":
            self.config.logger.warning(f"Cannot cancel {operation_id} - status: {operation.status}")
            return False
        
        operation.status = "CANCELLED"
        
        # Remover de la heap
        new_heap = []
        for priority, timestamp, op in self.scheduled_operations:
            if op.id != operation_id:
                heapq.heappush(new_heap, (priority, timestamp, op))
        
        self.scheduled_operations = new_heap
        self.operation_lookup.pop(operation_id)
        
        self.config.logger.info(f"❌ Cancelled scheduled operation {operation_id}")
        return True
    
    def cancel_recurring_operation(self, recurring_id: str) -> bool:
        """Cancela una operación recurrente"""
        if recurring_id not in self.recurring_operations:
            return False
        
        # Cancelar todas las operaciones pendientes de este recurrente
        ops_to_cancel = []
        for op_id, operation in self.operation_lookup.items():
            if (operation.metadata.get('recurring_id') == recurring_id and 
                operation.status == "PENDING"):
                ops_to_cancel.append(op_id)
        
        for op_id in ops_to_cancel:
            self.cancel_operation(op_id)
        
        # Remover configuración recurrente
        del self.recurring_operations[recurring_id]
        
        self.config.logger.info(f"❌ Cancelled recurring operation {recurring_id}")
        return True
    
    def get_scheduled_operations(self, 
                               status: str = None,
                               asset_pair: str = None) -> List[Dict]:
        """Obtiene operaciones programadas"""
        operations = []
        
        for priority, timestamp, operation in self.scheduled_operations:
            # Filtrar por status
            if status and operation.status != status:
                continue
            
            # Filtrar por asset pair
            if asset_pair and operation.asset_pair != asset_pair:
                continue
            
            operations.append({
                'id': operation.id,
                'asset_pair': operation.asset_pair,
                'operation_type': operation.operation_type,
                'price': float(operation.price),
                'quantity': float(operation.quantity),
                'scheduled_time': operation.scheduled_time.isoformat(),
                'status': operation.status,
                'priority': priority,
                'is_due': operation.is_due,
                'metadata': operation.metadata
            })
        
        return sorted(operations, key=lambda x: x['scheduled_time'])
    
    def get_recurring_operations(self) -> List[Dict]:
        """Obtiene operaciones recurrentes"""
        recurring_list = []
        
        for rec_id, config in self.recurring_operations.items():
            recurring_list.append({
                'id': rec_id,
                'asset_pair': config['asset_pair'],
                'operation_type': config['operation_type'],
                'interval_hours': config['interval'].total_seconds() / 3600,
                'last_execution': config['last_execution'].isoformat() if config['last_execution'] else None,
                'next_execution': config['next_execution'].isoformat() if config['next_execution'] else None,
                'executions_count': config['executions_count'],
                'metadata': config['metadata']
            })
        
        return recurring_list
    
    def stop(self):
        """Detiene el planificador"""
        self.is_running = False
        self.config.logger.info("🛑 Operation scheduler stopped")