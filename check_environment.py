#!/usr/bin/env python3
"""
Verificador de entorno simplificado
"""
import sys
import os
import json
from pathlib import Path

def check_python():
    """Verificar Python"""
    print("🐍 Python Version:", sys.version)
    return sys.version_info >= (3, 10)

def check_imports():
    """Verificar imports críticos"""
    print("\n📦 Verificando imports críticos:")
    
    critical = [
        ('solana', '0.30.1'),
        ('solders', '0.18.0'),
        ('anchorpy', '0.16.0'),
        ('requests', '2.31.0'),
        ('aiohttp', '3.9.1'),
    ]
    
    all_ok = True
    for module, expected in critical:
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', 'N/A')
            status = "✅" if version != 'N/A' else "⚠️"
            print(f"  {status} {module:15} v{version}")
        except ImportError:
            print(f"  ❌ {module:15} NO INSTALADO")
            all_ok = False
    
    return all_ok

def check_rust_bridge():
    """Verificar bridge Rust"""
    print("\n🦀 Verificando bridge Rust:")
    
    try:
        from rust_bridge_fixed import orca_bridge
        print(f"  ✅ Bridge cargado - Modo: {orca_bridge.mode}")
        print(f"     Program ID: {orca_bridge.whirlpool_program_id[:16]}...")
        return True
    except ImportError as e:
        print(f"  ❌ Error cargando bridge: {e}")
        
        # Intentar importar directamente
        try:
            import orca_rust_bridge
            print(f"  ✅ Módulo Rust importado directamente")
            return True
        except ImportError:
            print(f"  ⚠️  Módulo Rust no disponible")
            return False

def check_config():
    """Verificar configuración"""
    print("\n⚙️  Verificando configuración:")
    
    config_file = Path("config.json")
    env_file = Path(".env")
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"  ✅ config.json encontrado")
            print(f"     RPC: {config.get('rpc_url', 'No configurado')}")
        except:
            print(f"  ⚠️  config.json inválido")
    else:
        print(f"  ⚠️  config.json no encontrado")
    
    if env_file.exists():
        print(f"  ✅ .env encontrado")
    else:
        print(f"  ⚠️  .env no encontrado (crear desde .env.example)")

def check_network():
    """Verificar conectividad de red"""
    print("\n🌐 Verificando conectividad:")
    
    import socket
    import requests
    
    try:
        # Verificar DNS
        socket.gethostbyname('api.mainnet-beta.solana.com')
        print(f"  ✅ DNS resuelve")
    except:
        print(f"  ❌ Error DNS")
    
    try:
        # Verificar conexión a Solana
        response = requests.get('https://api.mainnet-beta.solana.com', timeout=5)
        print(f"  ✅ Conexión Solana RPC: OK")
    except Exception as e:
        print(f"  ❌ Error conexión Solana: {e}")

def main():
    print("=" * 60)
    print("🔧 VERIFICACIÓN DE ENTORNO ORCA BOT")
    print("=" * 60)
    
    results = {
        'python': check_python(),
        'imports': check_imports(),
        'rust': check_rust_bridge(),
    }
    
    check_config()
    check_network()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN:")
    
    all_passed = all(results.values())
    
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ¡ENTORNO LISTO PARA ORCA BOT!")
        print("\nPara ejecutar: python main_integrated.py")
    else:
        print("⚠️  HAY PROBLEMAS EN EL ENTORNO")
        print("\nSolución:")
        print("1. Ejecutar: pip install -r requirements_fixed.txt --no-deps")
        print("2. Verificar conflictos de dependencias")
    
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())