"""
Bridge entre Python y Rust - Versión corregida
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# ====== CLIENTE FALLBACK PYTHON ======
class OrcaFallbackClient:
    """Cliente Python puro como fallback"""
    
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        
    def get_balance(self, wallet_address: str) -> Optional[int]:
        """Balance simulado para desarrollo"""
        # En producción, conectarías a Solana RPC
        return 1000000000  # 1 SOL
    
    def get_token_balance(self, wallet_address: str, mint_address: str) -> Optional[int]:
        """Balance de token simulado"""
        return 1000000  # 1 USDC
    
    def get_swap_quote(self, input_mint: str, output_mint: str, amount: int, slippage: float = 0.5) -> Dict[str, Any]:
        """Cotización simulada"""
        return {
            "input_mint": input_mint,
            "output_mint": output_mint,
            "in_amount": amount,
            "out_amount": amount * 100 if "USDC" in output_mint else amount,
            "price_impact_pct": 0.05,
            "fee_mint_a": amount * 3 // 1000,
            "fee_mint_b": 0,
            "note": "Modo fallback - datos simulados"
        }
    
    def get_all_pools(self) -> List[Dict[str, Any]]:
        """Pools simulados"""
        return [
            {
                "address": "2ZnVuidTHpi5WWKUwFXauYGhvdT9jRKYv5MDahtbwtYr",
                "token_a": "So11111111111111111111111111111111111111112",
                "token_b": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "fee": 0.003,
                "tvl": 10000000,
            },
            {
                "address": "F13xvvx45jVGd84ynK3c8T89UejQVxjCLtmHfPmAXAHP",
                "token_a": "So11111111111111111111111111111111111111112",
                "token_b": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
                "fee": 0.003,
                "tvl": 5000000,
            }
        ]

# ====== BRIDGE PRINCIPAL ======
class OrcaRustBridge:
    """Wrapper para el módulo Rust con fallback robusto"""
    
    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.rpc_url = rpc_url
        self.client = None
        self.mode = "UNKNOWN"
        self.constants = {}
        
        self._initialize()
    
    def _initialize(self):
        """Inicializar el bridge"""
        print("🔧 Inicializando Orca Bridge...")
        
        # Constantes estándar de Orca
        self.constants = {
            "WHIRLPOOL_PROGRAM_ID": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
            "SOL_MINT": "So11111111111111111111111111111111111111112",
            "USDC_MINT": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT_MINT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "ORCA_MINT": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
        }
        
        # Intentar cargar módulo Rust
        try:
            import orca_rust_bridge
            self.client = orca_rust_bridge.PyOrcaClient(self.rpc_url)
            self.mode = "RUST"
            
            # Actualizar constantes desde Rust si están disponibles
            try:
                self.constants["WHIRLPOOL_PROGRAM_ID"] = orca_rust_bridge.WHIRLPOOL_PROGRAM_ID
                self.constants["SOL_MINT"] = orca_rust_bridge.SOL_MINT
                self.constants["USDC_MINT"] = orca_rust_bridge.USDC_MINT
                self.constants["USDT_MINT"] = orca_rust_bridge.USDT_MINT
                self.constants["ORCA_MINT"] = orca_rust_bridge.ORCA_MINT
            except:
                pass
                
            print("✅ Bridge Rust inicializado")
            
        except ImportError:
            print("⚠️  Módulo Rust no disponible, usando fallback Python")
            self.mode = "PYTHON_FALLBACK"
            self.client = OrcaFallbackClient(self.rpc_url)
        except Exception as e:
            print(f"⚠️  Error cargando Rust: {e}, usando fallback")
            self.mode = "PYTHON_FALLBACK"
            self.client = OrcaFallbackClient(self.rpc_url)
    
    # ====== MÉTODOS PÚBLICOS ======
    
    def get_balance(self, wallet_address: str) -> Optional[int]:
        """Obtener balance de SOL"""
        try:
            return self.client.get_balance(wallet_address)
        except Exception as e:
            print(f"Error get_balance: {e}")
            return None
    
    def get_token_balance(self, wallet_address: str, mint_address: str) -> Optional[int]:
        """Obtener balance de token"""
        try:
            return self.client.get_token_balance(wallet_address, mint_address)
        except Exception as e:
            print(f"Error get_token_balance: {e}")
            return None
    
    def get_swap_quote(self, input_mint: str, output_mint: str, amount: int, slippage: float = 0.5) -> Optional[Dict[str, Any]]:
        """Obtener cotización de swap"""
        try:
            if self.mode == "RUST":
                quote_json = self.client.get_swap_quote(input_mint, output_mint, amount, slippage)
                return json.loads(quote_json)
            else:
                return self.client.get_swap_quote(input_mint, output_mint, amount, slippage)
        except Exception as e:
            print(f"Error get_swap_quote: {e}")
            return None
    
    def get_all_pools(self) -> List[Dict[str, Any]]:
        """Obtener todos los pools"""
        try:
            if self.mode == "RUST":
                pools_json = self.client.get_all_pools()
                return json.loads(pools_json)
            else:
                return self.client.get_all_pools()
        except Exception as e:
            print(f"Error get_all_pools: {e}")
            return []
    
    def get_whirlpools(self) -> List[Dict[str, Any]]:
        """Obtener whirlpools"""
        try:
            if self.mode == "RUST":
                whirlpools_json = self.client.get_whirlpools()
                return json.loads(whirlpools_json)
            else:
                # Datos de ejemplo
                return [{
                    "address": "HJPjoWUrhoZzkNfRpHuieeFk9WcZWjwy6PBjZ81ngndJ",
                    "token_mint_a": self.sol_mint,
                    "token_mint_b": self.usdc_mint,
                    "tick_spacing": 64,
                    "fee_rate": 300,
                }]
        except Exception as e:
            print(f"Error get_whirlpools: {e}")
            return []
    
    # ====== PROPIEDADES ======
    
    @property
    def whirlpool_program_id(self) -> str:
        return self.constants["WHIRLPOOL_PROGRAM_ID"]
    
    @property
    def sol_mint(self) -> str:
        return self.constants["SOL_MINT"]
    
    @property
    def usdc_mint(self) -> str:
        return self.constants["USDC_MINT"]
    
    @property
    def usdt_mint(self) -> str:
        return self.constants["USDT_MINT"]
    
    @property
    def orca_mint(self) -> str:
        return self.constants["ORCA_MINT"]
    
    @property
    def is_rust_mode(self) -> bool:
        return self.mode == "RUST"

# Instancia global
orca_bridge = OrcaRustBridge()