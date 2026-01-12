#!/usr/bin/env python3
"""
Script de configuración inicial para OrcaBot
Configura variables de entorno, verifica dependencias y crea estructura
"""
import os
import sys
import json
import secrets
import base64
from pathlib import Path
import subprocess
import platform

def print_header():
    """Imprime encabezado del setup"""
    print("╔══════════════════════════════════════════════╗")
    print("║           ORCABOT v3.0 - SETUP               ║")
    print("║   Configuración Automática del Sistema       ║")
    print("╚══════════════════════════════════════════════╝")
    print()

def check_python_version():
    """Verifica versión de Python"""
    print("🔍 Verificando Python...")
    
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} (Se requiere 3.9+)")
        return False

def install_dependencies():
    """Instala dependencias de Python"""
    print("\n📦 Instalando dependencias...")
    
    # Determinar archivo de requirements
    requirements_file = "requirements_fixed_v2.txt"
    
    if not os.path.exists(requirements_file):
        print(f"  ❌ Archivo {requirements_file} no encontrado")
        return False
    
    try:
        # Instalar dependencias
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("  ✅ Dependencias instaladas correctamente")
            return True
        else:
            print(f"  ❌ Error instalando dependencias:")
            print(f"     {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def setup_directories():
    """Crea estructura de directorios"""
    print("\n📁 Creando estructura de directorios...")
    
    directories = [
        "logs",
        "data",
        "models",
        "backup",
        "historical/ohlcv",
        "historical/ml_features",
        "historical/trades"
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}/")
    
    return True

def generate_encryption_keys():
    """Genera claves de encriptación seguras"""
    print("\n🔐 Generando claves de encriptación...")
    
    # Generar contraseña segura
    password = secrets.token_urlsafe(32)
    salt = secrets.token_bytes(16)
    
    # Crear archivo .env
    env_content = f"""# ENCRYPTION KEYS - GUARDAR EN LUGAR SEGURO
ENCRYPTION_PASSWORD={password}
ENCRYPTION_SALT={base64.b64encode(salt).decode()}

# WALLET CONFIGURATION
# Configura tu wallet aquí después
PHANTOM_WALLET=
PHANTOM_PRIVATE_KEY_BYTES=

# HELIUS RPC
HELIUS_VOICEINDIGO_API_KEY=
HELIUS_BASE_URL=https://mainnet.helius-rpc.com

# TELEGRAM (opcional)
TELEGRAM_BOT_TOKEN=optional
TELEGRAM_CHAT_ID=
TELEGRAM_ADMIN_ID=

# TRADING PARAMETERS
MAX_POSITION_SIZE_USD=1000
MAX_PORTFOLIO_EXPOSURE=0.15
DAILY_LOSS_LIMIT=0.02
MIN_PROFIT_MARGIN=0.002

# ML PARAMETERS
ML_CONFIDENCE_THRESHOLD=0.68
ML_SEQUENCE_LENGTH=60

# LOGGING
LOG_LEVEL=INFO

# DIRECTORIES
BASE_DIR={os.getcwd()}
"""
    
    # Guardar .env
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    # Guardar copia de seguridad
    backup_dir = Path("backup")
    backup_dir.mkdir(exist_ok=True)
    
    backup_content = f"""⚠️ CLAVES DE ENCRIPTACIÓN - GUARDAR EN LUGAR SEGURO ⚠️

ENCRYPTION_PASSWORD={password}
ENCRYPTION_SALT={base64.b64encode(salt).decode()}

IMPORTANTE:
1. Estas claves son necesarias para desencriptar tu wallet
2. Sin ellas, perderás acceso a tus fondos
3. Guarda este archivo en un lugar seguro
4. No lo compartas con nadie

Fecha de generación: {os.path.getctime('.env')}
"""
    
    with open(backup_dir / "mis_datos.txt", "w", encoding="utf-8") as f:
        f.write(backup_content)
    
    print("  ✅ Claves generadas y guardadas en:")
    print(f"     - .env (archivo de configuración)")
    print(f"     - backup/mis_datos.txt (copia de seguridad)")
    print(f"  🔑 Password: {password[:16]}...")
    print(f"  🧂 Salt: {base64.b64encode(salt).decode()[:16]}...")
    
    return True

def create_config_json():
    """Crea archivo config.json inicial"""
    print("\n⚙️ Creando configuración inicial...")
    
    config = {
        "project": {
            "name": "OrcaBot DeepSeek",
            "version": "3.0.0",
            "description": "Bot de trading con selección automática de tokens"
        },
        "trading_mode": "paper",
        "rust_binary_path": "./target/release/orca_bridge",
        "solana": {
            "rpc_endpoint": "",
            "network": "mainnet-beta"
        },
        "security": {
            "encryption_enabled": True,
            "auto_generate_keys": True,
            "backup_credentials": True
        },
        "trading_pairs": [],
        "volatility_selection": {
            "top_n_tokens": 20,
            "min_volume_usd": 10000,
            "min_liquidity_usd": 50000,
            "update_interval_hours": 6,
            "volatility_window_days": 7
        },
        "gradual_entry": {
            "max_concurrent_trades": 5,
            "min_profit_margin_entry": 0.002,
            "check_interval_minutes": 5,
            "entry_buffer_percent": 0.1
        },
        "balance_requirements": {
            "min_usdc": 10.0,
            "min_sol_for_fees": 0.05,
            "check_on_startup": True
        },
        "logging": {
            "level": "INFO",
            "log_security_events": True
        }
    }
    
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("  ✅ config.json creado")
    return True

def setup_complete():
    """Muestra mensaje de finalización"""
    print("\n" + "="*50)
    print("✅ CONFIGURACIÓN COMPLETADA")
    print("="*50)
    
    print("\n📋 PASOS SIGUIENTES:")
    print("1. Edita el archivo .env con tu configuración:")
    print("   - Configura tu wallet Phantom")
    print("   - Añade tu API key de Helius")
    print("   - Configura Telegram (opcional)")
    
    print("\n2. Para modo PAPER trading (recomendado para empezar):")
    print("   python main_integrated.py")
    
    print("\n3. Para verificar el sistema:")
    print("   python check_environment.py")
    
    print("\n⚠️  IMPORTANTE:")
    print("   - El archivo backup/mis_datos.txt contiene tus claves")
    print("   - Guárdalo en un lugar seguro")
    print("   - Sin él, no podrás acceder a tu wallet encriptada")
    
    print("\n🎉 ¡Listo para comenzar! Buena suerte con el trading.")
    print("="*50)

def main():
    """Función principal del setup"""
    print_header()
    
    # Verificar Python
    if not check_python_version():
        print("\n❌ Python 3.9+ requerido. Actualiza Python e intenta de nuevo.")
        return
    
    # Instalar dependencias
    if not install_dependencies():
        print("\n❌ Error instalando dependencias. Revisa los mensajes arriba.")
        return
    
    # Crear directorios
    if not setup_directories():
        print("\n❌ Error creando directorios.")
        return
    
    # Generar claves
    if not generate_encryption_keys():
        print("\n❌ Error generando claves.")
        return
    
    # Crear config.json
    if not create_config_json():
        print("\n❌ Error creando configuración.")
        return
    
    # Éxito
    setup_complete()

if __name__ == "__main__":
    main()