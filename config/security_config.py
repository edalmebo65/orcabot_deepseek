# config/security_config.py
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional

class SecurityConfig:
    """Configuración de seguridad avanzada"""
    
    # Algoritmos de encriptación
    ENCRYPTION_ALGORITHM = "AES-256-GCM"
    KDF_ITERATIONS = 100000
    SALT_LENGTH = 16
    
    # Configuración de claves
    KEY_ROTATION_DAYS = 30
    MAX_KEY_USAGE = 1000
    
    # Políticas de seguridad
    MAX_LOGIN_ATTEMPTS = 5
    SESSION_TIMEOUT_MINUTES = 30
    REQUIRE_2FA = True
    
    # Configuración de auditoría
    AUDIT_LOG_RETENTION_DAYS = 365
    ENABLE_REAL_TIME_MONITORING = True
    
    @staticmethod
    def generate_salt() -> bytes:
        """Genera un salt criptográficamente seguro"""
        return os.urandom(SecurityConfig.SALT_LENGTH)
    
    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """Deriva una clave usando PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=SecurityConfig.KDF_ITERATIONS,
        )
        key = kdf.derive(password.encode())
        return base64.urlsafe_b64encode(key)
    
    @classmethod
    def get_encryption_settings(cls) -> dict:
        """Retorna configuración de encriptación"""
        return {
            "algorithm": cls.ENCRYPTION_ALGORITHM,
            "kdf_iterations": cls.KDF_ITERATIONS,
            "key_rotation_days": cls.KEY_ROTATION_DAYS,
            "require_2fa": cls.REQUIRE_2FA
        }