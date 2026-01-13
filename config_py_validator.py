#!/usr/bin/env python3
"""
Validador y configurador de config.py
Ayuda a verificar y completar la configuración
"""
import sys
import os
from pathlib import Path

def validate_config_py_structure():
    """Valida la estructura de config.py"""
    print("🔍 Validando estructura de config.py...")
    
    required_properties = [
        'BASE_DIR',
        'LOGS_DIR', 
        'HISTORICO_DIR',
        'SECURITY_DIR',
        'PRIVATE_KEY_B58',
        'WALLET_ADDRESS',
        'HELIUS_API_KEY',
        'RPC_FULL_URL',
        'MAX_POSITION_SIZE_USD',
        'MAX_PORTFOLIO_EXPOSURE',
        'DAILY_LOSS_LIMIT',
        'MIN_PROFIT_MARGIN',
        'ML_CONFIDENCE_THRESHOLD',
        'ML_SEQUENCE_LENGTH',
        'LOG_LEVEL'
    ]
    
    optional_properties = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID',
        'TELEGRAM_ADMIN_ID'
    ]
    
    try:
        # Intentar importar config.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("config", "config.py")
        if spec is None:
            print("❌ config.py no encontrado")
            return False
        
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        if not hasattr(config_module, 'CONFIG'):
            print("❌ No se encuentra objeto CONFIG en config.py")
            return False
        
        config_obj = config_module.CONFIG
        
        print("\n📋 PROPIEDADES REQUERIDAS:")
        missing_required = []
        for prop in required_properties:
            if hasattr(config_obj, prop):
                value = getattr(config_obj, prop)
                status = "✅" if value else "⚠️ (vacío)"
                print(f"  {status} {prop}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
                
                if not value and prop not in ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_ADMIN_ID']:
                    missing_required.append(prop)
            else:
                print(f"  ❌ {prop}: NO EXISTE")
                missing_required.append(prop)
        
        print("\n📋 PROPIEDADES OPCIONALES:")
        missing_optional = []
        for prop in optional_properties:
            if hasattr(config_obj, prop):
                value = getattr(config_obj, prop)
                status = "✅" if value else "⚠️ (vacío)"
                print(f"  {status} {prop}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
            else:
                print(f"  ⚠️  {prop}: NO EXISTE (opcional)")
                missing_optional.append(prop)
        
        print("\n" + "="*50)
        
        if missing_required:
            print(f"❌ FALTAN {len(missing_required)} PROPIEDADES REQUERIDAS:")
            for prop in missing_required:
                print(f"  • {prop}")
            return False
        else:
            print("✅ Todas las propiedades requeridas están presentes")
            return True
            
    except Exception as e:
        print(f"❌ Error validando config.py: {e}")
        return False

def create_config_py_template():
    """Crea template de config.py si no existe"""
    template = '''"""
CONFIGURACIÓN ORCABOT - Archivo principal de configuración
Todas las variables se configuran aquí, NO se usa .env
"""

import os
from pathlib import Path

class Config:
    # --- DIRECTORIOS ---
    BASE_DIR = Path("C:/Users/edalm/Documents/TradingAlgoritmico/OrcaBot_gemini")
    LOGS_DIR = BASE_DIR / "logs"
    HISTORICO_DIR = BASE_DIR / "historico"
    SECURITY_DIR = BASE_DIR / "security"
    
    # --- WALLET Y SEGURIDAD ---
    # Configura tu wallet Phantom aquí
    PRIVATE_KEY_B58 = "TU_CLAVE_PRIVADA_BASE58_AQUÍ"  # Clave privada en Base58
    WALLET_ADDRESS = "TU_DIRECCIÓN_WALLET_AQUÍ"  # Dirección pública
    
    # --- CONECTIVIDAD RPC ---
    # Obtén API key de https://www.helius.dev/
    HELIUS_API_KEY = "TU_API_KEY_HELIUS_AQUÍ"
    HELIUS_BASE = "https://mainnet.helius-rpc.com"
    
    @property
    def RPC_FULL_URL(self):
        """URL completa del RPC endpoint"""
        return f"{self.HELIUS_BASE}/?api-key={self.HELIUS_API_KEY}"
    
    # --- TELEGRAM (Opcional) ---
    TELEGRAM_BOT_TOKEN = ""  # Token del bot de Telegram
    TELEGRAM_CHAT_ID = ""    # Chat ID para notificaciones
    TELEGRAM_ADMIN_ID = ""   # ID del administrador
    
    # --- PARÁMETROS DE TRADING ---
    MAX_POSITION_SIZE_USD = 1000.0      # Máximo $1000 por operación
    MAX_PORTFOLIO_EXPOSURE = 0.15       # Máximo 15% exposición del portfolio
    DAILY_LOSS_LIMIT = 0.02             # Máximo 2% pérdida diaria
    MIN_PROFIT_MARGIN = 0.002           # Mínimo 0.2% margen de ganancia
    
    # --- PARÁMETROS ML ---
    ML_CONFIDENCE_THRESHOLD = 0.68      # 68% confianza mínima
    ML_SEQUENCE_LENGTH = 60             # Longitud de secuencia para LSTM
    
    # --- LOGGING ---
    LOG_LEVEL = "INFO"                  # DEBUG, INFO, WARNING, ERROR
    
    # --- MÉTODOS DE UTILIDAD ---
    @classmethod
    def setup_directories(cls):
        """Crea todos los directorios necesarios"""
        directories = [
            cls.LOGS_DIR,
            cls.HISTORICO_DIR,
            cls.SECURITY_DIR,
            cls.HISTORICO_DIR / "ohlcv",
            cls.HISTORICO_DIR / "ml_features",
            cls.HISTORICO_DIR / "trades",
            cls.HISTORICO_DIR / "models",
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

# Inicializar configuración
CONFIG = Config()
CONFIG.setup_directories()

# Validación básica
def validate_config():
    """Valida que la configuración mínima esté presente"""
    if not CONFIG.PRIVATE_KEY_B58 or CONFIG.PRIVATE_KEY_B58 == "TU_CLAVE_PRIVADA_BASE58_AQUÍ":
        raise ValueError("❌ Configura PRIVATE_KEY_B58 en config.py")
    
    if not CONFIG.WALLET_ADDRESS or CONFIG.WALLET_ADDRESS == "TU_DIRECCIÓN_WALLET_AQUÍ":
        raise ValueError("❌ Configura WALLET_ADDRESS en config.py")
    
    if not CONFIG.HELIUS_API_KEY or CONFIG.HELIUS_API_KEY == "TU_API_KEY_HELIUS_AQUÍ":
        raise ValueError("❌ Configura HELIUS_API_KEY en config.py")
    
    print("✅ Configuración validada correctamente")

# Ejecutar validación al importar
if __name__ == "__main__":
    try:
        validate_config()
    except ValueError as e:
        print(e)
'''

    with open("config.py.template", "w", encoding="utf-8") as f:
        f.write(template)
    
    print("📄 Template config.py.template creado")
    print("📝 Renómbralo a config.py y configura tus datos")
    return True

def migrate_from_env_to_config_py():
    """Migra configuración de .env a config.py"""
    if not Path(".env").exists():
        print("⚠️  No se encontró archivo .env para migrar")
        return False
    
    print("🔄 Migrando configuración de .env a config.py...")
    
    try:
        # Leer .env
        env_vars = {}
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
        
        # Crear config.py desde template
        with open("config.py", "r") as f:
            config_content = f.read()
        
        # Reemplazar valores
        replacements = {
            "TU_CLAVE_PRIVADA_BASE58_AQUÍ": env_vars.get("PHANTOM_PRIVATE_KEY_BYTES", ""),
            "TU_DIRECCIÓN_WALLET_AQUÍ": env_vars.get("PHANTOM_WALLET", ""),
            "TU_API_KEY_HELIUS_AQUÍ": env_vars.get("HELIUS_VOICEINDIGO_API_KEY", ""),
            "": env_vars.get("TELEGRAM_BOT_TOKEN", ""),
            "": env_vars.get("TELEGRAM_CHAT_ID", ""),
            "": env_vars.get("TELEGRAM_ADMIN_ID", "")
        }
        
        for old, new in replacements.items():
            if old and new:
                config_content = config_content.replace(old, new)
        
        # Guardar config.py actualizado
        with open("config.py.migrated", "w", encoding="utf-8") as f:
            f.write(config_content)
        
        print("✅ Migración completada: config.py.migrated")
        print("📝 Revisa el archivo y renómbralo a config.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        return False

def main():
    """Menú principal del validador"""
    print("="*60)
    print("🛠️  VALIDADOR Y CONFIGURADOR DE config.py")
    print("="*60)
    
    print("\nOpciones:")
    print("1. ✅ Validar config.py actual")
    print("2. 📄 Crear template de config.py")
    print("3. 🔄 Migrar de .env a config.py")
    print("4. 🚪 Salir")
    
    try:
        option = input("\nSelecciona opción (1-4): ").strip()
        
        if option == "1":
            if validate_config_py_structure():
                print("\n🎉 config.py está correctamente configurado")
                print("📁 El bot usará esta configuración (NO .env)")
            else:
                print("\n⚠️  Corrige los errores en config.py")
        
        elif option == "2":
            create_config_py_template()
            print("\n📝 Edita config.py.template con tus datos")
            print("🔁 Luego renómbralo a config.py")
        
        elif option == "3":
            migrate_from_env_to_config_py()
        
        elif option == "4":
            print("👋 ¡Hasta luego!")
        
        else:
            print("❌ Opción inválida")
    
    except KeyboardInterrupt:
        print("\n\n👋 Operación cancelada")

if __name__ == "__main__":
    main()