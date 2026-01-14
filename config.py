# config.py - EN LA RAIZ DEL PROYECTO
"""
CONFIGURACIÓN SIMPLIFICADA - SIN .env, SIN .env.encrypted
Todas las variables desde variables de entorno del sistema
"""
import os
import base64
from typing import Optional

print("🔧 Cargando configuración desde variables de entorno...")

# ============================================================================
# 🔐 1. ENCRIPTACIÓN (OBLIGATORIO)
# ============================================================================
ENCRYPTION_PASSWORD = os.environ.get('ENCRYPTION_PASSWORD', '')
ENCRYPTION_SALT = os.environ.get('ENCRYPTION_SALT', '')

# Si no están, pedirlas interactivamente
if not ENCRYPTION_PASSWORD:
    print("⚠️ ENCRYPTION_PASSWORD no encontrada")
    ENCRYPTION_PASSWORD = input("Ingresa ENCRYPTION_PASSWORD (min 32 chars): ")

if not ENCRYPTION_SALT:
    print("⚠️ ENCRYPTION_SALT no encontrada")
    ENCRYPTION_SALT = input("Ingresa ENCRYPTION_SALT (min 16 chars): ")

# Validar
if len(ENCRYPTION_PASSWORD) < 32:
    raise ValueError("ENCRYPTION_PASSWORD debe tener al menos 32 caracteres")
if len(ENCRYPTION_SALT) < 16:
    raise ValueError("ENCRYPTION_SALT debe tener al menos 16 caracteres")

ENCRYPTION_ITERATIONS = int(os.environ.get('ENCRYPTION_ITERATIONS', '480000'))

# ============================================================================
# 🏦 2. WALLET PHANTOM (OBLIGATORIO)
# ============================================================================
PHANTOM_PRIVATE_KEY_BYTES = os.environ.get('PHANTOM_PRIVATE_KEY_BYTES', '')
PHANTOM_WALLET = os.environ.get('PHANTOM_WALLET', '')

if not PHANTOM_PRIVATE_KEY_BYTES:
    print("⚠️ PHANTOM_PRIVATE_KEY_BYTES no encontrada")
    PHANTOM_PRIVATE_KEY_BYTES = input("Ingresa PHANTOM_PRIVATE_KEY_BYTES: ")

if not PHANTOM_WALLET:
    print("⚠️ PHANTOM_WALLET no encontrada")
    PHANTOM_WALLET = input("Ingresa PHANTOM_WALLET: ")

PHANTOM_PUBLIC_KEY = os.environ.get('PHANTOM_PUBLIC_KEY', PHANTOM_WALLET)

# ============================================================================
# 🌐 3. RPC HELIUS (OPCIONAL)
# ============================================================================
HELIUS_VOICEINDIGO_API_KEY = os.environ.get('HELIUS_VOICEINDIGO_API_KEY', '')
HELIUS_BASE_URL = "https://mainnet.helius-rpc.com"

# Si no hay clave Helius, usar RPC público
if not HELIUS_VOICEINDIGO_API_KEY:
    print("⚠️ Sin clave Helius, usando RPC público")
    HELIUS_BASE_URL = "https://api.mainnet-beta.solana.com"

# ============================================================================
# 🤖 4. TELEGRAM (OPCIONAL)
# ============================================================================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# ============================================================================
# 💰 5. TRADING (VALORES POR DEFECTO)
# ============================================================================
INITIAL_CAPITAL_USD = float(os.environ.get('INITIAL_CAPITAL_USD', '1000'))
MIN_USDC_BALANCE = float(os.environ.get('MIN_USDC_BALANCE', '10'))
MIN_SOL_FEES = float(os.environ.get('MIN_SOL_FEES', '0.05'))
POSITION_SIZE_PERCENT = float(os.environ.get('POSITION_SIZE_PERCENT', '0.10'))
MAX_CONCURRENT_TRADES = int(os.environ.get('MAX_CONCURRENT_TRADES', '5'))

