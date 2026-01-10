# core/blockchain/transaction_executor.py
import asyncio
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed, Processed
from solana.transaction import Transaction
from solana.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.message import Message

@dataclass
class TransactionResult:
    """Resultado de una transacción"""
    success: bool
    signature: Optional[str]
    error: Optional[str]
    block_time: Optional[int]
    slot: Optional[int]
    fee: Optional[int]
    simulation_logs: Optional[List[str]]
    timestamp: datetime

class TransactionExecutor:
    """Ejecutor seguro de transacciones"""
    
    def __init__(self, config, wallet_manager):
        self.config = config
        self.wallet = wallet_manager
        self.client = wallet_manager.client
        
        # Configuración
        self.max_retries = 3
        self.confirmation_timeout = 30
        self.priority_fee_micro_lamports = config.trading.priority_fee_micro_lamports
        
        # Estadísticas
        self.stats = {
            "total_transactions": 0,
            "successful": 0,
            "failed": 0,
            "total_fees": 0,
            "avg_confirmation_time": 0
        }
        
        # Cache de firmas recientes
        self.recent_signatures = set()
        self.signature_cache_size = 100
        
    async def execute_transaction(self, 
                                transaction: Transaction,
                                skip_preflight: bool = False) -> TransactionResult:
        """
        Ejecuta una transacción de forma segura
        """
        start_time = datetime.now()
        
        try:
            # 1. Simular transacción primero
            simulation = await self.client.simulate_transaction(transaction)
            
            if simulation.value.err:
                return TransactionResult(
                    success=False,
                    signature=None,
                    error=f"Simulation failed: {simulation.value.err}",
                    block_time=None,
                    slot=None,
                    fee=None,
                    simulation_logs=simulation.value.logs,
                    timestamp=start_time
                )
            
            # 2. Firmar transacción
            transaction.sign(self.wallet.keypair)
            
            # 3. Enviar transacción
            signature = await self.client.send_transaction(
                transaction,
                self.wallet.keypair,
                opts={
                    "skip_preflight": skip_preflight,
                    "preflight_commitment": Processed,
                    "max_retries": self.max_retries
                }
            )
            
            sig_str = str(signature.value)
            
            # 4. Esperar confirmación
            confirmed = await self._wait_for_confirmation(signature.value)
            
            if not confirmed:
                return TransactionResult(
                    success=False,
                    signature=sig_str,
                    error="Transaction not confirmed within timeout",
                    block_time=None,
                    slot=None,
                    fee=None,
                    simulation_logs=simulation.value.logs,
                    timestamp=start_time
                )
            
            # 5. Obtener detalles de la transacción
            tx_details = await self._get_transaction_details(signature.value)
            
            # 6. Actualizar estadísticas
            self._update_stats(True, tx_details.get('fee', 0))
            
            return TransactionResult(
                success=True,
                signature=sig_str,
                error=None,
                block_time=tx_details.get('blockTime'),
                slot=tx_details.get('slot'),
                fee=tx_details.get('fee'),
                simulation_logs=simulation.value.logs,
                timestamp=start_time
            )
            
        except Exception as e:
            # Actualizar estadísticas de error
            self._update_stats(False, 0)
            
            return TransactionResult(
                success=False,
                signature=None,
                error=str(e),
                block_time=None,
                slot=None,
                fee=None,
                simulation_logs=None,
                timestamp=start_time
            )
    
    async def _wait_for_confirmation(self, signature: Signature) -> bool:
        """Espera confirmación de transacción"""
        for _ in range(self.confirmation_timeout):
            try:
                response = await self.client.get_signature_statuses([signature])
                status = response.value[0]
                
                if status and status.confirmation_status:
                    return True
                    
                await asyncio.sleep(1)
            except Exception:
                await asyncio.sleep(1)
        
        return False
    
    async def _get_transaction_details(self, signature: Signature) -> Dict:
        """Obtiene detalles de una transacción confirmada"""
        try:
            response = await self.client.get_transaction(
                signature,
                encoding="jsonParsed",
                commitment=Confirmed
            )
            
            if response.value:
                tx = response.value
                return {
                    'slot': tx.slot,
                    'blockTime': tx.block_time,
                    'fee': tx.transaction.meta.fee if tx.transaction.meta else 0,
                    'logs': tx.transaction.meta.log_messages if tx.transaction.meta else [],
                    'err': tx.transaction.meta.err if tx.transaction.meta else None
                }
        except Exception as e:
            self.config.logger.error(f"Error getting transaction details: {e}")
        
        return {}
    
    def _update_stats(self, success: bool, fee: int):
        """Actualiza estadísticas"""
        self.stats["total_transactions"] += 1
        
        if success:
            self.stats["successful"] += 1
            self.stats["total_fees"] += fee
        else:
            self.stats["failed"] += 1
    
    async def execute_batch_transactions(self, 
                                       transactions: List[Transaction]) -> List[TransactionResult]:
        """Ejecuta múltiples transacciones en batch"""
        results = []
        
        for tx in transactions:
            result = await self.execute_transaction(tx)
            results.append(result)
            
            # Pequeña pausa entre transacciones
            await asyncio.sleep(0.1)
        
        return results
    
    async def estimate_transaction_cost(self, 
                                      transaction: Transaction) -> Dict:
        """Estima costo de una transacción"""
        try:
            # Simular para obtener tamaño
            simulation = await self.client.simulate_transaction(transaction)
            
            if simulation.value.err:
                return {"error": str(simulation.value.err)}
            
            # Calcular costo aproximado
            # Base fee + priority fee + rent
            base_fee = 5000  # lamports base
            priority_fee = self.priority_fee_micro_lamports
            
            # Estimación de costo total
            total_lamports = base_fee + priority_fee
            
            return {
                "lamports": total_lamports,
                "sol": total_lamports / 1_000_000_000,
                "priority_fee": priority_fee,
                "base_fee": base_fee
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas de ejecución"""
        success_rate = 0
        if self.stats["total_transactions"] > 0:
            success_rate = self.stats["successful"] / self.stats["total_transactions"]
        
        avg_fee = 0
        if self.stats["successful"] > 0:
            avg_fee = self.stats["total_fees"] / self.stats["successful"]
        
        return {
            **self.stats,
            "success_rate": success_rate,
            "avg_fee_sol": avg_fee / 1_000_000_000,
            "total_fees_sol": self.stats["total_fees"] / 1_000_000_000
        }