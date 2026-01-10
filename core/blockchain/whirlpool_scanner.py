# core/blockchain/whirlpool_scanner.py
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

@dataclass
class PoolMetrics:
    """Métricas de un pool de liquidez"""
    address: str
    token_a: str
    token_b: str
    token_a_symbol: str
    token_b_symbol: str
    liquidity: float
    volume_24h: float
    fee_rate: float
    apr: float
    volatility: float
    concentration: float
    price: float
    price_change_24h: float

class TimeframeAnalyzer:
    """Analiza pools por timeframe específico"""
    
    def __init__(self, timeframe: str):
        self.timeframe = timeframe
        self.required_volume = {
            '1m': 10000,    # $10k para 1min
            '5m': 25000,    # $25k para 5min
            '15m': 50000,   # $50k para 15min
            '1h': 100000,   # $100k para 1h
        }
    
    def calculate_timeframe_score(self, pool: PoolMetrics) -> float:
        """Calcula score específico para el timeframe"""
        base_score = 0
        
        # Peso por timeframe
        timeframe_weights = {
            '1m': {'volume': 0.4, 'volatility': 0.3, 'liquidity': 0.3},
            '5m': {'volume': 0.3, 'volatility': 0.4, 'liquidity': 0.3},
            '15m': {'volume': 0.25, 'volatility': 0.35, 'liquidity': 0.4},
            '1h': {'volume': 0.2, 'volatility': 0.3, 'liquidity': 0.5},
        }
        
        weights = timeframe_weights.get(self.timeframe, timeframe_weights['15m'])
        
        # Normalizar métricas
        volume_norm = min(pool.volume_24h / self.required_volume[self.timeframe], 1.0)
        volatility_norm = min(pool.volatility / 0.5, 1.0)  # Máximo 50% volatilidad
        liquidity_norm = min(pool.liquidity / 100000, 1.0)  # Máximo $100k liquidez
        
        # Calcular score ponderado
        score = (
            volume_norm * weights['volume'] +
            volatility_norm * weights['volatility'] +
            liquidity_norm * weights['liquidity']
        )
        
        # Bonus por concentración (para pools específicos)
        if pool.concentration > 0.7:
            score *= 1.1
        
        return score

class WhirlpoolScanner:
    """Escáner avanzado de Whirlpools"""
    
    def __init__(self, config, rpc_client):
        self.config = config
        self.client = rpc_client
        self.jupiter_api = "https://api.jup.ag"
        
    async def scan_top_pools(self, 
                           timeframe: str,
                           limit: int = 50) -> List[PoolMetrics]:
        """
        Escanea y analiza los mejores pools para el timeframe
        """
        try:
            # 1. Obtener pools de Jupiter API
            pools = await self._fetch_jupiter_pools()
            
            # 2. Filtrar por liquidez mínima
            filtered_pools = [
                p for p in pools 
                if p['liquidity'] > self.config.trading.min_pool_liquidity
            ]
            
            # 3. Analizar cada pool
            analyzer = TimeframeAnalyzer(timeframe)
            analyzed_pools = []
            
            for pool_data in filtered_pools[:100]:  # Limitar para performance
                metrics = await self._analyze_pool(pool_data, timeframe)
                if metrics:
                    score = analyzer.calculate_timeframe_score(metrics)
                    analyzed_pools.append((metrics, score))
            
            # 4. Ordenar por score y tomar top N
            analyzed_pools.sort(key=lambda x: x[1], reverse=True)
            top_pools = [p[0] for p in analyzed_pools[:limit]]
            
            return top_pools
            
        except Exception as e:
            print(f"Error escaneando pools: {e}")
            return []
    
    async def _fetch_jupiter_pools(self) -> List[Dict]:
        """Obtiene pools de Jupiter API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.jupiter_api}/pools/v1"
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return []
        except:
            # Fallback a lista estática si la API falla
            return self._get_static_pool_list()
    
    async def _analyze_pool(self, pool_data: Dict, timeframe: str) -> Optional[PoolMetrics]:
        """Analiza métricas detalladas de un pool"""
        try:
            # Obtener datos históricos para análisis
            historical_data = await self._get_pool_historical_data(
                pool_data['address'], 
                timeframe
            )
            
            if historical_data.empty:
                return None
            
            # Calcular métricas
            returns = historical_data['close'].pct_change().dropna()
            
            metrics = PoolMetrics(
                address=pool_data['address'],
                token_a=pool_data['tokenA']['mint'],
                token_b=pool_data['tokenB']['mint'],
                token_a_symbol=pool_data['tokenA'].get('symbol', 'UNKNOWN'),
                token_b_symbol=pool_data['tokenB'].get('symbol', 'UNKNOWN'),
                liquidity=float(pool_data.get('liquidity', 0)),
                volume_24h=float(pool_data.get('volume24h', 0)),
                fee_rate=float(pool_data.get('feeRate', 0)),
                apr=float(pool_data.get('apr', 0)),
                volatility=returns.std() * np.sqrt(365 * 24),  # Volatilidad anualizada
                concentration=float(pool_data.get('concentration', 0.5)),
                price=float(pool_data.get('price', 0)),
                price_change_24h=float(pool_data.get('priceChange24h', 0))
            )
            
            return metrics
            
        except Exception as e:
            print(f"Error analizando pool {pool_data.get('address', 'unknown')}: {e}")
            return None
    
    def _get_static_pool_list(self) -> List[Dict]:
        """Lista estática de pools populares (fallback)"""
        # Pools populares de Orca
        return [
            {
                'address': 'whirlpool_address_1',
                'tokenA': {'mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'symbol': 'USDC'},
                'tokenB': {'mint': 'So11111111111111111111111111111111111111112', 'symbol': 'SOL'},
                'liquidity': 5000000,
                'volume24h': 1000000,
                'feeRate': 0.0005,
                'apr': 0.15,
                'price': 100.0
            },
            # Agregar más pools según necesidad
        ]