#!/usr/bin/env python3
"""
Punto de entrada principal para OrcaBot
Gestiona inicio, configuración y ejecución del bot
"""
import os
import sys
import json
import logging
import argparse
from pathlib import Path

# Agregar directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_integrated import OrcaTradingBot, TradingMode, OperationStatus

def setup_logging(log_level="INFO"):
    """Configura el sistema de logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler('orca_bot.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def check_dependencies():
    """Verifica dependencias necesarias"""
    import importlib.util
    
    required_packages = [
        "numpy",
        "pandas",
        "schedule",
        "requests"
    ]
    
    missing = []
    for package in required_packages:
        spec = importlib.util.find_spec(package)
        if spec is None:
            missing.append(package)
    
    if missing:
        print(f"❌ Paquetes faltantes: {', '.join(missing)}")
        print("Instala con: pip install " + " ".join(missing))
        return False
    
    return True

def setup_configuration(args):
    """Configura el entorno según los argumentos"""
    config_path = args.config
    
    # Crear configuración por defecto si no existe
    if not os.path.exists(config_path):
        print(f"⚠️  Archivo de configuración {config_path} no encontrado")
        create_default = input("¿Crear configuración por defecto? (s/n): ")
        
        if create_default.lower() == 's':
            create_default_config(config_path)
        else:
            print("❌ Se requiere archivo de configuración")
            sys.exit(1)
    
    # Cargar configuración
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Aplicar argumentos de línea de comandos
    if args.mode:
        config['trading_mode'] = args.mode
    
    if args.log_level:
        config['logging']['level'] = args.log_level
    
    # Guardar configuración actualizada
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config

def create_default_config(config_path):
    """Crea configuración por defecto"""
    default_config = {
        "trading_mode": "paper",
        "rust_binary_path": "./target/release/orca_bridge",
        "solana": {
            "rpc_endpoint": "https://api.mainnet-beta.solana.com"
        },
        "trading_pairs": [
            {
                "base": "SOL",
                "quote": "USDC",
                "min_amount": 0.1,
                "max_amount": 10.0,
                "enabled": true
            }
        ],
        "risk_parameters": {
            "max_capital_per_trade": 0.1,
            "max_open_trades": 5,
            "stop_loss_percent": 2.0
        },
        "logging": {
            "level": "INFO"
        },
        "telegram": {
            "token": "",
            "chat_id": ""
        }
    }
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(config_path) or '.', exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    print(f"✅ Configuración por defecto creada en {config_path}")
    print("⚠️  Configura los parámetros necesarios antes de usar en modo LIVE")

def parse_arguments():
    """Parse argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='OrcaBot - Bot de Trading para Solana',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s                    # Inicia en modo paper con config por defecto
  %(prog)s --mode paper       # Modo paper trading
  %(prog)s --mode live        # Modo live trading (¡CUIDADO!)
  %(prog)s --config custom.json
  %(prog)s --log-level DEBUG
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['paper', 'live', 'backtest'],
        help='Modo de operación del bot'
    )
    
    parser.add_argument(
        '--config',
        default='config.json',
        help='Ruta al archivo de configuración'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Nivel de logging'
    )
    
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Ejecuta configuración inicial'
    )
    
    parser.add_argument(
        '--health',
        action='store_true',
        help='Verifica salud del sistema'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Muestra estado actual del bot'
    )
    
    return parser.parse_args()

