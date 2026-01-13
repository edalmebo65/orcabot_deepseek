#!/usr/bin/env python3
"""
Balance Checker actualizado para usar config.py
"""
import asyncio
import logging
from typing import Dict, Optional, Tuple
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey

logger = logging.getLogger(__name__)

class BalanceChecker:
    """Verifica saldos usando config.py"""
    
    def __init__(self):
        # Importar configuración desde config.py
        from config_manager_integrated import config_integrator
        self.config = config_integrator.get_config()
        self.client = None
        self._initialize_from_config()
    
    def _initialize_from_config(self):
        """Inicializa desde config.py"""
        try:
            # Obtener wallet info
            security_config = self.config.get("security", {})
            self.private_key = security_config.get("private_key", "")
            self.wallet_address = security_config.get("wallet_address", "")
            
            # Obtener RPC endpoint
            solana_config = self.config.get("solana", {})
            rpc_endpoint = solana_config.get("rpc_endpoint", "")
            
            if not rpc_endpoint:
                logger.error("RPC endpoint no configurado en config.py")
                return
            
            self.client = AsyncClient(rpc_endpoint)
            
            logger.info(f"✅ BalanceChecker inicializado desde config.py")
            logger.info(f"   Wallet: {self.wallet_address[:8]}...")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando BalanceChecker: {e}")
    
    # Resto del código permanece igual...
    # [Métodos check_minimum_balances, get_current_balances, etc.]