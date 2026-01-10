# utils/error_handler.py
import traceback
import sys
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import json

class ErrorSeverity(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ErrorContext:
    """Contexto para errores estructurados"""
    
    def __init__(self, module: str, function: str, **kwargs):
        self.module = module
        self.function = function
        self.extra_data = kwargs
        self.timestamp = datetime.now()
        self.error_id = self._generate_error_id()
    
    def _generate_error_id(self) -> str:
        """Genera ID único para el error"""
        import hashlib
        import uuid
        
        unique_str = f"{self.module}_{self.function}_{self.timestamp.isoformat()}_{uuid.uuid4()}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:8]
    
    def to_dict(self) -> Dict:
        return {
            "error_id": self.error_id,
            "module": self.module,
            "function": self.function,
            "timestamp": self.timestamp.isoformat(),
            **self.extra_data
        }

class ErrorHandler:
    """Manejador de errores avanzado"""
    
    def __init__(self, config):
        self.config = config
        self.error_log = config.base_dir / "logs" / "errors.jsonl"
        self.error_log.touch(exist_ok=True)
        
        # Configurar logging estructurado
        self._setup_structured_logging()
        
        # Estadísticas
        self.error_stats = {
            "total_errors": 0,
            "by_severity": {s.value: 0 for s in ErrorSeverity},
            "by_module": {},
            "last_error": None
        }
    
    def _setup_structured_logging(self):
        """Configura logging estructurado en JSON"""
        import structlog
        
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        self.logger = structlog.get_logger("error_handler")
    
    def handle_error(self, 
                    error: Exception, 
                    context: ErrorContext,
                    severity: ErrorSeverity = ErrorSeverity.ERROR,
                    send_alert: bool = True) -> Dict:
        """
        Maneja un error de forma estructurada
        
        Returns: Dict con información del error
        """
        self.error_stats["total_errors"] += 1
        self.error_stats["by_severity"][severity.value] += 1
        
        # Actualizar estadísticas por módulo
        module = context.module
        self.error_stats["by_module"][module] = self.error_stats["by_module"].get(module, 0) + 1
        
        # Crear registro de error
        error_record = {
            "error_id": context.error_id,
            "timestamp": datetime.now().isoformat(),
            "severity": severity.value,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context.to_dict(),
            "stack_trace": traceback.format_exc(),
            "system_info": self._get_system_info()
        }
        
        # Escribir en log estructurado
        self._write_error_log(error_record)
        
        # Loggear según severidad
        log_method = getattr(self.logger, severity.value.lower())
        log_method("error_occurred", **error_record)
        
        # Enviar alerta si es crítica
        if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.ERROR] and send_alert:
            self._send_alert(error_record)
        
        # Actualizar último error
        self.error_stats["last_error"] = error_record
        
        return error_record
    
    def _write_error_log(self, error_record: Dict):
        """Escribe error en archivo JSONL"""
        try:
            with open(self.error_log, 'a') as f:
                f.write(json.dumps(error_record) + '\n')
        except Exception as e:
            print(f"Error escribiendo log: {e}")
    
    def _get_system_info(self) -> Dict:
        """Obtiene información del sistema"""
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
    
    def _send_alert(self, error_record: Dict):
        """Envía alerta de error"""
        try:
            if hasattr(self.config, 'telegram') and self.config.telegram:
                message = (
                    f"🚨 *Error {error_record['severity']}*\n"
                    f"ID: `{error_record['error_id']}`\n"
                    f"Módulo: `{error_record['context']['module']}`\n"
                    f"Función: `{error_record['context']['function']}`\n"
                    f"Error: `{error_record['error_type']}`\n"
                    f"Mensaje: {error_record['error_message'][:100]}..."
                )
                asyncio.create_task(self.config.telegram.send_message(message))
        except Exception as e:
            print(f"Error enviando alerta: {e}")
    
    def get_error_summary(self) -> Dict:
        """Obtiene resumen de errores"""
        return {
            "summary": self.error_stats,
            "last_hour_errors": self._get_recent_errors(hours=1),
            "most_common_errors": self._get_most_common_errors(),
            "system_health": self._calculate_system_health()
        }
    
    def _get_recent_errors(self, hours: int = 1) -> List[Dict]:
        """Obtiene errores recientes"""
        recent_errors = []
        cutoff = datetime.now().timestamp() - (hours * 3600)
        
        try:
            with open(self.error_log, 'r') as f:
                for line in f:
                    try:
                        error = json.loads(line)
                        error_time = datetime.fromisoformat(error['timestamp']).timestamp()
                        if error_time > cutoff:
                            recent_errors.append(error)
                    except:
                        continue
        except:
            pass
        
        return recent_errors
    
    def _get_most_common_errors(self, limit: int = 5) -> List[Dict]:
        """Obtiene errores más comunes"""
        error_counts = {}
        
        try:
            with open(self.error_log, 'r') as f:
                for line in f:
                    try:
                        error = json.loads(line)
                        error_key = f"{error['error_type']}:{error['context']['module']}"
                        error_counts[error_key] = error_counts.get(error_key, 0) + 1
                    except:
                        continue
        except:
            pass
        
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"error": k, "count": v} for k, v in sorted_errors[:limit]]
    
    def _calculate_system_health(self) -> float:
        """Calcula salud del sistema basado en errores"""
        recent_errors = self._get_recent_errors(hours=24)
        
        if not recent_errors:
            return 100.0
        
        # Penalizar por errores críticos
        critical_errors = [e for e in recent_errors if e['severity'] in ['CRITICAL', 'ERROR']]
        health = 100.0
        
        # -5% por cada error crítico
        health -= len(critical_errors) * 5
        
        # -1% por cada warning
        warning_errors = [e for e in recent_errors if e['severity'] == 'WARNING']
        health -= len(warning_errors) * 1
        
        return max(0.0, health)