#!/usr/bin/env python3
"""
Orca Trading Bot - Python + Rust
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from rust_bridge import get_orca_bridge
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

class OrcaTradingBot:
    def __init__(self, config_path: str = "config/config.json"):
        self.config = self.load_config(config_path)
        self.rust_bridge = get_orca_bridge()
        
        # Inicializar cliente Solana
        self.solana_client = AsyncClient(self.config["rpc_url"])
        
        print(f"🔧 Modo: {self.rust_bridge.mode}")
        print(f"🌐 RPC: {self.config['rpc_url']}")
        print(f"🔄 Program ID: {self.rust_bridge.whirlpool_program_id}")
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Cargar configuración"""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Configuración por defecto
        default_config = {
            "rpc_url": "https://api.mainnet-beta.solana.com",
            "wallet_address": "",
            "trading_pairs": [
                {"base": "SOL", "quote": "USDC"},
                {"base": "ORCA", "quote": "USDC"},
            ],
            "slippage_bps": 50,
            "min_profit_bps": 10,
        }
        
        # Guardar configuración por defecto
        config_file.parent.mkdir(exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        print(f"📄 Configuración creada en: {config_path}")
        return default_config
    
    async def get_wallet_balance(self) -> Optional[float]:
        """Obtener balance de SOL"""
        if not self.config["wallet_address"]:
            print("⚠️  No hay dirección de wallet configurada")
            return None
        
        try:
            # Usar el puente Rust
            balance_lamports = self.rust_bridge.get_balance(self.config["wallet_address"])
            if balance_lamports:
                return balance_lamports / 1_000_000_000  # Convertir a SOL
        except Exception as e:
            print(f"❌ Error obteniendo balance: {e}")
        
        return None
    
    async def analyze_market(self, base_mint: str, quote_mint: str):
        """Analizar mercado para un par"""
        print(f"\n📊 Analizando {base_mint}/{quote_mint}...")
        
        # Encontrar pools disponibles
        pools = self.rust_bridge.find_whirlpools(base_mint, quote_mint)
        if pools:
            print(f"   🔍 Encontrados {len(pools)} pools:")
            for pool in pools:
                print(f"     • {pool['address'][:8]}... - Fee: {pool['fee_rate']/10000}%")
        
        # Obtener cotización de ejemplo
        quote = self.rust_bridge.get_swap_quote(
            input_mint=base_mint,
            output_mint=quote_mint,
            amount=1_000_000_000,  # 1 SOL en lamports
            slippage_bps=self.config["slippage_bps"]
        )
        
        if quote:
            print(f"   💰 Cotización:")
            print(f"     • Amount out: {quote['estimated_amount_out']}")
            print(f"     • Fee: {quote['estimated_fee']}")
            print(f"     • Price impact: {quote['price_impact']:.2%}")
        
        return pools
    
    async def monitor_prices(self):
        """Monitorizar precios en tiempo real"""
        print("\n👀 Monitorizando precios...")
        
        for pair in self.config["trading_pairs"]:
            base = pair["base"]
            quote = pair["quote"]
            
            # Obtener cotizaciones periódicamente
            quote_data = self.rust_bridge.get_swap_quote(
                input_mint=self.get_mint_address(base),
                output_mint=self.get_mint_address(quote),
                amount=1_000_000_000,
                slippage_bps=self.config["slippage_bps"]
            )
            
            if quote_data:
                price = quote_data["estimated_amount_out"] / 1_000_000_000
                print(f"   {base}/{quote}: {price:.4f}")
    
    def get_mint_address(self, symbol: str) -> str:
        """Obtener dirección mint desde símbolo"""
        mint_map = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
        }
        return mint_map.get(symbol, symbol)  # Si no está en el mapa, asumir que ya es una dirección
    
    async def run(self):
        """Ejecutar bot principal"""
        print("=" * 70)
        print("🐋 ORCA TRADING BOT - Python + Rust")
        print("=" * 70)
        print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Verificar balance
        balance = await self.get_wallet_balance()
        if balance is not None:
            print(f"💰 Balance: {balance:.4f} SOL")
        
        # Analizar mercados configurados
        for pair in self.config["trading_pairs"]:
            await self.analyze_market(
                self.get_mint_address(pair["base"]),
                self.get_mint_address(pair["quote"])
            )
        
        # Ejemplo de monitoreo continuo
        try:
            while True:
                await self.monitor_prices()
                await asyncio.sleep(10)  # Esperar 10 segundos
        except KeyboardInterrupt:
            print("\n\n👋 Bot detenido por usuario")
        
        # Cerrar conexiones
        await self.solana_client.close()

async def main():
    """Punto de entrada principal"""
    try:
        bot = OrcaTradingBot()
        await bot.run()
    except Exception as e:
        print(f"❌ Error en el bot: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    asyncio.run(main())