# 1. Exportar variables del sistema
export HELIUS_RPC_URL="https://mainnet.helius-rpc.com"
export HELIUS_VOICEINDIGO_API_KEY="tu_api_key"
export PHANTOM_WALLET="tu_direccion"
export PHANTOM_PRIVATE_KEY_BYTE="tu_clave_privada_base58"
export TELEGRAM_BOT_TOKEN="tu_token_bot"
export TELEGRAM_CHAT_ID="tu_chat_id"

# 2. Ejecutar script de configuración
python scripts/setup_environment.py

# 3. Instalar dependencias
pip install -r requirements.txt