# convert_to_base64.py
"""
Convertir cualquier formato de clave a Base64
"""
import base64
import ast
import sys

def convert_key():
    """Convertir clave interactivamente"""
    print("🔄 CONVERSOR DE CLAVE A Base64")
    print("="*50)
    
    print("\n¿Qué formato tiene tu clave?")
    print("1. Base64 (ya está bien)")
    print("2. Hexadecimal (ej: de1f2a3b...)")
    print("3. Array de bytes (ej: [1,2,3,...])")
    print("4. String plano")
    
    choice = input("\nSelecciona (1-4): ")
    
    if choice == '1':
        key = input("Pega tu clave Base64: ").strip()
        # Verificar que sea Base64 válido
        try:
            decoded = base64.b64decode(key)
            print(f"\n✅ Base64 válido")
            print(f"📏 Bytes: {len(decoded)}")
            print(f"🔑 Clave: {key[:30]}...")
            
            if len(decoded) == 64:
                print("🎉 ¡64 bytes perfecto!")
            else:
                print(f"⚠️ Tiene {len(decoded)} bytes (debería ser 64)")
                
            return key
            
        except:
            print("❌ No es Base64 válido")
            return None
    
    elif choice == '2':
        hex_key = input("Pega tu clave hexadecimal: ").strip()
        # Limpiar
        hex_clean = hex_key.replace('0x', '').replace(' ', '').replace('\n', '')
        
        try:
            bytes_key = bytes.fromhex(hex_clean)
            base64_key = base64.b64encode(bytes_key).decode()
            
            print(f"\n✅ Convertido a Base64")
            print(f"📏 Hex original: {len(hex_clean)//2} bytes")
            print(f"📏 Base64: {len(base64_key)} chars")
            print(f"🔑 Base64: {base64_key[:30]}...")
            
            if len(bytes_key) == 64:
                print("🎉 ¡64 bytes perfecto!")
            else:
                print(f"⚠️ Tiene {len(bytes_key)} bytes (debería ser 64)")
                
            return base64_key
            
        except:
            print("❌ Hexadecimal no válido")
            return None
    
    elif choice == '3':
        array_str = input("Pega tu array de bytes: ").strip()
        
        try:
            byte_list = ast.literal_eval(array_str)
            bytes_key = bytes(byte_list)
            base64_key = base64.b64encode(bytes_key).decode()
            
            print(f"\n✅ Convertido a Base64")
            print(f"📏 Array: {len(byte_list)} bytes")
            print(f"🔑 Base64: {base64_key[:30]}...")
            
            if len(bytes_key) == 64:
                print("🎉 ¡64 bytes perfecto!")
            else:
                print(f"⚠️ Tiene {len(bytes_key)} bytes (debería ser 64)")
                
            return base64_key
            
        except:
            print("❌ Array no válido")
            return None
    
    elif choice == '4':
        str_key = input("Pega tu clave como string: ").strip()
        
        try:
            bytes_key = str_key.encode('utf-8')
            base64_key = base64.b64encode(bytes_key).decode()
            
            print(f"\n✅ Convertido a Base64")
            print(f"📏 String: {len(str_key)} chars")
            print(f"📏 Bytes: {len(bytes_key)} bytes")
            print(f"🔑 Base64: {base64_key[:30]}...")
            
            if len(bytes_key) == 64:
                print("🎉 ¡64 bytes perfecto!")
            else:
                print(f"⚠️ Tiene {len(bytes_key)} bytes (debería ser 64)")
                
            return base64_key
            
        except:
            print("❌ Error en conversión")
            return None
    
    else:
        print("❌ Opción no válida")
        return None

def save_to_batch(base64_key, wallet_address):
    """Guardar en archivo batch"""
    batch_content = f"""@echo off
echo 🤖 ACTUALIZANDO CONFIGURACIÓN
echo.

:: 🔐 CLAVE PRIVADA EN Base64
set PHANTOM_PRIVATE_KEY_BYTES={base64_key}
set PHANTOM_WALLET={wallet_address}
set PHANTOM_PUBLIC_KEY={wallet_address}

:: 🔐 ENCRIPTACIÓN (si ya las tienes)
set ENCRYPTION_PASSWORD=%ENCRYPTION_PASSWORD%
set ENCRYPTION_SALT=%ENCRYPTION_SALT%

echo ✅ Clave actualizada a Base64
echo.
echo 📋 Verificar: python config.py
echo 💰 Check balances: python check_balances_fixed.py
echo.
pause
"""
    
    with open("update_key.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    print(f"\n📄 Archivo creado: update_key.bat")
    print("💡 Ejecútalo para actualizar tu clave")

if __name__ == "__main__":
    base64_key = convert_key()
    
    if base64_key:
        print("\n" + "="*50)
        wallet = input("Ingresa tu dirección de wallet Phantom: ").strip()
        
        if wallet:
            save_to_batch(base64_key, wallet)
            print("\n✅ ¡Listo! Ejecuta 'update_key.bat' y luego 'python check_balances_fixed.py'")
        else:
            print("❌ Dirección de wallet requerida")
    
    input("\nPresiona Enter para salir...")