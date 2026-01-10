# scripts/security/env_encryptor.py
import base64
import os

def encrypt_variable(value: str) -> str:
    """
    Función simple de encriptación para variables de entorno.
    En producción, usaría una solución más segura.
    """
    # Encriptación básica para desarrollo
    encoded = value.encode()
    # Rotación simple de bytes
    rotated = bytes((b + 1) % 256 for b in encoded)
    # Base64 para seguridad adicional
    return base64.b64encode(rotated).decode()

def decrypt_variable(encrypted: str) -> str:
    """Función complementaria para desencriptar"""
    decoded = base64.b64decode(encrypted)
    original = bytes((b - 1) % 256 for b in decoded)
    return original.decode()