# ============================================================================
# 🎯 6. RIESGO (VALORES POR DEFECTO)
# ============================================================================
STOP_LOSS_PERCENT = float(os.environ.get('STOP_LOSS_PERCENT', '2.0'))
TAKE_PROFIT_PERCENT = float(os.environ.get('TAKE_PROFIT_PERCENT', '5.0'))
DAILY_LOSS_LIMIT_PERCENT = float(os.environ.get('DAILY_LOSS_LIMIT_PERCENT', '2.0'))
MAX_DRAWDOWN_PERCENT = float(os.environ.get('MAX_DRAWDOWN_PERCENT', '15.0'))

# ============================================================================
# 🧠 7. MACHINE LEARNING (VALORES POR DEFECTO)
# ============================================================================
ML_CONFIDENCE_THRESHOLD = float(os.environ.get('ML_CONFIDENCE_THRESHOLD', '0.65'))
TRAINING_INTERVAL_HOURS = int(os.environ.get('TRAINING_INTERVAL_HOURS', '12'))

# ============================================================================
# 📊 8. UTILIDADES
# ============================================================================
def get_private_key() -> Optional[bytes]:
    """Obtener clave privada en formato bytes"""
    if not PHANTOM_PRIVATE_KEY_BYTES:
        return None
    
    try:
        # Si parece base64, decodificar
        if '=' in PHANTOM_PRIVATE_KEY_BYTES or (len(PHANTOM_PRIVATE_KEY_BYTES) % 4 == 0):
            return base64.b64decode(PHANTOM_PRIVATE_KEY_BYTES)
        # Sino, asumir que ya es string de bytes
        return PHANTOM_PRIVATE_KEY_BYTES.encode('utf-8')
    except:
        return None

def validate_config():
    """Validar configuración mínima"""
    errors = []
    
    if not ENCRYPTION_PASSWORD:
        errors.append("ENCRYPTION_PASSWORD")
    if not ENCRYPTION_SALT:
        errors.append("ENCRYPTION_SALT")
    if not PHANTOM_PRIVATE_KEY_BYTES:
        errors.append("PHANTOM_PRIVATE_KEY_BYTES")
    if not PHANTOM_WALLET:
        errors.append("PHANTOM_WALLET")
    
    if errors:
        print(f"❌ Faltan variables: {', '.join(errors)}")
        return False
    
    return True

def print_summary():
    """Mostrar resumen de configuración"""
    print("\n" + "="*60)
    print("📋 RESUMEN DE CONFIGURACIÓN")
    print("="*60)
    print(f"👛 Wallet: {PHANTOM_WALLET[:8]}...")
    print(f"🌐 RPC: {'Helius' if HELIUS_VOICEINDIGO_API_KEY else 'Público'}")
    print(f"🤖 Telegram: {'Sí' if TELEGRAM_ENABLED else 'No'}")
    print(f"💰 Capital: ${INITIAL_CAPITAL_USD}")
    print(f"🎯 Posición: {POSITION_SIZE_PERCENT*100}%")
    print(f"🛑 Stop Loss: {STOP_LOSS_PERCENT}%")
    print(f"📈 Take Profit: {TAKE_PROFIT_PERCENT}%")
    print(f"🧠 ML Confianza: {ML_CONFIDENCE_THRESHOLD*100}%")
    print("="*60)

# ============================================================================
# 🚀 EJECUCIÓN DIRECTA
# ============================================================================
if __name__ == "__main__":
    if validate_config():
        print("✅ Configuración válida")
        print_summary()
    else:
        print("\n💡 Configura las variables de entorno:")
        print("   set ENCRYPTION_PASSWORD=tu_password_32_chars")
        print("   set ENCRYPTION_SALT=tu_salt_16_chars")
        print("   set PHANTOM_PRIVATE_KEY_BYTES=tu_clave_base64")
        print("   set PHANTOM_WALLET=tu_direccion")
        print("\nO ejecuta: python setup_vars.py")