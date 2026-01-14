# setup_system_config.py
"""
Script para configurar las variables de entorno en el sistema
Ejecutar una vez antes de usar el bot
"""
import os
import sys
import getpass
import base64
from cryptography.fernet import Fernet

def configure_system():
    """Configurar variables de entorno en el sistema"""
    print("🔧 CONFIGURACIÓN DEL SISTEMA PARA ORCABOT")
    print("=" * 60)
    
    config_values = {}
    
    # 1. 🔐 ENCRIPTACIÓN
    print("\n🔐 CONFIGURACIÓN DE ENCRIPTACIÓN")
    print("-" * 40)
    
    encryption_password = getpass.getpass("Contraseña de encriptación (mínimo 32 caracteres): ")
    while len(encryption_password) < 32:
        print("❌ La contraseña debe tener al menos 32 caracteres")
        encryption_password = getpass.getpass("Contraseña de encriptación: ")
    
    config_values['ENCRYPTION_PASSWORD'] = encryption_password
    
    # Generar salt automáticamente
    import secrets
    encryption_salt = secrets.token_urlsafe(32)
    config_values['ENCRYPTION_SALT'] = encryption_salt
    print(f"✅ Salt generado automáticamente: {encryption_salt[:16]}...")
    
    # 2. 🏦 WALLET PHANTOM
    print("\n🏦 CONFIGURACIÓN DE WALLET PHANTOM")
    print("-" * 40)
    
    print("1. Clave privada en Base64 (recomendado)")
    print("2. Clave privada en texto plano")
    print("3. Frase semilla (12/24 palabras)")
    
    wallet_choice = input("\nSelecciona formato (1/2/3): ")
    
    if wallet_choice == '1':
        private_key_b64 = getpass.getpass("Clave privada en Base64: ")
        config_values['PHANTOM_PRIVATE_KEY_BYTES'] = private_key_b64
        
    elif wallet_choice == '2':
        private_key = getpass.getpass("Clave privada Phantom: ")
        config_values['PHANTOM_PRIVATE_KEY'] = private_key
        
    elif wallet_choice == '3':
        seed_phrase = getpass.getpass("Frase semilla (separada por espacios): ")
        config_values['PHANTOM_SEED_PHRASE'] = seed_phrase
        
    else:
        print("❌ Opción no válida")
        return False
    
    wallet_address = input("Dirección pública de la wallet: ")
    config_values['PHANTOM_WALLET'] = wallet_address
    config_values['PHANTOM_PUBLIC_KEY'] = wallet_address
    
    # 3. 🌐 HELIUS RPC
    print("\n🌐 CONFIGURACIÓN HELIUS RPC")
    print("-" * 40)
    
    helius_key = getpass.getpass("API Key de Helius (opcional, presiona Enter para usar RPC público): ")
    if helius_key:
        config_values['HELIUS_VOICEINDIGO_API_KEY'] = helius_key
        print("✅ Helius configurado")
    else:
        print("⚠️ Usando RPC público (limitado)")
    
    # 4. 🤖 TELEGRAM
    print("\n🤖 CONFIGURACIÓN DE TELEGRAM")
    print("-" * 40)
    
    telegram_choice = input("¿Configurar Telegram? (s/n): ").lower()
    if telegram_choice == 's':
        telegram_token = input("Token del bot de Telegram: ")
        telegram_chat_id = input("ID del chat de Telegram: ")
        
        config_values['TELEGRAM_BOT_TOKEN'] = telegram_token
        config_values['TELEGRAM_CHAT_ID'] = telegram_chat_id
        print("✅ Telegram configurado")
    else:
        print("⚠️ Telegram no configurado")
    
    # 5. ⚙️ CONFIGURACIONES AVANZADAS
    print("\n⚙️ CONFIGURACIONES AVANZADAS")
    print("-" * 40)
    
    print("Usar valores por defecto para configuraciones avanzadas? (s/n): ")
    use_defaults = input().lower() == 's'
    
    if not use_defaults:
        # Capital
        initial_capital = input(f"Capital inicial en USDC (default: 1000): ") or "1000"
        config_values['INITIAL_CAPITAL_USD'] = initial_capital
        
        # Tamaño de posición
        position_size = input(f"Tamaño de posición % (default: 10): ") or "10"
        config_values['POSITION_SIZE_PERCENT'] = str(float(position_size) / 100)
        
        # Stop Loss
        stop_loss = input(f"Stop Loss % (default: 2): ") or "2"
        config_values['STOP_LOSS_PERCENT'] = stop_loss
        
        # Take Profit
        take_profit = input(f"Take Profit % (default: 5): ") or "5"
        config_values['TAKE_PROFIT_PERCENT'] = take_profit
        
        # ML Confidence
        ml_confidence = input(f"Confianza mínima ML % (default: 65): ") or "65"
        config_values['ML_CONFIDENCE_THRESHOLD'] = str(float(ml_confidence) / 100)
    
    # 6. 💾 GUARDAR CONFIGURACIÓN
    print("\n💾 GUARDANDO CONFIGURACIÓN")
    print("-" * 40)
    
    # Crear script de configuración
    config_script = """#!/bin/bash
# Script para configurar variables de entorno de OrcaBot
# Ejecutar: source setup_orcabat.sh
    
"""
    
    for key, value in config_values.items():
        config_script += f'export {key}="{value}"\n'
    
    # Agregar variables por defecto
    default_vars = {
        'ENCRYPTION_ITERATIONS': '480000',
        'HELIUS_BASE_URL': 'https://mainnet.helius-rpc.com',
        'HELIUS_WSS_URL': 'wss://mainnet.helius-rpc.com',
        'RPC_TIMEOUT': '30',
        'MAX_RETRIES': '3',
        'COMMITMENT_LEVEL': 'confirmed',
        'TELEGRAM_NOTIFY_ON_ENTRY': 'true',
        'TELEGRAM_NOTIFY_ON_EXIT': 'true',
        'TELEGRAM_NOTIFY_ON_ERROR': 'true',
        'MIN_USDC_BALANCE': '10',
        'MIN_SOL_FEES': '0.05',
        'MAX_PORTFOLIO_EXPOSURE': '0.15',
        'MAX_CONCURRENT_TRADES': '5',
        'MIN_POSITION_SIZE_USD': '10',
        'MAX_SLIPPAGE_PERCENT': '0.5',
        'TRAILING_STOP_ACTIVATION': '0.2',
        'TRAILING_STOP_DISTANCE': '1.0',
        'DAILY_LOSS_LIMIT_PERCENT': '2.0',
        'MAX_DRAWDOWN_PERCENT': '15.0',
        'COOLDOWN_AFTER_LOSSES': '3',
        'TRAINING_INTERVAL_HOURS': '12',
        'ML_MODEL_TYPES': 'LSTM,RandomForest,GradientBoosting',
        'MAX_TOKENS_TO_SELECT': '20',
        'PRIMARY_DEX': 'orca',
        'LOG_LEVEL': 'INFO',
        'BACKUP_INTERVAL_HOURS': '6'
    }
    
    for key, value in default_vars.items():
        if key not in config_values:
            config_script += f'export {key}="{value}"\n'
    
    config_script += """
# Verificar configuración
echo "✅ Variables de entorno configuradas"
echo "🔧 Ejecuta: python config.py para verificar"
"""
    
    # Guardar script
    script_filename = "setup_orcabat.sh"
    with open(script_filename, 'w') as f:
        f.write(config_script)
    
    # Hacer ejecutable
    import stat
    os.chmod(script_filename, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
    
    print(f"✅ Script de configuración creado: {script_filename}")
    print("\n📋 INSTRUCCIONES:")
    print(f"1. Ejecutar: source {script_filename}")
    print("2. Verificar: python config.py")
    print("3. Iniciar bot: python run_bot.py")
    print("\n⚠️ IMPORTANTE:")
    print("- Guarda el script {script_filename} en lugar seguro")
    print("- Las variables solo están activas en esta terminal")
    print("- Para hacerlas permanentes, agrégalas a ~/.bashrc o ~/.zshrc")
    
    return True

def create_permanent_config():
    """Crear configuración permanente en ~/.bashrc o ~/.zshrc"""
    print("\n🔄 CREAR CONFIGURACIÓN PERMANENTE")
    print("-" * 40)
    
    shell_choice = input("¿Qué shell usas? (bash/zsh): ").lower()
    
    if shell_choice not in ['bash', 'zsh']:
        print("❌ Shell no soportado")
        return False
    
    rc_file = f"~/.{shell_choice}rc"
    rc_path = os.path.expanduser(rc_file)
    
    print(f"\nSe agregarán las variables a: {rc_path}")
    confirm = input("¿Continuar? (s/n): ").lower()
    
    if confirm != 's':
        return False
    
    # Leer script de configuración
    with open("setup_orcabat.sh", 'r') as f:
        config_lines = f.readlines()
    
    # Filtrar solo las líneas export
    export_lines = [line for line in config_lines if line.startswith('export')]
    
    # Agregar al archivo rc
    with open(rc_path, 'a') as f:
        f.write("\n# ============================================\n")
        f.write("# 🤖 ORCABOT DEEPSEEK CONFIGURATION\n")
        f.write("# ============================================\n\n")
        f.writelines(export_lines)
        f.write("\n")
    
    print(f"✅ Configuración agregada a {rc_path}")
    print("🔧 Reinicia la terminal o ejecuta: source {rc_path}")
    
    return True

if __name__ == "__main__":
    try:
        if configure_system():
            permanent = input("\n¿Hacer la configuración permanente? (s/n): ").lower()
            if permanent == 's':
                create_permanent_config()
        
        print("\n" + "=" * 60)
        print("✅ CONFIGURACIÓN COMPLETADA")
        print("=" * 60)
        print("\n🚀 Pasos siguientes:")
        print("1. source setup_orcabat.sh")
        print("2. python config.py (verificar)")
        print("3. python run_bot.py (iniciar)")
        
    except KeyboardInterrupt:
        print("\n\n❌ Configuración cancelada")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error durante configuración: {e}")
        sys.exit(1)