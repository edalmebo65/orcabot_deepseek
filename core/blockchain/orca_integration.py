# core/blockchain/orca_integration.py
import asyncio
import aiohttp
import base64
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction
from solana.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.instruction import Instruction, AccountMeta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import json

class OrcaIntegration:
    """Integración directa con Orca.so para operaciones en blockchain"""
    
    def __init__(self, config, wallet_manager):
        self.config = config
        self.wallet_manager = wallet_manager
        self.client = wallet_manager.client
        
        # Endpoints Orca
        self.orca_program_id = Pubkey.from_string("whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc")
        self.jupiter_api = "https://quote-api.jup.ag/v6"
        
        # Cache de pools
        self.pools_cache = {}
        self.cache_timeout = 300  # 5 minutos
    
    async def execute_swap(self,
                          input_mint: str,
                          output_mint: str,
                          amount: Decimal,
                          slippage_bps: int = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Ejecuta swap en Orca via Jupiter Aggregator
        Returns: (success, message, tx_details)
        """
        try:
            if slippage_bps is None:
                slippage_bps = self.config.trading.max_slippage_bps
            
            # 1. Obtener quote de Jupiter
            quote = await self._get_jupiter_quote(
                input_mint, 
                output_mint, 
                amount
            )
            
            if not quote:
                return False, "No se pudo obtener quote", None
            
            # 2. Verificar slippage
            min_output_amount = quote['outAmount'] * (10000 - slippage_bps) / 10000
            
            # 3. Obtener transaction
            swap_transaction = await self._get_swap_transaction(
                quote,
                self.wallet_manager.wallet_address,
                slippage_bps
            )
            
            if not swap_transaction:
                return False, "No se pudo construir transacción", None
            
            # 4. Firmar y enviar
            transaction = Transaction.deserialize(base64.b64decode(swap_transaction))
            transaction.sign(self.wallet_manager.keypair)
            
            # 5. Simular primero (opcional pero recomendado)
            simulation_result = await self.client.simulate_transaction(transaction)
            if simulation_result.value.err:
                return False, f"Simulación falló: {simulation_result.value.err}", None
            
            # 6. Enviar transacción real
            tx_signature = await self.client.send_transaction(
                transaction,
                self.wallet_manager.keypair,
                opts={"skip_preflight": False, "preflight_commitment": Confirmed}
            )
            
            # 7. Confirmar transacción
            confirmation = await self._confirm_transaction(tx_signature)
            
            if confirmation:
                tx_details = {
                    "signature": str(tx_signature),
                    "input_amount": float(amount),
                    "output_amount": float(quote['outAmount']),
                    "price_impact": float(quote.get('priceImpactPct', 0)),
                    "route": quote.get('routePlan', []),
                    "fees": float(quote.get('totalFees', {}).get('total', 0))
                }
                
                return True, "Swap ejecutado exitosamente", tx_details
            else:
                return False, "Transacción no confirmada", None
            
        except Exception as e:
            return False, f"Error en swap: {str(e)}", None
    
    async def execute_limit_order(self,
                                 asset_pair: str,
                                 side: str,  # 'buy' or 'sell'
                                 amount: Decimal,
                                 limit_price: Decimal,
                                 expiry_seconds: int = 3600) -> Tuple[bool, str]:
        """
        Ejecuta orden limitada (implementación simplificada)
        En producción usaríamos Serum o un programa de limit orders
        """
        try:
            # Para Orca, implementaríamos usando el programa Whirlpool
            # o un DEX que soporte limit orders como OpenBook
            
            # Por ahora, implementación placeholder
            self.config.logger.warning("Limit orders no implementados completamente")
            
            return False, "Limit orders no disponibles temporalmente"
            
        except Exception as e:
            return False, f"Error en limit order: {str(e)}"
    
    async def execute_stop_loss(self,
                               operation_id: str,
                               current_price: Decimal,
                               stop_price: Decimal) -> Tuple[bool, str, Optional[Dict]]:
        """
        Ejecuta stop loss como market order
        """
        # Determinar dirección del trade basado en posición
        # Por simplicidad, asumimos que estamos vendiendo
        
        asset_pair = "SOL/USDC"  # Esto vendría de la operación
        input_mint = "So11111111111111111111111111111111111111112"  # SOL
        output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        
        # Calcular cantidad a vender (esto vendría de la operación)
        amount_to_sell = Decimal('1.0')  # Placeholder
        
        return await self.execute_swap(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount_to_sell,
            slippage_bps=100  # 1% slippage para stops
        )
    
    async def check_transaction_status(self, signature: str) -> Dict:
        """Verifica estado de una transacción"""
        try:
            sig = Signature.from_string(signature)
            response = await self.client.get_transaction(
                sig,
                encoding="jsonParsed",
                commitment=Confirmed
            )
            
            if response.value:
                tx_info = response.value.transaction.meta
                return {
                    "confirmed": True,
                    "fee": tx_info.fee / 1_000_000_000 if tx_info.fee else 0,
                    "success": not tx_info.err,
                    "error": str(tx_info.err) if tx_info.err else None
                }
            else:
                return {"confirmed": False, "error": "Transacción no encontrada"}
                
        except Exception as e:
            return {"confirmed": False, "error": str(e)}
    
    async def _get_jupiter_quote(self,
                                input_mint: str,
                                output_mint: str,
                                amount: Decimal) -> Optional[Dict]:
        """Obtiene quote de Jupiter API"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "amount": int(amount * Decimal('1_000_000')),  # Asumiendo 6 decimales
                    "slippageBps": self.config.trading.max_slippage_bps,
                    "onlyDirectRoutes": False
                }
                
                async with session.get(f"{self.jupiter_api}/quote", params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.config.logger.error(f"Jupiter API error: {response.status}")
                        return None
                        
        except Exception as e:
            self.config.logger.error(f"Error getting Jupiter quote: {e}")
            return None
    
    async def _get_swap_transaction(self,
                                   quote: Dict,
                                   user_public_key: str,
                                   slippage_bps: int) -> Optional[str]:
        """Obtiene transacción de swap firmable"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "quoteResponse": quote,
                    "userPublicKey": user_public_key,
                    "wrapAndUnwrapSol": True,
                    "dynamicComputeUnitLimit": True,
                    "prioritizationFeeLamports": self.config.trading.priority_fee_micro_lamports
                }
                
                async with session.post(
                    f"{self.jupiter_api}/swap",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('swapTransaction')
                    else:
                        error_text = await response.text()
                        self.config.logger.error(f"Swap transaction error: {error_text}")
                        return None
                        
        except Exception as e:
            self.config.logger.error(f"Error getting swap transaction: {e}")
            return None
    
    async def _confirm_transaction(self, signature: Signature, timeout: int = 30) -> bool:
        """Espera confirmación de transacción"""
        try:
            for _ in range(timeout):
                status = await self.check_transaction_status(str(signature))
                if status["confirmed"]:
                    return True
                await asyncio.sleep(1)
            return False
        except Exception as e:
            self.config.logger.error(f"Error confirming transaction: {e}")
            return False