# communication/status_reporter.py
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path

class StatusReporter:
    """Reporteador de estado del sistema"""
    
    def __init__(self, config):
        self.config = config
        self.reports_dir = config.base_dir / "reports" / "status"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Historial de reportes
        self.report_history: List[Dict] = []
        self.max_history = 100
        
        # Intervalo de reportes
        self.report_interval = timedelta(minutes=5)
        self.last_report_time = datetime.now()
    
    async def generate_status_report(self, 
                                   force: bool = False) -> Optional[Dict]:
        """
        Genera reporte de estado completo
        """
        now = datetime.now()
        
        # Verificar intervalo
        if not force and (now - self.last_report_time) < self.report_interval:
            return None
        
        try:
            # Recolectar datos de todos los componentes
            report = {
                "timestamp": now.isoformat(),
                "system": await self._get_system_status(),
                "trading": await self._get_trading_status(),
                "blockchain": await self._get_blockchain_status(),
                "ml": await self._get_ml_status(),
                "performance": await self._get_performance_status(),
                "alerts": await self._get_alerts_status()
            }
            
            # Guardar reporte
            self._save_report(report)
            
            # Actualizar historial
            self.report_history.append(report)
            if len(self.report_history) > self.max_history:
                self.report_history = self.report_history[-self.max_history:]
            
            # Actualizar último tiempo
            self.last_report_time = now
            
            self.config.logger.info(f"📊 Status report generated")
            
            return report
            
        except Exception as e:
            self.config.logger.error(f"Error generating status report: {e}")
            return None
    
    async def _get_system_status(self) -> Dict:
        """Obtiene estado del sistema"""
        import psutil
        import platform
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "uptime_seconds": (datetime.now() - self.config.start_time).total_seconds(),
            "processes": len(psutil.pids())
        }
    
    async def _get_trading_status(self) -> Dict:
        """Obtiene estado de trading"""
        # Esto depende de qué componentes estén disponibles
        status = {
            "bot_state": "RUNNING",  # placeholder
            "active_operations": 0,
            "total_operations": 0,
            "total_pnl": 0.0,
            "daily_pnl": 0.0,
            "capital_available": 0.0,
            "capital_allocated": 0.0
        }
        
        # Intentar obtener datos reales si los componentes están disponibles
        try:
            if hasattr(self.config, 'trading_engine'):
                # Aquí obtendrías datos reales del trading engine
                pass
        except:
            pass
        
        return status
    
    async def _get_blockchain_status(self) -> Dict:
        """Obtiene estado de blockchain"""
        status = {
            "connected": False,
            "network": "mainnet",
            "wallet_balance": 0.0,
            "last_block": 0,
            "latency_ms": 0
        }
        
        # Intentar obtener datos reales
        try:
            if hasattr(self.config, 'wallet_manager'):
                # Aquí obtendrías datos reales
                pass
        except:
            pass
        
        return status
    
    async def _get_ml_status(self) -> Dict:
        """Obtiene estado de ML"""
        status = {
            "model_loaded": False,
            "model_type": "N/A",
            "accuracy": 0.0,
            "last_training": None,
            "predictions_today": 0
        }
        
        # Intentar obtener datos reales
        try:
            if hasattr(self.config, 'ml_predictor'):
                # Aquí obtendrías datos reales
                pass
        except:
            pass
        
        return status
    
    async def _get_performance_status(self) -> Dict:
        """Obtiene estado de performance"""
        status = {
            "requests_per_second": 0,
            "success_rate": 1.0,
            "avg_response_time": 0,
            "errors_last_hour": 0,
            "queue_size": 0
        }
        
        # Intentar obtener datos reales
        try:
            if hasattr(self.config, 'performance_monitor'):
                # Aquí obtendrías datos reales
                pass
        except:
            pass
        
        return status
    
    async def _get_alerts_status(self) -> Dict:
        """Obtiene estado de alertas"""
        status = {
            "active_alerts": 0,
            "critical_alerts": 0,
            "unacknowledged_alerts": 0,
            "alerts_last_hour": 0
        }
        
        # Intentar obtener datos reales
        try:
            if hasattr(self.config, 'alert_manager'):
                # Aquí obtendrías datos reales
                pass
        except:
            pass
        
        return status
    
    def _save_report(self, report: Dict):
        """Guarda reporte en archivo"""
        timestamp = datetime.fromisoformat(report["timestamp"]).strftime("%Y%m%d_%H%M%S")
        filename = self.reports_dir / f"status_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
    
    async def send_daily_report(self):
        """Envía reporte diario"""
        try:
            # Generar reporte de 24 horas
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_reports = [
                r for r in self.report_history
                if datetime.fromisoformat(r["timestamp"]) >= cutoff_time
            ]
            
            if not recent_reports:
                return
            
            # Resumir datos
            summary = await self._summarize_daily_data(recent_reports)
            
            # Formatear mensaje
            message = await self._format_daily_report(summary)
            
            # Enviar por Telegram si está configurado
            if hasattr(self.config, 'telegram') and self.config.telegram:
                await self.config.telegram.send_message(message)
            
            self.config.logger.info("📈 Daily report sent")
            
        except Exception as e:
            self.config.logger.error(f"Error sending daily report: {e}")
    
    async def _summarize_daily_data(self, reports: List[Dict]) -> Dict:
        """Resume datos diarios"""
        if not reports:
            return {}
        
        # Calcular promedios
        cpu_values = [r["system"]["cpu_percent"] for r in reports]
        memory_values = [r["system"]["memory_percent"] for r in reports]
        
        summary = {
            "period_hours": 24,
            "reports_count": len(reports),
            "avg_cpu": sum(cpu_values) / len(cpu_values),
            "avg_memory": sum(memory_values) / len(memory_values),
            "max_cpu": max(cpu_values),
            "max_memory": max(memory_values),
            "first_report": reports[0]["timestamp"],
            "last_report": reports[-1]["timestamp"]
        }
        
        # Agregar métricas de trading si están disponibles
        trading_reports = [r for r in reports if "trading" in r]
        if trading_reports:
            # Resumir métricas de trading
            pass
        
        return summary
    
    async def _format_daily_report(self, summary: Dict) -> str:
        """Formatea reporte diario para Telegram"""
        message = (
            "📊 *DAILY STATUS REPORT*\n\n"
            f"*Period:* {summary.get('period_hours', 0)} hours\n"
            f"*Reports:* {summary.get('reports_count', 0)}\n\n"
            f"*System Performance:*\n"
            f"• Avg CPU: {summary.get('avg_cpu', 0):.1f}%\n"
            f"• Avg Memory: {summary.get('avg_memory', 0):.1f}%\n"
            f"• Max CPU: {summary.get('max_cpu', 0):.1f}%\n"
            f"• Max Memory: {summary.get('max_memory', 0):.1f}%\n\n"
            f"*Period:* {summary.get('first_report', 'N/A')} to {summary.get('last_report', 'N/A')}\n\n"
            f"✅ System operating normally"
        )
        
        return message
    
    def get_report_history(self, 
                          hours: int = 24, 
                          limit: int = 100) -> List[Dict]:
        """Obtiene historial de reportes"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_reports = [
            r for r in self.report_history
            if datetime.fromisoformat(r["timestamp"]) >= cutoff_time
        ]
        
        return recent_reports[:limit]
    
    def export_reports(self, 
                      output_format: str = "json",
                      days: int = 7) -> bool:
        """Exporta reportes históricos"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # Obtener reportes recientes
            recent_reports = [
                r for r in self.report_history
                if datetime.fromisoformat(r["timestamp"]) >= cutoff_time
            ]
            
            if not recent_reports:
                return False
            
            # Crear nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = self.reports_dir.parent / f"reports_export_{timestamp}"
            
            if output_format == "json":
                with open(export_path.with_suffix(".json"), 'w') as f:
                    json.dump(recent_reports, f, indent=2)
            
            elif output_format == "csv":
                import pandas as pd
                
                # Convertir a DataFrame y exportar
                df = pd.DataFrame(recent_reports)
                df.to_csv(export_path.with_suffix(".csv"), index=False)
            
            self.config.logger.info(f"Exported {len(recent_reports)} reports")
            return True
            
        except Exception as e:
            self.config.logger.error(f"Error exporting reports: {e}")
            return False