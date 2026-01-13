# 🔧 CONFIGURACIÓN CON config.py

OrcaBot ahora usa **exclusivamente** `config.py` para toda la configuración. **NO se usa el archivo .env**.

## 📁 ESTRUCTURA DE config.py

Tu archivo `config.py` debe contener:

```python
class Config:
    # 1. DIRECTORIOS
    BASE_DIR = Path("ruta/a/tu/proyecto")
    LOGS_DIR = BASE_DIR / "logs"
    # ... etc
    
    # 2. WALLET Y SEGURIDAD
    PRIVATE_KEY_B58 = "tu_clave_privada_base58"
    WALLET_ADDRESS = "tu_direccion_publica"
    
    # 3. RPC
    HELIUS_API_KEY = "tu_api_key_helius"
    HELIUS_BASE = "https://mainnet.helius-rpc.com"
    
    # 4. TELEGRAM (Opcional)
    TELEGRAM_BOT_TOKEN = ""
    TELEGRAM_CHAT_ID = ""
    
    # 5. PARÁMETROS TRADING
    MAX_POSITION_SIZE_USD = 1000.0
    MAX_PORTFOLIO_EXPOSURE = 0.15
    # ... etc

CONFIG = Config()
CONFIG.setup_directories()