#!/usr/bin/env python3
"""
Script de instalación para el sistema Python-Rust
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, desc, check=True):
    """Ejecutar comando y mostrar resultado"""
    print(f"\n🔧 {desc}...")
    print(f"   $ {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Completado")
            if result.stdout.strip():
                print(f"   Output: {result.stdout[:200]}")
            return True
        else:
            print(f"   ❌ Error: {result.stderr[:200]}")
            if check:
                raise RuntimeError(f"Comando falló: {cmd}")
            return False
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
        if check:
            raise
        return False

def install_rust():
    """Instalar Rust en Windows"""
    print("\n🦀 INSTALANDO RUST...")
    
    # Verificar si Rust ya está instalado
    if run_command("rustc --version", "Verificando Rust", check=False):
        print("✅ Rust ya está instalado")
        return True
    
    # Instalar Rust usando rustup
    print("\n📥 Instalando Rust...")
    rustup_url = "https://win.rustup.rs/x86_64"
    
    # Descargar e instalar rustup
    run_command(
        f"curl -sSf {rustup_url} -o rustup-init.exe && "
        "rustup-init.exe -y --default-toolchain stable",
        "Instalando rustup"
    )
    
    # Añadir Rust al PATH
    run_command(
        'setx PATH "%USERPROFILE%\\.cargo\\bin;%PATH%"',
        "Añadiendo Rust al PATH"
    )
    
    # Verificar instalación
    return run_command("rustc --version", "Verificando instalación de Rust")

def build_rust_module():
    """Compilar módulo Rust"""
    print("\n🔨 COMPILANDO MÓDULO RUST...")
    
    rust_dir = Path("rust")
    if not rust_dir.exists():
        print("❌ No se encuentra el directorio rust/")
        return False
    
    # Construir el módulo
    os.chdir(rust_dir)
    
    # Instalar dependencias de Python para PyO3
    run_command(
        "pip install maturin",
        "Instalando maturin (build tool para Rust-Python)"
    )
    
    # Construir con maturin
    success = run_command(
        "maturin develop --release",
        "Construyendo módulo Rust con maturin",
        check=False
    )
    
    os.chdir("..")
    return success

def install_python_deps():
    """Instalar dependencias Python"""
    print("\n🐍 INSTALANDO DEPENDENCIAS PYTHON...")
    
    deps = [
        "solana==0.30.1",
        "solders==0.18.0",
        "anchorpy==0.16.0",
        "aiohttp==3.9.1",
        "aiogram==2.25.1",
        "pydantic==2.4.2",
        "ccxt==4.1.36",
        "websockets==10.4",
        "python-dotenv==1.0.0",
        "rich==13.5.3",
        "loguru==0.7.2",
    ]
    
    for dep in deps:
        run_command(f"pip install {dep}", f"Instalando {dep}")

def create_project_structure():
    """Crear estructura del proyecto"""
    print("\n📁 CREANDO ESTRUCTURA DEL PROYECTO...")
    
    directories = [
        "python",
        "rust/src",
        "scripts",
        "config",
        "data",
        "logs",
        "tests",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}/")
    
    # Crear archivos esenciales
    files_to_create = {
        "python/__init__.py": "# Python package\n",
        "rust/README.md": "# Módulo Rust para Orca\n",
        ".env.example": "RPC_URL=https://api.mainnet-beta.solana.com\nPRIVATE_KEY=\n",
        "README.md": "# Orca Trading Bot - Python + Rust\n",
    }
    
    for file_path, content in files_to_create.items():
        Path(file_path).write_text(content, encoding="utf-8")
        print(f"   📄 {file_path}")

def main():
    """Función principal"""
    print("=" * 70)
    print("🚀 INSTALADOR ORCA BOT - PYTHON + RUST")
    print("=" * 70)
    
    print(f"Sistema: {sys.platform}")
    print(f"Python: {sys.version}")
    
    try:
        # 1. Crear estructura
        create_project_structure()
        
        # 2. Instalar Rust si es necesario
        if sys.platform == "win32":
            install_rust()
        
        # 3. Instalar dependencias Python
        install_python_deps()
        
        # 4. Construir módulo Rust
        build_success = build_rust_module()
        
        if not build_success:
            print("\n⚠️  El módulo Rust no se pudo construir")
            print("   El bot funcionará en modo fallback (solo Python)")
        
        # 5. Verificar instalación
        print("\n🔍 VERIFICANDO INSTALACIÓN...")
        
        # Verificar Python
        python_check = '''
import sys
try:
    import solana
    import solders
    import aiohttp
    import pydantic
    print("✅ Python dependencies: OK")
except ImportError as e:
    print(f"❌ Python: {e}")
'''
        exec(python_check)
        
        # Verificar Rust
        if build_success:
            rust_check = '''
try:
    import orca_rust_bridge
    print("✅ Rust module: OK")
    print(f"   Program ID: {orca_rust_bridge.ORCA_WHIRLPOOL_PROGRAM_ID}")
except ImportError:
    print("❌ Rust module: Not available")
'''
            exec(rust_check)
        
        print("\n" + "=" * 70)
        print("🎉 ¡INSTALACIÓN COMPLETADA!")
        print("=" * 70)
        print("\n📋 PASOS SIGUIENTES:")
        print("1. Configurar .env con tu RPC URL y private key")
        print("2. Ejecutar: python python/main.py")
        print("3. Para desarrollo Rust: cd rust && cargo build")
        print("\n💡 NOTA: Si Rust falla, el bot funcionará en modo Python")
        
    except Exception as e:
        print(f"\n❌ Error durante la instalación: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())