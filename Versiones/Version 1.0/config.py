# config.py (versión mejorada con encriptación)
import os
import base64
import logging
import sys
import re
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class SecurityManager:
    """Gestor de seguridad para encriptación/desencriptación"""
    
    @staticmethod
    def derive_key_from_env() -> Optional[bytes]:
        """Deriva la clave de encriptación desde variables de entorno"""
        try:
            password = os.getenv("ENCRYPTION_PASSWORD", "").strip()
            salt_str = os.getenv("ENCRYPTION_SALT", "").strip()
            
            if not password or not salt_str:
                logging.warning("ENCRYPTION_PASSWORD o ENCRYPTION_SALT no configurados")
                return None
            
            salt = salt_str.encode()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = kdf.derive(password.encode())
            return base64.urlsafe_b64encode(key)
            
        except Exception as e:
            logging.error(f"Error derivando clave: {e}")
            return None
    
    @classmethod
    def get_decrypted_private_key(cls) -> Optional[str]:
        """Obtiene y desencripta la clave privada"""
        try:
            encrypted_key_b64 = os.getenv("ENCRYPTED_PRIVATE_KEY", "").strip()
            if not encrypted_key_b64:
                logging.warning("ENCRYPTED_PRIVATE_KEY no configurada")
                return None
            
            encryption_key = cls.derive_key_from_env()
            if not encryption_key:
                return None
            
            cipher = Fernet(encryption_key)
            encrypted_key = base64.b64decode(encrypted_key_b64)
            decrypted_key = cipher.decrypt(encrypted_key).decode()
            
            # Validar formato Base58
            if not re.match(r'^[1-9A-HJ-NP-Za-km-z]+$', decrypted_key):
                logging.error("Clave desencriptada no tiene formato Base58 válido")
                return None
            
            return decrypted_key
            
        except Exception as e:
            logging.error(f"Error desencriptando clave privada: {e}")
            return None

class Config:
    # --- Directorios ---
    BASE_DIR = Path(os.getenv("BASE_DIR", "C:/Users/edalm/Documents/TradingAlgoritmico/OrcaBot_gemini"))
    LOGS_DIR = BASE_DIR / "logs"
    HISTORICO_DIR = BASE_DIR / "historico"
    SECURITY_DIR = BASE_DIR / "security"
    
    # --- Identidad (con encriptación) ---
    @property
    def PRIVATE_KEY_B58(self) -> str:
        """Propiedad que desencripta la clave privada bajo demanda"""
        key = SecurityManager.get_decrypted_private_key()
        if not key:
            # Fallback a la variable original (solo para migración)
            raw_key = os.getenv("PHANTOM_PRIVATE_KEY_BYTES", "").strip()
            key = "".join(re.findall(r"[1-9A-HJ-NP-Za-km-z]", raw_key))
            if key:
                logging.warning("Usando clave privada en texto plano - MIGRAR A ENCRIPTACIÓN")
        return key or ""
    
    @property
    def WALLET_ADDRESS(self) -> str:
        return os.getenv("PHANTOM_WALLET", "").strip()
    
    # --- Conectividad RPC ---
    @property
    def HELIUS_API_KEY(self) -> str:
        return os.getenv("HELIUS_VOICEINDIGO_API_KEY", "").strip()
    
    @property
    def HELIUS_BASE(self) -> str:
        return os.getenv("HELIUS_BASE_URL", "https://mainnet.helius-rpc.com").strip()
    
    @property
    def RPC_FULL_URL(self) -> str:
        return f"{self.HELIUS_BASE}/?api-key={self.HELIUS_API_KEY}"
    
    # --- Telegram ---
    @property
    def TELEGRAM_BOT_TOKEN(self) -> str:
        return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    
    @property
    def TELEGRAM_CHAT_ID(self) -> str:
        return os.getenv("TELEGRAM_CHAT_ID", "").strip()
    
    @property
    def TELEGRAM_ADMIN_ID(self) -> str:
        return os.getenv("TELEGRAM_ADMIN_ID", "").strip()
    
    # --- Trading Parameters ---
    @property
    def MAX_POSITION_SIZE_USD(self) -> float:
        return float(os.getenv("MAX_POSITION_SIZE_USD", "1000"))
    
    @property
    def MAX_PORTFOLIO_EXPOSURE(self) -> float:
        return float(os.getenv("MAX_PORTFOLIO_EXPOSURE", "0.15"))
    
    @property
    def DAILY_LOSS_LIMIT(self) -> float:
        return float(os.getenv("DAILY_LOSS_LIMIT", "0.02"))
    
    @property
    def MIN_PROFIT_MARGIN(self) -> float:
        return float(os.getenv("MIN_PROFIT_MARGIN", "0.002"))
    
    # --- ML Parameters ---
    @property
    def ML_CONFIDENCE_THRESHOLD(self) -> float:
        return float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.68"))
    
    @property
    def ML_SEQUENCE_LENGTH(self) -> int:
        return int(os.getenv("ML_SEQUENCE_LENGTH", "60"))
    
    # --- Logging ---
    @property
    def LOG_LEVEL(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO").strip().upper()
    
    @classmethod
    def setup_directories(cls):
        """Crea todos los directorios necesarios"""
        directories = [
            cls.LOGS_DIR,
            cls.HISTORICO_DIR,
            cls.SECURITY_DIR,
            cls.HISTORICO_DIR / "ohlcv",
            cls.HISTORICO_DIR / "ml_features",
            cls.HISTORICO_DIR / "trades",
            cls.HISTORICO_DIR / "models",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

# Inicializar configuración
Config.setup_directories()

# Configurar logging
log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOGS_DIR / "bot.log"),
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.LOGS_DIR / "security.log")  # Log de seguridad separado
    ]
)

# Logger principal
LOGGER = logging.getLogger("OrcaBot")

# Logger de seguridad (separado)
SECURITY_LOGGER = logging.getLogger("OrcaBot.Security")
security_handler = logging.FileHandler(Config.LOGS_DIR / "security_audit.log")
security_handler.setFormatter(logging.Formatter('%(asctime)s - SECURITY - %(message)s'))
SECURITY_LOGGER.addHandler(security_handler)
SECURITY_LOGGER.propagate = False

# Instancia de configuración
CONFIG = Config()

# Validación inicial de configuración
def validate_config():
    """Valida que la configuración mínima esté presente"""
    errors = []
    
    if not CONFIG.PRIVATE_KEY_B58:
        errors.append("Clave privada no configurada o no pudo desencriptarse")
    
    if not CONFIG.WALLET_ADDRESS:
        errors.append("Dirección de wallet no configurada")
    
    if not CONFIG.HELIUS_API_KEY:
        errors.append("API Key de Helius no configurada")
    
    if not CONFIG.TELEGRAM_BOT_TOKEN and CONFIG.TELEGRAM_BOT_TOKEN != "optional":
        errors.append("Token de Telegram bot no configurado")
    
    if errors:
        error_msg = "Errores de configuración:\n" + "\n".join(f"  • {e}" for e in errors)
        LOGGER.error(error_msg)
        raise ValueError(error_msg)
    
    LOGGER.info("✅ Configuración validada exitosamente")
    SECURITY_LOGGER.info(f"Bot inicializado para wallet: {CONFIG.WALLET_ADDRESS[:8]}...")

# Ejecutar validación al importar
try:
    validate_config()
except ValueError as e:
    LOGGER.critical(f"Configuración inválida: {e}")
    # No salir aquí para permitir tests, pero loguear crítico