# quick_fix.py
"""
Solución rápida para clave de 66 bytes
"""
import base64
import os

# Tu clave actual (cámbiala por la tuya)
current_key = "5CQjsXo9k8vkK1oPuzJSMuYJ6v2BwWBqtG2xCSTgUc2cHFxK"  # Tus 88 caracteres

# Decodificar
decoded = base64.b64decode(current_key)
print(f"Bytes originales: {len(decoded)}")  # Debería ser 66

# ESTRATEGIA MÁS COMÚN: Quitar los primeros 2 bytes
# (En muchos formatos, los primeros bytes son metadatos)
fixed_bytes = decoded[2:]  # Esto debería darte 64 bytes
print(f"Bytes corregidos: {len(fixed_bytes)}")  # Debería ser 64

# Convertir a Base64
fixed_key = base64.b64encode(fixed_bytes).decode()
print(f"\nNueva clave Base64 (64 bytes):")
print(fixed_key)