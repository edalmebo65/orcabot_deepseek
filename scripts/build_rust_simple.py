#!/usr/bin/env python3
"""
Script simplificado para construir el módulo Rust
"""
import subprocess
import sys
import os
from pathlib import Path

def build_rust_module():
    """Construir módulo Rust usando cargo directamente"""
    print("🔨 Construyendo módulo Rust con cargo...")
    
    rust_dir = Path("rust")
    if not rust_dir.exists():
        print("❌ No se encuentra el directorio rust/")
        return False
    
    original_dir = os.getcwd()
    os.chdir(rust_dir)
    
    try:
        # Limpiar build anterior
        print("Limpiando build anterior...")
        subprocess.run(["cargo", "clean"], capture_output=True)
        
        # Construir en modo release
        print("Construyendo con cargo build --release...")
        result = subprocess.run(
            ["cargo", "build", "--release"],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            print("✅ Cargo build exitoso")
            
            # Encontrar la librería compilada
            target_dir = Path("target") / "release"
            
            # Para Windows
            dll_file = target_dir / "orca_rust_bridge.dll"
            if dll_file.exists():
                # Copiar al directorio python
                dest_dir = Path("..") / "python"
                dest_dir.mkdir(exist_ok=True)
                
                import shutil
                shutil.copy(dll_file, dest_dir / "orca_rust_bridge.pyd")
                print(f"📄 Copiada: {dll_file.name} -> python/orca_rust_bridge.pyd")
                
                # También copiar como .dll para import
                shutil.copy(dll_file, dest_dir / "orca_rust_bridge.dll")
                
                return True
            
            print("❌ No se encontró el archivo .dll compilado")
            return False
        else:
            print(f"❌ Error en cargo build:")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return False
        
    finally:
        os.chdir(original_dir)

def test_import():
    """Probar importación del módulo"""
    print("\n🔍 Probando importación del módulo...")
    
    try:
        # Añadir directorio python al path
        import sys
        python_dir = Path("python")
        if python_dir.exists():
            sys.path.insert(0, str(python_dir))
        
        import orca_rust_bridge
        print("✅ Módulo Rust importado correctamente")
        
        # Probar funcionalidad básica
        client = orca_rust_bridge.PyOrcaClient("https://api.mainnet-beta.solana.com")
        print(f"✅ Cliente creado")
        print(f"   Program ID: {orca_rust_bridge.WHIRLPOOL_PROGRAM_ID}")
        print(f"   SOL Mint: {orca_rust_bridge.SOL_MINT}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importando módulo: {e}")
        return False
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return False

def main():
    print("=" * 60)
    print("🦀 CONSTRUCTOR SIMPLIFICADO MÓDULO RUST")
    print("=" * 60)
    
    # Construir módulo
    build_success = build_rust_module()
    
    if build_success:
        # Probar importación
        import_success = test_import()
        
        if import_success:
            print("\n" + "=" * 60)
            print("🎉 ¡MÓDULO RUST CONSTRUIDO E IMPORTADO EXITOSAMENTE!")
            print("=" * 60)
            return 0
        else:
            print("\n⚠️  Módulo construido pero no se pudo importar")
    else:
        print("\n❌ FALLÓ LA CONSTRUCCIÓN DEL MÓDULO")
    
    print("\n💡 SOLUCIÓN ALTERNATIVA:")
    print("1. Usar el bot en modo Python puro (sin Rust)")
    print("2. Ejecutar: python python/main_pure.py")
    
    return 1

if __name__ == "__main__":
    sys.exit(main())