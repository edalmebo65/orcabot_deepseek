# token_selector_enhanced.py
"""
Selector avanzado de tokens basado en volatilidad, volumen y liquidez
Implementa cache, scoring y filtros inteligentes
"""
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import json
import hashlib
from dataclasses import dataclass
import time
from collections import defaultdict

from config import TOKENS

@dataclass
class TokenMetrics:
    """Métricas completas de un token"""
    address: str
    symbol: str
    price: float
    volume_24h: float
    liquidity: float
    volatility_24h: float
    volatility_7d: float
    price_change_24h: float
    market_cap: float
    holders: int
    social_score: float = 0.0
    last_updated: datetime = None

class TokenCache:
    """Sistema de cache para datos de tokens"""
    def __init__(self, ttl_minutes: int = 5):
        self.cache = {}
        self.ttl = ttl_minutes * 60
        
    def get(self, key: str):
        """Obtener item del cache si es válido"""
        if key in self.cache:
            item, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return item
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value):
        """Guardar item en cache"""
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """Limpiar cache"""
        self.cache.clear()

class VolatileTokenSelector:
    """Selector de tokens volátiles con scoring avanzado"""
    def __init__(self):
        self.cache = TokenCache(ttl_minutes=TOKENS.CACHE_DURATION_MINUTES)
        self.http_session = None
        self.token_metrics = {}
        self.whale_wallets = self._load_whale_wallets()
    
    def _load_whale_wallets(self) -> List[str]:
        """Cargar lista de wallets de whales"""
        # Esta lista puede venir de una base de datos o API
        return [
            "vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg",  # Ejemplo
            "4fynC4FsS8N3Czeroq2M6QhY1pPdaj1fR5whsEwMg7eZ"
        ]
    
    async def initialize(self):
        """Inicializar sesión HTTP"""
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def close(self):
        """Cerrar sesión HTTP"""
        if self.http_session:
            await self.http_session.close()
    
    async def select_top_tokens(self, count: int = TOKENS.MAX_TOKENS) -> List[TokenMetrics]:
        """Seleccionar los mejores tokens para trading"""
        print(f"🔍 Seleccionando top {count} tokens volátiles...")
        
        cache_key = f"top_tokens_{count}"
        cached = self.cache.get(cache_key)
        
        if cached:
            print("📦 Usando datos cacheados")
            return cached
        
        # Obtener todos los tokens disponibles
        all_tokens = await self._fetch_all_tokens()
        
        if not all_tokens:
            print("❌ No se pudieron obtener tokens")
            return []
        
        # Filtrar por volumen y liquidez mínima
        filtered_tokens = []
        for token in all_tokens:
            if (token.volume_24h >= TOKENS.MIN_24H_VOLUME and 
                token.liquidity >= TOKENS.MIN_LIQUIDITY):
                filtered_tokens.append(token)
        
        print(f"📊 {len(filtered_tokens)} tokens pasan filtros iniciales")
        
        # Calcular scores para cada token
        scored_tokens = []
        for token in filtered_tokens:
            score = await self._calculate_token_score(token)
            scored_tokens.append((token, score))
        
        # Ordenar por score descendente
        scored_tokens.sort(key=lambda x: x[1], reverse=True)
        
        # Tomar los mejores
        top_tokens = [token for token, score in scored_tokens[:count]]
        
        # Actualizar cache
        self.cache.set(cache_key, top_tokens)
        
        # Guardar métricas
        for token in top_tokens:
            self.token_metrics[token.address] = token
        
        print(f"✅ Seleccionados {len(top_tokens)} tokens")
        return top_tokens
    
    async def _fetch_all_tokens(self) -> List[TokenMetrics]:
        """Obtener todos los tokens disponibles de múltiples fuentes"""
        tokens = []
        
        # Fuente 1: Orca tokens
        orca_tokens = await self._fetch_orca_tokens()
        tokens.extend(orca_tokens)
        
        # Fuente 2: Jupiter tokens
        jupiter_tokens = await self._fetch_jupiter_tokens()
        tokens.extend(jupiter_tokens)
        
        # Fuente 3: Raydium tokens
        raydium_tokens = await self._fetch_raydium_tokens()
        tokens.extend(raydium_tokens)
        
        # Eliminar duplicados
        unique_tokens = {}
        for token in tokens:
            if token.address not in unique_tokens:
                unique_tokens[token.address] = token
            elif token.volume_24h > unique_tokens[token.address].volume_24h:
                unique_tokens[token.address] = token
        
        return list(unique_tokens.values())
    
    async def _fetch_orca_tokens(self) -> List[TokenMetrics]:
        """Obtener tokens de Orca"""
        tokens = []
        
        try:
            async with self.http_session.get(
                "https://api.orca.so/allPools"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for pool in data.get('pools', [])[:100]:  # Limitar a 100 pools
                        try:
                            token_a = pool.get('tokenA', {})
                            token_b = pool.get('tokenB', {})
                            
                            # Solo tokens con USDC o SOL
                            quote_tokens = ['USDC', 'SOL', 'USDT']
                            
                            for token_data, is_token_a in [(token_a, True), (token_b, False)]:
                                symbol = token_data.get('symbol', '')
                                
                                if symbol in quote_tokens:
                                    continue
                                
                                token = TokenMetrics(
                                    address=token_data.get('mint', ''),
                                    symbol=symbol,
                                    price=float(token_data.get('price', 0)),
                                    volume_24h=float(pool.get('volume24h', 0)),
                                    liquidity=float(pool.get('liquidity', 0)),
                                    volatility_24h=0.0,  # Calculado después
                                    volatility_7d=0.0,
                                    price_change_24h=float(pool.get('priceChange24h', 0)),
                                    market_cap=0.0,
                                    holders=int(token_data.get('holderCount', 0)),
                                    last_updated=datetime.now()
                                )
                                
                                tokens.append(token)
                                
                        except Exception as e:
                            continue
                            
        except Exception as e:
            print(f"⚠️ Error obteniendo tokens de Orca: {e}")
        
        return tokens
    
    async def _fetch_jupiter_tokens(self) -> List[TokenMetrics]:
        """Obtener tokens de Jupiter"""
        tokens = []
        
        try:
            # Obtener tokens más populares de Jupiter
            async with self.http_session.get(
                "https://api.jup.ag/tokens/v1/all"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for token_data in data[:50]:  # Tomar 50 tokens
                        try:
                            token = TokenMetrics(
                                address=token_data.get('address', ''),
                                symbol=token_data.get('symbol', ''),
                                price=0.0,  # Necesita otro endpoint
                                volume_24h=0.0,
                                liquidity=0.0,
                                volatility_24h=0.0,
                                volatility_7d=0.0,
                                price_change_24h=0.0,
                                market_cap=float(token_data.get('marketCap', 0)),
                                holders=int(token_data.get('holderCount', 0)),
                                last_updated=datetime.now()
                            )
                            
                            tokens.append(token)
                            
                        except Exception as e:
                            continue
                            
        except Exception as e:
            print(f"⚠️ Error obteniendo tokens de Jupiter: {e}")
        
        return tokens
    
    async def _fetch_raydium_tokens(self) -> List[TokenMetrics]:
        """Obtener tokens de Raydium"""
        tokens = []
        
        try:
            async with self.http_session.get(
                "https://api-v3.raydium.io/pairs"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for pool in data.get('data', [])[:50]:
                        try:
                            token = TokenMetrics(
                                address=pool.get('baseMint', ''),
                                symbol=pool.get('baseSymbol', ''),
                                price=float(pool.get('basePrice', 0)),
                                volume_24h=float(pool.get('volume24h', 0)),
                                liquidity=float(pool.get('liquidity', 0)),
                                volatility_24h=float(pool.get('priceChange24h', 0)) / 100,
                                volatility_7d=0.0,
                                price_change_24h=float(pool.get('priceChange24h', 0)),
                                market_cap=float(pool.get('marketCap', 0)),
                                holders=0,
                                last_updated=datetime.now()
                            )
                            
                            tokens.append(token)
                            
                        except Exception as e:
                            continue
                            
        except Exception as e:
            print(f"⚠️ Error obteniendo tokens de Raydium: {e}")
        
        return tokens
    
    async def _calculate_token_score(self, token: TokenMetrics) -> float:
        """Calcular score compuesto para el token"""
        scores = {}
        
        # 1. Score de volatilidad (40%)
        if token.volatility_24h > 0:
            # Normalizar volatilidad (objetivo: 5-15%)
            vol_score = min(token.volatility_24h / 0.15, 1.0) * 0.4
            scores['volatility'] = vol_score
        else:
            scores['volatility'] = 0.2  # Valor por defecto
        
        # 2. Score de volumen (20%)
        volume_growth = await self._calculate_volume_growth(token.address)
        volume_score = min(volume_growth / 3.0, 1.0) * 0.2  # 300% = score completo
        scores['volume'] = volume_score
        
        # 3. Score de liquidez (15%)
        liquidity_score = min(token.liquidity / 1000000, 1.0) * 0.15  # $1M = score completo
        scores['liquidity'] = liquidity_score
        
        # 4. Score de actividad de whales (15%)
        whale_score = await self._calculate_whale_activity(token.address) * 0.15
        scores['whales'] = whale_score
        
        # 5. Score de sentimiento social (10%)
        social_score = token.social_score * 0.1
        scores['social'] = social_score
        
        # Score total
        total_score = sum(scores.values())
        
        # Penalización por baja liquidez relativa al volumen
        if token.volume_24h > 0:
            liquidity_ratio = token.liquidity / token.volume_24h
            if liquidity_ratio < 2:  # Liquidez menor a 2x el volumen
                total_score *= 0.7
        
        return min(total_score, 1.0)
    
    async def _calculate_volume_growth(self, token_address: str) -> float:
        """Calcular crecimiento de volumen en las últimas horas"""
        try:
            # Obtener datos históricos de volumen
            cache_key = f"volume_growth_{token_address}"
            cached = self.cache.get(cache_key)
            
            if cached:
                return cached
            
            # En una implementación real, obtendríamos datos de APIs como Birdeye
            # Simulamos un crecimiento aleatorio para el ejemplo
            growth = np.random.uniform(1.5, 5.0)  # 150% a 500%
            
            self.cache.set(cache_key, growth)
            return growth
            
        except Exception as e:
            print(f"⚠️ Error calculando crecimiento de volumen: {e}")
            return 1.0
    
    async def _calculate_whale_activity(self, token_address: str) -> float:
        """Calcular actividad de whales en el token"""
        try:
            # En una implementación real, analizaríamos transacciones de grandes wallets
            # Simulamos actividad aleatoria
            activity = np.random.uniform(0.1, 0.9)
            
            # Verificar si whales conocidos tienen el token
            for whale in self.whale_wallets:
                # Aquí iría una llamada a la blockchain
                pass
            
            return activity
            
        except Exception as e:
            print(f"⚠️ Error calculando actividad de whales: {e}")
            return 0.5
    
    async def update_token_volatility(self, token_address: str, price_history: List[float]):
        """Actualizar métricas de volatilidad"""
        if not price_history or len(price_history) < 2:
            return
        
        prices = np.array(price_history)
        
        # Calcular retornos
        returns = np.diff(prices) / prices[:-1]
        
        # Volatilidad 24h (últimas 24 horas si hay suficientes datos)
        if len(returns) >= 24:
            volatility_24h = np.std(returns[-24:])
        else:
            volatility_24h = np.std(returns) if len(returns) > 1 else 0
        
        # Volatilidad 7d
        if len(returns) >= 168:  # 7 días * 24 horas
            volatility_7d = np.std(returns[-168:])
        else:
            volatility_7d = np.std(returns) if len(returns) > 1 else 0
        
        # Actualizar en métricas si el token existe
        if token_address in self.token_metrics:
            self.token_metrics[token_address].volatility_24h = volatility_24h
            self.token_metrics[token_address].volatility_7d = volatility_7d
    
    async def get_token_metrics(self, token_address: str) -> Optional[TokenMetrics]:
        """Obtener métricas específicas de un token"""
        return self.token_metrics.get(token_address)
    
    async def refresh_token_data(self, token_address: str):
        """Refrescar datos de un token específico"""
        # Limpiar cache para este token
        keys_to_remove = [key for key in self.cache.cache.keys() 
                         if token_address in key]
        for key in keys_to_remove:
            if key in self.cache.cache:
                del self.cache.cache[key]
        
        # Recalcular métricas
        if token_address in self.token_metrics:
            token = self.token_metrics[token_address]
            new_score = await self._calculate_token_score(token)
            print(f"🔄 Token {token.symbol} actualizado. Score: {new_score:.3f}")

async def test_token_selector():
    """Función de prueba"""
    selector = VolatileTokenSelector()
    await selector.initialize()
    
    try:
        tokens = await selector.select_top_tokens(20)
        
        print(f"\n🏆 TOP {len(tokens)} TOKENS SELECCIONADOS:")
        print("=" * 80)
        print(f"{'Symbol':<10} {'Price':<10} {'Vol 24h':<12} {'Liquidity':<12} {'Volatility':<12}")
        print("-" * 80)
        
        for token in tokens:
            print(f"{token.symbol:<10} ${token.price:<9.4f} "
                  f"${token.volume_24h:<11,.0f} ${token.liquidity:<11,.0f} "
                  f"{token.volatility_24h*100:<11.2f}%")
        
        print("=" * 80)
        
    finally:
        await selector.close()

if __name__ == "__main__":
    asyncio.run(test_token_selector())