def setup_wizard():
    """Asistente de configuración inicial"""
    print("""
╔════════════════════════════════════════╗
║      ORCABOT - ASISTENTE DE SETUP      ║
╚════════════════════════════════════════╝
""")
    
    config = {}
    
    # Modo de trading
    print("\n1. Modo de Trading:")
    print("   1) Paper Trading (simulación)")
    print("   2) Live Trading (fondos reales)")
    
    mode_choice = input("   Selecciona (1-2) [1]: ").strip() or "1"
    config['trading_mode'] = 'paper' if mode_choice == '1' else 'live'
    
    # Configuración de wallet (solo para live)
    if config['trading_mode'] == 'live':
        print("\n⚠️  ATENCIÓN: MODO LIVE CON FONDOS REALES")
        print("   Asegúrate de usar una wallet de prueba con fondos mínimos")
        
        use_testnet = input("   ¿Usar testnet? (s/n) [s]: ").strip().lower() or 's'
        
        if use_testnet == 's':
            config['solana'] = {
                'rpc_endpoint': 'https://api.testnet.solana.com',
                'network': 'testnet'
            }
        else:
            print("\n   Configuración Mainnet:")
            config['solana'] = {
                'rpc_endpoint': input("   RPC Endpoint [https://api.mainnet-beta.solana.com]: ").strip() 
                              or 'https://api.mainnet-beta.solana.com',
                'network': 'mainnet-beta'
            }
    
    # Pares de trading
    print("\n2. Pares de Trading:")
    pairs = []
    
    while True:
        base = input("   Token base (ej: SOL) [SOL]: ").strip().upper() or "SOL"
        quote = input("   Token quote (ej: USDC) [USDC]: ").strip().upper() or "USDC"
        min_amount = float(input(f"   Cantidad mínima de {base} [0.1]: ").strip() or "0.1")
        max_amount = float(input(f"   Cantidad máxima de {base} [10.0]: ").strip() or "10.0")
        
        pairs.append({
            'base': base,
            'quote': quote,
            'min_amount': min_amount,
            'max_amount': max_amount,
            'enabled': True
        })
        
        another = input("   ¿Agregar otro par? (s/n) [n]: ").strip().lower() or 'n'
        if another != 's':
            break
    
    config['trading_pairs'] = pairs
    
    # Gestión de riesgos
    print("\n3. Gestión de Riesgos:")
    config['risk_parameters'] = {
        'max_capital_per_trade': float(
            input("   Capital máximo por operación (0.01-0.5) [0.1]: ").strip() or "0.1"
        ),
        'max_open_trades': int(
            input("   Máximo de operaciones simultáneas [5]: ").strip() or "5"
        ),
        'stop_loss_percent': float(
            input("   Stop loss porcentaje [2.0]: ").strip() or "2.0"
        )
    }
    
    # Telegram (opcional)
    print("\n4. Notificaciones Telegram (opcional):")
    enable_telegram = input("   ¿Habilitar notificaciones? (s/n) [n]: ").strip().lower() or 'n'
    
    if enable_telegram == 's':
        config['telegram'] = {
            'token': input("   Token del bot: ").strip(),
            'chat_id': input("   Chat ID: ").strip(),
            'enable_notifications': True
        }
    
    # Guardar configuración
    config_path = input("\n   Ruta para guardar configuración [config.json]: ").strip() or "config.json"
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(config_path) or '.', exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Configuración guardada en {config_path}")
    print("\n⚠️  IMPORTANTE:")
    print("   1. Revisa la configuración antes de usar el bot")
    print("   2. En modo LIVE, usa una wallet con fondos mínimos")
    print("   3. Nunca compartas tus claves privadas")
    
    return config_path

