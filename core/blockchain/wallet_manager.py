# core/blockchain/wallet_manager.py
import asyncio
import base64
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.transaction import Transaction
from solders.signature import Signature
from typing import Dict, Tuple, Optional
import json

class WalletManager:
    """Gestor seguro de wallet y saldos"""
    
    def __init__(self, config):
        self.config = config
        self.client = None
        self.keypair = None
        self.wallet_address = PublicKey(config.PHANTOM_WALLET)
        self._initialize_keypair()
    
    def _initialize_keypair(self):
        """Inicializa keypair desde clave privada encriptada"""
        try:
            # Decodificar clave privada Base58
            import base58
            private_key_bytes = base58.b58decode(self.config.PHANTOM_PRIVATE_KEY)
            self.keypair = Keypair.from_secret_key(private_key_bytes)
            
            # Verificar que la dirección coincida
            if str(self.keypair.public_key) != self.config.PHANTOM_WALLET:
                raise ValueError("Wallet address no coincide con private key")
                
        except Exception as e:
            raise ValueError(f"Error inicializando wallet: {e}")
    
    async def connect(self):
        """Establece conexión con RPC"""
        self.client = AsyncClient(self.config.RPC_ENDPOINT, commitment=Confirmed)
        await self.client.is_connected()
    
    async def get_wallet_balances(self) -> Dict[str, float]:
        """Obtiene todos los saldos de la wallet"""
        try:
            balances = {}
            
            # Obtener saldo SOL
            sol_balance = await self.client.get_balance(self.wallet_address)
            balances['SOL'] = sol_balance.value / 1_000_000_000
            
            # Obtener tokens SPL (simplificado - en producción usar get_token_accounts_by_owner)
            # Aquí implementar lógica para detectar USDC y otros tokens relevantes
            
            return balances
            
        except Exception as e:
            raise Exception(f"Error obteniendo saldos: {e}")
    
    async def check_operation_viability(self, estimated_cost_sol: float) -> Tuple[bool, str]:
        """
        Verifica si hay suficiente SOL para operar
        Returns: (viable, message)
        """
        try:
            balances = await self.get_wallet_balances()
            sol_balance = balances.get('SOL', 0)
            
            # Mínimo requerido: costo estimado + buffer de seguridad
            required_sol = estimated_cost_sol * 1.5  # 50% buffer
            
            if sol_balance >= required_sol:
                return True, f"✅ SOL suficiente: {sol_balance:.6f} SOL (requerido: {required_sol:.6f})"
            else:
                return False, f"❌ SOL insuficiente: {sol_balance:.6f} SOL (requerido: {required_sol:.6f})"
                
        except Exception as e:
            return False, f"❌ Error verificando viabilidad: {e}"
    
    async def get_transaction_cost_estimate(self, 
                                          operation_type: str,
                                          priority_fee: bool = True) -> float:
        """
        Estima costo de transacción en SOL
        """
        # Valores estimados (ajustar según red actual)
        base_fees = {
            'swap': 0.000005,  # 5,000 lamports base
            'add_liquidity': 0.00001,
            'remove_liquidity': 0.000008,
            'create_position': 0.000015,
        }
        
        base_cost = base_fees.get(operation_type, 0.00001)
        
        if priority_fee:
            base_cost += self.config.trading.priority_fee_micro_lamports / 1_000_000_000
        
        # Añadir margen para variaciones
        return base_cost * 1.2
    
    async def get_portfolio_value(self) -> Dict:
        """Obtiene valor total del portfolio"""
        balances = await self.get_wallet_balances()
        
        # Aquí implementar lógica para obtener precios actuales
        # y calcular valor en USD
        
        portfolio = {
            'balances': balances,
            'total_usd': 0.0,  # Calcular con precios reales
            'available_sol': balances.get('SOL', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        return portfolio