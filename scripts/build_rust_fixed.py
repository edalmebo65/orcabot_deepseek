#!/usr/bin/env python3
"""
Script simplificado para construir el módulo Rust - Corregido para Windows
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path

def build_rust_module():
    """Construir módulo Rust usando cargo directamente"""
    print("Construyendo modulo Rust con cargo...")
    
    rust_dir = Path("rust")
    if not rust_dir.exists():
        print("❌ No se encuentra el directorio rust/")
        return False
    
    original_dir = os.getcwd()
    os.chdir(rust_dir)
    
    try:
        # 1. Actualizar Cargo.toml si es necesario
        print("1. Verificando Cargo.toml...")
        cargo_file = Path("Cargo.toml")
        if cargo_file.exists():
            content = cargo_file.read_text(encoding='utf-8')
            # Corregir pyo3 si es 0.21
            if 'pyo3 = "0.21"' in content:
                content = content.replace('pyo3 = "0.21"', 'pyo3 = "0.20"')
                cargo_file.write_text(content, encoding='utf-8')
                print("   ✅ Cargo.toml actualizado")
        
        # 2. Limpiar build anterior
        print("2. Limpiando build anterior...")
        subprocess.run(["cargo", "clean"], capture_output=True)
        
        # 3. Construir en modo release
        print("3. Construyendo con cargo build --release...")
        result = subprocess.run(
            ["cargo", "build", "--release"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print("✅ Cargo build exitoso")
            
            # Encontrar la librería compilada
            target_dir = Path("target") / "release"
            
            # Para Windows
            dll_files = list(target_dir.glob("*.dll"))
            if dll_files:
                dll_file = dll_files[0]
                
                # Copiar al directorio principal
                dest_dir = Path("..")
                dest_dir.mkdir(exist_ok=True)
                
                # Copiar como .pyd para Python
                pyd_dest = dest_dir / "orca_rust_bridge.pyd"
                shutil.copy(dll_file, pyd_dest)
                print(f"✅ Copiada: {dll_file.name} -> orca_rust_bridge.pyd")
                
                return True
            else:
                print("❌ No se encontraron archivos .dll")
                print("   Buscando en:", target_dir.absolute())
                return False
        else:
            print("❌ Error en cargo build:")
            if result.stdout:
                print("stdout:", result.stdout[:500])
            if result.stderr:
                print("stderr:", result.stderr[:500])
            return False
            
    except Exception as e:
        print(f"❌ Excepción: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        os.chdir(original_dir)

def test_import():
    """Probar importación del módulo"""
    print("\nProbando importación del módulo...")
    
    try:
        # Añadir directorio actual al path
        import sys
        sys.path.insert(0, ".")
        
        # Primero probar módulo Rust
        try:
            import orca_rust_bridge
            print("✅ Modulo Rust importado correctamente")
            
            # Probar funcionalidad básica
            client = orca_rust_bridge.PyOrcaClient("https://api.mainnet-beta.solana.com")
            print(f"✅ Cliente creado")
            print(f"   Program ID: {orca_rust_bridge.WHIRLPOOL_PROGRAM_ID}")
            
            return "RUST"
            
        except ImportError as e:
            print(f"⚠️  No se pudo importar módulo Rust: {e}")
            
            # Probar fallback Python
            from rust_bridge_fallback import OrcaBridgeFallback
            bridge = OrcaBridgeFallback()
            print(f"✅ Usando bridge Python fallback")
            
            return "PYTHON_FALLBACK"
            
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return "ERROR"

def main():
    print("=" * 60)
    print("CONSTRUCTOR MODULO RUST - CORREGIDO")
    print("=" * 60)
    
    # Construir módulo
    build_success = build_rust_module()
    
    # Probar importación
    mode = test_import()
    
    print("\n" + "=" * 60)
    print(f"RESULTADO: Modo {mode}")
    
    if mode == "RUST":
        print("🎉 ¡MODULO RUST FUNCIONAL!")
        print("\nPuedes ejecutar: python main_integrated.py")
    elif mode == "PYTHON_FALLBACK":
        print("⚠️  Usando modo Python fallback")
        print("   El bot funcionará sin optimizaciones Rust")
        print("\nPuedes ejecutar: python main_integrated.py")
    else:
        print("❌ Problemas de importación")
        print("\n💡 Soluciones:")
        print("1. Instalar Rust: https://rustup.rs/")
        print("2. Verificar Cargo.toml")
        print("3. Ejecutar en modo Python puro: python main_pure_python.py")
    
    print("=" * 60)
    return 0 if mode in ["RUST", "PYTHON_FALLBACK"] else 1

if __name__ == "__main__":
    sys.exit(main())