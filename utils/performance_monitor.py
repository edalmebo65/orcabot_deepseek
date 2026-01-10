# utils/performance_monitor.py
import asyncio
import time
import psutil
import gc
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    """Métricas de performance del sistema"""
    cpu_percent: float
    memory_mb: float
    network_io: Dict[str, float]
    latency_ms: float
    queue_size: int
    error_rate: float
    trades_per_hour: int

class PerformanceMonitor:
    """Monitor de performance en tiempo real"""
    
    def __init__(self, config):
        self.config = config
        self.metrics_history: List[PerformanceMetrics] = []
        self.start_time = datetime.now()
        
        # Estadísticas
        self.stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0
        }
        
        # Umbrales de alerta
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_mb': 4096,  # 4GB
            'latency_ms': 1000,
            'error_rate': 0.1  # 10%
        }
    
    async def collect_metrics(self) -> PerformanceMetrics:
        """Recolecta métricas del sistema"""
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memoria
        memory = psutil.virtual_memory()
        memory_mb = memory.used / 1024 / 1024
        
        # Network I/O
        net_io = psutil.net_io_counters()
        network_metrics = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv
        }
        
        # Latencia (simulada - en realidad mediría RPC)
        latency_ms = await self._measure_latency()
        
        # Métricas de la aplicación
        queue_size = 0  # Implementar según colas reales
        error_rate = 0.0  # Calcular basado en errores recientes
        
        # Trades por hora
        trades_per_hour = self._calculate_trades_per_hour()
        
        return PerformanceMetrics(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            network_io=network_metrics,
            latency_ms=latency_ms,
            queue_size=queue_size,
            error_rate=error_rate,
            trades_per_hour=trades_per_hour
        )
    
    async def _measure_latency(self) -> float:
        """Mide latencia de la red"""
        try:
            start = time.time()
            # Aquí se mediría latencia real a RPC
            await asyncio.sleep(0.01)  # Simulación
            return (time.time() - start) * 1000
        except:
            return 999.9  # Error
    
    def _calculate_trades_per_hour(self) -> int:
        """Calcula trades por hora"""
        # Implementar con datos reales
        return 0
    
    async def check_alerts(self, metrics: PerformanceMetrics) -> List[str]:
        """Verifica condiciones de alerta"""
        alerts = []
        
        if metrics.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append(f"⚠️ CPU alta: {metrics.cpu_percent:.1f}%")
        
        if metrics.memory_mb > self.alert_thresholds['memory_mb']:
            alerts.append(f"⚠️ Memoria alta: {metrics.memory_mb:.0f}MB")
        
        if metrics.latency_ms > self.alert_thresholds['latency_ms']:
            alerts.append(f"⚠️ Latencia alta: {metrics.latency_ms:.0f}ms")
        
        if metrics.error_rate > self.alert_thresholds['error_rate']:
            alerts.append(f"⚠️ Error rate alto: {metrics.error_rate:.1%}")
        
        return alerts
    
    def generate_report(self) -> Dict:
        """Genera reporte de performance"""
        if not self.metrics_history:
            return {}
        
        df = pd.DataFrame([m.__dict__ for m in self.metrics_history[-100:]])  # Últimas 100 muestras
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'uptime_hours': (datetime.now() - self.start_time).total_seconds() / 3600,
            'avg_cpu': df['cpu_percent'].mean(),
            'avg_memory_mb': df['memory_mb'].mean(),
            'avg_latency_ms': df['latency_ms'].mean(),
            'max_cpu': df['cpu_percent'].max(),
            'max_memory_mb': df['memory_mb'].max(),
            'current_alerts': len(self.check_alerts(self.metrics_history[-1]) if self.metrics_history else []),
            'performance_score': self._calculate_performance_score(df)
        }
        
        return report
    
    def _calculate_performance_score(self, df: pd.DataFrame) -> float:
        """Calcula score de performance 0-100"""
        score = 100
        
        # Penalizar por CPU alta
        if df['cpu_percent'].mean() > 70:
            score -= 20
        elif df['cpu_percent'].mean() > 50:
            score -= 10
        
        # Penalizar por latencia
        if df['latency_ms'].mean() > 500:
            score -= 30
        elif df['latency_ms'].mean() > 200:
            score -= 15
        
        # Penalizar por errores
        if df['error_rate'].mean() > 0.05:
            score -= 25
        
        return max(0, score)
    
    async def run_monitoring(self):
        """Bucle principal de monitoreo"""
        while True:
            try:
                metrics = await self.collect_metrics()
                self.metrics_history.append(metrics)
                
                # Mantener tamaño manejable
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-500:]
                
                # Verificar alertas
                alerts = await self.check_alerts(metrics)
                if alerts and hasattr(self.config, 'telegram'):
                    for alert in alerts:
                        await self.config.telegram.send_message(f"🚨 {alert}")
                
                # Generar reporte periódico
                if len(self.metrics_history) % 60 == 0:  # Cada 60 ciclos
                    report = self.generate_report()
                    self._save_report(report)
                
                await asyncio.sleep(5)  # Recolectar cada 5 segundos
                
            except Exception as e:
                self.config.logger.error(f"Error en monitor: {e}")
                await asyncio.sleep(10)
    
    def _save_report(self, report: Dict):
        """Guarda reporte de performance"""
        from pathlib import Path
        import json
        
        reports_dir = Path("reports/performance")
        reports_dir.mkdir(exist_ok=True)
        
        filename = reports_dir / f"performance_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)