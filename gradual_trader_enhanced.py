# gradual_trader_enhanced.py
"""
Sistema de trading gradual con gestión avanzada de posiciones
Implementa trailing stops, gestión de riesgo y ejecución escalonada
"""
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from decimal import Decimal
import json
import hashlib

from config import TRADING, RISK, WALLET, SOLANA

class TradeStatus(Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    STOPPED = "STOPPED"
    CANCELLED = "CANCELLED"

class ExitReason(Enum):
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    TRAILING_STOP = "TRAILING_STOP"
    MANUAL = "MANUAL"
    TIMEOUT = "TIMEOUT"
    EMERGENCY = "EMERGENCY"

@dataclass
class Trade:
    """Estructura de datos para una operación"""
    id: str
    token_address: str
    token_symbol: str
    entry_price: float
    current_price: float
    position_size_usd: float
    position_size_tokens: float
    entry_time: datetime
    stop_loss_price: float
    take_profit_price: float
    trailing_stop_price: float
    trailing_activated: bool
    status: TradeStatus
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    pnl_percent: float = 0.0
    pnl_usd: float = 0.0
    fees_paid: float = 0.0
    confidence_score: float = 0.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def update_pnl(self, current_price: float):
        """Actualizar P&L"""
        self.current_price = current_price
        self.pnl_percent = (current_price - self.entry_price) / self.entry_price * 100
        self.pnl_usd = self.position_size_usd * self.pnl_percent / 100
    
    def should_exit(self) -> Tuple[bool, Optional[ExitReason]]:
        """Verificar si se debe salir de la operación"""
        # Stop Loss
        if self.current_price <= self.stop_loss_price:
            return True, ExitReason.STOP_LOSS
        
        # Take Profit
        if self.current_price >= self.take_profit_price:
            return True, ExitReason.TAKE_PROFIT
        
        # Trailing Stop (si está activado)
        if self.trailing_activated and self.current_price <= self.trailing_stop_price:
            return True, ExitReason.TRAILING_STOP
        
        # Timeout (24 horas máximo)
        if datetime.now() - self.entry_time > timedelta(hours=24):
            return True, ExitReason.TIMEOUT
        
        # Drawdown excesivo desde máximo
        if hasattr(self, 'max_price'):
            drawdown = (self.max_price - self.current_price) / self.max_price
            if drawdown > 0.08:  # 8% drawdown desde máximo
                return True, ExitReason.EMERGENCY
        
        return False, None
    
    def update_trailing_stop(self, current_price: float):
        """Actualizar trailing stop dinámicamente"""
        if not self.trailing_activated:
            # Activar trailing stop al 0.2% de ganancia
            if current_price >= self.entry_price * (1 + TRADING.TRAILING_STOP_ACTIVATION):
                self.trailing_activated = True
                self.trailing_stop_price = current_price * (1 - TRADING.TRAILING_STOP_DISTANCE)
        else:
            # Actualizar trailing stop si el precio sube
            new_trailing_stop = current_price * (1 - TRADING.TRAILING_STOP_DISTANCE)
            if new_trailing_stop > self.trailing_stop_price:
                self.trailing_stop_price = new_trailing_stop
        
        # Guardar precio máximo
        if not hasattr(self, 'max_price') or current_price > self.max_price:
            self.max_price = current_price

class GradualTrader:
    """Gestor de trading gradual con múltiples operaciones simultáneas"""
    def __init__(self, wallet_manager, dex_manager):
        self.wallet = wallet_manager
        self.dex = dex_manager
        self.active_trades: Dict[str, Trade] = {}
        self.trade_history: List[Trade] = []
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_concurrent = TRADING.MAX_CONCURRENT_TRADES
        self.is_trading = False
        self.monitor_task = None
        
        # Estadísticas
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl_usd': 0.0,
            'total_fees': 0.0,
            'max_win': 0.0,
            'max_loss': 0.0,
            'avg_holding_time': timedelta(0)
        }
    
    async def initialize(self):
        """Inicializar trader"""
        print("🚀 Inicializando Gradual Trader...")
        
        # Cargar trades activos de base de datos
        await self._load_active_trades()
        
        # Iniciar monitoreo
        self.is_trading = True
        self.monitor_task = asyncio.create_task(self._monitor_trades())
        
        print(f"✅ Gradual Trader inicializado. Trades activos: {len(self.active_trades)}")
    
    async def shutdown(self):
        """Apagar trader de forma segura"""
        print("🛑 Apagando Gradual Trader...")
        
        self.is_trading = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        # Cerrar todas las posiciones abiertas
        await self._close_all_positions()
        
        # Guardar estado
        await self._save_state()
        
        print("✅ Gradual Trader apagado")
    
    async def execute_gradual_entry(
        self, 
        token_address: str, 
        token_symbol: str,
        entry_price: float,
        confidence_score: float,
        stop_loss_percent: float = None,
        take_profit_percent: float = None
    ) -> Optional[str]:
        """Ejecutar entrada gradual en una operación"""
        
        # Verificar límites
        if len(self.active_trades) >= self.max_concurrent:
            print(f"⚠️ Límite de {self.max_concurrent} operaciones alcanzado")
            return None
        
        # Verificar confianza mínima
        if confidence_score < TRADING.ML_CONFIDENCE_THRESHOLD:
            print(f"⚠️ Confianza insuficiente: {confidence_score:.2f} < {TRADING.ML_CONFIDENCE_THRESHOLD}")
            return None
        
        # Verificar límites de riesgo diario
        if self.daily_pnl <= -RISK.DAILY_LOSS_LIMIT * 100:  # En porcentaje
            print(f"⚠️ Límite de pérdida diaria alcanzado: {self.daily_pnl:.2f}%")
            return None
        
        # Calcular tamaño de posición
        position_size_usd = await self._calculate_position_size(confidence_score)
        
        if position_size_usd <= 0:
            print("⚠️ Tamaño de posición inválido")
            return None
        
        # Verificar balance suficiente
        if not await self._check_balance(position_size_usd):
            print(f"⚠️ Balance insuficiente para posición de ${position_size_usd:.2f}")
            return None
        
        # Calcular precios de SL/TP
        if stop_loss_percent is None:
            stop_loss_percent = TRADING.STOP_LOSS_PERCENT
        
        if take_profit_percent is None:
            take_profit_percent = TRADING.TAKE_PROFIT_PERCENT
        
        stop_loss_price = entry_price * (1 - stop_loss_percent)
        take_profit_price = entry_price * (1 + take_profit_percent)
        
        # Calcular cantidad de tokens
        position_size_tokens = position_size_usd / entry_price
        
        # Crear trade ID único
        trade_id = hashlib.md5(
            f"{token_address}_{datetime.now().timestamp()}".encode()
        ).hexdigest()[:16]
        
        # Crear objeto Trade
        trade = Trade(
            id=trade_id,
            token_address=token_address,
            token_symbol=token_symbol,
            entry_price=entry_price,
            current_price=entry_price,
            position_size_usd=position_size_usd,
            position_size_tokens=position_size_tokens,
            entry_time=datetime.now(),
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            trailing_stop_price=0.0,
            trailing_activated=False,
            status=TradeStatus.ACTIVE,
            confidence_score=confidence_score,
            metadata={
                'volatility': 0.0,
                'rsi': 0.0,
                'market_condition': 'neutral',
                'entry_strategy': 'ml_prediction'
            }
        )
        
        # Ejecutar orden en DEX
        success, tx_hash, fees = await self._execute_buy_order(
            token_address, 
            position_size_tokens, 
            entry_price
        )
        
        if not success:
            print(f"❌ Error ejecutando orden para {token_symbol}")
            return None
        
        trade.fees_paid = fees
        
        # Agregar a trades activos
        self.active_trades[trade_id] = trade
        
        # Actualizar estadísticas
        self.daily_trades += 1
        self.stats['total_trades'] += 1
        
        # Guardar en base de datos
        await self._save_trade(trade)
        
        print(f"✅ Entrada ejecutada: {token_symbol} | "
              f"Size: ${position_size_usd:.2f} | "
              f"Entry: ${entry_price:.4f} | "
              f"Confidence: {confidence_score:.2%}")
        
        return trade_id
    
    async def _calculate_position_size(self, confidence_score: float) -> float:
        """Calcular tamaño de posición adaptativo"""
        # Obtener balance disponible
        balance = await self.wallet.get_usdc_balance()
        
        # Tamaño base (10% del balance)
        base_size = balance * TRADING.POSITION_SIZE_PERCENT
        
        # Ajustar por confianza
        if confidence_score > 0.8:
            # Alta confianza: +50%
            base_size *= 1.5
        elif confidence_score > 0.7:
            # Buena confianza: +25%
            base_size *= 1.25
        elif confidence_score < 0.6:
            # Baja confianza: -50%
            base_size *= 0.5
        
        # Ajustar por volatilidad del mercado
        market_volatility = await self._get_market_volatility()
        if market_volatility > 0.1:  # Alta volatilidad
            base_size *= 0.7
        elif market_volatility < 0.03:  # Baja volatilidad
            base_size *= 1.3
        
        # Límite máximo (15% del portafolio)
        max_size = balance * TRADING.MAX_PORTFOLIO_EXPOSURE
        
        return min(base_size, max_size)
    
    async def _check_balance(self, required_amount: float) -> bool:
        """Verificar balance suficiente"""
        balance = await self.wallet.get_usdc_balance()
        return balance >= required_amount + WALLET.MIN_USDC_BALANCE
    
    async def _execute_buy_order(
        self, 
        token_address: str, 
        amount: float, 
        price: float
    ) -> Tuple[bool, Optional[str], float]:
        """Ejecutar orden de compra en DEX"""
        try:
            # Obtener quote de Orca
            quote = await self.dex.get_quote(
                input_mint="USDC",
                output_mint=token_address,
                amount=amount * price,
                slippage=WALLET.MAX_SLIPPAGE
            )
            
            if not quote:
                return False, None, 0.0
            
            # Ejecutar swap
            tx_hash, fees = await self.dex.execute_swap(quote)
            
            if tx_hash:
                # Confirmar transacción
                confirmed = await self.dex.confirm_transaction(tx_hash)
                
                if confirmed:
                    return True, tx_hash, fees
            
            return False, None, 0.0
            
        except Exception as e:
            print(f"❌ Error ejecutando orden: {e}")
            return False, None, 0.0
    
    async def execute_exit(
        self, 
        trade_id: str, 
        exit_reason: ExitReason,
        exit_price: Optional[float] = None
    ) -> bool:
        """Ejecutar salida de una operación"""
        if trade_id not in self.active_trades:
            print(f"⚠️ Trade {trade_id} no encontrado")
            return False
        
        trade = self.active_trades[trade_id]
        
        # Obtener precio actual si no se proporciona
        if exit_price is None:
            exit_price = await self._get_current_price(trade.token_address)
        
        # Actualizar P&L
        trade.update_pnl(exit_price)
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.exit_reason = exit_reason
        trade.status = TradeStatus.CLOSED
        
        # Ejecutar orden de venta
        success, tx_hash, fees = await self._execute_sell_order(
            trade.token_address,
            trade.position_size_tokens,
            exit_price
        )
        
        if not success:
            print(f"❌ Error ejecutando salida para trade {trade_id}")
            trade.status = TradeStatus.STOPPED
            return False
        
        trade.fees_paid += fees
        
        # Actualizar estadísticas
        self._update_stats(trade)
        
        # Mover a historial
        self.trade_history.append(trade)
        del self.active_trades[trade_id]
        
        # Actualizar P&L diario
        self.daily_pnl += trade.pnl_percent
        
        # Guardar trade cerrado
        await self._save_trade(trade)
        
        print(f"✅ Salida ejecutada: {trade.token_symbol} | "
              f"Exit: ${exit_price:.4f} | "
              f"PNL: {trade.pnl_percent:+.2f}% (${trade.pnl_usd:+.2f}) | "
              f"Razón: {exit_reason.value}")
        
        return True
    
    async def _execute_sell_order(
        self, 
        token_address: str, 
        amount: float, 
        price: float
    ) -> Tuple[bool, Optional[str], float]:
        """Ejecutar orden de venta en DEX"""
        try:
            # Obtener quote de Orca
            quote = await self.dex.get_quote(
                input_mint=token_address,
                output_mint="USDC",
                amount=amount,
                slippage=WALLET.MAX_SLIPPAGE
            )
            
            if not quote:
                return False, None, 0.0
            
            # Ejecutar swap
            tx_hash, fees = await self.dex.execute_swap(quote)
            
            if tx_hash:
                # Confirmar transacción
                confirmed = await self.dex.confirm_transaction(tx_hash)
                
                if confirmed:
                    return True, tx_hash, fees
            
            return False, None, 0.0
            
        except Exception as e:
            print(f"❌ Error ejecutando orden de venta: {e}")
            return False, None, 0.0
    
    async def _monitor_trades(self):
        """Monitorear trades activos continuamente"""
        print("👁️ Iniciando monitoreo de trades...")
        
        while self.is_trading:
            try:
                for trade_id, trade in list(self.active_trades.items()):
                    # Obtener precio actual
                    current_price = await self._get_current_price(trade.token_address)
                    
                    if current_price is None:
                        continue
                    
                    # Actualizar P&L
                    trade.update_pnl(current_price)
                    
                    # Actualizar trailing stop
                    trade.update_trailing_stop(current_price)
                    
                    # Verificar si se debe salir
                    should_exit, exit_reason = trade.should_exit()
                    
                    if should_exit:
                        await self.execute_exit(trade_id, exit_reason, current_price)
                    
                    # Verificar condiciones especiales
                    await self._check_special_conditions(trade, current_price)
                
                # Esperar antes de siguiente verificación
                await asyncio.sleep(2)  # Cada 2 segundos
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Error en monitoreo: {e}")
                await asyncio.sleep(5)
    
    async def _check_special_conditions(self, trade: Trade, current_price: float):
        """Verificar condiciones especiales para salida"""
        # Salida de emergencia si baja 4% desde entrada
        emergency_threshold = trade.entry_price * 0.96
        if current_price <= emergency_threshold and trade.exit_reason is None:
            print(f"🚨 Emergencia: {trade.token_symbol} bajó 4% desde entrada")
            await self.execute_exit(trade.id, ExitReason.EMERGENCY, current_price)
        
        # Verificar soporte y resistencia
        support, resistance = await self._get_support_resistance(trade.token_address)
        
        if support and current_price <= support * 1.01:  # 1% sobre soporte
            # Si el precio toca soporte y no hay volumen, considerar salida
            volume = await self._get_volume(trade.token_address)
            if volume < trade.metadata.get('avg_volume', 0) * 0.5:
                print(f"⚠️ {trade.token_symbol} tocando soporte con bajo volumen")
    
    async def _get_current_price(self, token_address: str) -> Optional[float]:
        """Obtener precio actual de un token"""
        # Implementar llamada a API de precios
        try:
            # Esto es un ejemplo - implementar con API real
            return 1.0  # Precio simulado
        except:
            return None
    
    async def _get_support_resistance(self, token_address: str) -> Tuple[Optional[float], Optional[float]]:
        """Obtener niveles de soporte y resistencia"""
        # Implementar análisis técnico
        return None, None
    
    async def _get_volume(self, token_address: str) -> float:
        """Obtener volumen actual"""
        # Implementar llamada a API
        return 0.0
    
    async def _get_market_volatility(self) -> float:
        """Obtener volatilidad del mercado general"""
        # Implementar cálculo de volatilidad
        return 0.05
    
    def _update_stats(self, trade: Trade):
        """Actualizar estadísticas"""
        if trade.pnl_usd > 0:
            self.stats['winning_trades'] += 1
            self.stats['max_win'] = max(self.stats['max_win'], trade.pnl_usd)
        else:
            self.stats['losing_trades'] += 1
            self.stats['max_loss'] = min(self.stats['max_loss'], trade.pnl_usd)
        
        self.stats['total_pnl_usd'] += trade.pnl_usd
        self.stats['total_fees'] += trade.fees_paid
        
        # Tiempo promedio de holding
        holding_time = trade.exit_time - trade.entry_time
        total_trades = self.stats['winning_trades'] + self.stats['losing_trades']
        
        if total_trades == 1:
            self.stats['avg_holding_time'] = holding_time
        else:
            self.stats['avg_holding_time'] = (
                self.stats['avg_holding_time'] * (total_trades - 1) + holding_time
            ) / total_trades
    
    async def _close_all_positions(self):
        """Cerrar todas las posiciones abiertas"""
        print("🔒 Cerrando todas las posiciones abiertas...")
        
        for trade_id, trade in list(self.active_trades.items()):
            await self.execute_exit(trade_id, ExitReason.MANUAL)
    
    async def _load_active_trades(self):
        """Cargar trades activos desde base de datos"""
        # Implementar carga desde DB
        pass
    
    async def _save_trade(self, trade: Trade):
        """Guardar trade en base de datos"""
        # Implementar guardado en DB
        pass
    
    async def _save_state(self):
        """Guardar estado del trader"""
        # Implementar guardado de estado
        pass
    
    def get_performance_summary(self) -> Dict:
        """Obtener resumen de performance"""
        total_trades = self.stats['total_trades']
        winning_trades = self.stats['winning_trades']
        
        if total_trades > 0:
            win_rate = winning_trades / total_trades * 100
        else:
            win_rate = 0.0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': self.stats['losing_trades'],
            'win_rate': win_rate,
            'total_pnl_usd': self.stats['total_pnl_usd'],
            'total_fees': self.stats['total_fees'],
            'avg_pnl_per_trade': self.stats['total_pnl_usd'] / total_trades if total_trades > 0 else 0,
            'max_win': self.stats['max_win'],
            'max_loss': self.stats['max_loss'],
            'avg_holding_time': str(self.stats['avg_holding_time']),
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'active_trades': len(self.active_trades)
        }

# Ejemplo de uso
async def test_gradual_trader():
    """Función de prueba"""
    # Esto requeriría implementaciones de wallet_manager y dex_manager
    print("⚠️ Esta es una demostración - requiere implementaciones adicionales")

if __name__ == "__main__":
    asyncio.run(test_gradual_trader())