# scripts/security.py
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import getpass

class SecurityManager:
    def __init__(self, key_file='secret.key'):
        self.key_file = key_file
        self.key = self._load_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _load_or_create_key(self):
        """Carga una clave existente o crea una nueva"""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            # Solicitar contraseña al usuario
            password = getpass.getpass("🔐 Ingresa una contraseña maestra para encriptar las variables: ")
            confirm = getpass.getpass("🔐 Confirma la contraseña: ")
            
            if password != confirm:
                raise ValueError("Las contraseñas no coinciden")
            
            # Derivar clave de la contraseña
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            
            # Guardar la clave
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            print(f"✅ Clave maestra guardada en {self.key_file}")
            return key
    
    def encrypt(self, data):
        """Encripta datos"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data):
        """Desencripta datos"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

def encrypt_variable(value):
    """Función de ayuda para encriptar una variable"""
    security = SecurityManager()
    return security.encrypt(value)

if __name__ == "__main__":
    # Prueba básica
    test_value = "test_secret"
    encrypted = encrypt_variable(test_value)
    print(f"Valor encriptado: {encrypted}")