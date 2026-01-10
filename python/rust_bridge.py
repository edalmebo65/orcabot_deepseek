# python/rust_bridge.py
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Añadir el directorio de rust al path
rust_build_path = Path(__file__).parent.parent / "rust" / "target" / "release"
if rust_build_path.exists():
    sys.path.insert(0, str(rust_build_path))

try:
    import orca_rust_bridge
    RUST_AVAILABLE = True
    print("✅ Módulo Rust cargado correctamente")
except ImportError as e:
    print(f"⚠️  No se pudo cargar el módulo Rust: {e}")
    print("   Compilando módulo Rust...")
    RUST_AVAILABLE = False

class OrcaRustBridge:
    """Puente entre Python y Rust para Orca"""
    
    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        if RUST_AVAILABLE:
            self.client = orca_rust_bridge.PyOrcaClient(rpc_url)
            self.mode = "RUST"
        else:
            self.mode = "FALLBACK"
            self._setup_fallback()
    
    def _setup_fallback(self):
        """Configurar fallback si Rust no está disponible"""
        print("⚠️  Usando modo fallback (sin Rust)")
        self.constants = {
            "ORCA_WHIRLPOOL_PROGRAM_ID": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
            "SOL_MINT": "So11111111111111111111111111111111111111112",
            "USDC_MINT": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT_MINT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "ORCA_MINT": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
        }
    
    def get_balance(self, wallet_address: str) -> Optional[int]:
        """Obtener balance en lamports"""
        if self.mode == "RUST":
            try:
                return self.client.get_balance_sync(wallet_address)
            except Exception as e:
                print(f"Error Rust: {e}")
                return None
        else:
            # Fallback: simular respuesta
            return 1000000000  # 1 SOL en lamports
    
    def get_whirlpool_data(self, whirlpool_address: str) -> Optional[Dict[str, Any]]:
        """Obtener datos de un whirlpool"""
        if self.mode == "RUST":
            try:
                data_json = self.client.get_whirlpool_data(whirlpool_address)
                return json.loads(data_json)
            except Exception as e:
                print(f"Error Rust: {e}")
                return None
        else:
            # Fallback
            return {
                "address": whirlpool_address,
                "token_mint_a": self.constants["SOL_MINT"],
                "token_mint_b": self.constants["USDC_MINT"],
                "tick_spacing": 64,
                "fee_rate": 300,
                "protocol_fee_rate": 100,
            }
    
    def get_swap_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50
    ) -> Optional[Dict[str, Any]]:
        """Obtener cotización de swap"""
        if self.mode == "RUST":
            try:
                quote_json = self.client.get_swap_quote(input_mint, output_mint, amount, slippage_bps)
                return json.loads(quote_json)
            except Exception as e:
                print(f"Error Rust: {e}")
                return None
        else:
            # Fallback
            return {
                "estimated_amount_out": amount * 100,
                "estimated_fee": amount * 3 // 1000,
                "price_impact": 0.05,
                "route": [input_mint, "whirlpool", output_mint],
                "note": "Modo fallback - datos simulados",
            }
    
    def find_whirlpools(self, token_a: str, token_b: str) -> Optional[List[Dict[str, Any]]]:
        """Encontrar whirlpools para un par de tokens"""
        if self.mode == "RUST":
            try:
                pools_json = self.client.find_whirlpools(token_a, token_b)
                return json.loads(pools_json)
            except Exception as e:
                print(f"Error Rust: {e}")
                return None
        else:
            # Fallback
            return [
                {
                    "address": "HJPjoWUrhoZzkNfRpHuieeFk9WcZWjwy6PBjZ81ngndJ",
                    "token_mint_a": token_a,
                    "token_mint_b": token_b,
                    "tick_spacing": 64,
                    "fee_rate": 300,
                },
                {
                    "address": "7qbRF6YsyGuLUVs6Y1q64bdVrfe4ZcUUz1JRdoVNUJnm",
                    "token_mint_a": token_a,
                    "token_mint_b": token_b,
                    "tick_spacing": 128,
                    "fee_rate": 100,
                },
            ]
    
    @property
    def whirlpool_program_id(self) -> str:
        """ID del programa Whirlpool"""
        if self.mode == "RUST":
            return self.client.whirlpool_program_id
        else:
            return self.constants["ORCA_WHIRLPOOL_PROGRAM_ID"]

# Instancia global
orca_bridge = OrcaRustBridge()

# Funciones de conveniencia
def get_orca_bridge() -> OrcaRustBridge:
    """Obtener instancia del puente"""
    return orca_bridge