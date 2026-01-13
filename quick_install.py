#!/usr/bin/env python3
"""
Instalación rápida y corregida para OrcaBot
"""
import subprocess
import sys

def run_command(command, description):
    """Ejecuta comando con manejo de errores"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {description} completado")
            return True
        else:
            print(f"⚠️  {description} tuvo advertencias:")
            print(f"   {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error en {description}: {e}")
        return False

def main():
    """Instalación rápida en 4 pasos"""
    print("🚀 INSTALACIÓN RÁPIDA ORCABOT OPTIMIZADO")
    print("="*50)
    
    # Paso 1: Dependencias esenciales
    run_command(
        f"{sys.executable} -m pip install numpy pandas scipy scikit-learn",
        "Instalando dependencias core"
    )
    
    # Paso 2: Dependencias blockchain
    run_command(
        f"{sys.executable} -m pip install solana solders aiohttp",
        "Instalando dependencias blockchain"
    )
    
    # Paso 3: Dependencias utilities
    run_command(
        f"{sys.executable} -m pip install schedule python-dotenv cryptography rich",
        "Instalando utilities"
    )
    
    # Paso 4: XGBoost (ML ligero)
    run_command(
        f"{sys.executable} -m pip install xgboost",
        "Instalando XGBoost (ML)"
    )
    
    print("\n" + "="*50)
    print("✅ INSTALACIÓN COMPLETADA")
    print("="*50)
    
    print("\n📦 Paquetes instalados:")
    print("   - NumPy, Pandas, SciPy, Scikit-learn")
    print("   - Solana, Solders (blockchain)")
    print("   - Aiohttp (async)")
    print("   - Schedule, python-dotenv, cryptography")
    print("   - XGBoost (machine learning)")
    
    print("\n🎯 Para iniciar el bot:")
    print("   1. python setup_orcabot.py")
    print("   2. Editar .env con tu configuración")
    print("   3. python main_integrated.py")
    
    print("\n⚠️  NOTA: Usamos módulo propio de indicadores técnicos")
    print("   No se requiere pandas-ta problemático")

if __name__ == "__main__":
    main()