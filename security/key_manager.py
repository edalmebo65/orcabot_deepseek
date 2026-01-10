# security/key_manager.py
import os
import base64
import hashlib
import secrets
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class KeyManager:
    """Gestor seguro de claves criptográficas"""
    
    def __init__(self, config):
        self.config = config
        self.keys_dir = config.base_dir / "security" / "keys"
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache de claves en memoria (encriptadas)
        self.key_cache: Dict[str, bytes] = {}
        self.cache_timeout = timedelta(minutes=5)
        self.cache_expiry: Dict[str, datetime] = {}
        
        # Rotación de claves
        self.key_rotation_days = 30
        self.last_rotation_check = datetime.now()
    
    def generate_key_pair(self, 
                         key_name: str,
                         key_type: str = "aes") -> Tuple[bytes, bytes]:
        """
        Genera par de claves (pública/privada o clave/iv)
        """
        if key_type == "aes":
            # AES-256
            key = secrets.token_bytes(32)  # 256 bits
            iv = secrets.token_bytes(16)   # 128 bits
            return key, iv
        
        elif key_type == "fernet":
            # Fernet (AES-128 en CBC mode con HMAC)
            key = Fernet.generate_key()
            return key, b""  # Fernet maneja IV internamente
        
        elif key_type == "hmac":
            # HMAC key
            key = secrets.token_bytes(32)
            return key, b""
        
        else:
            raise ValueError(f"Unsupported key type: {key_type}")
    
    def encrypt_data(self, 
                    data: bytes, 
                    key_name: str,
                    key_type: str = "aes") -> bytes:
        """
        Encripta datos usando la clave especificada
        """
        # Obtener o generar clave
        key, iv = self._get_or_create_key(key_name, key_type)
        
        if key_type == "aes":
            # AES-256-GCM
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            encrypted = encryptor.update(data) + encryptor.finalize()
            return base64.b64encode(iv + encryptor.tag + encrypted)
        
        elif key_type == "fernet":
            # Fernet
            fernet = Fernet(key)
            return fernet.encrypt(data)
        
        else:
            raise ValueError(f"Unsupported encryption type: {key_type}")
    
    def decrypt_data(self, 
                    encrypted_data: bytes, 
                    key_name: str,
                    key_type: str = "aes") -> bytes:
        """
        Desencripta datos usando la clave especificada
        """
        # Obtener clave
        key, iv = self._get_key(key_name, key_type)
        
        if key is None:
            raise ValueError(f"Key {key_name} not found")
        
        if key_type == "aes":
            # Decodificar y separar componentes
            decoded = base64.b64decode(encrypted_data)
            iv = decoded[:16]
            tag = decoded[16:32]
            ciphertext = decoded[32:]
            
            # AES-256-GCM
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            return decryptor.update(ciphertext) + decryptor.finalize()
        
        elif key_type == "fernet":
            # Fernet
            fernet = Fernet(key)
            return fernet.decrypt(encrypted_data)
        
        else:
            raise ValueError(f"Unsupported decryption type: {key_type}")
    
    def _get_or_create_key(self, 
                          key_name: str, 
                          key_type: str) -> Tuple[bytes, bytes]:
        """Obtiene o crea una clave"""
        key_path = self.keys_dir / f"{key_name}_{key_type}.key"
        iv_path = self.keys_dir / f"{key_name}_{key_type}.iv"
        
        if key_path.exists() and iv_path.exists():
            # Cargar clave existente
            with open(key_path, 'rb') as f:
                key = f.read()
            with open(iv_path, 'rb') as f:
                iv = f.read()
        else:
            # Generar nueva clave
            key, iv = self.generate_key_pair(key_name, key_type)
            
            # Guardar de forma segura
            self._save_key(key_name, key_type, key, iv)
        
        # Cache en memoria (encriptado)
        cache_key = f"{key_name}_{key_type}"
        self.key_cache[cache_key] = self._encrypt_for_cache(key)
        self.cache_expiry[cache_key] = datetime.now() + self.cache_timeout
        
        return key, iv
    
    def _get_key(self, 
                key_name: str, 
                key_type: str) -> Tuple[Optional[bytes], Optional[bytes]]:
        """Obtiene una clave del cache o disco"""
        cache_key = f"{key_name}_{key_type}"
        
        # Verificar cache
        if (cache_key in self.key_cache and 
            cache_key in self.cache_expiry and
            datetime.now() < self.cache_expiry[cache_key]):
            
            cached_key = self._decrypt_from_cache(self.key_cache[cache_key])
            
            # Cargar IV del disco
            iv_path = self.keys_dir / f"{key_name}_{key_type}.iv"
            if iv_path.exists():
                with open(iv_path, 'rb') as f:
                    iv = f.read()
                return cached_key, iv
        
        # Cargar del disco
        key_path = self.keys_dir / f"{key_name}_{key_type}.key"
        iv_path = self.keys_dir / f"{key_name}_{key_type}.iv"
        
        if key_path.exists() and iv_path.exists():
            with open(key_path, 'rb') as f:
                key = f.read()
            with open(iv_path, 'rb') as f:
                iv = f.read()
            
            # Actualizar cache
            self.key_cache[cache_key] = self._encrypt_for_cache(key)
            self.cache_expiry[cache_key] = datetime.now() + self.cache_timeout
            
            return key, iv
        
        return None, None
    
    def _save_key(self, 
                 key_name: str, 
                 key_type: str, 
                 key: bytes, 
                 iv: bytes):
        """Guarda clave de forma segura"""
        # Encriptar clave para almacenamiento
        master_key = self._get_master_key()
        encrypted_key = self._encrypt_with_master(key, master_key)
        
        # Guardar
        key_path = self.keys_dir / f"{key_name}_{key_type}.key"
        iv_path = self.keys_dir / f"{key_name}_{key_type}.iv"
        
        with open(key_path, 'wb') as f:
            f.write(encrypted_key)
        os.chmod(key_path, 0o600)
        
        with open(iv_path, 'wb') as f:
            f.write(iv)
        os.chmod(iv_path, 0o600)
    
    def _get_master_key(self) -> bytes:
        """Obtiene clave maestra desde variables de entorno"""
        master_key_env = os.getenv("MASTER_ENCRYPTION_KEY")
        
        if not master_key_env:
            # Generar y almacenar si no existe
            master_key_env = base64.b64encode(secrets.token_bytes(32)).decode()
            
            # En un entorno real, esto se guardaría en un key manager
            # como AWS KMS, HashiCorp Vault, etc.
            self.config.logger.warning(
                "MASTER_ENCRYPTION_KEY not found in environment. "
                "Generated temporary key. In production, use a proper key management system."
            )
        
        return base64.b64decode(master_key_env)
    
    def _encrypt_with_master(self, data: bytes, master_key: bytes) -> bytes:
        """Encripta datos con clave maestra"""
        # Deriva una clave para AES
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"fixed_salt_for_key_encryption",  # En producción usar salt único
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(master_key)
        iv = secrets.token_bytes(16)
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        encrypted = encryptor.update(data) + encryptor.finalize()
        return base64.b64encode(iv + encryptor.tag + encrypted)
    
    def _decrypt_with_master(self, encrypted_data: bytes, master_key: bytes) -> bytes:
        """Desencripta datos con clave maestra"""
        # Decodificar
        decoded = base64.b64decode(encrypted_data)
        iv = decoded[:16]
        tag = decoded[16:32]
        ciphertext = decoded[32:]
        
        # Deriva clave
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"fixed_salt_for_key_encryption",
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(master_key)
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        return decryptor.update(ciphertext) + decryptor.finalize()
    
    def _encrypt_for_cache(self, data: bytes) -> bytes:
        """Encripta datos para cache en memoria"""
        # Usar una clave efímera para cache
        cache_key = hashlib.sha256(str(datetime.now().timestamp()).encode()).digest()[:32]
        iv = secrets.token_bytes(16)
        
        cipher = Cipher(
            algorithms.AES(cache_key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        encrypted = encryptor.update(data) + encryptor.finalize()
        return base64.b64encode(iv + encryptor.tag + encrypted)
    
    def _decrypt_from_cache(self, encrypted_data: bytes) -> bytes:
        """Desencripta datos del cache"""
        # Asume que la última clave efímera aún es válida
        # En implementación real, se manejaría mejor
        try:
            decoded = base64.b64decode(encrypted_data)
            iv = decoded[:16]
            tag = decoded[16:32]
            ciphertext = decoded[32:]
            
            # Recrear clave efímera (mismo método que encriptación)
            cache_key = hashlib.sha256(str(datetime.now().timestamp()).encode()).digest()[:32]
            
            cipher = Cipher(
                algorithms.AES(cache_key),
                modes.GCM(iv, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            return decryptor.update(ciphertext) + decryptor.finalize()
        except:
            # Si falla, retornar datos vacíos
            return b""
    
    def rotate_keys(self, force: bool = False) -> Dict[str, bool]:
        """
        Rota las claves según política de rotación
        """
        results = {}
        now = datetime.now()
        
        # Verificar si es tiempo de rotación
        if not force and (now - self.last_rotation_check).days < self.key_rotation_days:
            return {"skipped": "Not time for rotation yet"}
        
        # Rotar cada clave
        for key_file in self.keys_dir.glob("*.key"):
            key_name = key_file.stem.replace(".key", "")
            key_type = key_name.split("_")[-1]
            key_name_base = "_".join(key_name.split("_")[:-1])
            
            # Obtener clave actual
            key, iv = self._get_key(key_name_base, key_type)
            
            if key:
                # Generar nueva clave
                new_key, new_iv = self.generate_key_pair(key_name_base, key_type)
                
                # Re-encriptar cualquier dato que use esta clave
                # (en implementación real, se manejaría migración de datos)
                
                # Guardar nueva clave
                self._save_key(key_name_base, key_type, new_key, new_iv)
                
                results[f"{key_name_base}_{key_type}"] = True
        
        self.last_rotation_check = now
        
        if results:
            self.config.logger.info(f"Rotated {len(results)} keys")
        
        return results
    
    def get_key_status(self) -> Dict:
        """Obtiene estado de las claves"""
        status = {
            "total_keys": 0,
            "key_types": {},
            "rotation_due": False,
            "cache_size": len(self.key_cache)
        }
        
        # Contar claves por tipo
        for key_file in self.keys_dir.glob("*.key"):
            status["total_keys"] += 1
            
            key_name = key_file.stem
            key_type = key_name.split("_")[-1]
            
            if key_type not in status["key_types"]:
                status["key_types"][key_type] = 0
            status["key_types"][key_type] += 1
        
        # Verificar rotación
        days_since_check = (datetime.now() - self.last_rotation_check).days
        status["rotation_due"] = days_since_check >= self.key_rotation_days
        status["days_since_last_check"] = days_since_check
        
        return status
    
    def clear_cache(self):
        """Limpia cache de claves en memoria"""
        self.key_cache.clear()
        self.cache_expiry.clear()
        self.config.logger.info("Cleared key cache")