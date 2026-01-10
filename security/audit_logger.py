# security/audit_logger.py
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class AuditEventType(Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    TRADE = "trade"
    CONFIG_CHANGE = "config_change"
    ERROR = "error"
    SECURITY = "security"
    SYSTEM = "system"

class AuditSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Evento de auditoría"""
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user: str
    action: str
    details: Dict
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "user": self.user,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success
        }

class AuditLogger:
    """Logger de auditoría para seguimiento de seguridad"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = config.base_dir / "security" / "audit.db"
        self._init_database()
        
        # Cache para eventos frecuentes
        self.event_cache: List[AuditEvent] = []
        self.max_cache_size = 100
    
    def _init_database(self):
        """Inicializa base de datos de auditoría"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de eventos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                user TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                success BOOLEAN NOT NULL
            )
        ''')
        
        # Índices para búsquedas eficientes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_severity ON audit_events(severity)')
        
        conn.commit()
        conn.close()
    
    def log_event(self, event: AuditEvent):
        """Registra un evento de auditoría"""
        # Agregar al cache
        self.event_cache.append(event)
        
        # Vaciar cache si está llena
        if len(self.event_cache) >= self.max_cache_size:
            self._flush_cache()
        
        # También loggear inmediatamente eventos críticos
        if event.severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
            self._save_event(event)
    
    def _flush_cache(self):
        """Vacía el cache a la base de datos"""
        if not self.event_cache:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for event in self.event_cache:
            self._save_event_to_db(event, cursor)
        
        conn.commit()
        conn.close()
        
        self.event_cache.clear()
    
    def _save_event(self, event: AuditEvent):
        """Guarda un evento individual"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        self._save_event_to_db(event, cursor)
        
        conn.commit()
        conn.close()
    
    def _save_event_to_db(self, event: AuditEvent, cursor):
        """Guarda evento en base de datos"""
        cursor.execute('''
            INSERT INTO audit_events 
            (timestamp, event_type, severity, user, action, details, ip_address, user_agent, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.timestamp.isoformat(),
            event.event_type.value,
            event.severity.value,
            event.user,
            event.action,
            json.dumps(event.details),
            event.ip_address,
            event.user_agent,
            1 if event.success else 0
        ))
    
    def log_trade(self, 
                 user: str, 
                 action: str, 
                 details: Dict,
                 success: bool = True):
        """Registra evento de trading"""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=AuditEventType.TRADE,
            severity=AuditSeverity.INFO if success else AuditSeverity.ERROR,
            user=user,
            action=action,
            details=details,
            success=success
        )
        
        self.log_event(event)
    
    def log_security_event(self,
                          user: str,
                          action: str,
                          details: Dict,
                          severity: AuditSeverity = AuditSeverity.WARNING):
        """Registra evento de seguridad"""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=AuditEventType.SECURITY,
            severity=severity,
            user=user,
            action=action,
            details=details
        )
        
        self.log_event(event)
    
    def log_config_change(self,
                         user: str,
                         action: str,
                         details: Dict):
        """Registra cambio de configuración"""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=AuditEventType.CONFIG_CHANGE,
            severity=AuditSeverity.INFO,
            user=user,
            action=action,
            details=details
        )
        
        self.log_event(event)
    
    def get_events(self,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None,
                  event_type: Optional[AuditEventType] = None,
                  user: Optional[str] = None,
                  severity: Optional[AuditSeverity] = None,
                  limit: int = 1000) -> List[Dict]:
        """Obtiene eventos de auditoría con filtros"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Construir query
            query = "SELECT * FROM audit_events WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value)
            
            if user:
                query += " AND user = ?"
                params.append(user)
            
            if severity:
                query += " AND severity = ?"
                params.append(severity.value)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            events = []
            for row in cursor.fetchall():
                event = {
                    "id": row[0],
                    "timestamp": row[1],
                    "event_type": row[2],
                    "severity": row[3],
                    "user": row[4],
                    "action": row[5],
                    "details": json.loads(row[6]),
                    "ip_address": row[7],
                    "user_agent": row[8],
                    "success": bool(row[9])
                }
                events.append(event)
            
            conn.close()
            return events
            
        except Exception as e:
            self.config.logger.error(f"Error getting audit events: {e}")
            return []
    
    def get_event_stats(self,
                       days: int = 30) -> Dict:
        """Obtiene estadísticas de eventos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Total eventos
            cursor.execute(
                "SELECT COUNT(*) FROM audit_events WHERE timestamp >= ?",
                (cutoff_date,)
            )
            total_events = cursor.fetchone()[0]
            
            # Eventos por tipo
            cursor.execute('''
                SELECT event_type, COUNT(*), AVG(success)*100
                FROM audit_events 
                WHERE timestamp >= ?
                GROUP BY event_type
            ''', (cutoff_date,))
            
            events_by_type = {}
            for row in cursor.fetchall():
                events_by_type[row[0]] = {
                    "count": row[1],
                    "success_rate": row[2]
                }
            
            # Eventos por severidad
            cursor.execute('''
                SELECT severity, COUNT(*)
                FROM audit_events 
                WHERE timestamp >= ?
                GROUP BY severity
            ''', (cutoff_date,))
            
            events_by_severity = {}
            for row in cursor.fetchall():
                events_by_severity[row[0]] = row[1]
            
            # Eventos por usuario
            cursor.execute('''
                SELECT user, COUNT(*), AVG(success)*100
                FROM audit_events 
                WHERE timestamp >= ?
                GROUP BY user
                ORDER BY COUNT(*) DESC
                LIMIT 10
            ''', (cutoff_date,))
            
            events_by_user = {}
            for row in cursor.fetchall():
                events_by_user[row[0]] = {
                    "count": row[1],
                    "success_rate": row[2]
                }
            
            conn.close()
            
            return {
                "period_days": days,
                "total_events": total_events,
                "events_by_type": events_by_type,
                "events_by_severity": events_by_severity,
                "top_users": events_by_user,
                "from_date": cutoff_date,
                "to_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.config.logger.error(f"Error getting event stats: {e}")
            return {}
    
    def export_events(self, 
                     output_format: str = "json",
                     output_path: Optional[Path] = None) -> bool:
        """Exporta eventos de auditoría"""
        try:
            # Obtener todos los eventos
            events = self.get_events(limit=1000000)  # 1 millón máximo
            
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = self.config.base_dir / "reports" / f"audit_export_{timestamp}"
            
            output_path.parent.mkdir(exist_ok=True)
            
            if output_format == "json":
                with open(output_path.with_suffix(".json"), 'w') as f:
                    json.dump(events, f, indent=2)
            
            elif output_format == "csv":
                import csv
                
                if events:
                    # Obtener todas las claves
                    all_keys = set()
                    for event in events:
                        all_keys.update(event.keys())
                    
                    with open(output_path.with_suffix(".csv"), 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=list(all_keys))
                        writer.writeheader()
                        writer.writerows(events)
            
            else:
                raise ValueError(f"Unsupported format: {output_format}")
            
            self.config.logger.info(f"Exported {len(events)} audit events to {output_path}")
            return True
            
        except Exception as e:
            self.config.logger.error(f"Error exporting audit events: {e}")
            return False
    
    def cleanup_old_events(self, days_to_keep: int = 365) -> int:
        """Limpia eventos antiguos"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Contar eventos a eliminar
            cursor.execute(
                "SELECT COUNT(*) FROM audit_events WHERE timestamp < ?",
                (cutoff_date,)
            )
            count_to_delete = cursor.fetchone()[0]
            
            # Eliminar eventos antiguos
            cursor.execute(
                "DELETE FROM audit_events WHERE timestamp < ?",
                (cutoff_date,)
            )
            
            conn.commit()
            
            # Vacuum para recuperar espacio
            cursor.execute("VACUUM")
            
            conn.close()
            
            if count_to_delete > 0:
                self.config.logger.info(f"Cleaned up {count_to_delete} audit events older than {days_to_keep} days")
            
            return count_to_delete
            
        except Exception as e:
            self.config.logger.error(f"Error cleaning up audit events: {e}")
            return 0