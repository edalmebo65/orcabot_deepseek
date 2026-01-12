#!/usr/bin/env python3
"""
Script para ejecutar el bot paso a paso - Actualizado
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
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            print("✅ Completado")
            return True
        else:
            print(f"❌ Error (code: {result.returncode}):")
            if result.stdout:
                print(f"stdout: {result.stdout[:300]}")
            if result.stderr:
                print(f"stderr: {result.stderr[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ Excepción: {e}")
        return False

def main():
    print("EJECUCION DEL BOT ORCA - PASO A PASO")
    print("=" * 60)
    
    steps = [
        (1, "python install_deps_no_conflict.py", "Instalar dependencias sin conflictos"),
        (2, "python scripts/build_rust_fixed.py", "Construir módulo Rust"),
        (3, "python check_environment.py", "Verificar entorno"),
        (4, "python main_integrated.py", "Ejecutar bot integrado"),
    ]
    
    all_success = True
    
    for step, command, description in steps:
        success = run_step(step, command, description)
        if not success:
            all_success = False
            print(f"\n¿Continuar con el paso {step+1}? (s/n): ", end="")
            try:
                response = input().strip().lower()
                if response not in ['s', 'si', 'sí', 'y', 'yes']:
                    print(f"\nSaltando paso {step+1}...")
                    # Para el paso 4, necesitamos continuar de todos modos
                    if step == 3:  # Si es el último paso
                        print("El bot no se ejecutará")
                    continue
            except:
                continue
    
    print("\n" + "=" * 60)
    if all_success:
        print("🎉 ¡PROCESO COMPLETADO EXITOSAMENTE!")
        print("\nEl bot debería estar funcionando.")
        print("Si hay errores, ejecutar manualmente: python main_integrated.py")
    else:
        print("⚠️  ALGUNOS PASOS TUVIERON ERRORES")
        print("\nPara ejecutar manualmente:")
        print("1. python check_environment.py")
        print("2. python main_integrated.py")
    
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())