def health_check(config):
    """Verifica salud del sistema"""
    print("\n🔍 VERIFICANDO SALUD DEL SISTEMA")
    print("=" * 40)
    
    checks = []
    
    # Verificar archivo de configuración
    if os.path.exists(config.get('config_path', 'config.json')):
        checks.append(("✅", "Archivo de configuración"))
    else:
        checks.append(("❌", "Archivo de configuración"))
    
    # Verificar módulo Rust
    rust_binary = config.get('rust_binary_path', './target/release/orca_bridge')
    if os.path.exists(rust_binary):
        checks.append(("✅", "Binario Rust"))
    else:
        checks.append(("⚠️ ", "Binario Rust (modo simulación)"))
    
    # Verificar dependencias Python
    try:
        import numpy
        import pandas
        checks.append(("✅", "Dependencias Python"))
    except ImportError:
        checks.append(("❌", "Dependencias Python"))
    
    # Verificar conexión RPC
    try:
        import requests
        rpc_endpoint = config.get('solana', {}).get('rpc_endpoint', '')
        if rpc_endpoint:
            response = requests.post(rpc_endpoint, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getHealth"
            }, timeout=5)
            if response.status_code == 200:
                checks.append(("✅", "Conexión RPC Solana"))
            else:
                checks.append(("⚠️ ", "Conexión RPC limitada"))
    except:
        checks.append(("❌", "Conexión RPC Solana"))
    
    # Mostrar resultados
    for status, check in checks:
        print(f"{status} {check}")
    
    print("\n" + "=" * 40)
    
    # Evaluación general
    all_ok = all(status in ["✅", "⚠️ "] for status, _ in checks)
    
    if all_ok:
        print("✅ Sistema listo para operar")
        return True
    else:
        print("❌ Problemas detectados en el sistema")
        return False

def main():
    """Función principal"""
    args = parse_arguments()
    
    # Mostrar banner
    print("""
╔═══════════════════════════════════════════════╗
║               🤖 ORCABOT v2.0                ║
║     Trading Algorítmico para Solana          ║
╚═══════════════════════════════════════════════╝
""")
    
    # Ejecutar setup si se solicita
    if args.setup:
        config_path = setup_wizard()
        args.config = config_path
    
    # Verificar dependencias
    if not check_dependencies():
        sys.exit(1)
    
    # Configurar logging
    logger = setup_logging(args.log_level or "INFO")
    
    try:
        # Configurar el bot
        config = setup_configuration(args)
        
        # Verificar salud si se solicita
        if args.health:
            if not health_check(config):
                sys.exit(1)
            return
        
        # Crear instancia del bot
        bot = OrcaTradingBot(args.config)
        
        # Mostrar estado si se solicita
        if args.status:
            status = bot.get_status()
            print("\n📊 ESTADO DEL BOT")
            print("=" * 40)
            print(f"Modo: {status['mode']}")
            print(f"Estado: {status['status']}")
            print(f"Balance: {status['balance']}")
            print(f"Posiciones activas: {len(status['positions'])}")
            print(f"Operaciones totales: {status['statistics']['total_trades']}")
            return
        
        # Mostrar información de inicio
        print(f"\n📋 CONFIGURACIÓN:")
        print(f"   Modo: {config['trading_mode']}")
        print(f"   Pares: {len(config['trading_pairs'])}")
        print(f"   RPC: {config.get('solana', {}).get('rpc_endpoint', 'No configurado')}")
        
        if config['trading_mode'] == 'live':
            print("\n⚠️  ⚠️  ⚠️  ADVERTENCIA ⚠️  ⚠️  ⚠️")
            print("   MODO LIVE ACTIVADO - FONDOS REALES EN RIESGO")
            print("   Presiona Ctrl+C para cancelar en 5 segundos...")
            
            try:
                import time
                for i in range(5, 0, -1):
                    print(f"   Iniciando en {i}...", end='\r')
                    time.sleep(1)
                print()
            except KeyboardInterrupt:
                print("\n❌ Inicio cancelado por usuario")
                sys.exit(0)
        
        # Iniciar el bot
        print("\n🚀 INICIANDO ORCABOT...")
        bot.start()
        
        # Mantener ejecución
        print("\n🔄 Bot en ejecución. Presiona Ctrl+C para detener.")
        print("   Comandos disponibles via Telegram si está configurado.")
        
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Detención solicitada por usuario")
        if 'bot' in locals():
            bot.stop()
        print("✅ OrcaBot detenido correctamente")
        
    except Exception as e:
        logger.error(f"Error crítico: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()