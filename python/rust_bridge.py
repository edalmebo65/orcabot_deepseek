"""
Bridge entre Python y el módulo Rust para Orca.so
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)

class OrcaRustBridge:
    """Wrapper para el módulo Rust"""
    
    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.rpc_url = rpc_url
        self.client = None
        self.mode = "UNKNOWN"
        
        self._initialize()
    
    def _initialize(self):
        """Inicializar el bridge Rust"""
        try:
            # Intentar importar el módulo Rust
            import orca_rust_bridge
            self.client = orca_rust_bridge.PyOrcaClient(self.rpc_url)
            self.mode = "RUST"
            
            # Guardar constantes
            self.constants = {
                "WHIRLPOOL_PROGRAM_ID": orca_rust_bridge.WHIRLPOOL_PROGRAM_ID,
                "SOL_MINT": orca_rust_bridge.SOL_MINT,
                "USDC_MINT": orca_rust_bridge.USDC_MINT,
                "USDT_MINT": orca_rust_bridge.USDT_MINT,
                "ORCA_MINT": orca_rust_bridge.ORCA_MINT,
            }
            
            logger.info("✅ Bridge Rust inicializado correctamente")
            
        except ImportError as e:
            logger.warning(f"⚠️  No se pudo cargar módulo Rust: {e}")
            self.mode = "FALLBACK"
            self._setup_fallback()
    
    def _setup_fallback(self):
        """Configurar modo fallback (Python puro)"""
        logger.info("Usando modo fallback (Python puro)")
        
        self.constants = {
            "WHIRLPOOL_PROGRAM_ID": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
            "SOL_MINT": "So11111111111111111111111111111111111111112",
            "USDC_MINT": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT_MINT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "ORCA_MINT": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
        }
    
    def get_balance(self, wallet_address: str) -> Optional[int]:
        """Obtener balance de SOL"""
        if self.mode == "RUST" and self.client:
            try:
                return self.client.get_balance(wallet_address)
            except Exception as e:
                logger.error(f"Error Rust get_balance: {e}")
                return None
        else:
            # Fallback: simulación
            return 1000000000  # 1 SOL
    
    def get_token_balance(self, wallet_address: str, mint_address: str) -> Optional[int]:
        """Obtener balance de token"""
        if self.mode == "RUST" and self.client:
            try:
                return self.client.get_token_balance(wallet_address, mint_address)
            except Exception as e:
                logger.error(f"Error Rust get_token_balance: {e}")
                return None
        else:
            # Fallback: simulación
            return 1000000  # 1 USDC
    
    def get_swap_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """Obtener cotización de swap"""
        if self.mode == "RUST" and self.client:
            try:
                quote_json = self.client.get_swap_quote(input_mint, output_mint, amount, slippage)
                return json.loads(quote_json)
            except Exception as e:
                logger.error(f"Error Rust get_swap_quote: {e}")
                return None
        else:
            # Fallback: simulación
            return {
                "input_mint": input_mint,
                "output_mint": output_mint,
                "in_amount": amount,
                "out_amount": amount * 100,  # 1 SOL = 100 USDC
                "price_impact_pct": 0.05,
                "fee_mint_a": amount * 3 // 1000,  # 0.3%
                "fee_mint_b": 0,
            }
    
    def get_all_pools(self) -> List[Dict[str, Any]]:
        """Obtener todos los pools"""
        if self.mode == "RUST" and self.client:
            try:
                pools_json = self.client.get_all_pools()
                return json.loads(pools_json)
            except Exception as e:
                logger.error(f"Error Rust get_all_pools: {e}")
                return []
        else:
            # Fallback: pools conocidos
            return [
                {
                    "address": "2ZnVuidTHpi5WWKUwFXauYGhvdT9jRKYv5MDahtbwtYr",
                    "token_a": self.constants["SOL_MINT"],
                    "token_b": self.constants["USDC_MINT"],
                    "lp_mint": "APDFRM3HMr8CAGXwKHiu2f5ePSpaiEJhaURwhsRrUUt9",
                    "fee": 0.003,
                },
                {
                    "address": "F13xvvx45jVGd84ynK3c8T89UejQVxjCLtmHfPmAXAHP",
                    "token_a": self.constants["SOL_MINT"],
                    "token_b": self.constants["USDT_MINT"],
                    "lp_mint": "FZthQCuYHhcfiDma7QrX7buDHwrZEd7vL8SjS6LQa3Tx",
                    "fee": 0.003,
                }
            ]
    
    def get_whirlpools(self) -> List[Dict[str, Any]]:
        """Obtener whirlpools"""
        if self.mode == "RUST" and self.client:
            try:
                whirlpools_json = self.client.get_whirlpools()
                return json.loads(whirlpools_json)
            except Exception as e:
                logger.error(f"Error Rust get_whirlpools: {e}")
                return []
        else:
            # Fallback: whirlpools conocidos
            return [
                {
                    "address": "HJPjoWUrhoZzkNfRpHuieeFk9WcZWjwy6PBjZ81ngndJ",
                    "token_mint_a": self.constants["SOL_MINT"],
                    "token_mint_b": self.constants["USDC_MINT"],
                    "tick_spacing": 64,
                    "fee_rate": 300,
                    "liquidity": 1000000000000,
                }
            ]
    
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

# Instancia global
orca_bridge = OrcaRustBridge()