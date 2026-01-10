# core/blockchain/connection_manager.py
import asyncio
import aiohttp
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

@dataclass
class ConnectionMetrics:
    """Métricas de conexión"""
    latency_ms: float
    success_rate: float
    last_success: datetime
    total_requests: int
    failed_requests: int

class ConnectionManager:
    """Gestor de conexiones a blockchain"""
    
    def __init__(self, config):
        self.config = config
        self.connections: Dict[str, ConnectionMetrics] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_endpoint = config.RPC_ENDPOINT
        
        # Pool de endpoints de respaldo
        self.backup_endpoints = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
            "https://rpc.ankr.com/solana"
        ]
        
        # Configuración de reconexión
        self.max_retries = 3
        self.retry_delay = 1
        self.timeout = 30
        
    async def connect(self):
        """Establece conexión inicial"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
        # Probar conexión
        success = await self._test_connection(self.current_endpoint)
        
        if not success:
            # Intentar endpoints de respaldo
            for endpoint in self.backup_endpoints:
                success = await self._test_connection(endpoint)
                if success:
                    self.current_endpoint = endpoint
                    break
        
        if not success:
            raise ConnectionError("No se pudo conectar a ningún endpoint RPC")
        
        # Inicializar métricas
        self.connections[self.current_endpoint] = ConnectionMetrics(
            latency_ms=0,
            success_rate=1.0,
            last_success=datetime.now(),
            total_requests=1,
            failed_requests=0
        )
        
        return True
    
    async def _test_connection(self, endpoint: str) -> bool:
        """Prueba conexión a un endpoint"""
        try:
            start = datetime.now()
            
            # Crear sesión temporal para prueba
            async with aiohttp.ClientSession() as temp_session:
                # Enviar request simple
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth"
                }
                
                async with temp_session.post(
                    endpoint, 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        latency = (datetime.now() - start).total_seconds() * 1000
                        
                        # Actualizar métricas
                        if endpoint in self.connections:
                            self.connections[endpoint].latency_ms = latency
                            self.connections[endpoint].last_success = datetime.now()
                            self.connections[endpoint].total_requests += 1
                        else:
                            self.connections[endpoint] = ConnectionMetrics(
                                latency_ms=latency,
                                success_rate=1.0,
                                last_success=datetime.now(),
                                total_requests=1,
                                failed_requests=0
                            )
                        
                        return True
        except Exception as e:
            self.config.logger.debug(f"Connection test failed for {endpoint}: {e}")
        
        return False
    
    async def request(self, method: str, params: List = None) -> Dict:
        """Realiza request a la blockchain"""
        for attempt in range(self.max_retries):
            try:
                start = datetime.now()
                
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params or []
                }
                
                async with self.session.post(
                    self.current_endpoint,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Calcular latencia
                        latency = (datetime.now() - start).total_seconds() * 1000
                        
                        # Actualizar métricas
                        metrics = self.connections[self.current_endpoint]
                        metrics.latency_ms = (metrics.latency_ms + latency) / 2
                        metrics.total_requests += 1
                        metrics.last_success = datetime.now()
                        
                        return result
                    else:
                        raise Exception(f"HTTP {response.status}")
                        
            except Exception as e:
                self.config.logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                
                # Actualizar métricas de error
                if self.current_endpoint in self.connections:
                    self.connections[self.current_endpoint].failed_requests += 1
                
                # Esperar antes de reintentar
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                
                # Cambiar de endpoint si es necesario
                if attempt == 1:
                    await self._switch_endpoint()
        
        raise Exception(f"Failed after {self.max_retries} attempts")
    
    async def _switch_endpoint(self):
        """Cambia a un endpoint de mejor performance"""
        if len(self.connections) < 2:
            return
        
        # Encontrar endpoint con mejor métricas
        best_endpoint = None
        best_score = -1
        
        for endpoint, metrics in self.connections.items():
            if metrics.total_requests == 0:
                continue
                
            success_rate = 1 - (metrics.failed_requests / metrics.total_requests)
            score = success_rate * (1000 / max(metrics.latency_ms, 1))
            
            if score > best_score:
                best_score = score
                best_endpoint = endpoint
        
        if best_endpoint and best_endpoint != self.current_endpoint:
            self.config.logger.info(f"Switching endpoint to {best_endpoint}")
            self.current_endpoint = best_endpoint
    
    async def get_performance_report(self) -> Dict:
        """Genera reporte de performance"""
        report = {
            "current_endpoint": self.current_endpoint,
            "total_endpoints": len(self.connections),
            "connections": {}
        }
        
        for endpoint, metrics in self.connections.items():
            success_rate = 1 - (metrics.failed_requests / max(metrics.total_requests, 1))
            
            report["connections"][endpoint] = {
                "latency_ms": round(metrics.latency_ms, 2),
                "success_rate": round(success_rate, 3),
                "total_requests": metrics.total_requests,
                "failed_requests": metrics.failed_requests,
                "last_success": metrics.last_success.isoformat() if metrics.last_success else None,
                "is_active": endpoint == self.current_endpoint
            }
        
        return report
    
    async def close(self):
        """Cierra todas las conexiones"""
        if self.session and not self.session.closed:
            await self.session.close()