# fix_keypair_mismatch.py
"""
Detectar y corregir desajuste entre clave privada y dirección pública
"""
import os
import base64
from solders.keypair import Keypair
from solders.pubkey import Pubkey

def diagnose_problem():
    """Diagnosticar el problema exacto"""
    print("🔍 DIAGNÓSTICO DE CLAVE PRIVADA/DIRECCIÓN")
    print("="*60)
    
    # Obtener datos actuales
    key_str = os.environ.get('PHANTOM_PRIVATE_KEY_BYTES', '')
    configured_wallet = os.environ.get('PHANTOM_WALLET', '')
    
    if not key_str or not configured_wallet:
        print("❌ Configuración incompleta")
        return
    
    print(f"\n📋 CONFIGURACIÓN ACTUAL:")
    print(f"   Clave privada: {len(key_str)} chars")
    print(f"   Wallet config: {configured_wallet[:8]}...")
    
    # Intentar diferentes formatos
    print("\n🔄 PROBANDO DIFERENTES FORMATOS:")
    
    formats_to_try = []
    
    # 1. Base64 directo
    formats_to_try.append(("Base64 directo", key_str))
    
    # 2. Si parece Base64 pero podría tener metadatos
    if len(key_str) == 88:  # 66 bytes en Base64
        # Intentar quitar primeros 2 bytes
        try:
            decoded = base64.b64decode(key_str)
            if len(decoded) == 66:
                fixed = decoded[2:]  # Quitar primeros 2 bytes
                formats_to_try.append(("Base64 sin 2 primeros", base64.b64encode(fixed).decode()))
        except:
            pass
    
    # 3. Si es hexadecimal convertido a Base64
    clean_hex = key_str.strip().replace('0x', '').replace(' ', '')
    if len(clean_hex) == 128 and all(c in '0123456789abcdefABCDEF' for c in clean_hex):
        try:
            bytes_from_hex = bytes.fromhex(clean_hex)
            hex_base64 = base64.b64encode(bytes_from_hex).decode()
            formats_to_try.append(("Hex a Base64", hex_base64))
        except:
            pass
    
    # Probar cada formato
    working_formats = []
    
    for format_name, test_key in formats_to_try:
        try:
            decoded = base64.b64decode(test_key.strip())
            
            if len(decoded) == 64:
                keypair = Keypair.from_bytes(decoded)
                derived_wallet = str(keypair.pubkey())
                
                print(f"\n🔧 {format_name}:")
                print(f"   📏 Bytes: {len(decoded)}")
                print(f"   👛 Wallet derivada: {derived_wallet[:8]}...")
                print(f"   ✅ Válida: {len(decoded) == 64}")
                
                # Verificar si coincide con la configurada
                matches_config = derived_wallet == configured_wallet
                print(f"   🎯 Coincide con config: {'✅ SÍ' if matches_config else '❌ NO'}")
                
                if matches_config:
                    working_formats.append((format_name, test_key, derived_wallet))
            else:
                print(f"\n⚠️ {format_name}: {len(decoded)} bytes (deberían ser 64)")
                
        except Exception as e:
            print(f"\n❌ {format_name}: Error - {str(e)[:50]}")
    
    # Resultados
    print("\n" + "="*60)
    print("📊 RESULTADOS DEL DIAGNÓSTICO")
    print("="*60)
    
    if working_formats:
        print(f"\n✅ {len(working_formats)} formato(s) válido(s) encontrado(s):")
        for i, (name, key, wallet) in enumerate(working_formats, 1):
            print(f"\n{i}. {name}:")
            print(f"   👛 Wallet: {wallet}")
            print(f"   🔑 Key: {key[:30]}...")
        
        # Si hay uno que coincide
        matching = [f for f in working_formats if f[2] == configured_wallet]
        if matching:
            print(f"\n🎉 ¡ENCONTRADO! El formato '{matching[0][0]}' coincide con tu wallet")
            save_fixed_key(matching[0][1], configured_wallet)
        else:
            print(f"\n⚠️  Ningún formato coincide con tu wallet configurada")
            print(f"   Wallet config: {configured_wallet}")
            print(f"   ¿Es esta tu wallet correcta?")
            
            # Mostrar todas las wallets derivadas
            print(f"\n📋 WALLETS DERIVADAS ENCONTRADAS:")
            for name, _, wallet in working_formats:
                print(f"   • {wallet}")
            
            # Preguntar cuál es la correcta
            choice = input("\n¿Cuál es tu wallet correcta? (pega la dirección completa): ").strip()
            if choice:
                # Buscar qué clave genera esa wallet
                for name, key, wallet in working_formats:
                    if wallet == choice:
                        print(f"\n✅ Usando formato '{name}' para wallet {choice[:8]}...")
                        save_fixed_key(key, choice)
                        break
    
    else:
        print("\n❌ No se encontraron formatos válidos")
        print("\n💡 SOLUCIONES:")
        print("1. Exporta NUEVAMENTE tu clave privada desde Phantom")
        print("2. Asegúrate de copiar TODA la clave")
        print("3. El formato más común es hexadecimal (128 caracteres)")

def save_fixed_key(fixed_key: str, wallet_address: str):
    """Guardar clave corregida"""
    print(f"\n💾 GUARDANDO CLAVE CORREGIDA...")
    
    batch_content = f"""@echo off
echo 🔐 ACTUALIZANDO CLAVE PRIVADA CORREGIDA
echo.

:: 🔑 CLAVE PRIVADA CORRECTA
set PHANTOM_PRIVATE_KEY_BYTES={fixed_key}
set PHANTOM_WALLET={wallet_address}
set PHANTOM_PUBLIC_KEY={wallet_address}

echo ✅ Clave actualizada para wallet: {wallet_address[:8]}...
echo.
echo 📋 Para verificar: python verify_fixed_key.py
echo.
pause
"""
    
    with open("fix_keypair.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    print(f"📄 Archivo creado: fix_keypair.bat")
    print(f"💡 Ejecútalo para actualizar tu configuración")

if __name__ == "__main__":
    diagnose_problem()
    input("\nPresiona Enter para salir...")