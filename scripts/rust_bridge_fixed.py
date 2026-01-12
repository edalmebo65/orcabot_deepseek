"""
Bridge entre Python y Rust - Versión corregida e integrada
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class OrcaRustBridge:
    """Wrapper para el módulo Rust con fallback robusto"""
    
    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.rpc_url = rpc_url
        self.client = None
        self.mode = "UNKNOWN"
        self.constants = {}
        
        self._initialize()
    
    def _initialize(self):
        """Inicializar el bridge Rust con múltiples intentos"""
        print("🔧 Inicializando Orca Bridge...")
        
        # Intentar diferentes métodos de importación
        import_methods = [
            self._try_import_rust,
            self._try_import_pyd,
            self._try_import_dll,
            self._setup_fallback
        ]
        
        for method in import_methods:
            try:
                if method():
                    break
            except Exception as e:
                print(f"   ⚠️  {method.__name__} falló: {e}")
                continue
    
    def _try_import_rust(self):
        """Intentar importar módulo Rust normal"""
        try:
            import orca_rust_bridge
            self.client = orca_rust_bridge.PyOrcaClient(self.rpc_url)
            self.mode = "RUST"
            
            self.constants = {
                "WHIRLPOOL_PROGRAM_ID": orca_rust_bridge.WHIRLPOOL_PROGRAM_ID,
                "SOL_MINT": orca_rust_bridge.SOL_MINT,
                "USDC_MINT": orca_rust_bridge.USDC_MINT,
                "USDT_MINT": orca_rust_bridge.USDT_MINT,
                "ORCA_MINT": orca_rust_bridge.ORCA_MINT,
            }
            
            print("✅ Bridge Rust inicializado correctamente")
            return True
        except ImportError:
            return False
    
    def _try_import_pyd(self):
        """Intentar importar desde .pyd (Windows)"""
        try:
            # Buscar archivo .pyd
            pyd_file = Path("orca_rust_bridge.pyd")
            if pyd_file.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("orca_rust_bridge", str(pyd_file))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Hacer disponible globalmente
                sys.modules["orca_rust_bridge"] = module
                return self._try_import_rust()
        except:
            pass
        return False
    
    def _try_import_dll(self):
        """Intentar importar desde .dll"""
        try:
            dll_file = Path("orca_rust_bridge.dll")
            if dll_file.exists():
                # En Windows, .dll puede ser importado como .pyd
                import ctypes
                dll = ctypes.CDLL(str(dll_file))
                print("✅ DLL cargada via ctypes")
                # Nota: Esto solo carga la DLL, no proporciona interfaz Python
                return False  # Necesitaríamos más trabajo para usar esto
        except:
            pass
        return False
    
    def _setup_fallback(self):
        """Configurar modo fallback (Python puro)"""
        print("⚠️  Usando modo fallback (Python puro)")
        self.mode = "PYTHON_FALLBACK"
        
        self.constants = {
            "WHIRLPOOL_PROGRAM_ID": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
            "SOL_MINT": "So11111111111111111111111111111111111111112",
            "USDC_MINT": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT_MINT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "ORCA_MINT": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
        }
        
        # Inicializar cliente fallback
        self.client = OrcaFallbackClient(self.rpc_url)
        return True
    
    # Métodos de interfaz común
    def get_balance(self, wallet_address: str) -> Optional[int]:
        """Obtener balance de SOL"""
        if self.mode == "RUST" and self.client:
            try:
                return self.client.get_balance(wallet_address)
            except Exception as e:
                print(f"Error Rust get_balance: {e}")
                return None
        else:
            return self.client.get_balance(wallet_address)
    
    def get_token_balance(self, wallet_address: str, mint_address: str) -> Optional[int]:
        """Obtener balance de token"""
        if self.mode == "RUST" and self.client:
            try:
                return self.client.get_token_balance(wallet_address, mint_address)
            except Exception as e:
                print(f"Error Rust get_token_balance: {e}")
                return None
        else:
            return self.client.get_token_balance(wallet_address, mint_address)
    
    def get_swap_quote(self, input_mint: str, output_mint: str, amount: int, slippage: float = 0.5) -> Optional[Dict[str, Any]]:
        """Obtener cotización de swap"""
        if self.mode == "RUST" and self.client:
            try:
                quote_json = self.client.get_swap_quote(input_mint, output_mint, amount, slippage)
                return json.loads(quote_json)
            except Exception as e:
                print(f"Error Rust get_swap_quote: {e}")
                return None
        else:
            return self.client.get_swap_quote(input_mint, output_mint, amount, slippage)
    
    def get_all_pools(self) -> List[Dict[str, Any]]:
        """Obtener todos los pools"""
        if self.mode == "RUST" and self.client:
            try:
                pools_json = self.client.get_all_pools()
                return json.loads(pools_json)
            except Exception as e:
                print(f"Error Rust get_all_pools: {e}")
                return []
        else:
            return self.client.get_all_pools()
    
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

# Cliente fallback Python
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
            }
        ]

# Instancia global
orca_bridge = OrcaRustBridge()