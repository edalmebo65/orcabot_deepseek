# fix_private_key.py
"""
Corregir clave privada de 66 bytes a 64 bytes para Solana
"""
import base64
import os
import sys

def fix_66_to_64_bytes():
    """Convertir clave de 66 bytes a 64 bytes"""
    print("🔧 CORRECTOR DE CLAVE PRIVADA (66 → 64 bytes)")
    print("="*60)
    
    # Obtener clave actual
    current_key = os.environ.get('PHANTOM_PRIVATE_KEY_BYTES', '')
    
    if not current_key:
        print("❌ PHANTOM_PRIVATE_KEY_BYTES no encontrada")
        print("💡 Configura primero las variables de entorno")
        return None
    
    print(f"\n📏 Clave actual: {len(current_key)} caracteres Base64")
    print(f"📋 Inicio: {current_key[:20]}...")
    
    try:
        # Decodificar Base64
        decoded_bytes = base64.b64decode(current_key)
        print(f"📏 Bytes decodificados: {len(decoded_bytes)}")
        
        if len(decoded_bytes) == 66:
            print("✅ Detectado: 66 bytes (necesita conversión)")
            
            # MOSTRAR LOS BYTES
            print("\n🔍 ANALIZANDO BYTES:")
            print(f"   Bytes 0-15:  {decoded_bytes[:16].hex()}")
            print(f"   Bytes 16-31: {decoded_bytes[16:32].hex()}")
            print(f"   Bytes 32-47: {decoded_bytes[32:48].hex()}")
            print(f"   Bytes 48-63: {decoded_bytes[48:64].hex()}")
            print(f"   Bytes 64-65: {decoded_bytes[64:66].hex()} (EXTRA)")
            
            # Diferentes estrategias para extraer 64 bytes
            print("\n🔄 PROBANDO ESTRATEGIAS:")
            
            # Estrategia 1: Quitar primeros 2 bytes (prefijo)
            option1 = decoded_bytes[2:66]  # Bytes 2-65
            print(f"1. Quitar primeros 2 bytes: {len(option1)} bytes")
            print(f"   Resultado: {option1[:8].hex()}...")
            
            # Estrategia 2: Quitar últimos 2 bytes (checksum)
            option2 = decoded_bytes[0:64]  # Bytes 0-63
            print(f"2. Quitar últimos 2 bytes: {len(option2)} bytes")
            print(f"   Resultado: {option2[:8].hex()}...")
            
            # Estrategia 3: Quitar byte 0 y byte 65
            option3 = decoded_bytes[1:65]  # Bytes 1-64
            print(f"3. Quitar byte 0 y 65: {len(option3)} bytes")
            print(f"   Resultado: {option3[:8].hex()}...")
            
            # Estrategia 4: Bytes 32-95 (si es clave extendida)
            if len(decoded_bytes) >= 96:
                option4 = decoded_bytes[32:96]  # Bytes 32-95
                print(f"4. Bytes 32-95: {len(option4)} bytes")
                print(f"   Resultado: {option4[:8].hex()}...")
            
            # Preguntar al usuario
            print("\n🎯 SELECCIÓN DE ESTRATEGIA:")
            print("   A. Usar estrategia 1 (quitar primeros 2 bytes)")
            print("   B. Usar estrategia 2 (quitar últimos 2 bytes)")
            print("   C. Usar estrategia 3 (quitar byte 0 y 65)")
            print("   D. Probar todas y ver cuál funciona")
            
            choice = input("\nSelecciona (A/B/C/D): ").upper()
            
            fixed_bytes = None
            
            if choice == 'A':
                fixed_bytes = option1
            elif choice == 'B':
                fixed_bytes = option2
            elif choice == 'C':
                fixed_bytes = option3
            elif choice == 'D':
                # Probar todas automáticamente
                return test_all_options(current_key, decoded_bytes)
            else:
                print("❌ Opción no válida")
                return None
            
            if fixed_bytes and len(fixed_bytes) == 64:
                # Convertir a Base64
                fixed_base64 = base64.b64encode(fixed_bytes).decode()
                
                print(f"\n✅ CLAVE CORREGIDA:")
                print(f"📏 Nueva longitud: {len(fixed_base64)} chars Base64")
                print(f"📏 Bytes: {len(fixed_bytes)} (¡64 perfecto!)")
                print(f"🔑 Clave Base64: {fixed_base64[:30]}...")
                
                return fixed_base64
            else:
                print(f"❌ No se pudo obtener 64 bytes")
                return None
                
        elif len(decoded_bytes) == 64:
            print("🎉 ¡Ya tiene 64 bytes! No necesita corrección")
            return current_key
        else:
            print(f"⚠️ Longitud inesperada: {len(decoded_bytes)} bytes")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_all_options(original_base64: str, decoded_bytes: bytes):
    """Probar todas las opciones automáticamente"""
    print("\n🧪 PROBANDO TODAS LAS OPCIONES...")
    
    options = {
        '1': ("Quitar primeros 2 bytes", decoded_bytes[2:66]),
        '2': ("Quitar últimos 2 bytes", decoded_bytes[0:64]),
        '3': ("Quitar byte 0 y 65", decoded_bytes[1:65]),
    }
    
    # Si hay más bytes, agregar más opciones
    if len(decoded_bytes) >= 96:
        options['4'] = ("Bytes 32-95", decoded_bytes[32:96])
    
    valid_options = []
    
    for key, (desc, bytes_data) in options.items():
        if len(bytes_data) == 64:
            base64_key = base64.b64encode(bytes_data).decode()
            
            # Verificar si funciona con solders
            try:
                from solders.keypair import Keypair
                kp = Keypair.from_bytes(bytes_data)
                wallet_addr = str(kp.pubkey())
                
                print(f"\n✅ OPCIÓN {key} FUNCIONA:")
                print(f"   {desc}")
                print(f"   👛 Wallet: {wallet_addr[:8]}...")
                print(f"   🔑 Base64: {base64_key[:30]}...")
                
                valid_options.append((key, desc, base64_key, wallet_addr))
                
            except Exception as e:
                print(f"❌ Opción {key} falló: {e}")
        else:
            print(f"⚠️ Opción {key}: {len(bytes_data)} bytes (no 64)")
    
    if valid_options:
        print(f"\n🎉 {len(valid_options)} opciones válidas encontradas")
        
        if len(valid_options) == 1:
            # Solo una funciona, usarla
            _, _, fixed_key, wallet = valid_options[0]
            print(f"\n✅ Usando la única opción válida")
            print(f"   👛 Wallet: {wallet[:8]}...")
            return fixed_key
        else:
            # Mostrar opciones
            print("\n🔢 OPCIONES VÁLIDAS:")
            for i, (key, desc, _, wallet) in enumerate(valid_options, 1):
                print(f"   {i}. {desc} -> {wallet[:8]}...")
            
            # Preguntar cuál usar
            try:
                choice_idx = int(input("\nSelecciona opción (1,2,3...): ")) - 1
                if 0 <= choice_idx < len(valid_options):
                    _, _, fixed_key, wallet = valid_options[choice_idx]
                    print(f"\n✅ Seleccionada opción {choice_idx+1}")
                    print(f"   👛 Wallet: {wallet}")
                    return fixed_key
                else:
                    print("❌ Opción no válida")
            except:
                print("❌ Entrada no válida")
    
    print("❌ No se encontraron opciones válidas")
    return None

