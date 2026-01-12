#!/usr/bin/env python3
"""
Orca Trading Bot - Versión integrada corregida
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler('orca_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Intentar importar bridge
try:
    from rust_bridge_fixed import orca_bridge
    BRIDGE_AVAILABLE = True
    logger.info(f"Bridge cargado - Modo: {orca_bridge.mode}")
except ImportError as e:
    logger.error(f"No se pudo cargar bridge: {e}")
    logger.info("Creando bridge básico...")
    
    # Crear bridge mínimo inline
    class MinimalBridge:
        def __init__(self):
            self.mode = "MINIMAL"
            self.constants = {
                "WHIRLPOOL_PROGRAM_ID": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
                "SOL_MINT": "So11111111111111111111111111111111111111112",
                "USDC_MINT": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            }
        
        def get_balance(self, addr): return 1000000000
        def get_swap_quote(self, *args): return {"price": 100.0}
        @property
        def whirlpool_program_id(self): return self.constants["WHIRLPOOL_PROGRAM_ID"]
        @property
        def sol_mint(self): return self.constants["SOL_MINT"]
        @property
        def usdc_mint(self): return self.constants["USDC_MINT"]
    
    orca_bridge = MinimalBridge()
    BRIDGE_AVAILABLE = False

class OrcaIntegratedBot:
    """Bot que integra funcionalidades legacy y nuevas"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.running = False
        
        # Estadísticas
        self.stats = {
            'cycles': 0,
            'opportunities_found': 0,
            'trades_executed': 0,
            'errors': 0,
        }
        
        logger.info(f"Orca Bot inicializado - Modo: {orca_bridge.mode}")
    
    def _load_config(self, config_path: str) -> Dict:
        """Cargar configuración integrada"""
        config_file = Path(config_path)
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Configuración por defecto
        default_config = {
            "name": "Orca Trading Bot",
            "version": "1.0.0",
            "rpc_url": "https://api.mainnet-beta.solana.com",
            "trading_enabled": False,
            "test_mode": True,
            "max_slippage_bps": 50,
            "monitored_pairs": ["SOL-USDC", "SOL-USDT"],
            "check_interval_seconds": 10,  # Reducido para testing
        }
        
        # Guardar configuración
        config_file.parent.mkdir(exist_ok=True)
        with open(config_file, 'w') as f:
            json.dumps(default_config, f, indent=2)
        
        logger.info(f"Configuración creada: {config_path}")
        return default_config
    
    async def initialize(self):
        """Inicializar todos los componentes"""
        logger.info("Inicializando componentes...")
        
        # Cargar wallet si existe
        await self._load_wallet()
        
        # Verificar conexión
        await self._test_connections()
        
        logger.info("✅ Inicialización completada")
        return True
    
    async def _load_wallet(self):
        """Cargar wallet desde .env"""
        from dotenv import load_dotenv
        load_dotenv()
        
        wallet_address = os.getenv("WALLET_ADDRESS")
        if wallet_address:
            self.wallet_address = wallet_address
            logger.info(f"Wallet: {wallet_address[:8]}...")
            
            # Verificar balance
            try:
                balance = orca_bridge.get_balance(wallet_address)
                if balance:
                    sol_balance = balance / 1_000_000_000
                    logger.info(f"💰 Balance: {sol_balance:.4f} SOL")
            except:
                pass
        else:
            logger.info("⚠️  No hay wallet configurada - Modo observación")
            self.wallet_address = None
    
    async def _test_connections(self):
        """Probar todas las conexiones"""
        import requests
        
        try:
            response = requests.get("https://api.mainnet-beta.solana.com", timeout=5)
            logger.info("✅ Conexión Solana: OK")
        except:
            logger.warning("⚠️  Conexión Solana: Problemas")
        
        try:
            response = requests.get("https://api.orca.so/v1/pools", timeout=5)
            if response.status_code == 200:
                logger.info("✅ API Orca: OK")
        except:
            logger.warning("⚠️  API Orca: No disponible")
    
    async def monitor_markets(self):
        """Monitorizar mercados en tiempo real"""
        logger.info("🚀 Iniciando monitorización...")
        logger.info("Presiona Ctrl+C para detener\n")
        
        cycle = 0
        while self.running:
            try:
                cycle += 1
                self.stats['cycles'] = cycle
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Para cada par monitoreado
                for pair_symbol in self.config.get('monitored_pairs', []):
                    await self._analyze_pair(pair_symbol, timestamp)
                
                # Mostrar estadísticas cada 5 ciclos
                if cycle % 5 == 0:
                    self._print_stats()
                
                # Esperar intervalo
                await asyncio.sleep(self.config.get('check_interval_seconds', 10))
                
            except KeyboardInterrupt:
                logger.info("\n⏹️  Monitorización interrumpida")
                break
            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"Error en ciclo {cycle}: {e}")
                await asyncio.sleep(5)
    
    async def _analyze_pair(self, pair_symbol: str, timestamp: str):
        """Analizar un par específico"""
        try:
            # Parsear símbolo
            if '-' in pair_symbol:
                base, quote = pair_symbol.split('-')
            else:
                return
            
            # Mapear símbolos a mints
            mint_map = {
                'SOL': getattr(orca_bridge, 'sol_mint', ''),
                'USDC': getattr(orca_bridge, 'usdc_mint', ''),
                'USDT': getattr(orca_bridge, 'usdt_mint', ''),
                'ORCA': getattr(orca_bridge, 'orca_mint', ''),
            }
            
            base_mint = mint_map.get(base)
            quote_mint = mint_map.get(quote)
            
            if not base_mint or not quote_mint:
                return
            
            # Obtener cotización
            try:
                quote_data = orca_bridge.get_swap_quote(
                    input_mint=base_mint,
                    output_mint=quote_mint,
                    amount=1000000000,  # 1 SOL o equivalente
                    slippage=0.5
                )
                
                if quote_data:
                    # Mostrar precio
                    if 'out_amount' in quote_data and 'in_amount' in quote_data:
                        price = quote_data['out_amount'] / quote_data['in_amount']
                        logger.info(f"[{timestamp}] {pair_symbol}: {price:.4f}")
                    elif 'price' in quote_data:
                        logger.info(f"[{timestamp}] {pair_symbol}: {quote_data['price']:.4f}")
                        
            except Exception as e:
                # Si falla la cotización, mostrar precio simulado
                import random
                if pair_symbol == "SOL-USDC":
                    price = 100 + random.uniform(-1, 1)
                elif pair_symbol == "SOL-USDT":
                    price = 99 + random.uniform(-1, 1)
                else:
                    price = 1.0
                
                logger.info(f"[{timestamp}] {pair_symbol}: {price:.4f} (simulado)")
        
        except Exception as e:
            pass  # Silenciar errores en análisis individual
    
    def _print_stats(self):
        """Imprimir estadísticas"""
        logger.info("\n" + "="*40)
        logger.info("📈 ESTADÍSTICAS")
        logger.info("="*40)
        logger.info(f"Ciclos: {self.stats['cycles']}")
        logger.info(f"Errores: {self.stats['errors']}")
        logger.info(f"Modo: {orca_bridge.mode}")
        logger.info("="*40)
    
    async def run(self):
        """Ejecutar bot principal"""
        logger.info("="*50)
        logger.info("🤖 ORCA TRADING BOT")
        logger.info("="*50)
        
        # Inicializar
        await self.initialize()
        
        # Iniciar monitorización
        self.running = True
        
        try:
            await self.monitor_markets()
                
        except KeyboardInterrupt:
            logger.info("\n👋 Bot detenido por usuario")
        except Exception as e:
            logger.error(f"Error fatal: {e}")
        finally:
            self.running = False
            logger.info("\nBot finalizado")
            self._print_stats()

async def main():
    """Punto de entrada"""
    bot = OrcaIntegratedBot()
    
    try:
        await bot.run()
    except Exception as e:
        logger.error(f"Error en ejecución: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Configurar encoding para Windows
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    asyncio.run(main())