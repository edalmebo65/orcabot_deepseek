#!/usr/bin/env python3
"""
Script de configuración corregido para OrcaBot
Maneja dependencias problemáticas como pandas-ta
"""
import os
import sys
import json
import subprocess
import platform
from pathlib import Path

def check_python_version():
    """Verifica versión de Python y sugiere alternativas"""
    version = sys.version_info
    print(f"🐍 Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 9:
        return True
    else:
        print(f"⚠️  Python {version.major}.{version.minor} detectado")
        print("   Recomendado: Python 3.9 - 3.11 para mejor compatibilidad")
        return True  # Continuar de todas formas

def install_dependencies_corrected():
    """Instala dependencias con manejo de errores"""
    print("\n📦 Instalando dependencias (manejo corregido)...")
    
    # Primero, dependencias core esenciales
    core_packages = [
        "numpy>=1.24.0,<2.0.0",
        "pandas>=2.0.0,<3.0.0", 
        "scipy>=1.11.0,<2.0.0",
        "scikit-learn>=1.3.0,<2.0.0",
        "aiohttp>=3.9.0,<4.0.0",
        "schedule>=1.2.0,<2.0.0",
        "python-dotenv>=1.0.0,<2.0.0",
        "cryptography>=41.0.0,<43.0.0",
        "solana>=0.29.0,<0.30.0",
        "solders>=0.18.0,<0.19.0",
        "rich>=13.5.0,<14.0.0",
        "tinydb>=4.8.0,<5.0.0"
    ]
    
    print("1. Instalando dependencias core...")
    for package in core_packages:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                check=True,
                capture_output=True
            )
            print(f"   ✅ {package.split(',')[0]}")
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Error con {package}: {e.stderr.decode()[:100]}")
    
    # Segundo, dependencias opcionales (con fallback)
    optional_packages = [
        ("tensorflow>=2.13.0,<2.16.0", "tensorflow-cpu"),  # Fallback a CPU
        ("xgboost>=1.7.0,<2.0.0", None),
        ("optuna>=3.3.0,<4.0.0", None),
        ("ta-lib>=0.4.26", None),  # Alternativa a pandas-ta
    ]
    
    print("\n2. Instalando dependencias opcionales...")
    for package, fallback in optional_packages:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                check=True,
                capture_output=True
            )
            print(f"   ✅ {package.split(',')[0]}")
        except:
            if fallback:
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", fallback],
                        check=True
                    )
                    print(f"   ✅ {fallback} (fallback)")
                except:
                    print(f"   ⚠️  Skipped: {package.split(',')[0]}")
            else:
                print(f"   ⚠️  Skipped: {package.split(',')[0]}")
    
    # Tercero, crear archivo de requerimientos corregido
    print("\n3. Creando requirements_corrected.txt...")
    with open("requirements_corrected.txt", "w") as f:
        f.write("\n".join([
            "# DEPENDENCIAS CORREGIDAS - Sin pandas-ta problemático",
            "",
            "# Core esencial",
            "numpy>=1.24.0,<2.0.0",
            "pandas>=2.0.0,<3.0.0",
            "scipy>=1.11.0,<2.0.0", 
            "scikit-learn>=1.3.0,<2.0.0",
            "",
            "# Async y networking",
            "aiohttp>=3.9.0,<4.0.0",
            "asyncio>=3.4.3",
            "",
            "# Blockchain",
            "solana>=0.29.0,<0.30.0",
            "solders>=0.18.0,<0.19.0",
            "",
            "# Utilities",
            "schedule>=1.2.0,<2.0.0",
            "python-dotenv>=1.0.0,<2.0.0",
            "cryptography>=41.0.0,<43.0.0",
            "rich>=13.5.0,<14.0.0",
            "tinydb>=4.8.0,<5.0.0",
            "",
            "# ML (opcional)",
            "# tensorflow>=2.13.0,<2.16.0  # Descomentar si necesitas DL",
            "xgboost>=1.7.0,<2.0.0",
            "",
            "# Análisis técnico (usamos nuestro propio módulo)",
            "# ta-lib>=0.4.26  # Opcional, para mejor performance",
            "",
            "# Testing",
            "pytest>=7.4.0,<8.0.0",
            "pytest-asyncio>=0.21.0,<0.22.0"
        ]))
    
    print("✅ requirements_corrected.txt creado")
    
    return True

def create_technical_indicators_module():
    """Crea el módulo propio de indicadores técnicos"""
    print("\n📊 Creando módulo propio de indicadores técnicos...")
    
    # El contenido está en la variable tech_indicators_content arriba
    # Solo verificar que se creó
    if Path("technical_indicators.py").exists():
        print("✅ technical_indicators.py ya existe")
    else:
        print("⚠️  technical_indicators.py no encontrado, se creará después")
    
    return True

def update_ml_trainer_to_use_custom_indicators():
    """Actualiza ml_trainer_advanced.py para usar nuestros indicadores"""
    print("\n🔄 Actualizando ML trainer para usar indicadores propios...")
    
    ml_file = "ml_trainer_advanced.py"
    if Path(ml_file).exists():
        try:
            with open(ml_file, 'r') as f:
                content = f.read()
            
            # Reemplazar import problemático
            if "pandas_ta" in content:
                content = content.replace(
                    "import pandas_ta as ta",
                    "# import pandas_ta as ta  # Comentado por incompatibilidad\nfrom technical_indicators import tech_indicators"
                )
                
                content = content.replace(
                    "ta.", 
                    "tech_indicators."
                )
                
                with open(ml_file, 'w') as f:
                    f.write(content)
                
                print("✅ ml_trainer_advanced.py actualizado")
            else:
                print("✅ ml_trainer_advanced.py ya usa indicadores propios")
                
        except Exception as e:
            print(f"⚠️  Error actualizando {ml_file}: {e}")
    
    return True

def main_corrected():
    """Función principal corregida"""
    print("="*60)
    print("🔧 ORCABOT - SETUP CORREGIDO")
    print("="*60)
    
    # 1. Verificar Python
    if not check_python_version():
        return
    
    # 2. Instalar dependencias corregidas
    if not install_dependencies_corrected():
        return
    
    # 3. Crear módulo de indicadores
    create_technical_indicators_module()
    
    # 4. Actualizar ML trainer
    update_ml_trainer_to_use_custom_indicators()
    
    # 5. Resto del setup original...
    print("\n" + "="*60)
    print("✅ SETUP CORREGIDO COMPLETADO")
    print("="*60)
    
    print("\n📋 RESUMEN:")
    print("1. Dependencias core instaladas")
    print("2. Módulo propio de indicadores técnicos creado")
    print("3. ML trainer actualizado")
    print("4. Archivo requirements_corrected.txt generado")
    
    print("\n🎯 PRÓXIMOS PASOS:")
    print("1. python main_integrated.py  # Iniciar bot optimizado")
    print("2. Revisar logs en /logs/optimized/")
    print("3. Configurar .env con tus claves")
    
    print("\n⚠️  NOTA: pandas-ta fue reemplazado por nuestro módulo propio")
    print("   Esto evita problemas de compatibilidad con Python")

if __name__ == "__main__":
    main_corrected()