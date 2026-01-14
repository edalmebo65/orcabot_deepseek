# verify_fixed_key.py
"""
Verificar que la clave y dirección coincidan
"""
import os
import base64
from solders.keypair import Keypair

print("✅ VERIFICACIÓN DE CLAVE/DIRECCIÓN")
print("="*50)

# Obtener datos
key_str = os.environ.get('PHANTOM_PRIVATE_KEY_BYTES', '')
configured_wallet = os.environ.get('PHANTOM_WALLET', '')

if not key_str:
    print("❌ PHANTOM_PRIVATE_KEY_BYTES no configurada")
    exit(1)

if not configured_wallet:
    print("❌ PHANTOM_WALLET no configurada")
    exit(1)

print(f"\n📋 CONFIGURACIÓN:")
print(f"   Clave: {len(key_str)} caracteres")
print(f"   Wallet config: {configured_wallet}")

try:
    # Decodificar
    decoded = base64.b64decode(key_str.strip())
    print(f"\n🔍 DECODIFICACIÓN:")
    print(f"   Bytes: {len(decoded)}")
    
    if len(decoded) != 64:
        print(f"   ⚠️  Deberían ser 64 bytes, son {len(decoded)}")
    
    # Crear keypair
    keypair = Keypair.from_bytes(decoded)
    derived_wallet = str(keypair.pubkey())
    
    print(f"\n🎯 RESULTADO:")
    print(f"   Wallet derivada: {derived_wallet}")
    
    # Comparar
    if derived_wallet == configured_wallet:
        print(f"\n✅ ¡PERFECTO! Clave y dirección coinciden")
        print(f"   🎉 Tu configuración es correcta")
    else:
        print(f"\n❌ ¡PROBLEMA! No coinciden:")
        print(f"   Config: {configured_wallet}")
        print(f"   Derivada: {derived_wallet}")
        print(f"\n💡 Ejecuta: python fix_keypair_mismatch.py")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print(f"\n💡 Ejecuta: python fix_keypair_mismatch.py")

input("\nPresiona Enter para salir...")