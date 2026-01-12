#!/usr/bin/env python3
"""
Script para ejecutar el bot paso a paso
"""
import subprocess
import sys
import os
from pathlib import Path

def run_step(step, command, description):
    print(f"\n{'='*60}")
    print(f"PASO {step}: {description}")
    print(f"{'='*60}")
    print(f"Ejecutando: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Completado")
            if result.stdout:
                print(f"Output: {result.stdout[:200]}")
            return True
        else:
            print(f"❌ Error:")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return False

def main():
    print("🚀 EJECUCIÓN DEL BOT ORCA - PASO A PASO")
    print("=" * 60)
    
    steps = [
        (1, "python scripts/build_rust_simple.py", "Construir módulo Rust"),
        (2, "pip install -r python/requirements.txt", "Instalar dependencias Python"),
        (3, "python -c \"from rust_bridge import orca_bridge; print(f'✅ Bridge: {orca_bridge.mode}')\"", "Probar bridge"),
        (4, "python python/main.py", "Ejecutar bot principal"),
    ]
    
    all_success = True
    
    for step, command, description in steps:
        success = run_step(step, command, description)
        if not success:
            all_success = False
            print("\n⚠️  ¿Continuar con el siguiente paso? (s/n): ", end="")
            response = input().strip().lower()
            if response not in ['s', 'si', 'sí', 'y', 'yes']:
                break
    
    print("\n" + "=" * 60)
    if all_success:
        print("🎉 ¡PROCESO COMPLETADO EXITOSAMENTE!")
    else:
        print("⚠️  ALGUNOS PASOS TUVIERON ERRORES")
    print("=" * 60)
    
    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main())