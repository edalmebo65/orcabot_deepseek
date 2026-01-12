#!/usr/bin/env python3
"""
Verificador de saldos para OrcaBot
Verifica que la wallet tenga saldos suficientes para operar:
- 10 USDC para operaciones
- 0.05 SOL para costos de transacción
"""
import asyncio
import logging
from typing import Dict, Optional, Tuple
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey
from solders.signature import Signature
import base58

logger = logging.getLogger(__name__)

class BalanceChecker:
    """Verifica y gestiona saldos de la wallet"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.config
        self.client = None
        self.wallet_address = None
        self.private_key = None
        self._initialize_wallet()
    
    def _initialize_wallet(self):
        """Inicializa la wallet desde la configuración"""
        try:
            # Obtener clave privada
            security_config = self.config.get("security", {})
            self.private_key = security_config.get("private_key", "")
            
            if not self.private_key:
                logger.error("No se pudo obtener la clave privada")
                return
            
            # Obtener dirección de wallet
            self.wallet_address = security_config.get("wallet_address", "")
            
            if not self.wallet_address:
                logger.error("No se pudo obtener la dirección de wallet")
                return
            
            # Configurar cliente RPC
            solana_config = self.config.get("solana", {})
            rpc_endpoint = solana_config.get("rpc_endpoint", "")
            
            if not rpc_endpoint:
                logger.error("No se configuró el endpoint RPC")
                return
            
            self.client = AsyncClient(rpc_endpoint)
            logger.info(f"Wallet inicializada: {self.wallet_address[:8]}...")
            
        except Exception as e:
            logger.error(f"Error inicializando wallet: {e}")
    
    async def check_minimum_balances(self) -> bool:
        """
        Verifica que la wallet tenga saldos mínimos para operar
        
        Returns:
            bool: True si tiene saldos suficientes
        """
        try:
            logger.info("🔍 Verificando saldos mínimos...")
            
            # Obtener saldos actuales
            balances = await self.get_current_balances()
            
            # Verificar USDC mínimo
            usdc_balance = balances.get("USDC", 0)
            usdc_required = 10.0
            
            if usdc_balance < usdc_required:
                logger.error(f"USDC insuficiente: {usdc_balance:.2f} < {usdc_required}")
                return False
            
            # Verificar SOL mínimo para fees
            sol_balance = balances.get("SOL", 0)
            sol_required = 0.05
            
            if sol_balance < sol_required:
                logger.error(f"SOL insuficiente para fees: {sol_balance:.4f} < {sol_required}")
                return False
            
            logger.info(f"✅ Saldos OK: USDC={usdc_balance:.2f}, SOL={sol_balance:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"Error verificando saldos: {e}")
            return False
    
    async def get_current_balances(self) -> Dict[str, float]:
        """
        Obtiene saldos actuales de la wallet
        
        Returns:
            Dict con símbolos y balances
        """
        try:
            if not self.client or not self.wallet_address:
                logger.error("Wallet no inicializada")
                return {}
            
            # Obtener balance de SOL
            sol_balance = await self._get_sol_balance()
            
            # Obtener balance de USDC (necesita token account)
            usdc_balance = await self._get_usdc_balance()
            
            return {
                "SOL": sol_balance,
                "USDC": usdc_balance
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo balances: {e}")
            return {"SOL": 0.0, "USDC": 0.0}
    
    async def _get_sol_balance(self) -> float:
        """Obtiene balance de SOL"""
        try:
            if not self.client:
                return 0.0
            
            # Obtener balance de SOL
            response = await self.client.get_balance(
                PublicKey(self.wallet_address)
            )
            
            if response.value:
                # Convertir lamports a SOL
                sol_balance = response.value / 1_000_000_000
                logger.debug(f"Balance SOL: {sol_balance:.4f}")
                return sol_balance
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error obteniendo balance SOL: {e}")
            return 0.0
    
    async def _get_usdc_balance(self) -> float:
        """Obtiene balance de USDC"""
        try:
            if not self.client:
                return 0.0
            
            # Dirección del token USDC en Solana
            usdc_mint = PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
            
            # Encontrar la token account para USDC
            response = await self.client.get_token_accounts_by_owner(
                PublicKey(self.wallet_address),
                {"mint": usdc_mint},
                "jsonParsed"
            )
            
            if response.value and len(response.value) > 0:
                # Obtener balance de la primera token account
                account_info = response.value[0].account.data.parsed["info"]
                token_amount = account_info["tokenAmount"]["uiAmount"]
                
                if token_amount:
                    logger.debug(f"Balance USDC: {token_amount:.2f}")
                    return float(token_amount)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error obteniendo balance USDC: {e}")
            return 0.0
    
    async def get_estimated_fees(self, num_transactions: int = 5) -> float:
        """
        Estima el costo de fees para un número de transacciones
        
        Args:
            num_transactions: Número de transacciones a estimar
            
        Returns:
            Costo estimado en SOL
        """
        try:
            if not self.client:
                return 0.0
            
            # Obtener fee reciente
            response = await self.client.get_recent_prioritization_fees()
            
            if response.value and len(response.value) > 0:
                # Tomar el fee más reciente
                recent_fee = response.value[0].prioritization_fee
                
                # Convertir lamports a SOL y estimar para N transacciones
                fee_per_tx = recent_fee / 1_000_000_000
                estimated_total = fee_per_tx * num_transactions * 1.5  # Buffer 50%
                
                logger.info(f"Fee estimado: {estimated_total:.6f} SOL para {num_transactions} tx")
                return estimated_total
            
            # Valor por defecto si no se puede obtener
            default_fee = 0.000005 * num_transactions * 1.5
            return default_fee
            
        except Exception as e:
            logger.error(f"Error estimando fees: {e}")
            return 0.000005 * num_transactions * 2.0  # Valor conservador
    
    async def check_transaction_feasibility(self, usdc_amount: float) -> Tuple[bool, str]:
        """
        Verifica si una transacción es factible con los saldos actuales
        
        Args:
            usdc_amount: Cantidad de USDC a usar
            
        Returns:
            Tuple (es_factible, mensaje)
        """
        try:
            # Obtener balances
            balances = await self.get_current_balances()
            
            usdc_balance = balances.get("USDC", 0)
            sol_balance = balances.get("SOL", 0)
            
            # Verificar USDC
            if usdc_balance < usdc_amount:
                return False, f"USDC insuficiente: {usdc_balance:.2f} < {usdc_amount:.2f}"
            
            # Estimar fees para 3 transacciones (entry, stop loss, take profit)
            estimated_fees = await self.get_estimated_fees(3)
            
            # Verificar SOL para fees
            if sol_balance < estimated_fees:
                return False, f"SOL insuficiente para fees: {sol_balance:.4f} < {estimated_fees:.4f}"
            
            # Verificar que quede algo de USDC después
            remaining_usdc = usdc_balance - usdc_amount
            if remaining_usdc < 5:  # Mínimo de reserva
                logger.warning(f"Quedarían solo {remaining_usdc:.2f} USDC después de la operación")
            
            return True, f"Saldos OK: USDC={usdc_balance:.2f}, SOL={sol_balance:.4f}"
            
        except Exception as e:
            logger.error(f"Error verificando factibilidad: {e}")
            return False, f"Error: {str(e)}"
    
    async def reserve_funds(self, usdc_amount: float) -> bool:
        """
        Reserva fondos para una operación (lógica de marcado)
        
        Args:
            usdc_amount: Cantidad a reservar
            
        Returns:
            bool: True si se pudieron reservar
        """
        try:
            # En una implementación real, esto manejaría bloqueo de fondos
            # Por ahora solo verifica
            feasible, message = await self.check_transaction_feasibility(usdc_amount)
            
            if feasible:
                logger.info(f"✅ Fondos reservados: {usdc_amount:.2f} USDC - {message}")
                return True
            else:
                logger.warning(f"❌ No se pueden reservar fondos: {message}")
                return False
                
        except Exception as e:
            logger.error(f"Error reservando fondos: {e}")
            return False
    
    async def release_funds(self, usdc_amount: float):
        """Libera fondos reservados"""
        logger.info(f"Fondos liberados: {usdc_amount:.2f} USDC")
        # En implementación real, liberaría el bloqueo
    
    async def close(self):
        """Cierra conexiones"""
        if self.client:
            await self.client.close()
            logger.info("Conexiones de balance cerradas")