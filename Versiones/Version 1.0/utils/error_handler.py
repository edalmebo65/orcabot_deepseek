# utils/error_handler.py
import logging
import traceback
from datetime import datetime
from typing import Dict, Any
import json
from pathlib import Path

class ErrorHandler:
    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir
        self.error_log = logs_dir / "errors.jsonl"
        self.error_log.touch(exist_ok=True)
        
        # Configurar logger estructurado
        self.logger = logging.getLogger("ErrorHandler")
        self._setup_structured_logging()
    
    def _setup_structured_logging(self):
        """Configura logging estructurado en JSON"""
        handler = logging.FileHandler(self.logs_dir / "structured_errors.log")
        
        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                log_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }
                
                if record.exc_info:
                    log_record["exception"] = self.formatException(record.exc_info)
                    log_record["stack_trace"] = traceback.format_stack()
                
                return json.dumps(log_record)
        
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)
    
    def log_error(self, 
                  error: Exception, 
                  context: Dict[str, Any] = None,
                  severity: str = "ERROR"):
        """Registra error con contexto estructurado"""
        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "stack_trace": traceback.format_exc(),
        }
        
        # Escribir en JSONL
        with open(self.error_log, 'a') as f:
            f.write(json.dumps(error_data) + '\n')
        
        # También en logger estructurado
        self.logger.error(f"Error: {error}", extra=error_data)
        
        # Alerta por Telegram si es crítico
        if severity in ["CRITICAL", "FATAL"]:
            self.send_telegram_alert(error_data)
    
    def send_telegram_alert(self, error_data: Dict):
        """Envía alerta crítica a Telegram"""
        try:
            message = f"🚨 **ERROR CRÍTICO DETECTADO**\n\n"
            message += f"Tipo: {error_data['error_type']}\n"
            message += f"Mensaje: {error_data['error_message'][:200]}...\n"
            message += f"Módulo: {error_data['context'].get('module', 'N/A')}\n"
            
            # Implementar envío a Telegram...
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")