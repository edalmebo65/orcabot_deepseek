# ============================================
# ORCABOT - CONFIGURACIÓN SEGURA DE TRADING WEB3
# ============================================

# --- IDENTIDAD WALLET (ENCRIPTADA) ---
# Clave privada Phantom en Base58 original (PARA ENCRIPTAR)
PHANTOM_PRIVATE_KEY_BYTES="YOUR_ACTUAL_BASE58_PRIVATE_KEY_HERE"

# Clave privada encriptada (generar con el script de abajo)
ENCRYPTED_PRIVATE_KEY="gAAAAABn0iV1... (será generado automáticamente)"

# Dirección pública de la wallet
PHANTOM_WALLET="YOUR_PHANTOM_WALLET_ADDRESS_HERE"

# --- CONFIGURACIÓN ENCRIPTACIÓN HÍBRIDA ---
# Salt para derivación de clave (aleatorio y único)
ENCRYPTION_SALT="e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8"

# Contraseña maestra para desencriptar
ENCRYPTION_PASSWORD="YourStrongMasterPassword123!@#"

# IV para AES (Initialization Vector)
ENCRYPTION_IV="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"

# --- CONECTIVIDAD HELIUS RPC ---
HELIUS_VOICEINDIGO_API_KEY="your_helius_api_key_here"

# URL base Helius (no cambiar a menos que uses otra red)
HELIUS_BASE_URL="https://mainnet.helius-rpc.com"

# --- CONFIGURACIÓN TELEGRAM BOT ---
TELEGRAM_BOT_TOKEN="1234567890:AAHxQ6xxxxxxxxxxxxxxxxxxxxxxx"
TELEGRAM_CHAT_ID="-1001234567890"
TELEGRAM_ADMIN_ID="987654321"

# --- PARÁMETROS DE TRADING Y RIESGO ---
MAX_POSITION_SIZE_USD=1000                     # Tamaño máximo por posición en USD
MAX_PORTFOLIO_EXPOSURE=0.15                    # 15% exposición máxima total
DAILY_LOSS_LIMIT=0.02                          # 2% pérdida máxima diaria
MIN_PROFIT_MARGIN=0.002                        # 0.2% ganancia mínima requerida
TRAILING_STOP_ACTIVATION=0.005                 # 0.5% para activar trailing stop
TRAILING_STOP_DISTANCE=0.002                   # 0.2% distancia del trailing
SLIPPAGE_TOLERANCE=0.005                       # 0.5% slippage máximo permitido

# --- CONFIGURACIÓN ML Y ANÁLISIS ---
ML_CONFIDENCE_THRESHOLD=0.68                   # 68% confianza mínima para operar
ML_SEQUENCE_LENGTH=60                          # Longitud de secuencia LSTM
ML_TRAINING_INTERVAL_HOURS=24                  # Reentrenar cada 24 horas
ML_MIN_SAMPLES_REQUIRED=1000                   # Mínimo muestras para entrenar
RSI_OVERBOUGHT=70
RSI_OVERSOLD=30
BBANDS_PERIOD=20
BBANDS_STD=2.0

# --- WHIRLPOOL SCANNING ---
MIN_POOL_LIQUIDITY=10000                       # $10k mínimo de liquidez
MAX_POOL_FEE_RATE=0.003                        # 0.3% máximo fee rate
MIN_DAILY_VOLUME=50000                         # $50k volumen mínimo diario
POOL_SCAN_INTERVAL_SECONDS=300                 # Escanear cada 5 minutos
TOP_POOLS_TO_ANALYZE=50                        # Analizar top 50 pools

# --- SISTEMA DE LOGGING Y MONITOREO ---
LOG_LEVEL="INFO"                               # DEBUG, INFO, WARNING, ERROR
ENABLE_PERFORMANCE_LOGGING=true
ENABLE_TRADE_AUDIT_TRAIL=true
SENTRY_DSN="https://xxxxxxxxxxxxxxx.ingest.sentry.io/xxxxxxxxxx"
HEALTH_CHECK_URL="https://hc-ping.com/your-uuid-here"
MONITORING_PORT=9090

# --- SEGURIDAD AVANZADA ---
ENABLE_ANOMALY_DETECTION=true
ENABLE_COOLDOWN_PERIODS=true
MAX_TRADES_PER_HOUR=10
REQUIRE_TELEGRAM_CONFIRMATION_ABOVE_USD=500
AUTO_PAUSE_ON_ANOMALY=true
ENABLE_CIRCUIT_BREAKER=true

# --- ALERTAS Y NOTIFICACIONES ---
ALERT_ON_LARGE_TRADE=true
ALERT_ON_STOP_LOSS_HIT=true
ALERT_ON_ANOMALY_DETECTED=true
ALERT_ON_BOT_START_STOP=true

# --- BACKUP Y RECUPERACIÓN ---
AUTO_BACKUP_INTERVAL_HOURS=6
KEEP_BACKUP_FILES_DAYS=30
ENABLE_AUTO_RECOVERY=true