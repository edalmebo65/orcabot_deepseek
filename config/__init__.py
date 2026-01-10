# config/__init__.py (versión mejorada)
import os
import json
import base64
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_DOWN
import logging

class Timeframe(Enum):
    """Marcos temporales disponibles"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

@dataclass
class CapitalManagementConfig:
    """Configuración de gestión de capital"""
    
    # Límites por operación
    max_capital_per_trade_pct: Decimal = Decimal('0.10')  # 10% del capital
    max_capital_per_trade_usdc: Optional[Decimal] = None  # Límite absoluto en USDC
    
    # Operaciones simultáneas
    max_concurrent_operations: int = 5
    min_capital_available_for_new_trade: Decimal = Decimal('0.05')  # 5% mínimo disponible
    
    # Distribución de capital
    capital_reserve_pct: Decimal = Decimal('0.20')  # 20% en reserva
    max_portfolio_exposure_pct: Decimal = Decimal('0.50')  # 50% exposición máxima
    
    # Umbrales de riesgo
    risk_zero_buffer_pct: Decimal = Decimal('0.002')  # 0.2% buffer para riesgo cero
    stop_loss_pct: Decimal = Decimal('0.02')  # Stop loss inicial 2%
    take_profit_pct: Decimal = Decimal('0.05')  # Take profit inicial 5%
    
    # Trailing stop
    trailing_stop_activation_pct: Decimal = Decimal('0.005')  # Activa a 0.5% ganancia
    trailing_stop_distance_pct: Decimal = Decimal('0.002')  # Distancia 0.2%

@dataclass
class TradingConfig:
    """Configuración completa de trading"""
    
    # Gestión de capital
    capital: CapitalManagementConfig = field(default_factory=CapitalManagementConfig)
    
    # Timeframes activos
    active_timeframes: list = field(default_factory=lambda: [
        Timeframe.M5.value,
        Timeframe.M15.value,
        Timeframe.H1.value
    ])
    
    # Configuración Orca
    max_slippage_bps: int = 50  # 0.5%
    priority_fee_micro_lamports: int = 100000  # 0.0001 SOL
    min_pool_liquidity_usd: Decimal = Decimal('10000')  # $10k mínimo
    
    # Comisiones y fees
    orca_fee_pct: Decimal = Decimal('0.0025')  # 0.25% fee de Orca
    network_fee_estimate_sol: Decimal = Decimal('0.00001')  # Estimado por transacción
    
    # Umbrales de operación
    min_profit_threshold_pct: Decimal = Decimal('0.002')  # 0.2% ganancia mínima
    min_volume_requirement_usd: Dict[str, Decimal] = field(default_factory=lambda: {
        '1m': Decimal('10000'),
        '5m': Decimal('25000'),
        '15m': Decimal('50000'),
        '1h': Decimal('100000')
    })
    
    # Cooldowns y límites temporales
    trade_cooldown_minutes: int = 1  # 1 minuto entre trades del mismo asset
    max_trades_per_hour: int = 10
    daily_trade_limit: int = 50
    
    def validate(self):
        """Valida que la configuración sea coherente"""
        errors = []
        
        if self.capital.max_capital_per_trade_pct > Decimal('0.50'):
            errors.append("max_capital_per_trade_pct no puede ser mayor al 50%")
        
        if self.capital.max_concurrent_operations > 10:
            errors.append("max_concurrent_operations no puede ser mayor a 10")
        
        if self.capital.max_portfolio_exposure_pct > Decimal('1.0'):
            errors.append("max_portfolio_exposure_pct no puede ser mayor a 100%")
        
        if errors:
            raise ValueError(f"Errores en configuración: {', '.join(errors)}")

class Config:
    """Configuración principal del bot"""
    
    def __init__(self, encrypted_env_path: str = ".env.encrypted"):
        self.base_dir = Path(__file__).parent.parent
        self._load_encrypted_env(encrypted_env_path)
        
        # Configuración de trading
        self.trading = TradingConfig()
        self.trading.validate()
        
        # Configuración ML
        self.ml_confidence_threshold = 0.75
        self.top_assets_to_analyze = 20
        self.retrain_interval_hours = 6
        self.ml_sequence_length = 60
        
        # Directorios
        self._setup_directories()
        
        # Estado del bot
        self.current_capital_usdc = Decimal('0')
        self.active_operations = 0
        self.daily_trades_count = 0
        
        # Inicializar logger
        self._setup_logging()
    
    def _load_encrypted_env(self, env_path: str):
        """Carga variables encriptadas desde archivo"""
        try:
            if not os.path.exists(env_path):
                raise FileNotFoundError(f"Archivo encriptado no encontrado: {env_path}")
            
            with open(env_path, 'r') as f:
                encrypted_data = json.load(f)
            
            # Solicitar master password
            from security.env_encryptor import SystemEnvEncryptor
            print("🔐 Desencriptando configuración...")
            encryptor = SystemEnvEncryptor()
            
            # Desencriptar variables
            self.HELIUS_RPC_URL = encryptor.decrypt_variable(
                encrypted_data['variables']['HELIUS_RPC_URL']
            )
            self.HELIUS_API_KEY = encryptor.decrypt_variable(
                encrypted_data['variables']['HELIUS_VOICEINDIGO_API_KEY']
            )
            self.PHANTOM_WALLET = encryptor.decrypt_variable(
                encrypted_data['variables']['PHANTOM_WALLET']
            )
            self.PHANTOM_PRIVATE_KEY = encryptor.decrypt_variable(
                encrypted_data['variables']['PHANTOM_PRIVATE_KEY_BYTE']
            )
            self.TELEGRAM_BOT_TOKEN = encryptor.decrypt_variable(
                encrypted_data['variables']['TELEGRAM_BOT_TOKEN']
            )
            self.TELEGRAM_CHAT_ID = encryptor.decrypt_variable(
                encrypted_data['variables']['TELEGRAM_CHAT_ID']
            )
            
            # Construir URL completa
            self.RPC_ENDPOINT = f"{self.HELIUS_RPC_URL}?api-key={self.HELIUS_API_KEY}"
            
            print("✅ Configuración desencriptada exitosamente")
            
        except Exception as e:
            raise ValueError(f"Error cargando configuración encriptada: {e}")
    
    def _setup_directories(self):
        """Crea estructura de directorios"""
        directories = [
            self.base_dir / "logs",
            self.base_dir / "data" / "training",
            self.base_dir / "data" / "live",
            self.base_dir / "data" / "signals",
            self.base_dir / "models",
            self.base_dir / "state",
            self.base_dir / "reports",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _setup_logging(self):
        """Configura sistema de logging"""
        log_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Logger principal
        self.logger = logging.getLogger("OrcaBot")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(self.base_dir / "logs" / "bot.log")
        file_handler.setFormatter(log_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        self.logger.addHandler(console_handler)
        
        # Logger de operaciones
        self.trade_logger = logging.getLogger("OrcaBot.Trades")
        trade_handler = logging.FileHandler(self.base_dir / "logs" / "trades.log")
        trade_handler.setFormatter(log_formatter)
        self.trade_logger.addHandler(trade_handler)
        self.trade_logger.propagate = False
    
    def get_max_trade_amount_usdc(self) -> Decimal:
        """
        Calcula el monto máximo por operación en USDC
        Considera: 10% del capital o límite absoluto si está configurado
        """
        if not self.current_capital_usdc:
            return Decimal('0')
        
        # Calcular 10% del capital
        max_by_percentage = self.current_capital_usdc * self.trading.capital.max_capital_per_trade_pct
        
        # Si hay límite absoluto, tomar el menor
        if self.trading.capital.max_capital_per_trade_usdc:
            max_amount = min(max_by_percentage, self.trading.capital.max_capital_per_trade_usdc)
        else:
            max_amount = max_by_percentage
        
        # Redondear a 2 decimales (centavos de USDC)
        return max_amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    
    def can_open_new_operation(self, estimated_cost_usdc: Decimal) -> tuple[bool, str]:
        """
        Verifica si se puede abrir una nueva operación
        Returns: (puede_abrir, mensaje)
        """
        # Verificar límite de operaciones simultáneas
        if self.active_operations >= self.trading.capital.max_concurrent_operations:
            return False, f"Máximo de {self.trading.capital.max_concurrent_operations} operaciones activas"
        
        # Verificar capital disponible
        max_trade_amount = self.get_max_trade_amount_usdc()
        if estimated_cost_usdc > max_trade_amount:
            return False, f"Costo estimado (${estimated_cost_usdc}) excede máximo por operación (${max_trade_amount})"
        
        # Verificar exposición total del portfolio
        current_exposure = self._calculate_current_exposure()
        max_exposure = self.current_capital_usdc * self.trading.capital.max_portfolio_exposure_pct
        
        if current_exposure + estimated_cost_usdc > max_exposure:
            return False, f"Nueva operación excedería exposición máxima del portfolio"
        
        # Verificar límite diario de operaciones
        if self.daily_trades_count >= self.trading.daily_trade_limit:
            return False, f"Límite diario de {self.trading.daily_trade_limit} operaciones alcanzado"
        
        return True, "✅ Puede abrir nueva operación"
    
    def _calculate_current_exposure(self) -> Decimal:
        """Calcula exposición actual del portfolio (simplificado)"""
        # En implementación real, esto leería de la base de datos de operaciones
        return Decimal('0')  # Placeholder
    
    def update_capital(self, new_capital_usdc: Decimal):
        """Actualiza el capital disponible"""
        self.current_capital_usdc = new_capital_usdc
        self._save_state()
    
    def increment_active_operations(self):
        """Incrementa contador de operaciones activas"""
        self.active_operations += 1
        self._save_state()
    
    def decrement_active_operations(self):
        """Decrementa contador de operaciones activas"""
        self.active_operations = max(0, self.active_operations - 1)
        self._save_state()
    
    def increment_daily_trades(self):
        """Incrementa contador de trades diarios"""
        self.daily_trades_count += 1
        self._save_state()
    
    def _save_state(self):
        """Guarda el estado actual del bot"""
        state = {
            'current_capital_usdc': str(self.current_capital_usdc),
            'active_operations': self.active_operations,
            'daily_trades_count': self.daily_trades_count,
            'last_update': datetime.now().isoformat()
        }
        
        with open(self.base_dir / "state" / "bot_state.json", 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self):
        """Carga el estado guardado del bot"""
        state_path = self.base_dir / "state" / "bot_state.json"
        if state_path.exists():
            with open(state_path, 'r') as f:
                state = json.load(f)
                self.current_capital_usdc = Decimal(state.get('current_capital_usdc', '0'))
                self.active_operations = state.get('active_operations', 0)
                self.daily_trades_count = state.get('daily_trades_count', 0)

# Instancia global de configuración
CONFIG = Config()