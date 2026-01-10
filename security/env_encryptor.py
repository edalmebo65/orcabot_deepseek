# security/env_encryptor.py
import os
import json
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from pathlib import Path
import getpass
import sys

class SystemEnvEncryptor:
    """Encripta variables de entorno del sistema para uso seguro"""
    
    def __init__(self, master_password=None):
        self.master_password = master_password or getpass.getpass("🔐 Master Password: ")
        self.salt = self._generate_salt()
        self.encryption_key = self._derive_key()
        self.cipher = Fernet(self.encryption_key)
        
    def _generate_salt(self):
        """Genera salt único basado en hardware"""
        try:
            import uuid
            import platform
            import socket
            
            # Combinar identificadores únicos del sistema
            system_info = f"{platform.node()}-{socket.gethostname()}-{uuid.getnode()}"
            return hashlib.sha256(system_info.encode()).digest()[:16]
            
        except Exception:
            # Fallback a salt aleatorio
            return os.urandom(16)
    
    def _derive_key(self):
        """Deriva clave de encriptación usando PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(self.master_password.encode())
        return base64.urlsafe_b64encode(key)
    
    def encrypt_variable(self, variable_name, value):
        """Encripta una variable individual"""
        encrypted = self.cipher.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_variable(self, encrypted_value):
        """Desencripta una variable"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_value.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Error desencriptando: {e}")
    
    def read_system_env_vars(self):
        """Lee variables críticas del sistema"""
        env_vars = {}
        
        # Variables requeridas
        required_vars = {
            'HELIUS_RPC_URL': os.environ.get('HELIUS_RPC_URL'),
            'HELIUS_VOICEINDIGO_API_KEY': os.environ.get('HELIUS_VOICEINDIGO_API_KEY'),
            'PHANTOM_WALLET': os.environ.get('PHANTOM_WALLET'),
            'PHANTOM_PRIVATE_KEY_BYTE': os.environ.get('PHANTOM_PRIVATE_KEY_BYTE'),
            'TELEGRAM_BOT_TOKEN': os.environ.get('TELEGRAM_BOT_TOKEN'),
            'TELEGRAM_CHAT_ID': os.environ.get('TELEGRAM_CHAT_ID'),
        }
        
        # Validar que todas existan
        missing_vars = [k for k, v in required_vars.items() if not v]
        if missing_vars:
            raise ValueError(f"Variables faltantes en sistema: {missing_vars}")
        
        return required_vars
    
    def create_encrypted_env_file(self, output_path=".env.encrypted"):
        """Crea archivo .env.encrypted con variables encriptadas"""
        env_vars = self.read_system_env_vars()
        
        encrypted_data = {
            'salt': base64.b64encode(self.salt).decode(),
            'variables': {}
        }
        
        for name, value in env_vars.items():
            encrypted_data['variables'][name] = self.encrypt_variable(name, value)
        
        with open(output_path, 'w') as f:
            json.dump(encrypted_data, f, indent=2)
        
        # Establecer permisos seguros
        os.chmod(output_path, 0o600)
        
        print(f"✅ Archivo encriptado creado: {output_path}")
        print(f"⚠️  Guarda tu master password en lugar seguro!")
        
        return output_path

# Script de inicialización
if __name__ == "__main__":
    encryptor = SystemEnvEncryptor()
    encryptor.create_encrypted_env_file()