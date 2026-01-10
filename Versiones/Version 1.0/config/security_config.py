# config/security_config.py
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional

class SecurityConfig:
    """Configuración avanzada de seguridad con HSM simulado"""
    
    # Derivación de clave a partir de variables de entorno
    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    @classmethod
    def get_encrypted_key(cls) -> Optional[str]:
        """Recupera y desencripta la clave privada"""
        try:
            encrypted_key = os.getenv("ENCRYPTED_PRIVATE_KEY")
            if not encrypted_key:
                return None
            
            # Usar KMS o HSM en producción
            salt = os.getenv("ENCRYPTION_SALT", "default_salt").encode()
            password = os.getenv("ENCRYPTION_PASSWORD", "")
            
            key = cls.derive_key(password, salt)
            cipher = Fernet(key)
            
            return cipher.decrypt(encrypted_key.encode()).decode()
        except Exception as e:
            logging.error(f"Error decrypting key: {e}")
            return None