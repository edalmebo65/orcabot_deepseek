#!/usr/bin/env python3
"""
Gestor de Configuración Integrado - Usa config.py en lugar de .env
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import sys

logger = logging.getLogger(__name__)

class ConfigIntegrator:
    """Integra config.py con el sistema optimizado"""
    
    def __init__(self):
        self.config_py = self._load_config_py()
        self.config_json = self._load_config_json()
        self.merged_config = self._merge_configs()
        
    def _load_config_py(self) -> Dict[str, Any]:
        """Carga configuración desde config.py"""
        try:
            # Dynamically import config.py
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", "config.py")
            if spec is None:
                raise ImportError("No se pudo cargar config.py")
            
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            # Extract configuration from CONFIG object
            config_data = {}
            
            # Get directories
            if hasattr(config_module, 'CONFIG'):
                config_obj = config_module.CONFIG
                
                # Extract all properties
                config_data['directories'] = {
                    'base': str(getattr(config_obj, 'BASE_DIR', Path.cwd())),
                    'logs': str(getattr(config_obj, 'LOGS_DIR', Path.cwd() / 'logs')),
                    'historical': str(getattr(config_obj, 'HISTORICO_DIR', Path.cwd() / 'historico')),
                    'security': str(getattr(config_obj, 'SECURITY_DIR', Path.cwd() / 'security')),
                    'models': str(Path.cwd() / 'models'),
                    'backup': str(Path.cwd() / 'backup')
                }
                
                # Get wallet info
                config_data['security'] = {
                    'private_key': getattr(config_obj, 'PRIVATE_KEY_B58', ''),
                    'wallet_address': getattr(config_obj, 'WALLET_ADDRESS', ''),
                    'encryption_enabled': True
                }
                
                # Get RPC configuration
                config_data['solana'] = {
                    'rpc_endpoint': getattr(config_obj, 'RPC_FULL_URL', ''),
                    'api_key': getattr(config_obj, 'HELIUS_API_KEY', ''),
                    'network': 'mainnet-beta'
                }
                
                # Get Telegram configuration
                config_data['telegram'] = {
                    'token': getattr(config_obj, 'TELEGRAM_BOT_TOKEN', ''),
                    'chat_id': getattr(config_obj, 'TELEGRAM_CHAT_ID', ''),
                    'admin_id': getattr(config_obj, 'TELEGRAM_ADMIN_ID', ''),
                    'enable_notifications': bool(getattr(config_obj, 'TELEGRAM_BOT_TOKEN', ''))
                }
                
                # Get trading parameters
                config_data['trading'] = {
                    'max_position_size_usd': getattr(config_obj, 'MAX_POSITION_SIZE_USD', 1000.0),
                    'max_portfolio_exposure': getattr(config_obj, 'MAX_PORTFOLIO_EXPOSURE', 0.15),
                    'daily_loss_limit': getattr(config_obj, 'DAILY_LOSS_LIMIT', 0.02),
                    'min_profit_margin': getattr(config_obj, 'MIN_PROFIT_MARGIN', 0.002)
                }
                
                # Get ML parameters
                config_data['ml'] = {
                    'confidence_threshold': getattr(config_obj, 'ML_CONFIDENCE_THRESHOLD', 0.68),
                    'sequence_length': getattr(config_obj, 'ML_SEQUENCE_LENGTH', 60),
                    'volatile_tokens_count': 20,
                    'max_concurrent_trades': 5
                }
                
                # Get logging
                config_data['logging'] = {
                    'level': getattr(config_obj, 'LOG_LEVEL', 'INFO'),
                    'log_security_events': True
                }
                
                logger.info("✅ Configuración cargada desde config.py")
                
            return config_data
            
        except Exception as e:
            logger.error(f"❌ Error cargando config.py: {e}")
            return {}
    
    def _load_config_json(self) -> Dict[str, Any]:
        """Carga configuración desde config.json"""
        config_path = "config.json"
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _merge_configs(self) -> Dict[str, Any]:
        """Combina config.py y config.json (prioridad a config.py)"""
        merged = self.config_json.copy()
        
        # Merge dictionaries recursively
        def deep_merge(target, source):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value
        
        deep_merge(merged, self.config_py)
        return merged
    
    def get_config(self) -> Dict[str, Any]:
        """Retorna configuración combinada"""
        return self.merged_config
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """Valida configuración requerida"""
        errors = []
        
        # Check wallet configuration
        security = self.merged_config.get('security', {})
        if not security.get('private_key'):
            errors.append("Clave privada no configurada en config.py")
        if not security.get('wallet_address'):
            errors.append("Dirección de wallet no configurada en config.py")
        
        # Check RPC configuration
        solana = self.merged_config.get('solana', {})
        if not solana.get('rpc_endpoint'):
            errors.append("Endpoint RPC no configurado en config.py")
        
        # Check trading mode
        trading_mode = self.merged_config.get('trading_mode', 'paper')
        if trading_mode not in ['paper', 'live', 'backtest']:
            errors.append(f"Modo de trading inválido: {trading_mode}")
        
        # Check directories exist
        directories = self.merged_config.get('directories', {})
        for dir_name, dir_path in directories.items():
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Error con directorio {dir_name}: {e}")
        
        return len(errors) == 0, errors
    
    def generate_config_report(self) -> str:
        """Genera reporte de configuración"""
        config = self.merged_config
        
        report_lines = [
            "📋 REPORTE DE CONFIGURACIÓN",
            "=" * 40,
            f"Fuente principal: config.py",
            f"Configuración combinada con: config.json",
            "",
            "🔐 SEGURIDAD:",
            f"  • Wallet: {config.get('security', {}).get('wallet_address', 'NO CONFIGURADA')}",
            f"  • Clave privada: {'CONFIGURADA' if config.get('security', {}).get('private_key') else 'NO CONFIGURADA'}",
            f"  • Encriptación: {'ACTIVADA' if config.get('security', {}).get('encryption_enabled', False) else 'DESACTIVADA'}",
            "",
            "🌐 SOLANA:",
            f"  • RPC: {config.get('solana', {}).get('rpc_endpoint', 'NO CONFIGURADO')}",
            f"  • API Key: {'CONFIGURADA' if config.get('solana', {}).get('api_key') else 'NO CONFIGURADA'}",
            "",
            "🤖 TRADING:",
            f"  • Modo: {config.get('trading_mode', 'paper')}",
            f"  • Tamaño máx posición: ${config.get('trading', {}).get('max_position_size_usd', 1000)}",
            f"  • Exposición máx: {config.get('trading', {}).get('max_portfolio_exposure', 0.15)*100}%",
            "",
            "📁 DIRECTORIOS:",
        ]
        
        directories = config.get('directories', {})
        for dir_name, dir_path in directories.items():
            report_lines.append(f"  • {dir_name}: {dir_path}")
        
        report_lines.extend([
            "",
            "✅ Validación: " + ("PASADA" if self.validate_config()[0] else "FALLADA"),
            "=" * 40
        ])
        
        return "\n".join(report_lines)

# Instancia global
config_integrator = ConfigIntegrator()