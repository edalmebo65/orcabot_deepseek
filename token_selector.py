#!/usr/bin/env python3
"""
Selector de los 20 tokens más volátiles para trading
Analiza volumen, liquidez y volatilidad histórica
"""
import asyncio
import logging
from typing import List, Dict, Optional, Any
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import time

logger = logging.getLogger(__name__)

@dataclass
class TokenMetrics:
    """Métricas de un token para evaluación"""
    symbol: str
    address: str
    price: float
    volume_24h: float
    liquidity: float
    volatility_24h: float
    volatility_7d: float
    price_change_24h: float
    market_cap: float
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def volatility_score(self) -> float:
        """Calcula score compuesto de volatilidad"""
        # Ponderar volatilidad 24h (40%), 7d (30%), volume (20%), liquidity (10%)
        score = (
            self.volatility_24h * 0.4 +
            self.volatility_7d * 0.3 +
            (min(self.volume_24h / 1_000_000, 1.0) * 0.2) +  # Normalizar volumen
            (min(self.liquidity / 500_000, 1.0) * 0.1)       # Normalizar liquidez
        )
        return score

class TokenSelector:
    """Selecciona tokens basado en volatilidad y métricas"""
    
    def __init__(self, top_n_tokens: int = 20, min_volume_usd: float = 10000, 
                 min_liquidity_usd: float = 50000):
        self.top_n_tokens = top_n_tokens
        self.min_volume_usd = min_volume_usd
        self.min_liquidity_usd = min_liquidity_usd
        self.session = None
        self.cache_file = "data/token_cache.json"
        self.cache_duration = 3600  # 1 hora en segundos
    
    async def __aenter__(self):
        await self._initialize_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()
    
    async def _initialize_session(self):
        """Inicializa sesión HTTP"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def _close_session(self):
        """Cierra sesión HTTP"""
        if self.session:
            await self.session.close()
    
    async def select_volatile_tokens(self) -> List[Any]:
        """
        Selecciona los N tokens más volátiles
        
        Returns:
            Lista de objetos TokenInfo
        """
        try:
            logger.info(f"Seleccionando {self.top_n_tokens} tokens volátiles...")
            
            # Obtener datos de tokens
            tokens_data = await self._fetch_tokens_data()
            
            if not tokens_data:
                logger.warning("No se pudieron obtener datos de tokens")
                return []
            
            # Filtrar y evaluar tokens
            evaluated_tokens = []
            
            for token_data in tokens_data:
                try:
                    metrics = await self._evaluate_token(token_data)
                    
                    if metrics and self._passes_filters(metrics):
                        from main_integrated import TokenInfo
                        
                        token_info = TokenInfo(
                            symbol=metrics.symbol,
                            address=token_data.get("address", ""),
                            volatility_score=metrics.volatility_score,
                            probability_score=0.5,  # Se actualizará después con ML
                            current_price=metrics.price,
                            volume_24h=metrics.volume_24h,
                            liquidity=metrics.liquidity,
                            last_updated=metrics.last_updated
                        )
                        
                        evaluated_tokens.append(token_info)
                        
                except Exception as e:
                    logger.debug(f"Error evaluando token: {e}")
                    continue
            
            # Ordenar por score de volatilidad (mayor primero)
            evaluated_tokens.sort(key=lambda x: x.volatility_score, reverse=True)
            
            # Tomar top N
            selected_tokens = evaluated_tokens[:self.top_n_tokens]
            
            logger.info(f"✅ Seleccionados {len(selected_tokens)} tokens volátiles")
            
            # Guardar cache
            await self._save_to_cache(selected_tokens)
            
            return selected_tokens
            
        except Exception as e:
            logger.error(f"Error seleccionando tokens: {e}")
            return []
    
    async def _fetch_tokens_data(self) -> List[Dict]:
        """Obtiene datos de tokens desde APIs"""
        try:
            # Intentar cargar desde cache primero
            cached_data = await self._load_from_cache()
            if cached_data and len(cached_data) > 50:
                logger.info(f"Usando cache con {len(cached_data)} tokens")
                return cached_data
            
            logger.info("Obteniendo datos frescos de tokens...")
            
            # Usar múltiples fuentes para obtener datos
            all_tokens = []
            
            # 1. Jupiter API para tokens populares
            jupiter_tokens = await self._fetch_jupiter_tokens()
            if jupiter_tokens:
                all_tokens.extend(jupiter_tokens)
            
            # 2. Orca API para pools de liquidez
            orca_tokens = await self._fetch_orca_pools()
            if orca_tokens:
                all_tokens.extend(orca_tokens)
            
            # 3. Raydium API
            raydium_tokens = await self._fetch_raydium_tokens()
            if raydium_tokens:
                all_tokens.extend(raydium_tokens)
            
            # Eliminar duplicados por address
            unique_tokens = {}
            for token in all_tokens:
                address = token.get("address")
                if address and address not in unique_tokens:
                    unique_tokens[address] = token
            
            return list(unique_tokens.values())
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de tokens: {e}")
            return []
    
    async def _fetch_jupiter_tokens(self) -> List[Dict]:
        """Obtiene tokens de Jupiter API"""
        try:
            url = "https://token.jup.ag/all"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    tokens = []
                    for item in data[:200]:  # Limitar a 200 tokens
                        if all(k in item for k in ["symbol", "address", "decimals"]):
                            tokens.append({
                                "symbol": item["symbol"],
                                "address": item["address"],
                                "decimals": item["decimals"],
                                "name": item.get("name", ""),
                                "logoURI": item.get("logoURI", ""),
                                "source": "jupiter"
                            })
                    
                    logger.info(f"Obtenidos {len(tokens)} tokens de Jupiter")
                    return tokens
                
        except Exception as e:
            logger.error(f"Error obteniendo tokens de Jupiter: {e}")
        
        return []
    
    async def _fetch_orca_pools(self) -> List[Dict]:
        """Obtiene pools de Orca"""
        try:
            url = "https://api.orca.so/v1/tokens"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    tokens = []
                    for item in data.get("tokens", []):
                        if "mint" in item and "symbol" in item:
                            tokens.append({
                                "symbol": item["symbol"],
                                "address": item["mint"],
                                "decimals": item.get("decimals", 9),
                                "name": item.get("name", ""),
                                "source": "orca"
                            })
                    
                    logger.info(f"Obtenidos {len(tokens)} tokens de Orca")
                    return tokens
                
        except Exception as e:
            logger.error(f"Error obteniendo tokens de Orca: {e}")
        
        return []
    
    async def _fetch_raydium_tokens(self) -> List[Dict]:
        """Obtiene tokens de Raydium"""
        try:
            url = "https://api-v3.raydium.io/mint/list"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    tokens = []
                    for item in data.get("data", [])[:150]:  # Limitar
                        if "symbol" in item and "mint" in item:
                            tokens.append({
                                "symbol": item["symbol"],
                                "address": item["mint"],
                                "decimals": item.get("decimals", 9),
                                "name": item.get("name", ""),
                                "source": "raydium"
                            })
                    
                    logger.info(f"Obtenidos {len(tokens)} tokens de Raydium")
                    return tokens
                
        except Exception as e:
            logger.error(f"Error obteniendo tokens de Raydium: {e}")
        
        return []
    
    async def _evaluate_token(self, token_data: Dict) -> Optional[TokenMetrics]:
        """Evalúa métricas para un token específico"""
        try:
            symbol = token_data.get("symbol", "UNKNOWN")
            address = token_data.get("address", "")
            
            if not address:
                return None
            
            # Obtener datos de precio y volumen
            price_data = await self._fetch_token_metrics(address)
            
            if not price_data:
                return None
            
            # Calcular métricas
            volatility_24h = self._calculate_volatility(price_data.get("prices_24h", []))
            volatility_7d = self._calculate_volatility(price_data.get("prices_7d", []))
            
            metrics = TokenMetrics(
                symbol=symbol,
                address=address,
                price=price_data.get("current_price", 0),
                volume_24h=price_data.get("volume_24h", 0),
                liquidity=price_data.get("liquidity", 0),
                volatility_24h=volatility_24h,
                volatility_7d=volatility_7d,
                price_change_24h=price_data.get("price_change_24h", 0),
                market_cap=price_data.get("market_cap", 0),
                last_updated=datetime.now()
            )
            
            return metrics
            
        except Exception as e:
            logger.debug(f"Error evaluando token {token_data.get('symbol')}: {e}")
            return None
    
    async def _fetch_token_metrics(self, token_address: str) -> Optional[Dict]:
        """Obtiene métricas específicas para un token"""
        try:
            # Usar Birdeye API para métricas
            url = f"https://public-api.birdeye.so/public/token_overview?address={token_address}"
            
            headers = {
                "X-API-KEY": "YOUR_BIRDEYE_API_KEY",  # Necesitarás obtener una API key
                "accept": "application/json"
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("success"):
                        result = data.get("data", {})
                        
                        return {
                            "current_price": result.get("price", 0),
                            "volume_24h": result.get("volume24hUSD", 0),
                            "liquidity": result.get("liquidity", 0),
                            "price_change_24h": result.get("priceChange24h", 0),
                            "market_cap": result.get("marketCap", 0),
                            "prices_24h": [],  # Necesitarías endpoint adicional
                            "prices_7d": []    # Necesitarías endpoint adicional
                        }
        
        except Exception as e:
            logger.debug(f"Error obteniendo métricas para {token_address[:8]}...: {e}")
        
        return None
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calcula volatilidad basada en precios"""
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if returns:
            return np.std(returns)
        
        return 0.0
    
    def _passes_filters(self, metrics: TokenMetrics) -> bool:
        """Verifica si el token pasa los filtros mínimos"""
        # Filtro de volumen
        if metrics.volume_24h < self.min_volume_usd:
            return False
        
        # Filtro de liquidez
        if metrics.liquidity < self.min_liquidity_usd:
            return False
        
        # Filtro de precio (no demasiado bajo)
        if metrics.price < 0.0001:
            return False
        
        # Filtro de volatilidad mínima
        if metrics.volatility_24h < 0.02:  # Mínimo 2% de volatilidad
            return False
        
        return True
    
    async def get_historical_data(self, token_address: str, days: int = 30) -> Optional[pd.DataFrame]:
        """Obtiene datos históricos para entrenamiento ML"""
        try:
            # Esta es una implementación simplificada
            # En producción, usarías una API como Birdeye, CoinGecko, etc.
            
            # Simular datos históricos para desarrollo
            np.random.seed(hash(token_address) % 10000)
            
            dates = pd.date_range(end=datetime.now(), periods=days*24, freq='H')
            base_price = np.random.uniform(0.1, 100)
            
            # Generar serie temporal con tendencia y volatilidad
            returns = np.random.normal(0.0001, 0.02, len(dates))
            prices = base_price * np.exp(np.cumsum(returns))
            
            # Agregar algo de autocorrelación
            for i in range(1, len(prices)):
                prices[i] = 0.7 * prices[i-1] + 0.3 * prices[i]
            
            # Crear DataFrame
            df = pd.DataFrame({
                'timestamp': dates,
                'open': prices,
                'high': prices * (1 + np.random.uniform(0, 0.01, len(dates))),
                'low': prices * (1 - np.random.uniform(0, 0.01, len(dates))),
                'close': prices,
                'volume': np.random.uniform(1000, 100000, len(dates))
            })
            
            logger.debug(f"Datos históricos simulados para {token_address[:8]}...: {len(df)} registros")
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos: {e}")
            return None
    
    async def _save_to_cache(self, tokens: List[Any]):
        """Guarda tokens en cache"""
        try:
            import os
            os.makedirs("data", exist_ok=True)
            
            cache_data = {
                "timestamp": time.time(),
                "tokens": [
                    {
                        "symbol": t.symbol,
                        "address": t.address,
                        "volatility_score": t.volatility_score,
                        "current_price": t.current_price,
                        "volume_24h": t.volume_24h,
                        "liquidity": t.liquidity
                    }
                    for t in tokens
                ]
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            logger.debug(f"Error guardando cache: {e}")
    
    async def _load_from_cache(self) -> Optional[List[Dict]]:
        """Carga tokens desde cache"""
        try:
            import os
            if not os.path.exists(self.cache_file):
                return None
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Verificar que el cache no esté expirado
            cache_time = cache_data.get("timestamp", 0)
            if time.time() - cache_time > self.cache_duration:
                return None
            
            return cache_data.get("tokens", [])
            
        except Exception as e:
            logger.debug(f"Error cargando cache: {e}")
            return None