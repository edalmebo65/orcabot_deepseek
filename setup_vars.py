# setup_vars.py
"""
Configurar variables de entorno en Windows
"""
import os
import sys

def setup_windows():
    """Configurar variables para Windows"""
    print("🔧 CONFIGURADOR PARA WINDOWS")
    print("="*50)
    
    print("\n1️⃣ ENCRIPTACIÓN:")
    encryption_pw = input("ENCRYPTION_PASSWORD (min 32 chars): ")
    encryption_salt = input("ENCRYPTION_SALT (min 16 chars): ")
    
    print("\n2️⃣ WALLET PHANTOM:")
    private_key = input("PHANTOM_PRIVATE_KEY_BYTES (en base64): ")
    wallet_addr = input("PHANTOM_WALLET (dirección pública): ")
    
    print("\n3️⃣ HELIUS RPC (opcional):")
    helius_key = input("HELIUS_VOICEINDIGO_API_KEY (Enter para omitir): ")
    
    print("\n4️⃣ TELEGRAM (opcional):")
    telegram_token = input("TELEGRAM_BOT_TOKEN (Enter para omitir): ")
    telegram_chat = ""
    if telegram_token:
        telegram_chat = input("TELEGRAM_CHAT_ID: ")
    
    # Crear archivo batch
    create_batch_file(
        encryption_pw,
        encryption_salt,
        private_key,
        wallet_addr,
        helius_key,
        telegram_token,
        telegram_chat
    )
    
    print("\n✅ Archivo creado: start_orcabat.bat")
    print("💡 Ejecuta este archivo ANTES de usar el bot")

def create_batch_file(pw, salt, pkey, wallet, helius, telegram_t, telegram_c):
    """Crear archivo .bat para Windows"""
    content = f"""@echo off
echo 🤖 CONFIGURANDO ORCABOT DEEPSEEK
echo.

:: 🔐 ENCRIPTACIÓN
set ENCRYPTION_PASSWORD={pw}
set ENCRYPTION_SALT={salt}
set ENCRYPTION_ITERATIONS=480000

:: 🏦 WALLET
set PHANTOM_PRIVATE_KEY_BYTES={pkey}
set PHANTOM_WALLET={wallet}
set PHANTOM_PUBLIC_KEY={wallet}

:: 🌐 HELIUS RPC
"""
    
    if helius:
        content += f"set HELIUS_VOICEINDIGO_API_KEY={helius}\n"
    else:
        content += ":: Sin Helius, se usará RPC público\n"
    
    if telegram_t and telegram_c:
        content += f"""
:: 🤖 TELEGRAM
set TELEGRAM_BOT_TOKEN={telegram_t}
set TELEGRAM_CHAT_ID={telegram_c}
"""
    
    # Valores por defecto
    content += """
:: 💰 TRADING (valores por defecto)
set INITIAL_CAPITAL_USD=1000
set MIN_USDC_BALANCE=10
set MIN_SOL_FEES=0.05
set POSITION_SIZE_PERCENT=0.10
set MAX_CONCURRENT_TRADES=5

:: 🎯 RIESGO
set STOP_LOSS_PERCENT=2.0
set TAKE_PROFIT_PERCENT=5.0
set DAILY_LOSS_LIMIT_PERCENT=2.0
set MAX_DRAWDOWN_PERCENT=15.0

:: 🧠 ML
set ML_CONFIDENCE_THRESHOLD=0.65
set TRAINING_INTERVAL_HOURS=12

echo ✅ Variables configuradas!
echo.
echo 📋 Para verificar: python config.py
echo 🚀 Para ejecutar bot: python run_bot_simple.py
echo.
pause
"""
    
    with open("start_orcabat.bat", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    setup_windows()