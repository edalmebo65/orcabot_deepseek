# scripts/encrypt_env_vars.py
#!/usr/bin/env python3
"""
Script para encriptar variables de entorno del sistema
"""

import os
import sys
import json
import base64
from pathlib import Path

# Agregar directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from security.env_encryptor import SystemEnvEncryptor

def main():
    """Función principal"""
    print("="*60)
    print("🔐 ENCRIPTADOR DE VARIABLES DE ENTORNO")
    print("="*60)
    
    # Verificar que estén las variables requeridas
    required_vars = [
        'HELIUS_RPC_URL',
        'HELIUS_VOICEINDIGO_API_KEY', 
        'PHANTOM_WALLET',
        'PHANTOM_PRIVATE_KEY_BYTE',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    print("\n📋 Verificando variables de sistema...")
    
    missing_vars = []
    for var in required_vars:
        if var not in os.environ:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Variables faltantes en el sistema:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Ejecuta primero:")
        print("   export VARIABLE=valor")
        sys.exit(1)
    
    print("✅ Todas las variables requeridas encontradas")
    
    # Crear encriptador
    print("\n🔐 Creando encriptador...")
    print("\n" + "="*50)
    print("IMPORTANTE: Necesitarás esta contraseña maestra")
    print("cada vez que el bot inicie para desencriptar las variables.")
    print("\nGUÁRDALA EN UN LUGAR SEGURO!")
    print("="*50 + "\n")
    
    encryptor = SystemEnvEncryptor()
    
    # Crear archivo encriptado
    output_file = ".env.encrypted"
    print(f"\n📁 Creando archivo encriptado: {output_file}")
    
    encryptor.create_encrypted_env_file(output_file)
    
    # Establecer permisos seguros
    os.chmod(output_file, 0o600)
    
    print(f"\n✅ Archivo encriptado creado: {output_file}")
    print("🔒 Permisos configurados a 600 (solo lectura para propietario)")
    
    # Verificar que se puede desencriptar
    print("\n🧪 Verificando desencriptación...")
    try:
        # Leer archivo encriptado
        with open(output_file, 'r') as f:
            encrypted_data = json.load(f)
        
        # Intentar desencriptar una variable
        test_var = encryptor.decrypt_variable(
            encrypted_data['variables']['PHANTOM_WALLET']
        )
        
        if test_var == os.environ['PHANTOM_WALLET']:
            print("✅ Desencriptación verificada correctamente")
        else:
            print("❌ Error en verificación de desencriptación")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error verificando desencriptación: {e}")
        sys.exit(1)
    
    # Recomendaciones de seguridad
    print("\n" + "="*60)
    print("🎉 ENCRIPTACIÓN COMPLETADA EXITOSAMENTE")
    print("="*60)
    print("\n📋 Recomendaciones de seguridad:")
    print("1. ✅ Elimina las variables de entorno del sistema:")
    print("   unset HELIUS_RPC_URL HELIUS_VOICEINDIGO_API_KEY ...")
    print("\n2. ✅ Nunca compartas el archivo .env.encrypted")
    print("\n3. ✅ Usa un password manager para guardar la contraseña maestra")
    print("\n4. ✅ Configura backups seguros del archivo encriptado")
    print("\n5. ✅ Considera usar un HSM o AWS KMS en producción")
    print("\n🚀 Para iniciar el bot: python main.py")

if __name__ == "__main__":
    main()