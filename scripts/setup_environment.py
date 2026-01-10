# scripts/setup_environment.py
#!/usr/bin/env python3
"""
Script para configurar el entorno del bot
Lee variables del sistema, las encripta y configura el bot
"""

import os
import sys
import getpass
from pathlib import Path

def check_system_variables():
    """Verifica que todas las variables requeridas existan"""
    required_vars = [
        'HELIUS_RPC_URL',
        'HELIUS_VOICEINDIGO_API_KEY',
        'PHANTOM_WALLET',
        'PHANTOM_PRIVATE_KEY_BYTE',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if var not in os.environ:
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Variables de sistema faltantes:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Ejecuta: export VARIABLE=valor")
        return False
    
    return True

def encrypt_environment():
    """Encripta las variables del sistema"""
    try:
        from security.env_encryptor import SystemEnvEncryptor
        
        print("🔐 Encriptando variables de entorno...")
        
        # Solicitar master password
        print("\n" + "="*50)
        print("IMPORTANTE: Esta contraseña maestra se usará para")
        print("desencriptar las variables cada vez que el bot inicie.")
        print("GUÁRDALA EN UN LUGAR SEGURO.")
        print("="*50 + "\n")
        
        # Crear encriptador
        encryptor = SystemEnvEncryptor()
        
        # Crear archivo encriptado
        output_file = encryptor.create_encrypted_env_file()
        
        print(f"\n✅ Archivo encriptado creado: {output_file}")
        print("🔒 Permisos configurados a 600 (solo lectura para propietario)")
        
        # Crear estructura de directorios
        create_directory_structure()
        
        return True
        
    except Exception as e:
        print(f"❌ Error encriptando variables: {e}")
        return False

def create_directory_structure():
    """Crea la estructura de directorios del bot"""
    directories = [
        "logs",
        "data/training",
        "data/live",
        "data/signals",
        "models",
        "state",
        "reports",
        "scripts"
    ]
    
    base_dir = Path(__file__).parent.parent
    for directory in directories:
        dir_path = base_dir / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Creado: {dir_path}")
    
    # Establecer permisos seguros
    os.chmod(base_dir / ".env.encrypted", 0o600)
    os.chmod(base_dir / "logs", 0o755)
    
    print("✅ Estructura de directorios creada")

def create_config_example():
    """Crea archivo de configuración de ejemplo"""
    config_example = """# config.py - Configuración del Bot Orca

from decimal import Decimal

# Configuración de capital
MAX_CAPITAL_PER_TRADE_PCT = Decimal('0.10')  # 10% del capital por operación
MAX_CONCURRENT_OPERATIONS = 5  # Máximo 5 operaciones simultáneas

# Timeframes activos
ACTIVE_TIMEFRAMES = ['5m', '15m', '1h']

# Configuración de riesgo
STOP_LOSS_PCT = Decimal('0.02')  # 2% stop loss inicial
TAKE_PROFIT_PCT = Decimal('0.05')  # 5% take profit inicial
RISK_ZERO_BUFFER_PCT = Decimal('0.002')  # 0.2% buffer para riesgo cero

# Configuración ML
ML_CONFIDENCE_THRESHOLD = 0.75  # 75% confianza mínima
TOP_ASSETS_TO_ANALYZE = 20  # Analizar top 20 activos
"""
    
    config_path = Path(__file__).parent.parent / "config_example.py"
    with open(config_path, 'w') as f:
        f.write(config_example)
    
    print(f"📄 Archivo de ejemplo creado: {config_path}")

def main():
    """Función principal del script"""
    print("="*60)
    print("🛠️  CONFIGURACIÓN DEL BOT ORCA MULTI-OPERACIÓN")
    print("="*60)
    
    # Verificar variables del sistema
    print("\n1. Verificando variables de entorno del sistema...")
    if not check_system_variables():
        sys.exit(1)
    
    print("✅ Todas las variables requeridas encontradas")
    
    # Encriptar variables
    print("\n2. Encriptando variables...")
    if not encrypt_environment():
        sys.exit(1)
    
    # Crear estructura
    print("\n3. Creando estructura de directorios...")
    create_directory_structure()
    
    # Crear ejemplo de configuración
    print("\n4. Creando archivos de ejemplo...")
    create_config_example()
    
    print("\n" + "="*60)
    print("🎉 CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
    print("="*60)
    print("\n📋 Pasos siguientes:")
    print("1. Revisa config_example.py y ajusta los parámetros")
    print("2. Copia config_example.py a config.py y personaliza")
    print("3. Para iniciar el bot: python main.py")
    print("\n⚠️  IMPORTANTE:")
    print("   - Guarda tu master password en lugar seguro")
    print("   - Nunca compartas el archivo .env.encrypted")
    print("   - Verifica los permisos de los archivos")
    print("\n🚀 ¡Listo para operar!")

if __name__ == "__main__":
    main()