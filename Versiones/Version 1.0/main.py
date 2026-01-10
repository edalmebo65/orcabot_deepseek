# main.py
import asyncio
import signal
import sys
from contextlib import AsyncExitStack
from typing import Dict, Any

from config import CONFIG
from core.blockchain.whirlpool_scanner import WhirlpoolScanner
from core.ml.lstm_model import MLPipeline
from core.trading.strategy_engine import StrategyEngine
from communication.telegram_bot import TradingTelegramBot
from security.anomaly_detector import AnomalyDetector
from utils.error_handler import ErrorHandler
from utils.data_storage import HistoricalDataStorage

class OrcaBot:
    def __init__(self):
        self.config = CONFIG
        self.error_handler = ErrorHandler(self.config.LOGS_DIR)
        self.data_storage = HistoricalDataStorage(self.config.HISTORICO_DIR)
        
        # Inicializar componentes
        self.whirlpool_scanner = WhirlpoolScanner(self.config.RPC_FULL_URL)
        self.ml_pipeline = MLPipeline(self.config.HISTORICO_DIR / "models")
        self.anomaly_detector = AnomalyDetector()
        
        # Engine principal
        self.strategy_engine = StrategyEngine(
            config=self.config,
            whirlpool_scanner=self.whirlpool_scanner,
            ml_pipeline=self.ml_pipeline,
            anomaly_detector=self.anomaly_detector,
            data_storage=self.data_storage
        )
        
        # Bot de Telegram
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if telegram_token:
            self.telegram_bot = TradingTelegramBot(
                token=telegram_token,
                trading_engine=self.strategy_engine
            )
        
        self.is_running = False
        
    async def start(self):
        """Inicia el bot con manejo de errores"""
        try:
            self.is_running = True
            
            # Configurar señales de terminación
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda: asyncio.create_task(self.shutdown())
                )
            
            # Iniciar componentes
            await self.strategy_engine.initialize()
            
            # Iniciar bot de Telegram
            if hasattr(self, 'telegram_bot'):
                await self.telegram_bot.app.initialize()
                await self.telegram_bot.app.start()
                await self.telegram_bot.app.updater.start_polling()
            
            # Bucle principal
            await self.main_loop()
            
        except Exception as e:
            self.error_handler.log_error(e, {"module": "main", "function": "start"})
            await self.shutdown()
    
    async def main_loop(self):
        """Bucle principal de trading"""
        while self.is_running:
            try:
                # 1. Escanear whirlpools
                top_pools = await self.whirlpool_scanner.scan_top_pools(limit=10)
                
                # 2. Analizar cada pool con ML
                for pool in top_pools:
                    await self.analyze_and_trade(pool)
                
                # 3. Esperar para siguiente ciclo
                await asyncio.sleep(60)  # 1 minuto entre ciclos
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error_handler.log_error(e, {"module": "main", "function": "main_loop"})
                await asyncio.sleep(10)  # Esperar antes de reintentar
    
    async def analyze_and_trade(self, pool_data: Dict[str, Any]):
        """Analiza y ejecuta trading en un pool"""
        try:
            # 1. Obtener datos históricos
            historical_data = self.data_storage.load_training_data(
                symbol=f"{pool_data['token_a']}_{pool_data['token_b']}",
                lookback_days=30
            )
            
            # 2. Predecir con ML
            ml_prediction = await self.ml_pipeline.predict(historical_data)
            
            # 3. Verificar anomalías
            anomalies = await self.anomaly_detector.detect_market_anomalies(pool_data)
            
            if not anomalies:  # Solo operar si no hay anomalías
                # 4. Ejecutar estrategia
                trade_signal = self.strategy_engine.analyze_signal(
                    pool_data=pool_data,
                    ml_prediction=ml_prediction
                )
                
                if trade_signal.should_trade:
                    # 5. Ejecutar trade con gestión de riesgo
                    await self.strategy_engine.execute_trade(
                        pool_data=pool_data,
                        signal=trade_signal
                    )
        
        except Exception as e:
            self.error_handler.log_error(e, {
                "module": "main", 
                "function": "analyze_and_trade",
                "pool": pool_data.get('address')
            })
    
    async def shutdown(self):
        """Apagado controlado"""
        self.is_running = False
        
        try:
            # Cerrar todas las posiciones abiertas
            await self.strategy_engine.close_all_positions()
            
            # Guardar estado
            await self.strategy_engine.save_state()
            
            # Detener bot de Telegram
            if hasattr(self, 'telegram_bot'):
                await self.telegram_bot.app.stop()
            
            # Log shutdown
            self.config.LOGGER.info("Bot shutdown completed")
            
        except Exception as e:
            self.error_handler.log_error(e, {"module": "main", "function": "shutdown"})
        
        finally:
            sys.exit(0)

if __name__ == "__main__":
    bot = OrcaBot()
    
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        bot.config.LOGGER.info("Bot stopped by user")
    except Exception as e:
        bot.error_handler.log_error(e, {"module": "__main__"}, severity="FATAL")