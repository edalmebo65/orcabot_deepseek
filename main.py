# main.py
import asyncio
import signal
import sys
from datetime import datetime, timedelta
from decimal import Decimal
import json
from typing import Dict, List

from config import CONFIG, Timeframe
from core.blockchain.wallet_manager import WalletManager
from core.blockchain.whirlpool_scanner import WhirlpoolScanner
from core.blockchain.orca_integration import OrcaIntegration
from core.trading.capital_manager import CapitalManager
from core.ml_engine.lstm_predictor import LSTMPredictor
from communication.telegram_bridge import TelegramBridge
from utils.performance_monitor import PerformanceMonitor

class OrcaMultiOperationBot:
    """Bot principal con capacidad multi-operación"""
    
    def __init__(self):
        self.config = CONFIG
        self.config.load_state()
        
        # Inicializar componentes
        self.wallet_manager = WalletManager(self.config)
        self.whirlpool_scanner = WhirlpoolScanner(self.config, None)  # Client se setea después
        self.capital_manager = CapitalManager(self.config)
        self.ml_predictor = LSTMPredictor(self.config)
        self.performance_monitor = PerformanceMonitor(self.config)
        
        # Telegram (opcional)
        if self.config.TELEGRAM_BOT_TOKEN and self.config.TELEGRAM_BOT_TOKEN != "optional":
            self.telegram = TelegramBridge(self.config)
        else:
            self.telegram = None
        
        # Estado del bot
        self.is_running = False
        self.current_cycle = 0
        self.last_balance_check = None
        self.top_assets_cache = {}
        
        # Estadísticas
        self.stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_pnl_usdc": Decimal('0'),
            "start_time": datetime.now().isoformat()
        }
    
    async def initialize(self):
        """Inicializa todos los componentes"""
        try:
            self.config.logger.info("🚀 Inicializando Orca Multi-Operation Bot...")
            
            # 1. Conectar a blockchain
            await self.wallet_manager.connect()
            self.whirlpool_scanner.client = self.wallet_manager.client
            
            # 2. Inicializar Orca integration
            self.orca_integration = OrcaIntegration(self.config, self.wallet_manager)
            
            # 3. Verificar saldos iniciales
            await self._check_initial_balances()
            
            # 4. Inicializar Telegram si está configurado
            if self.telegram:
                await self.telegram.initialize()
                await self.telegram.send_message(
                    f"🤖 *Orca Bot Iniciado*\n"
                    f"Wallet: `{self.config.PHANTOM_WALLET[:8]}...`\n"
                    f"Capital inicial: ${self.config.current_capital_usdc:.2f}\n"
                    f"Límite por operación: {self.config.trading.capital.max_capital_per_trade_pct*100}%"
                )
            
            # 5. Cargar modelo ML si existe
            self.config.logger.info("✅ Bot inicializado exitosamente")
            
            return True
            
        except Exception as e:
            self.config.logger.error(f"❌ Error inicializando bot: {e}")
            return False
    
    async def _check_initial_balances(self):
        """Verifica saldos iniciales y actualiza capital"""
        try:
            balances = await self.wallet_manager.get_wallet_balances()
            
            # Asumimos que el capital principal está en USDC
            # En implementación real, buscaríamos el balance de USDC
            usdc_balance = balances.get('USDC', Decimal('0'))
            
            if usdc_balance == Decimal('0'):
                self.config.logger.warning("Balance USDC es 0. Usando SOL como referencia.")
                sol_balance = balances.get('SOL', Decimal('0'))
                # Convertir SOL a USDC usando precio actual
                # Esto requiere integración con oráculo de precios
                usdc_balance = sol_balance * Decimal('100')  # Placeholder: 1 SOL = $100
            
            self.config.update_capital(usdc_balance)
            
            self.config.logger.info(
                f"💰 Capital inicial: ${self.config.current_capital_usdc:.2f} "
                f"(Máx por operación: ${self.config.get_max_trade_amount_usdc():.2f})"
            )
            
        except Exception as e:
            self.config.logger.error(f"Error verificando balances: {e}")
    
    async def run_trading_cycle(self):
        """Ejecuta un ciclo completo de trading"""
        self.current_cycle += 1
        self.config.logger.info(f"🔄 Ciclo {self.current_cycle} iniciado")
        
        try:
            # 1. Verificar saldos y viabilidad
            viability, message = await self._check_operation_viability()
            if not viability:
                self.config.logger.info(f"⏸️  Ciclo pausado: {message}")
                return
            
            # 2. Obtener top 20 activos por timeframe
            top_assets = await self._get_top_assets_for_timeframes()
            if not top_assets:
                self.config.logger.info("⏸️  No hay activos adecuados para trading")
                return
            
            # 3. Analizar con ML y calcular probabilidades
            assets_with_probabilities = await self._analyze_assets_with_ml(top_assets)
            
            # 4. Seleccionar mejor operación disponible
            best_operation = await self._select_best_operation(assets_with_probabilities)
            if not best_operation:
                self.config.logger.info("⏸️  No se encontró operación con probabilidad suficiente")
                return
            
            # 5. Ejecutar operación
            await self._execute_operation(best_operation)
            
            # 6. Verificar y gestionar operaciones existentes
            await self._manage_existing_operations()
            
            # 7. Reportar estado
            await self._report_status()
            
        except Exception as e:
            self.config.logger.error(f"❌ Error en ciclo de trading: {e}")
            if self.telegram:
                await self.telegram.send_message(
                    f"🚨 *Error en ciclo de trading*\n```{str(e)[:200]}...```"
                )
    
    async def _check_operation_viability(self) -> tuple[bool, str]:
        """Verifica si se puede operar"""
        # 1. Verificar capital mínimo
        min_capital = Decimal('100')  # $100 mínimo
        if self.config.current_capital_usdc < min_capital:
            return False, f"Capital insuficiente: ${self.config.current_capital_usdc:.2f}"
        
        # 2. Verificar operaciones simultáneas máximas
        if self.config.active_operations >= self.config.trading.capital.max_concurrent_operations:
            return False, f"Máximo de {self.config.trading.capital.max_concurrent_operations} operaciones activas"
        
        # 3. Verificar capital disponible para trading
        available_capital = self.capital_manager.get_available_capital_for_trading()
        min_trade_size = self.config.get_max_trade_amount_usdc() * Decimal('0.1')  # 10% del máximo
        
        if available_capital < min_trade_size:
            return False, f"Capital disponible insuficiente: ${available_capital:.2f}"
        
        return True, "✅ Puede operar"
    
    async def _get_top_assets_for_timeframes(self) -> Dict[str, List[Dict]]:
        """Obtiene top 20 activos por timeframe"""
        top_assets = {}
        
        for timeframe in self.config.trading.active_timeframes:
            try:
                # Usar cache para evitar llamadas repetidas
                cache_key = f"{timeframe}_{datetime.now().strftime('%Y%m%d%H')}"
                
                if cache_key in self.top_assets_cache:
                    assets = self.top_assets_cache[cache_key]
                else:
                    assets = await self.whirlpool_scanner.scan_top_pools(
                        timeframe=timeframe,
                        limit=20
                    )
                    self.top_assets_cache[cache_key] = assets
                
                top_assets[timeframe] = assets
                
                self.config.logger.debug(
                    f"📊 Timeframe {timeframe}: {len(assets)} activos encontrados"
                )
                
            except Exception as e:
                self.config.logger.error(f"Error obteniendo activos para {timeframe}: {e}")
                top_assets[timeframe] = []
        
        return top_assets
    
    async def _analyze_assets_with_ml(self, top_assets: Dict) -> List[Dict]:
        """Analiza activos con modelo ML"""
        assets_with_probs = []
        
        for timeframe, assets in top_assets.items():
            for asset in assets[:5]:  # Analizar solo top 5 por timeframe
                try:
                    # Obtener datos históricos
                    historical_data = await self._get_asset_historical_data(
                        asset['address'],
                        timeframe
                    )
                    
                    if historical_data.empty:
                        continue
                    
                    # Predecir probabilidad
                    prediction = self.ml_predictor.predict_probabilities({
                        timeframe: historical_data
                    })
                    
                    if prediction.get('model_used'):
                        asset_data = {
                            'asset': asset,
                            'timeframe': timeframe,
                            'buy_probability': prediction['buy_probability'],
                            'confidence': prediction['confidence'],
                            'timeframe_scores': prediction['timeframe_scores'],
                            'current_price': asset.get('price', 0),
                            'liquidity': asset.get('liquidity', 0),
                            'volume_24h': asset.get('volume_24h', 0)
                        }
                        
                        assets_with_probs.append(asset_data)
                        
                except Exception as e:
                    self.config.logger.error(f"Error analizando asset {asset.get('address', 'unknown')}: {e}")
        
        # Ordenar por probabilidad * confianza
        assets_with_probs.sort(
            key=lambda x: x['buy_probability'] * x['confidence'],
            reverse=True
        )
        
        return assets_with_probs
    
    async def _select_best_operation(self, assets_with_probs: List[Dict]) -> Optional[Dict]:
        """Selecciona la mejor operación disponible"""
        for asset_data in assets_with_probs:
            try:
                # Verificar umbral mínimo de confianza
                if asset_data['buy_probability'] < self.config.ml_confidence_threshold:
                    continue
                
                # Verificar liquidez suficiente
                min_liquidity = self.config.trading.min_pool_liquidity_usd
                if asset_data['liquidity'] < min_liquidity:
                    continue
                
                # Verificar volumen suficiente para el timeframe
                timeframe = asset_data['timeframe']
                min_volume = self.config.trading.min_volume_requirement_usd.get(timeframe, Decimal('10000'))
                if asset_data['volume_24h'] < min_volume:
                    continue
                
                # Calcular tamaño de posición
                position_size, calc_details = self.capital_manager.calculate_position_size(
                    asset_price=Decimal(str(asset_data['current_price'])),
                    confidence_score=asset_data['confidence']
                )
                
                if position_size == Decimal('0'):
                    continue
                
                # Verificar si se puede abrir operación
                can_open, message, position_details = self.capital_manager.can_open_operation(
                    asset_pair=f"{asset_data['asset']['token_a_symbol']}/{asset_data['asset']['token_b_symbol']}",
                    estimated_cost_usdc=position_size,
                    confidence_score=asset_data['confidence']
                )
                
                if can_open:
                    operation_data = {
                        **asset_data,
                        'position_size_usdc': float(position_size),
                        'calculation_details': calc_details,
                        'can_open_message': message
                    }
                    return operation_data
                
            except Exception as e:
                self.config.logger.error(f"Error evaluando operación: {e}")
        
        return None
    
    async def _execute_operation(self, operation_data: Dict):
        """Ejecuta una operación"""
        try:
            self.config.logger.info(
                f"🎯 Ejecutando operación: {operation_data['asset']['token_a_symbol']}/"
                f"{operation_data['asset']['token_b_symbol']} - "
                f"Prob: {operation_data['buy_probability']:.2%} - "
                f"Conf: {operation_data['confidence']:.2%} - "
                f"Tamaño: ${operation_data['position_size_usdc']:.2f}"
            )
            
            # 1. Obtener precio actual exacto
            current_price = await self._get_exact_price(operation_data['asset'])
            
            # 2. Crear ID único para la operación
            operation_id = f"op_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{operation_data['asset']['token_a_symbol']}"
            
            # 3. Abrir operación en el capital manager
            operation = self.capital_manager.open_operation(
                operation_id=operation_id,
                asset_pair=f"{operation_data['asset']['token_a_symbol']}/{operation_data['asset']['token_b_symbol']}",
                entry_price=Decimal(str(current_price)),
                position_size_usdc=Decimal(str(operation_data['position_size_usdc']))
            )
            
            # 4. Ejecutar swap en blockchain
            success, message, tx_details = await self.orca_integration.execute_swap(
                input_mint=operation_data['asset']['token_b'],  # USDC
                output_mint=operation_data['asset']['token_a'],  # Token a comprar
                amount=operation.position_size_usdc
            )
            
            if success:
                # 5. Actualizar operación con detalles de transacción
                operation.tx_signature = tx_details['signature']
                
                # 6. Notificar por Telegram
                if self.telegram:
                    await self.telegram.send_message(
                        f"✅ *Operación Ejecutada*\n"
                        f"Par: `{operation.asset_pair}`\n"
                        f"Tamaño: `${operation.position_size_usdc:.2f}`\n"
                        f"Precio entrada: `${operation.entry_price:.4f}`\n"
                        f"Stop Loss: `${operation.stop_loss_price:.4f}`\n"
                        f"Take Profit: `${operation.take_profit_price:.4f}`\n"
                        f"Riesgo cero: `${operation.risk_zero_price:.4f}`\n"
                        f"TX: `{tx_details['signature'][:20]}...`"
                    )
                
                self.config.logger.info(f"✅ Operación {operation_id} ejecutada exitosamente")
                self.stats["total_operations"] += 1
                
            else:
                self.config.logger.error(f"❌ Error ejecutando operación: {message}")
                # Revertir operación en el capital manager
                self.capital_manager.operations.pop(operation_id, None)
                self.config.decrement_active_operations()
                
        except Exception as e:
            self.config.logger.error(f"❌ Error en ejecución de operación: {e}")
    
    async def _manage_existing_operations(self):
        """Gestiona operaciones existentes (SL, TP, trailing)"""
        for operation_id, operation in list(self.capital_manager.operations.items()):
            if operation.status != "ACTIVE":
                continue
            
            try:
                # Obtener precio actual
                current_price = await self._get_asset_current_price(operation.asset_pair)
                
                # Verificar triggers
                triggers = self.capital_manager.check_operation_triggers(
                    operation_id, 
                    Decimal(str(current_price))
                )
                
                for trigger in triggers:
                    if trigger['action'] == 'CLOSE':
                        # Ejecutar cierre
                        success, message, tx_details = await self._close_operation(
                            operation, 
                            trigger['type']
                        )
                        
                        if success:
                            self.config.logger.info(
                                f"🔒 Operación {operation_id} cerrada: {trigger['reason']}"
                            )
                            
                            # Actualizar estadísticas
                            if "PROFIT" in trigger['type']:
                                self.stats["successful_operations"] += 1
                            else:
                                self.stats["failed_operations"] += 1
                            
                            # Notificar por Telegram
                            if self.telegram:
                                await self.telegram.send_message(
                                    f"🔒 *Operación Cerrada*\n"
                                    f"Par: `{operation.asset_pair}`\n"
                                    f"Razón: {trigger['reason']}\n"
                                    f"P&L: `{operation.current_pnl_pct:.2f}%`\n"
                                    f"TX: `{tx_details['signature'][:20]}...`"
                                )
                    
                    elif trigger['action'] == 'UPDATE':
                        # Solo actualizar (trailing stop activado)
                        self.config.logger.info(
                            f"📊 Operación {operation_id}: {trigger['reason']}"
                        )
                
            except Exception as e:
                self.config.logger.error(f"Error gestionando operación {operation_id}: {e}")
    
    async def _close_operation(self, operation: Operation, close_reason: str) -> tuple:
        """Cierra una operación"""
        # Obtener precio actual para el cierre
        current_price = await self._get_asset_current_price(operation.asset_pair)
        
        # Ejecutar swap inverso
        # (Implementar lógica específica basada en la operación)
        
        # Por ahora, placeholder
        success = True
        message = "Operación cerrada"
        tx_details = {"signature": "placeholder"}
        
        # Registrar cierre en capital manager
        close_details = self.capital_manager.close_operation(
            operation.id,
            Decimal(str(current_price)),
            close_reason
        )
        
        # Actualizar P&L total
        self.stats["total_pnl_usdc"] += Decimal(str(close_details.get('pnl_usdc', 0)))
        
        return success, message, tx_details
    
    async def _report_status(self):
        """Reporta estado actual del bot"""
        status_report = {
            "cycle": self.current_cycle,
            "timestamp": datetime.now().isoformat(),
            "capital_usdc": float(self.config.current_capital_usdc),
            "active_operations": self.config.active_operations,
            "available_capital": float(self.capital_manager.get_available_capital_for_trading()),
            "max_trade_amount": float(self.config.get_max_trade_amount_usdc()),
            "stats": {
                **self.stats,
                "total_pnl_usdc": float(self.stats["total_pnl_usdc"])
            }
        }
        
        # Guardar reporte
        report_file = self.config.base_dir / "reports" / f"status_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(report_file, 'w') as f:
            json.dump(status_report, f, indent=2)
        
        # Loggear resumen
        self.config.logger.info(
            f"📊 Estado: ${self.config.current_capital_usdc:.2f} capital | "
            f"{self.config.active_operations}/{self.config.trading.capital.max_concurrent_operations} ops | "
            f"P&L total: ${self.stats['total_pnl_usdc']:.2f}"
        )
    
    async def _get_asset_historical_data(self, pool_address: str, timeframe: str):
        """Obtiene datos históricos de un pool (placeholder)"""
        # Implementar con API de Orca o fuente de datos históricos
        import pandas as pd
        return pd.DataFrame()  # Placeholder
    
    async def _get_exact_price(self, asset_data: Dict) -> float:
        """Obtiene precio exacto actual (placeholder)"""
        # Implementar con Orca/Jupiter API
        return asset_data.get('price', 0)
    
    async def _get_asset_current_price(self, asset_pair: str) -> float:
        """Obtiene precio actual de un asset pair (placeholder)"""
        # Implementar con API de precios
        return 100.0  # Placeholder
    
    async def run(self):
        """Bucle principal del bot"""
        self.is_running = True
        self.config.logger.info("🤖 Bot iniciado. Presiona Ctrl+C para detener.")
        
        # Configurar manejo de señales
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.shutdown())
            )
        
        try:
            while self.is_running:
                # Ejecutar ciclo de trading
                await self.run_trading_cycle()
                
                # Esperar antes del siguiente ciclo
                # Tiempo basado en el timeframe más corto
                shortest_timeframe = min(
                    self.config.trading.active_timeframes,
                    key=lambda x: int(x.replace('m', '').replace('h', '00'))
                )
                
                wait_seconds = {
                    '1m': 60,
                    '5m': 300,
                    '15m': 900,
                    '1h': 3600
                }.get(shortest_timeframe, 60)
                
                await asyncio.sleep(wait_seconds)
                
        except Exception as e:
            self.config.logger.error(f"❌ Error en bucle principal: {e}")
            await self.shutdown()
    
    async def shutdown(self):
        """Apagado controlado del bot"""
        self.config.logger.info("🛑 Apagando bot...")
        self.is_running = False
        
        # Cerrar todas las operaciones activas
        for operation_id, operation in list(self.capital_manager.operations.items()):
            if operation.status == "ACTIVE":
                await self._close_operation(operation, "SHUTDOWN")
        
        # Guardar estado final
        self.config._save_state()
        self.capital_manager.save_operations()
        
        # Notificar por Telegram
        if self.telegram:
            await self.telegram.send_message(
                f"🛑 *Bot Detenido*\n"
                f"Operaciones totales: {self.stats['total_operations']}\n"
                f"Exitosa: {self.stats['successful_operations']}\n"
                f"Fallidas: {self.stats['failed_operations']}\n"
                f"P&L total: ${self.stats['total_pnl_usdc']:.2f}"
            )
            await self.telegram.shutdown()
        
        self.config.logger.info("👋 Bot detenido exitosamente")
        sys.exit(0)

async def main():
    """Función principal"""
    bot = OrcaMultiOperationBot()
    
    # Inicializar
    if not await bot.initialize():
        print("❌ No se pudo inicializar el bot")
        sys.exit(1)
    
    # Ejecutar
    try:
        await bot.run()
    except KeyboardInterrupt:
        await bot.shutdown()

if __name__ == "__main__":
    asyncio.run(main())