# .env.example
# Copiar a .env y completar con tus credenciales

# --- WALLET (OBLIGATORIO) ---
PHANTOM_PRIVATE_KEY_BYTES="tu_clave_privada_base58_aqui"
PHANTOM_WALLET="tu_direccion_phantom_aqui"

# --- ENCRYPTION (OBLIGATORIO) ---
# Generar con: openssl rand -base64 32
ENCRYPTION_SALT="generar_salt_unico_aqui"
ENCRYPTION_PASSWORD="tu_password_fuerte_aqui"

# --- HELIUS RPC (OBLIGATORIO) ---
HELIUS_VOICEINDIGO_API_KEY="tu_api_key_helius_aqui"

# --- TELEGRAM (OPCIONAL pero recomendado) ---
TELEGRAM_BOT_TOKEN="optional"
TELEGRAM_CHAT_ID="optional"
TELEGRAM_ADMIN_ID="optional"

# --- TRADING PARAMETERS (AJUSTAR) ---
MAX_POSITION_SIZE_USD=1000
MAX_PORTFOLIO_EXPOSURE=0.15
DAILY_LOSS_LIMIT=0.02
MIN_PROFIT_MARGIN=0.002

# --- ML PARAMETERS ---
ML_CONFIDENCE_THRESHOLD=0.68
ML_SEQUENCE_LENGTH=60

# --- LOGGING ---
LOG_LEVEL=INFO