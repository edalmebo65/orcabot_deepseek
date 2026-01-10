#!/usr/bin/env python3
"""
Instalador específico para orca-py en Windows
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(cmd, desc):
    """Ejecuta un comando"""
    print(f"\n🔧 {desc}")
    print(f"   $ {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print(f"   ✅ Completado")
            return True
        else:
            print(f"   ❌ Error: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
        return False

def check_orca_installed():
    """Verifica si orca está instalado"""
    try:
        import orca
        print(f"✅ orca-py encontrado en: {orca.__file__}")
        return True
    except ImportError:
        return False

def main():
    print("=" * 60)
    print("🐋 INSTALADOR ORCA-PY PARA WINDOWS")
    print("=" * 60)
    
    # Verificar entorno
    env = os.environ.get('CONDA_DEFAULT_ENV', 'base')
    print(f"Entorno: {env}")
    print(f"Python: {sys.executable}")
    
    # 1. Limpiar instalaciones previas
    print("\n1. Limpiando instalaciones previas...")
    run_command("pip uninstall orca-py -y", "Desinstalando orca-py")
    
    # 2. Instalar dependencias
    print("\n2. Instalando dependencias...")
    dependencies = [
        "pip install typing-extensions==4.8.0",
        "pip install construct-typing==0.6.0",
        "pip install base58==2.1.1",
        "pip install pydantic==2.4.2",
        "pip install solders==0.18.0 --force-reinstall",
    ]
    
    for dep in dependencies:
        run_command(dep, f"Instalando {dep.split()[2]}")
    
    # 3. Intentar diferentes métodos de instalación
    print("\n3. Intentando instalar orca-py...")
    
    methods = [
        # Método 1: Desde GitHub con flags
        'pip install "git+https://github.com/orca-so/orca-py.git" --no-cache-dir --no-build-isolation',
        
        # Método 2: Específicamente desde main branch
        'pip install "git+https://github.com/orca-so/orca-py.git@main"',
        
        # Método 3: Clonar e instalar
        '''
        git clone https://github.com/orca-so/orca-py.git orca_temp &&
        cd orca_temp &&
        pip install -e . &&
        cd .. &&
        rmdir /s /q orca_temp
        ''',
        
        # Método 4: Usar wheel si disponible
        'pip install "orca-py @ https://github.com/orca-so/orca-py/releases/download/v0.6.0/orca_py-0.6.0-py3-none-any.whl"',
    ]
    
    success = False
    for i, method in enumerate(methods, 1):
        print(f"\n   🔄 Intentando método {i}...")
        if run_command(method, f"Método {i}"):
            if check_orca_installed():
                success = True
                break
    
    # 4. Verificación final
    print("\n" + "=" * 60)
    print("🔍 VERIFICACIÓN FINAL")
    print("=" * 60)
    
    if check_orca_installed():
        print("🎉 ¡ORCA-PY INSTALADO CORRECTAMENTE!")
        
        # Probar importaciones específicas
        try:
            from orca.whirlpool.accounts import Whirlpool
            print("✅ Whirlpool accounts importado")
            
            from orca.whirlpool.constants import ORCA_WHIRLPOOL_PROGRAM_ID
            print(f"✅ Whirlpool program ID: {ORCA_WHIRLPOOL_PROGRAM_ID}")
            
            from orca.pool.accounts import Pool
            print("✅ Pool accounts importado")
            
        except Exception as e:
            print(f"⚠️  Algunas importaciones fallaron: {e}")
            
    else:
        print("❌ ORCA-PY NO SE PUDO INSTALAR")
        print("\n💡 SOLUCIONES ALTERNATIVAS:")
        print("1. Usar una versión más antigua:")
        print("   pip install orca-py==0.5.0")
        print("\n2. Clonar manualmente y corregir problemas:")
        print("   git clone https://github.com/orca-so/orca-py.git")
        print("   cd orca-py")
        print("   # Editar setup.py si es necesario")
        print("   pip install -e .")
        print("\n3. Usar un fork actualizado:")
        print("   pip install git+https://github.com/your-fork/orca-py.git")
    
    print("=" * 60)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())