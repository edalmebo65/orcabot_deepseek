# scripts/encrypt_key.py
import os
import base64
import logging
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()

def derive_encryption_key(password: str, salt: str) -> bytes:
    """
    Deriva una clave criptográfica segura usando PBKDF2
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode(),
        iterations=100000,
    )
    key = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(key)

def encrypt_private_key():
    """
    Lee la clave privada del .env, la encripta y actualiza el archivo
    """
    try:
        # Obtener valores del .env
        raw_private_key = os.getenv("PHANTOM_PRIVATE_KEY_BYTES", "").strip()
        encryption_password = os.getenv("ENCRYPTION_PASSWORD", "")
        encryption_salt = os.getenv("ENCRYPTION_SALT", "")
        
        if not raw_private_key:
            raise ValueError("PHANTOM_PRIVATE_KEY_BYTES no encontrado en .env")
        
        if not encryption_password or not encryption_salt:
            raise ValueError("ENCRYPTION_PASSWORD o ENCRYPTION_SALT no configurados")
        
        # Derivar clave de encriptación
        encryption_key = derive_encryption_key(encryption_password, encryption_salt)
        
        # Crear cipher Fernet
        cipher = Fernet(encryption_key)
        
        # Encriptar clave privada
        encrypted_key = cipher.encrypt(raw_private_key.encode())
        encrypted_key_b64 = base64.b64encode(encrypted_key).decode()
        
        # Leer archivo .env actual
        env_path = Path(".env")
        if not env_path.exists():
            raise FileNotFoundError("Archivo .env no encontrado")
        
        with open(env_path, "r") as f:
            lines = f.readlines()
        
        # Actualizar línea ENCRYPTED_PRIVATE_KEY
        new_lines = []
        key_updated = False
        
        for line in lines:
            if line.startswith("ENCRYPTED_PRIVATE_KEY="):
                new_lines.append(f'ENCRYPTED_PRIVATE_KEY="{encrypted_key_b64}"\n')
                key_updated = True
            else:
                new_lines.append(line)
        
        if not key_updated:
            # Agregar si no existe
            new_lines.append(f'\nENCRYPTED_PRIVATE_KEY="{encrypted_key_b64}"\n')
        
        # Escribir archivo actualizado
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        
        # Eliminar clave privada en texto plano del archivo (OPCIONAL PERI RECOMENDADO)
        # Descomentar solo después de verificar que la encriptación funciona
        
        # for i, line in enumerate(new_lines):
        #     if line.startswith("PHANTOM_PRIVATE_KEY_BYTES="):
        #         new_lines[i] = '# PHANTOM_PRIVATE_KEY_BYTES="[ENCRIPTADA]"\n'
        
        # with open(env_path, "w") as f:
        #     f.writelines(new_lines)
        
        print("✅ Clave privada encriptada exitosamente")
        print(f"🔐 Clave encriptada: {encrypted_key_b64[:50]}...")
        
        # Generar archivo de recuperación de emergencia
        generate_emergency_recovery_file(encrypted_key_b64)
        
    except Exception as e:
        print(f"❌ Error encriptando clave: {e}")
        logging.error(f"Error en encrypt_private_key: {e}")

def generate_emergency_recovery_file(encrypted_key: str):
    """
    Genera archivo de recuperación de emergencia (guardar en lugar seguro)
    """
    recovery_data = {
        "encrypted_private_key": encrypted_key,
        "salt": os.getenv("ENCRYPTION_SALT"),
        "timestamp": datetime.now().isoformat(),
        "wallet_address": os.getenv("PHANTOM_WALLET"),
        "note": "GUARDAR EN LUGAR SEGURO FUERA DEL SERVIDOR"
    }
    
    recovery_path = Path("emergency_recovery.json")
    with open(recovery_path, "w") as f:
        json.dump(recovery_data, f, indent=2)
    
    print(f"📄 Archivo de recuperación generado: {recovery_path}")
    print("⚠️  GUARDAR ESTE ARCHIVO EN LUGAR SEGURO Y LUEGO ELIMINARLO DEL SERVIDOR")

def decrypt_private_key_locally():
    """
    Función para desencriptar la clave (solo para pruebas locales)
    """
    try:
        encrypted_key_b64 = os.getenv("ENCRYPTED_PRIVATE_KEY", "")
        password = os.getenv("ENCRYPTION_PASSWORD", "")
        salt = os.getenv("ENCRYPTION_SALT", "")
        
        if not encrypted_key_b64:
            raise ValueError("ENCRYPTED_PRIVATE_KEY no configurada")
        
        # Derivar clave
        encryption_key = derive_encryption_key(password, salt)
        cipher = Fernet(encryption_key)
        
        # Desencriptar
        encrypted_key = base64.b64decode(encrypted_key_b64)
        decrypted_key = cipher.decrypt(encrypted_key).decode()
        
        print(f"✅ Clave desencriptada (primeros 10 chars): {decrypted_key[:10]}...")
        return decrypted_key
        
    except Exception as e:
        print(f"❌ Error desencriptando: {e}")
        return None

if __name__ == "__main__":
    import sys
    from datetime import datetime
    import json
    
    if len(sys.argv) > 1 and sys.argv[1] == "decrypt":
        # Solo para pruebas - NO USAR EN PRODUCCIÓN
        print("🔓 Modo prueba - Desencriptando clave...")
        decrypt_private_key_locally()
    else:
        print("🔐 Iniciando encriptación de clave privada...")
        encrypt_private_key()