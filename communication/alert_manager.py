# communication/alert_manager.py
import asyncio
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class AlertType(Enum):
    TRADE = "trade"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SECURITY = "security"
    PERFORMANCE = "performance"

class AlertPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Alert:
    """Alerta del sistema"""
    id: str
    type: AlertType
    priority: AlertPriority
    title: str
    message: str
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    metadata: Dict = None
    
    @property
    def is_acknowledged(self) -> bool:
        return self.acknowledged
    
    @property
    def age(self) -> timedelta:
        return datetime.now() - self.timestamp

class AlertManager:
    """Gestor de alertas del sistema"""
    
    def __init__(self, config):
        self.config = config
        self.alerts: Dict[str, Alert] = {}
        self.subscribers: Set[str] = set()  # IDs de suscriptores
        self.alert_history: List[Alert] = []
        self.max_history = 1000
        
        # Umbrales de rate limiting
        self.rate_limits = {
            AlertType.ERROR: timedelta(seconds=60),
            AlertType.WARNING: timedelta(seconds=30),
            AlertType.INFO: timedelta(seconds=10)
        }
        self.last_alert_time: Dict[AlertType, datetime] = {}
    
    def create_alert(self,
                    alert_type: AlertType,
                    priority: AlertPriority,
                    title: str,
                    message: str,
                    metadata: Dict = None) -> Alert:
        """
        Crea una nueva alerta
        """
        # Verificar rate limiting
        if not self._check_rate_limit(alert_type):
            self.config.logger.debug(f"Rate limited alert: {alert_type.value} - {title}")
            return None
        
        # Crear ID único
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.alerts)}"
        
        # Crear alerta
        alert = Alert(
            id=alert_id,
            type=alert_type,
            priority=priority,
            title=title,
            message=message,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # Guardar alerta
        self.alerts[alert_id] = alert
        
        # Agregar a historial
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        # Actualizar último tiempo de alerta
        self.last_alert_time[alert_type] = datetime.now()
        
        # Notificar suscriptores
        self._notify_subscribers(alert)
        
        # Loggear
        self.config.logger.info(f"🚨 Alert created: {title} ({priority.value})")
        
        return alert
    
    def _check_rate_limit(self, alert_type: AlertType) -> bool:
        """Verifica rate limiting para tipo de alerta"""
        if alert_type not in self.rate_limits:
            return True
        
        last_time = self.last_alert_time.get(alert_type)
        if last_time is None:
            return True
        
        time_since_last = datetime.now() - last_time
        return time_since_last >= self.rate_limits[alert_type]
    
    def _notify_subscribers(self, alert: Alert):
        """Notifica a suscriptores sobre nueva alerta"""
        for subscriber_id in self.subscribers:
            # En implementación real, esto enviaría notificaciones
            # a Telegram, email, webhook, etc.
            pass
        
        # Por ahora, solo loggear
        self.config.logger.debug(f"Notified {len(self.subscribers)} subscribers about alert {alert.id}")
    
    def acknowledge_alert(self,
                         alert_id: str,
                         user: str) -> bool:
        """Marca alerta como reconocida"""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        
        if alert.acknowledged:
            return True
        
        alert.acknowledged = True
        alert.acknowledged_by = user
        alert.acknowledged_at = datetime.now()
        
        self.config.logger.info(f"✅ Alert {alert_id} acknowledged by {user}")
        
        return True
    
    def create_trade_alert(self,
                          trade_data: Dict,
                          priority: AlertPriority = AlertPriority.MEDIUM):
        """Crea alerta de trading"""
        title = f"Trade {trade_data.get('side', 'UNKNOWN')} - {trade_data.get('asset_pair', 'UNKNOWN')}"
        message = (
            f"Trade executed: {trade_data.get('side')} {trade_data.get('asset_pair')}\n"
            f"Price: ${trade_data.get('price', 0):.4f}\n"
            f"Size: ${trade_data.get('size', 0):.2f}\n"
            f"P&L: {trade_data.get('pnl_pct', 0):.2f}%"
        )
        
        return self.create_alert(
            alert_type=AlertType.TRADE,
            priority=priority,
            title=title,
            message=message,
            metadata=trade_data
        )
    
    def create_error_alert(self,
                          error_data: Dict,
                          priority: AlertPriority = AlertPriority.HIGH):
        """Crea alerta de error"""
        error_type = error_data.get('error_type', 'Unknown')
        module = error_data.get('module', 'Unknown')
        
        title = f"Error in {module}: {error_type}"
        message = f"Error details: {error_data.get('error_message', 'No details')}"
        
        return self.create_alert(
            alert_type=AlertType.ERROR,
            priority=priority,
            title=title,
            message=message,
            metadata=error_data
        )
    
    def create_performance_alert(self,
                                metrics: Dict,
                                priority: AlertPriority = AlertPriority.MEDIUM):
        """Crea alerta de performance"""
        title = "Performance Alert"
        
        # Construir mensaje basado en métricas
        message_parts = []
        
        if metrics.get('cpu_percent', 0) > 80:
            message_parts.append(f"CPU high: {metrics['cpu_percent']:.1f}%")
        
        if metrics.get('memory_percent', 0) > 80:
            message_parts.append(f"Memory high: {metrics['memory_percent']:.1f}%")
        
        if metrics.get('latency_ms', 0) > 1000:
            message_parts.append(f"Latency high: {metrics['latency_ms']:.0f}ms")
        
        if not message_parts:
            return None
        
        message = " | ".join(message_parts)
        
        return self.create_alert(
            alert_type=AlertType.PERFORMANCE,
            priority=priority,
            title=title,
            message=message,
            metadata=metrics
        )
    
    def get_active_alerts(self,
                         alert_type: Optional[AlertType] = None,
                         priority: Optional[AlertPriority] = None,
                         max_age: Optional[timedelta] = None) -> List[Alert]:
        """Obtiene alertas activas (no reconocidas)"""
        active_alerts = []
        now = datetime.now()
        
        for alert in self.alerts.values():
            if alert.acknowledged:
                continue
            
            # Filtrar por tipo
            if alert_type and alert.type != alert_type:
                continue
            
            # Filtrar por prioridad
            if priority and alert.priority != priority:
                continue
            
            # Filtrar por edad
            if max_age and (now - alert.timestamp) > max_age:
                continue
            
            active_alerts.append(alert)
        
        # Ordenar por prioridad y timestamp
        priority_order = {
            AlertPriority.CRITICAL: 0,
            AlertPriority.HIGH: 1,
            AlertPriority.MEDIUM: 2,
            AlertPriority.LOW: 3
        }
        
        active_alerts.sort(key=lambda x: (priority_order[x.priority], x.timestamp))
        
        return active_alerts
    
    def get_alert_stats(self, hours: int = 24) -> Dict:
        """Obtiene estadísticas de alertas"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        stats = {
            "total_alerts": 0,
            "acknowledged_alerts": 0,
            "by_type": {},
            "by_priority": {},
            "recent_alerts": []
        }
        
        for alert in self.alert_history:
            if alert.timestamp < cutoff_time:
                continue
            
            stats["total_alerts"] += 1
            
            if alert.acknowledged:
                stats["acknowledged_alerts"] += 1
            
            # Por tipo
            alert_type = alert.type.value
            if alert_type not in stats["by_type"]:
                stats["by_type"][alert_type] = 0
            stats["by_type"][alert_type] += 1
            
            # Por prioridad
            priority = alert.priority.value
            if priority not in stats["by_priority"]:
                stats["by_priority"][priority] = 0
            stats["by_priority"][priority] += 1
        
        # Alertas recientes (últimas 10)
        stats["recent_alerts"] = [
            {
                "id": alert.id,
                "type": alert.type.value,
                "priority": alert.priority.value,
                "title": alert.title,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged
            }
            for alert in self.alert_history[-10:]
        ]
        
        # Calcular tasa de reconocimiento
        if stats["total_alerts"] > 0:
            stats["acknowledgement_rate"] = stats["acknowledged_alerts"] / stats["total_alerts"]
        else:
            stats["acknowledgement_rate"] = 0
        
        return stats
    
    def cleanup_old_alerts(self, days_to_keep: int = 7) -> int:
        """Limpia alertas antiguas"""
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        removed_count = 0
        
        # Limpiar alertas activas
        alerts_to_remove = []
        for alert_id, alert in self.alerts.items():
            if alert.timestamp < cutoff_time:
                alerts_to_remove.append(alert_id)
        
        for alert_id in alerts_to_remove:
            del self.alerts[alert_id]
            removed_count += 1
        
        # Limpiar historial
        self.alert_history = [
            alert for alert in self.alert_history
            if alert.timestamp >= cutoff_time
        ]
        
        if removed_count > 0:
            self.config.logger.info(f"Cleaned up {removed_count} alerts older than {days_to_keep} days")
        
        return removed_count
    
    def subscribe(self, subscriber_id: str):
        """Suscribe un componente a alertas"""
        self.subscribers.add(subscriber_id)
        self.config.logger.debug(f"Subscriber added: {subscriber_id}")
    
    def unsubscribe(self, subscriber_id: str):
        """Desuscribe un componente de alertas"""
        self.subscribers.discard(subscriber_id)
        self.config.logger.debug(f"Subscriber removed: {subscriber_id}")
    
    async def send_telegram_alert(self, alert: Alert):
        """Envía alerta por Telegram (si está configurado)"""
        if not hasattr(self.config, 'telegram') or self.config.telegram is None:
            return
        
        try:
            # Formatear mensaje
            emoji = "🚨" if alert.priority in [AlertPriority.HIGH, AlertPriority.CRITICAL] else "⚠️"
            
            message = (
                f"{emoji} *{alert.title}*\n\n"
                f"*Type:* {alert.type.value}\n"
                f"*Priority:* {alert.priority.value}\n"
                f"*Time:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"{alert.message}\n\n"
                f"ID: `{alert.id}`"
            )
            
            await self.config.telegram.send_message(message)
            
        except Exception as e:
            self.config.logger.error(f"Error sending Telegram alert: {e}")