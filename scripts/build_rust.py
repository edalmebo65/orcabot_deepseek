#!/usr/bin/env python3
"""
Script para construir el módulo Rust
"""
import subprocess
import sys
import os
from pathlib import Path

def build_rust_module():
    """Construir módulo Rust usando maturin"""
    print("🔨 Construyendo módulo Rust...")
    
    # Verificar si maturin está instalado
    try:
        subprocess.run(["maturin", "--version"], check=True, capture_output=True)
    except:
        print("Instalando maturin...")
        subprocess.run([sys.executable, "-m", "pip", "install", "maturin"], check=True)
    
    rust_dir = Path("rust")
    if not rust_dir.exists():
        print("❌ No se encuentra el directorio rust/")
        return False
    
    # Cambiar al directorio rust
    original_dir = os.getcwd()
    os.chdir(rust_dir)
    
    try:
        # Construir en modo desarrollo
        print("Construyendo con maturin develop...")
        result = subprocess.run(
            ["maturin", "develop", "--release"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Módulo Rust construido exitosamente")
            
            # Verificar que se puede importar
            print("Verificando importación...")
            test_code = '''
try:
    import orca_rust_bridge
    print(f"✅ Módulo Rust importado: versión {orca_rust_bridge.version()}")
    
    # Probar funcionalidad básica
    client = orca_rust_bridge.PyOrcaClient("https://api.mainnet-beta.solana.com")
    print(f"✅ Cliente creado, program ID: {client.whirlpool_program_id}")
    
    return True
except Exception as e:
    print(f"❌ Error: {e}")
    return False
'''
            
            import_ok = eval(test_code)
            return import_ok
            
        else:
            print(f"❌ Error construyendo módulo: {result.stderr}")
            
            # Intentar con cargo-maturin
            print("Intentando con cargo build...")
            result = subprocess.run(
                ["cargo", "build", "--release"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Cargo build exitoso, intentando enlazar manualmente...")
                
                # Copiar la librería compilada
                lib_path = Path("target") / "release"
                for file in lib_path.glob("*.dll"):
                    dest = Path("..") / "python" / file.name
                    import shutil
                    shutil.copy(file, dest)
                    print(f"📄 Copiada: {file.name} -> python/")
                
                return True
            else:
                print(f"❌ Cargo build también falló: {result.stderr}")
                return False
                
    finally:
        os.chdir(original_dir)

def main():
    """Función principal"""
    print("=" * 60)
    print("🦀 CONSTRUCTOR MÓDULO RUST PARA ORCA BOT")
    print("=" * 60)
    
    success = build_rust_module()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ¡MÓDULO RUST CONSTRUIDO EXITOSAMENTE!")
        print("\n📋 Pasos siguientes:")
        print("1. Ejecutar el bot: python python/main.py")
        print("2. Para desarrollo: cd rust && cargo check")
        print("3. Para reconstruir: python scripts/build_rust.py")
    else:
        print("❌ FALLÓ LA CONSTRUCCIÓN DEL MÓDULO RUST")
        print("\n💡 Soluciones:")
        print("1. Verificar que Rust esté instalado: rustc --version")
        print("2. Instalar maturin: pip install maturin")
        print("3. Verificar dependencias en Cargo.toml")
        print("4. El bot funcionará en modo Python fallback")
    
    print("=" * 60)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())