def save_corrected_key(corrected_key: str):
    """Guardar clave corregida"""
    if not corrected_key:
        return
    
    # Obtener wallet actual
    wallet = os.environ.get('PHANTOM_WALLET', '')
    if not wallet:
        wallet = input("\nIngresa tu dirección de wallet: ").strip()
    
    # Crear batch file
    batch_content = f"""@echo off
echo 🤖 ACTUALIZANDO CLAVE PRIVADA CORREGIDA
echo.

:: 🔐 CLAVE PRIVADA CORREGIDA (64 bytes)
set PHANTOM_PRIVATE_KEY_BYTES={corrected_key}
set PHANTOM_WALLET={wallet}
set PHANTOM_PUBLIC_KEY={wallet}

:: 🔐 MANTENER ENCRIPTACIÓN EXISTENTE
if not "%ENCRYPTION_PASSWORD%"=="" set ENCRYPTION_PASSWORD=%ENCRYPTION_PASSWORD%
if not "%ENCRYPTION_SALT%"=="" set ENCRYPTION_SALT=%ENCRYPTION_SALT%

:: 🌐 MANTENER HELIUS
if not "%HELIUS_VOICEINDIGO_API_KEY%"=="" set HELIUS_VOICEINDIGO_API_KEY=%HELIUS_VOICEINDIGO_API_KEY%

echo ✅ Clave corregida a 64 bytes
echo.
echo 📋 Verificar: python config.py
echo 💰 Check balances: python check_balances_fixed.py
echo.
pause
"""
    
    with open("fix_key.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    print(f"\n📄 Archivo creado: fix_key.bat")
    print("💡 Ejecuta 'fix_key.bat' para actualizar tu clave")

def main():
    """Función principal"""
    corrected_key = fix_66_to_64_bytes()
    
    if corrected_key:
        save_corrected_key(corrected_key)
        print("\n✅ ¡LISTO! Siguientes pasos:")
        print("   1. Ejecuta: fix_key.bat")
        print("   2. Verifica: python config.py")
        print("   3. Check balances: python check_balances_fixed.py")
        print("   4. Swap test: python swap_test_simple.py")
    else:
        print("\n❌ No se pudo corregir la clave")

if __name__ == "__main__":
    main()
    input("\nPresiona Enter para salir...")