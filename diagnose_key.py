# diagnose_key.py
"""
Diagnosticar el formato de la clave privada
"""
import os
import base64
import sys

print("🔍 DIAGNÓSTICO DE CLAVE PRIVADA")
print("="*50)

# Obtener clave de variables de entorno
key = os.environ.get('PHANTOM_PRIVATE_KEY_BYTES', '')

if not key:
    print("❌ PHANTOM_PRIVATE_KEY_BYTES no configurada")
    print("💡 Ejecuta primero: start_orcabat.bat")
    sys.exit(1)

print(f"\n📏 Longitud original: {len(key)} caracteres")
print(f"📋 Primeros 20 chars: {key[:20]}...")
print(f"📋 Últimos 20 chars: ...{key[-20:] if len(key) > 20 else key}")

# Analizar formato
print("\n🔎 ANALIZANDO FORMATO:")

# 1. Verificar si es Base64
is_base64 = False
try:
    # Intentar decodificar como base64
    decoded = base64.b64decode(key)
    print(f"✅ Es Base64 válido")
    print(f"   📏 Bytes decodificados: {len(decoded)}")
    print(f"   🔑 Primeros bytes: {decoded[:8].hex()}...")
    is_base64 = True
except:
    print("❌ No es Base64 válido")

# 2. Verificar si es hexadecimal
is_hex = False
clean_hex = key.strip().replace(' ', '').replace('0x', '')
if all(c in '0123456789abcdefABCDEF' for c in clean_hex):
    print(f"✅ Parece hexadecimal")
    print(f"   📏 Longitud hex: {len(clean_hex)}")
    print(f"   📏 Bytes esperados: {len(clean_hex)//2}")
    is_hex = True
else:
    print("❌ No es hexadecimal")

# 3. Verificar si es array de bytes
is_array = False
if key.startswith('[') and key.endswith(']'):
    print(f"✅ Parece array de bytes")
    is_array = True
else:
    print("❌ No es array de bytes")

# 4. Mostrar recomendaciones
print("\n💡 RECOMENDACIONES:")

if is_base64:
    decoded = base64.b64decode(key)
    if len(decoded) == 64:
        print("🎉 ¡Tu clave está en el formato CORRECTO (Base64 -> 64 bytes)!")
        print("   El problema está en la decodificación en check_balances_simple.py")
    elif len(decoded) == 32:
        print("⚠️ Tu clave tiene 32 bytes (quizás es solo la semilla)")
        print("   Necesitas 64 bytes para la clave privada completa")
    else:
        print(f"⚠️ Tu clave decodificada tiene {len(decoded)} bytes")
        print("   Debería tener 64 bytes para Solana")

elif is_hex:
    byte_count = len(clean_hex) // 2
    if byte_count == 64:
        print("🎉 Tu clave es hexadecimal de 64 bytes")
        print("   Conviértela a Base64 con el script a continuación")
    else:
        print(f"⚠️ Tu hex tiene {byte_count} bytes (debería ser 64)")

elif is_array:
    print("📋 Tu clave es un array de bytes")
    print("   Conviértela a Base64 con el script a continuación")

else:
    print("🤔 Formato no reconocido")
    print("   Prueba convertirla a Base64")

# Script de conversión
print("\n🔧 SCRIPT DE CONVERSIÓN A Base64:")
print("""# Ejecuta en Python:
import base64

# Si tu clave es hexadecimal:
hex_key = "tu_clave_hex_aqui"  # Sin 0x, sin espacios
bytes_key = bytes.fromhex(hex_key)
base64_key = base64.b64encode(bytes_key).decode()
print(f"Base64: {base64_key}")

# Si tu clave es array de bytes como string:
import ast
array_str = "[1,2,3,...]"  # Tu array completo
byte_list = ast.literal_eval(array_str)
bytes_key = bytes(byte_list)
base64_key = base64.b64encode(bytes_key).decode()
print(f"Base64: {base64_key}")
""")

input("\nPresiona Enter para salir...")