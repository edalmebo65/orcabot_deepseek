#!/usr/bin/env python3
"""
Bridge completo Python-Rust para OrcaBot
Permite comunicación eficiente con módulos Rust para operaciones en Solana
"""
import json
import subprocess
import os
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging
from enum import Enum
import time

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradeType(Enum):
    """Tipos de operaciones disponibles"""
    SWAP = "swap"
    LIMIT_ORDER = "limit_order"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class TradeStatus(Enum):
    """Estados de una operación"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TradeParams:
    """Parámetros para una operación de trading"""
    trade_id: str
    trade_type: TradeType
    input_token: str  # Símbolo del token de entrada (ej: "SOL")
    output_token: str  # Símbolo del token de salida (ej: "USDC")
    amount: float  # Cantidad a intercambiar
    slippage: float = 0.5  # Slippage permitido en porcentaje
    priority_fee: float = 0.000005  # Prioridad fee en SOL
    dex: str = "orca"  # DEX a utilizar (orca, raydium, etc.)
    timestamp: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización"""
        data = asdict(self)
        data['trade_type'] = self.trade_type.value
        data['timestamp'] = data['timestamp'] or int(time.time())
        return data

@dataclass
class TradeResult:
    """Resultado de una operación ejecutada"""
    trade_id: str
    status: TradeStatus
    tx_hash: Optional[str] = None
    input_amount: Optional[float] = None
    output_amount: Optional[float] = None
    price_impact: Optional[float] = None
    fees: Optional[float] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización"""
        data = asdict(self)
        data['status'] = self.status.value
        data['timestamp'] = data['timestamp'] or int(time.time())
        return data

class RustBridge:
    """
    Clase principal para comunicación con módulos Rust
    Maneja ejecución de operaciones, consultas y monitoreo
    """
    
    def __init__(self, rust_binary_path: str = "./target/release/orca_bridge"):
        """
        Inicializa el bridge Rust
        
        Args:
            rust_binary_path: Ruta al ejecutable Rust compilado
        """
        self.rust_binary = rust_binary_path
        self.active_trades: Dict[str, TradeParams] = {}
        self.trade_history: List[TradeResult] = []
        
        # Verificar que el binario existe
        if not os.path.exists(self.rust_binary):
            logger.warning(f"Binario Rust no encontrado en {self.rust_binary}")
            logger.info("Modo simulación activado para desarrollo")
            self.simulation_mode = True
        else:
            self.simulation_mode = False
            
        logger.info(f"RustBridge inicializado en modo {'simulación' if self.simulation_mode else 'producción'}")
    
    def execute_trade(self, trade_params: TradeParams) -> TradeResult:
        """
        Ejecuta una operación de trading a través del módulo Rust
        
        Args:
            trade_params: Parámetros de la operación
            
        Returns:
            TradeResult con el resultado de la operación
        """
        logger.info(f"Ejecutando operación {trade_params.trade_id}: "
                   f"{trade_params.amount} {trade_params.input_token} -> {trade_params.output_token}")
        
        # Registrar operación activa
        self.active_trades[trade_params.trade_id] = trade_params
        
        try:
            if self.simulation_mode:
                # Modo simulación para desarrollo
                result = self._simulate_trade(trade_params)
            else:
                # Comunicación real con Rust
                result = self._execute_rust_trade(trade_params)
                
            # Registrar en historial
            self.trade_history.append(result)
            
            # Eliminar de activas si está completada o fallida
            if result.status in [TradeStatus.COMPLETED, TradeStatus.FAILED, TradeStatus.CANCELLED]:
                self.active_trades.pop(trade_params.trade_id, None)
                
            return result
            
        except Exception as e:
            logger.error(f"Error ejecutando operación {trade_params.trade_id}: {e}")
            error_result = TradeResult(
                trade_id=trade_params.trade_id,
                status=TradeStatus.FAILED,
                error_message=str(e),
                timestamp=int(time.time())
            )
            self.trade_history.append(error_result)
            return error_result
    
    def _execute_rust_trade(self, trade_params: TradeParams) -> TradeResult:
        """
        Ejecuta operación a través del binario Rust
        
        Args:
            trade_params: Parámetros de la operación
            
        Returns:
            TradeResult con resultados
        """
        start_time = time.time()
        
        # Preparar datos para Rust
        trade_data = trade_params.to_dict()
        trade_json = json.dumps(trade_data)
        
        try:
            # Ejecutar comando Rust
            cmd = [self.rust_binary, "execute-swap", trade_json]
            logger.debug(f"Ejecutando comando: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Timeout de 30 segundos
            )
            
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                # Parsear respuesta exitosa
                rust_result = json.loads(result.stdout)
                
                return TradeResult(
                    trade_id=trade_params.trade_id,
                    status=TradeStatus.COMPLETED,
                    tx_hash=rust_result.get("tx_hash"),
                    input_amount=trade_params.amount,
                    output_amount=rust_result.get("output_amount"),
                    price_impact=rust_result.get("price_impact", 0),
                    fees=rust_result.get("fees", 0),
                    execution_time=execution_time,
                    timestamp=int(time.time())
                )
            else:
                # Error en Rust
                error_msg = result.stderr or "Error desconocido en módulo Rust"
                logger.error(f"Rust error: {error_msg}")
                
                return TradeResult(
                    trade_id=trade_params.trade_id,
                    status=TradeStatus.FAILED,
                    error_message=error_msg,
                    execution_time=execution_time,
                    timestamp=int(time.time())
                )
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout ejecutando operación {trade_params.trade_id}")
            return TradeResult(
                trade_id=trade_params.trade_id,
                status=TradeStatus.FAILED,
                error_message="Timeout en ejecución",
                execution_time=30.0,
                timestamp=int(time.time())
            )
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta Rust: {e}")
            return TradeResult(
                trade_id=trade_params.trade_id,
                status=TradeStatus.FAILED,
                error_message=f"Respuesta inválida: {e}",
                execution_time=time.time() - start_time,
                timestamp=int(time.time())
            )
    
    def _simulate_trade(self, trade_params: TradeParams) -> TradeResult:
        """
        Simula una operación para desarrollo sin módulo Rust
        
        Args:
            trade_params: Parámetros de la operación
            
        Returns:
            TradeResult simulado
        """
        import random
        import hashlib
        
        logger.info(f"Simulando operación {trade_params.trade_id}")
        time.sleep(0.5)  # Simular tiempo de ejecución
        
        # Simular éxito/fallo aleatorio (90% éxito en desarrollo)
        success = random.random() < 0.9
        
        if success:
            # Simular resultado exitoso
            tx_hash = hashlib.sha256(
                f"{trade_params.trade_id}{time.time()}".encode()
            ).hexdigest()[:64]
            
            # Simular precio con pequeño impacto
            simulated_price_impact = random.uniform(0.01, 0.5)
            output_amount = trade_params.amount * (1 - simulated_price_impact / 100)
            
            return TradeResult(
                trade_id=trade_params.trade_id,
                status=TradeStatus.COMPLETED,
                tx_hash=tx_hash,
                input_amount=trade_params.amount,
                output_amount=output_amount,
                price_impact=simulated_price_impact,
                fees=0.0001,  # Fee simulado
                execution_time=0.5,
                timestamp=int(time.time())
            )
        else:
            # Simular fallo
            error_messages = [
                "Insufficient liquidity",
                "Slippage tolerance exceeded",
                "Transaction simulation failed",
                "Network congestion"
            ]
            
            return TradeResult(
                trade_id=trade_params.trade_id,
                status=TradeStatus.FAILED,
                error_message=random.choice(error_messages),
                execution_time=0.5,
                timestamp=int(time.time())
            )
    
    def get_quote(self, input_token: str, output_token: str, amount: float) -> Dict[str, Any]:
        """
        Obtiene cotización para un swap
        
        Args:
            input_token: Token de entrada
            output_token: Token de salida
            amount: Cantidad a intercambiar
            
        Returns:
            Diccionario con información de cotización
        """
        if self.simulation_mode:
            # Simular cotización
            import random
            
            return {
                "input_token": input_token,
                "output_token": output_token,
                "input_amount": amount,
                "output_amount": amount * random.uniform(0.95, 1.05),
                "price_impact": random.uniform(0.1, 1.0),
                "liquidity": random.uniform(10000, 1000000),
                "fees": amount * 0.003,
                "timestamp": int(time.time())
            }
        else:
            # Consultar a Rust
            quote_data = {
                "input_token": input_token,
                "output_token": output_token,
                "amount": amount,
                "timestamp": int(time.time())
            }
            
            try:
                result = subprocess.run(
                    [self.rust_binary, "get-quote", json.dumps(quote_data)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    return json.loads(result.stdout)
                else:
                    logger.error(f"Error obteniendo cotización: {result.stderr}")
                    return {"error": result.stderr}
                    
            except Exception as e:
                logger.error(f"Excepción obteniendo cotización: {e}")
                return {"error": str(e)}
    
    def get_balance(self, token_symbol: str = "SOL") -> Dict[str, Any]:
        """
        Obtiene balance de un token
        
        Args:
            token_symbol: Símbolo del token
            
        Returns:
            Diccionario con información de balance
        """
        if self.simulation_mode:
            # Simular balance
            import random
            
            return {
                "token": token_symbol,
                "balance": random.uniform(0.5, 10.0),
                "usd_value": random.uniform(5.0, 200.0),
                "timestamp": int(time.time())
            }
        else:
            # Consultar a Rust
            balance_data = {"token": token_symbol}
            
            try:
                result = subprocess.run(
                    [self.rust_binary, "get-balance", json.dumps(balance_data)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    return json.loads(result.stdout)
                else:
                    logger.error(f"Error obteniendo balance: {result.stderr}")
                    return {"error": result.stderr}
                    
            except Exception as e:
                logger.error(f"Excepción obteniendo balance: {e}")
                return {"error": str(e)}
    
    def get_active_trades(self) -> List[Dict[str, Any]]:
        """
        Obtiene lista de operaciones activas
        
        Returns:
            Lista de operaciones activas
        """
        return [trade.to_dict() for trade in self.active_trades.values()]
    
    def get_trade_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene historial de operaciones
        
        Args:
            limit: Número máximo de operaciones a retornar
            
        Returns:
            Lista de operaciones históricas
        """
        sorted_history = sorted(
            self.trade_history,
            key=lambda x: x.timestamp or 0,
            reverse=True
        )
        return [trade.to_dict() for trade in sorted_history[:limit]]
    
    def cancel_trade(self, trade_id: str) -> bool:
        """
        Cancela una operación activa
        
        Args:
            trade_id: ID de la operación a cancelar
            
        Returns:
            True si se canceló exitosamente
        """
        if trade_id in self.active_trades:
            logger.info(f"Cancelando operación {trade_id}")
            
            if not self.simulation_mode:
                # Enviar comando de cancelación a Rust
                cancel_data = {"trade_id": trade_id}
                result = subprocess.run(
                    [self.rust_binary, "cancel-trade", json.dumps(cancel_data)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Error cancelando operación: {result.stderr}")
                    return False
            
            # Registrar cancelación
            cancel_result = TradeResult(
                trade_id=trade_id,
                status=TradeStatus.CANCELLED,
                timestamp=int(time.time())
            )
            self.trade_history.append(cancel_result)
            
            # Eliminar de activas
            self.active_trades.pop(trade_id, None)
            
            return True
        else:
            logger.warning(f"Operación {trade_id} no encontrada")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica estado del bridge y conexión con Rust
        
        Returns:
            Diccionario con estado de salud
        """
        health = {
            "rust_binary_exists": os.path.exists(self.rust_binary),
            "simulation_mode": self.simulation_mode,
            "active_trades": len(self.active_trades),
            "total_trades": len(self.trade_history),
            "timestamp": int(time.time())
        }
        
        if not self.simulation_mode:
            try:
                # Verificar que Rust responde
                test_data = {"test": "health_check"}
                result = subprocess.run(
                    [self.rust_binary, "health", json.dumps(test_data)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                health["rust_responding"] = result.returncode == 0
                health["rust_version"] = result.stdout.strip() if result.stdout else "unknown"
            except Exception as e:
                health["rust_responding"] = False
                health["rust_error"] = str(e)
        
        return health

# Funciones de utilidad para uso directo
def create_trade_params(
    trade_id: str,
    trade_type: TradeType,
    input_token: str,
    output_token: str,
    amount: float,
    **kwargs
) -> TradeParams:
    """Crea parámetros de operación"""
    return TradeParams(
        trade_id=trade_id,
        trade_type=trade_type,
        input_token=input_token,
        output_token=output_token,
        amount=amount,
        **kwargs
    )

def execute_simple_swap(
    input_token: str,
    output_token: str,
    amount: float,
    bridge: Optional[RustBridge] = None
) -> TradeResult:
    """
    Función simplificada para ejecutar un swap
    
    Args:
        input_token: Token de entrada
        output_token: Token de salida
        amount: Cantidad a intercambiar
        bridge: Instancia de RustBridge (opcional)
        
    Returns:
        Resultado de la operación
    """
    if bridge is None:
        bridge = RustBridge()
    
    trade_id = f"swap_{input_token}_{output_token}_{int(time.time())}"
    
    trade_params = TradeParams(
        trade_id=trade_id,
        trade_type=TradeType.SWAP,
        input_token=input_token,
        output_token=output_token,
        amount=amount
    )
    
    return bridge.execute_trade(trade_params)

# Ejemplo de uso
if __name__ == "__main__":
    print("🧪 Probando RustBridge...")
    
    # Crear instancia del bridge
    bridge = RustBridge()
    
    # Verificar salud
    health = bridge.health_check()
    print(f"Estado: {health}")
    
    # Ejecutar operación de prueba
    if health.get("rust_binary_exists", False) or health.get("simulation_mode", False):
        result = execute_simple_swap("SOL", "USDC", 0.1, bridge)
        print(f"Resultado: {result.to_dict()}")
    else:
        print("⚠️  Modo simulación activado, probando cotización...")
        quote = bridge.get_quote("SOL", "USDC", 1.0)
        print(f"Cotización: {quote}")