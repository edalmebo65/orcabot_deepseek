#!/usr/bin/env python3
"""
Orca Trading Bot - Integración completa con Bridge Rust
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

# Añadir directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from rust_bridge import orca_bridge
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('orca_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OrcaTradingBot:
    """Bot principal usando Bridge Rust"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self.load_config(config_path)
        self.solana_client = None
        self.running = False
        
        logger.info(f"Bot inicializado en modo: {orca_bridge.mode}")
        logger.info(f"Program ID: {orca_bridge.whirlpool_program_id}")
    
    def load_config(self, config_path: str) -> Dict:
        """Cargar configuración"""
        config_file = Path(config_path)
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Configuración por defecto
        default_config = {
            "rpc_url": "https://api.mainnet-beta.solana.com",
            "wallet_address": "",
            "private_key": "",  # Usar .env para esto
            "trading_enabled": False,
            "test_mode": True,
            "max_slippage_bps": 50,
            "monitored_pairs": [
                {"name": "SOL-USDC", "base": "SOL", "quote": "USDC"},
                {"name": "SOL-USDT", "base": "SOL", "quote": "USDT"},
                {"name": "ORCA-USDC", "base": "ORCA", "quote": "USDC"},
            ],
            "check_interval": 30,
            "min_profit_threshold": 0.001,  # 0.1%
        }
        
        config_file.parent.mkdir(exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    async def initialize(self):
        """Inicializar conexiones"""
        logger.info("Inicializando bot...")
        
        try:
            # Inicializar cliente Solana
            self.solana_client = AsyncClient(
                self.config["rpc_url"],
                commitment=Confirmed
            )
            
            # Verificar conexión
            version = await self.solana_client.get_version()
            logger.info(f"✅ Solana RPC conectado: {version}")
            
            # Cargar wallet si existe
            await self.load_wallet()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando: {e}")
            return False
    
    async def load_wallet(self):
        """Cargar wallet desde .env"""
        from dotenv import load_dotenv
        load_dotenv()
        
        private_key = os.getenv("PRIVATE_KEY")
        if private_key:
            # Configurar wallet
            from solders.keypair import Keypair
            import base58
            
            try:
                keypair_bytes = base58.b58decode(private_key)
                self.wallet = Keypair.from_bytes(keypair_bytes)
                logger.info(f"✅ Wallet cargada: {self.wallet.pubkey()}")
            except Exception as e:
                logger.error(f"Error cargando wallet: {e}")
                self.wallet = None
        else:
            logger.warning("⚠️  No hay PRIVATE_KEY en .env - Modo solo lectura")
            self.wallet = None
    
    async def get_market_data(self):
        """Obtener datos de mercado usando el bridge Rust"""
        logger.info("Obteniendo datos de mercado...")
        
        try:
            # Obtener pools de Orca
            pools = orca_bridge.get_all_pools()
            logger.info(f"📊 {len(pools)} pools disponibles")
            
            # Obtener whirlpools
            whirlpools = orca_bridge.get_whirlpools()
            logger.info(f"🌀 {len(whirlpools)} whirlpools disponibles")
            
            # Mostrar algunos pools importantes
            important_pools = ["SOL-USDC", "SOL-USDT", "ORCA-USDC"]
            for pool in pools[:5]:  # Mostrar primeros 5
                # Determinar símbolos
                token_a = pool.get("token_a", "")
                token_b = pool.get("token_b", "")
                
                # Identificar símbolos conocidos
                symbols = []
                for mint, sym in [
                    (orca_bridge.sol_mint, "SOL"),
                    (orca_bridge.usdc_mint, "USDC"),
                    (orca_bridge.usdt_mint, "USDT"),
                    (orca_bridge.orca_mint, "ORCA")
                ]:
                    if token_a == mint:
                        symbols.append(sym)
                    if token_b == mint:
                        symbols.append(sym)
                
                if len(symbols) == 2:
                    pair_name = f"{symbols[0]}-{symbols[1]}"
                    fee = pool.get("fee", 0)
                    logger.info(f"   {pair_name}: Fee={fee*100:.2f}%")
            
            return pools, whirlpools
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado: {e}")
            return [], []
    
    async def monitor_prices(self):
        """Monitorizar precios en tiempo real"""
        logger.info("Iniciando monitorización de precios...")
        
        while self.running:
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Para cada par monitoreado
                for pair in self.config["monitored_pairs"]:
                    base = pair["base"]
                    quote = pair["quote"]
                    
                    # Obtener mints
                    base_mint = getattr(orca_bridge, f"{base.lower()}_mint", "")
                    quote_mint = getattr(orca_bridge, f"{quote.lower()}_mint", "")
                    
                    if base_mint and quote_mint:
                        # Obtener cotización
                        quote_data = orca_bridge.get_swap_quote(
                            input_mint=base_mint,
                            output_mint=quote_mint,
                            amount=1000000000,  # 1 SOL o equivalente
                            slippage=0.5
                        )
                        
                        if quote_data:
                            in_amount = quote_data.get("in_amount", 0)
                            out_amount = quote_data.get("out_amount", 0)
                            
                            if in_amount > 0:
                                price = out_amount / in_amount
                                pair_name = f"{base}/{quote}"
                                logger.info(f"[{timestamp}] {pair_name}: {price:.4f}")
                
                # Esperar antes de la próxima verificación
                await asyncio.sleep(self.config["check_interval"])
                
            except KeyboardInterrupt:
                logger.info("Monitorización interrumpida por usuario")
                break
            except Exception as e:
                logger.error(f"Error en monitorización: {e}")
                await asyncio.sleep(10)
    
    async def check_arbitrage_opportunities(self):
        """Buscar oportunidades de arbitraje"""
        logger.info("Buscando oportunidades de arbitraje...")
        
        try:
            # Obtener todos los pools
            pools = orca_bridge.get_all_pools()
            
            # Para simplificar, buscar entre SOL-USDC y SOL-USDT
            sol_usdc_pool = None
            sol_usdt_pool = None
            
            for pool in pools:
                token_a = pool.get("token_a", "")
                token_b = pool.get("token_b", "")
                
                if token_a == orca_bridge.sol_mint and token_b == orca_bridge.usdc_mint:
                    sol_usdc_pool = pool
                elif token_a == orca_bridge.sol_mint and token_b == orca_bridge.usdt_mint:
                    sol_usdt_pool = pool
            
            if sol_usdc_pool and sol_usdt_pool:
                # Obtener precios
                quote_sol_usdc = orca_bridge.get_swap_quote(
                    orca_bridge.sol_mint, orca_bridge.usdc_mint, 1000000000, 0.5
                )
                quote_sol_usdt = orca_bridge.get_swap_quote(
                    orca_bridge.sol_mint, orca_bridge.usdt_mint, 1000000000, 0.5
                )
                
                if quote_sol_usdc and quote_sol_usdt:
                    price_sol_usdc = quote_sol_usdc.get("out_amount", 0) / 1000000000
                    price_sol_usdt = quote_sol_usdt.get("out_amount", 0) / 1000000000
                    
                    # Calcular diferencia
                    if price_sol_usdc > 0 and price_sol_usdt > 0:
                        diff_pct = abs(price_sol_usdc - price_sol_usdt) / max(price_sol_usdc, price_sol_usdt)
                        
                        if diff_pct > 0.01:  # 1% de diferencia
                            logger.info(f"⚡ Oportunidad de arbitraje detectada!")
                            logger.info(f"   SOL/USDC: {price_sol_usdc:.2f}")
                            logger.info(f"   SOL/USDT: {price_sol_usdt:.2f}")
                            logger.info(f"   Diferencia: {diff_pct*100:.2f}%")
            
        except Exception as e:
            logger.error(f"Error buscando arbitraje: {e}")
    
    async def run_strategies(self):
        """Ejecutar estrategias de trading"""
        if not self.config.get("trading_enabled", False):
            logger.info("🚫 Trading deshabilitado en configuración")
            return
        
        logger.info("Ejecutando estrategias...")
        
        # Ejemplo: Estrategia simple de market making
        # En producción, implementarías estrategias más sofisticadas
        
        await self.check_arbitrage_opportunities()
    
    async def run(self):
        """Ejecutar bot principal"""
        logger.info("=" * 60)
        logger.info("🚀 ORCA TRADING BOT - BRIDGE RUST")
        logger.info("=" * 60)
        
        # Inicializar
        if not await self.initialize():
            logger.error("No se pudo inicializar el bot")
            return
        
        # Obtener datos iniciales
        await self.get_market_data()
        
        # Mostrar balance si hay wallet
        if hasattr(self, 'wallet') and self.wallet:
            balance = orca_bridge.get_balance(str(self.wallet.pubkey()))
            if balance:
                sol_balance = balance / 1_000_000_000
                logger.info(f"💰 Balance inicial: {sol_balance:.4f} SOL")
        
        # Iniciar monitorización
        self.running = True
        
        try:
            # Ejecutar en loop
            while self.running:
                # Ejecutar estrategias
                await self.run_strategies()
                
                # Monitorizar precios (en paralelo)
                monitor_task = asyncio.create_task(self.monitor_prices())
                
                # Esperar un ciclo
                await asyncio.sleep(self.config["check_interval"] * 3)
                
                # Cancelar monitorización para reiniciar
                monitor_task.cancel()
                
        except KeyboardInterrupt:
            logger.info("\n👋 Bot detenido por usuario")
        except Exception as e:
            logger.error(f"Error en ejecución principal: {e}")
        finally:
            self.running = False
            if self.solana_client:
                await self.solana_client.close()
            logger.info("Bot finalizado")

async def main():
    """Punto de entrada"""
    bot = OrcaTradingBot()
    
    try:
        await bot.run()
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    asyncio.run(main())