#!/usr/bin/env python3
"""
Instalador de dependencias sin conflictos
"""
import subprocess
import sys

def run_command(cmd):
    """Ejecutar comando"""
    print(f"Ejecutando: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Completado")
        return True
    else:
        print(f"❌ Error: {result.stderr[:200]}")
        return False

def main():
    print("=" * 60)
    print("📦 INSTALADOR DE DEPENDENCIAS SIN CONFLICTOS")
    print("=" * 60)
    
    # Instalar en orden específico para evitar conflictos
    packages = [
        # Core primero
        ("pip install --upgrade pip setuptools wheel", "Actualizar herramientas"),
        
        # Dependencias base
        ("pip install requests==2.31.0", "Instalar requests"),
        ("pip install aiohttp==3.9.1", "Instalar aiohttp"),
        
        # Solana stack
        ("pip install solana==0.30.1 --no-deps", "Instalar solana sin dependencias"),
        ("pip install base58==2.1.1 construct==2.10.68", "Dependencias de solana"),
        
        # Solders y AnchorPy
        ("pip install solders==0.18.0", "Instalar solders"),
        ("pip install anchorpy==0.16.0", "Instalar anchorpy"),
        
        # Utilidades
        ("pip install python-dotenv==1.0.0", "Instalar python-dotenv"),
        ("pip install rich==13.5.3", "Instalar rich"),
        ("pip install loguru==0.7.2", "Instalar loguru"),
        
        # Opcionales (si no causan conflictos)
        ("pip install pandas==2.0.3", "Instalar pandas"),
        ("pip install pydantic==2.4.2", "Instalar pydantic"),
    ]
    
    all_success = True
    
    for cmd, desc in packages:
        print(f"\n🔧 {desc}")
        if not run_command(cmd):
            print(f"   ⚠️  Continuando...")
            all_success = False
    
    print("\n" + "=" * 60)
    if all_success:
        print("🎉 ¡DEPENDENCIAS INSTALADAS!")
    else:
        print("⚠️  Algunas dependencias pueden tener problemas")
    
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())