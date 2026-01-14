# install_deps.py
"""
Instalar todas las dependencias necesarias automáticamente
"""
import subprocess
import sys
import os

def install_dependencies():
    """Instalar dependencias de Solana"""
    print("📦 INSTALANDO DEPENDENCIAS NECESARIAS")
    print("="*50)
    
    packages = [
        ("solana", "0.30.4"),
        ("solders", "0.18.0"),
        ("anchorpy", "0.19.0"),
        ("aiohttp", "3.9.1"),
        ("base58", "2.1.1"),
        ("construct", "2.10.68"),
        ("cryptography", "41.0.7"),
    ]
    
    for package, version in packages:
        print(f"\n🔧 Instalando {package}=={version}...")
        try:
            # Primero intentar desinstalar versiones conflictivas
            subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", package], 
                          capture_output=True)
            
            # Instalar versión específica
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", f"{package}=={version}"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"   ✅ {package} instalado correctamente")
            else:
                print(f"   ⚠️  Problema con {package}: {result.stderr[:100]}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "="*50)
    print("✅ INSTALACIÓN COMPLETADA")
    print("\n💡 Verifica las instalaciones:")
    
    # Verificar
    check_packages = ["solana", "solders", "aiohttp"]
    for pkg in check_packages:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"   ✅ {pkg} importable")
        except ImportError:
            print(f"   ❌ {pkg} no se puede importar")

def check_current_installations():
    """Verificar qué está instalado actualmente"""
    print("\n🔍 VERIFICANDO INSTALACIONES ACTUALES...")
    
    result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                          capture_output=True, text=True)
    
    print("Paquetes instalados relacionados:")
    for line in result.stdout.split('\n'):
        if any(pkg in line.lower() for pkg in ['solan', 'solder', 'anchor', 'aiohttp', 'base58']):
            print(f"   {line}")

if __name__ == "__main__":
    print("🤖 INSTALADOR DE DEPENDENCIAS PARA ORCABOT")
    print("="*60)
    
    check_current_installations()
    
    response = input("\n¿Instalar/actualizar dependencias? (s/n): ").lower()
    
    if response == 's':
        install_dependencies()
        
        print("\n🎯 PRUEBA RÁPIDA DE IMPORTACIONES:")
        test_imports = """
try:
    import solana
    import solders
    import aiohttp
    print("✅ Importaciones básicas OK")
    
    from solders.keypair import Keypair
    from solana.rpc.async_api import AsyncClient
    print("✅ Submódulos principales OK")
    
    print("\n🎉 ¡Todo listo para OrcaBot!")
    
except ImportError as e:
    print(f"❌ Error: {e}")
"""
        
        print(test_imports)
        
    else:
        print("🛑 Instalación cancelada")
    
    input("\nPresiona Enter para salir...")