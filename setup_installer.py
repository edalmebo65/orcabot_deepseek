# setup_installer.py
"""
Script de instalación y configuración automática
Configura todo el entorno del bot desde cero
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import json
import getpass

class BotInstaller:
    """Instalador automatizado del bot de trading"""
    
    def __init__(self):
        self.base_dir = Path.cwd()
        self.config_template = """# Configuración del Bot de Trading
# Generado automáticamente por setup_installer.py

# Solana Configuration
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_WS_URL=wss://api.mainnet-beta.solana.com
COMMITMENT=confirmed

# Wallet Configuration
PRIVATE_KEY={private_key}
PUBLIC_KEY={public_key}
WALLET_PROVIDER=phantom
MIN_USDC_BALANCE=10
MIN_SOL_FEES=0.05
MAX_SLIPPAGE=0.01

# Trading Configuration
MAX_CONCURRENT_TRADES=5
POSITION_SIZE_PERCENT=0.10
MAX_PORTFOLIO_EXPOSURE=0.15
TRAILING_STOP_ACTIVATION=0.002
TRAILING_STOP_DISTANCE=0.01
STOP_LOSS_PERCENT=0.02
TAKE_PROFIT_PERCENT=0.05
ML_CONFIDENCE_THRESHOLD=0.65

# Telegram Configuration
TELEGRAM_BOT_TOKEN={telegram_token}
TELEGRAM_CHAT_ID={telegram_chat_id}

# Security Configuration
ENCRYPTION_KEY={encryption_key}

# Nota: Para desarrollo, puedes usar variables de entorno
# export PRIVATE_KEY="tu_clave_privada"
"""
        
        self.requirements = """# Dependencias del Bot de Trading
# Versiones fijas para evitar conflictos

# Core dependencies
python-dotenv==1.0.0
aiohttp==3.9.1
asyncio==3.4.3
pandas==2.1.4
numpy==1.24.4

# Machine Learning
torch==2.1.0
scikit-learn==1.3.2
joblib==1.3.2

# Cryptography
cryptography==41.0.7
base58==2.1.1

# Solana
solana==0.30.4
anchorpy==0.19.0

# Trading & Finance
ccxt==4.1.59
ta==0.10.2
pyti==0.2.2

# Utils
colorama==0.4.6
tqdm==4.66.1
tabulate==0.9.0

# Monitoring
prometheus-client==0.19.0
psutil==5.9.6
"""
    
    def check_prerequisites(self) -> bool:
        """Verificar prerrequisitos del sistema"""
        print("🔍 Verificando prerrequisitos...")
        
        checks = {
            "Python 3.9+": self._check_python_version(),
            "pip": self._check_pip(),
            "git": self._check_git(),
            "Directorio de trabajo": self._check_working_directory(),
        }
        
        all_ok = True
        for check, (ok, message) in checks.items():
            if ok:
                print(f"  ✅ {check}: {message}")
            else:
                print(f"  ❌ {check}: {message}")
                all_ok = False
        
        return all_ok
    
    def _check_python_version(self) -> tuple:
        """Verificar versión de Python"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 9:
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        return False, f"Python {version.major}.{version.minor}.{version.micro} - Se requiere 3.9+"
    
    def _check_pip(self) -> tuple:
        """Verificar pip"""
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return True, "pip está instalado"
        except:
            pass
        return False, "pip no encontrado"
    
    def _check_git(self) -> tuple:
        """Verificar git"""
        try:
            result = subprocess.run(["git", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return True, "git está instalado"
        except:
            pass
        return False, "git no encontrado (opcional)"
    
    def _check_working_directory(self) -> tuple:
        """Verificar directorio de trabajo"""
        required_space = 1024 * 1024 * 1024  # 1GB
        try:
            stat = shutil.disk_usage(self.base_dir)
            if stat.free > required_space:
                return True, f"{stat.free // (1024**3)}GB disponibles"
            else:
                return False, f"Espacio insuficiente: {stat.free // (1024**3)}GB"
        except:
            return False, "No se pudo verificar espacio en disco"
    
    def create_directory_structure(self):
        """Crear estructura de directorios"""
        print("📁 Creando estructura de directorios...")
        
        directories = [
            "models",
            "metadata",
            "logs/audit",
            "logs/trading",
            "backup",
            "data/historical",
            "data/realtime",
            "config_backups"
        ]
        
        for directory in directories:
            dir_path = self.base_dir / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  📂 Creado: {directory}")
    
    def install_dependencies(self):
        """Instalar dependencias de Python"""
        print("📦 Instalando dependencias...")
        
        # Escribir requirements.txt
        requirements_path = self.base_dir / "requirements_fixed_v2.txt"
        with open(requirements_path, 'w') as f:
            f.write(self.requirements)
        
        # Instalar con pip
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
                         check=True, capture_output=True)
            
            print("✅ Dependencias instaladas correctamente")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando dependencias: {e}")
            return False
    
    def setup_configuration(self):
        """Configurar archivos de configuración"""
        print("⚙️ Configurando archivos de configuración...")
        
        # Solicitar información del usuario
        print("\n📝 Por favor ingresa la siguiente información:")
        print("=" * 50)
        
        private_key = getpass.getpass("🔑 Clave privada de Solana (se encriptará): ").strip()
        public_key = input("🏦 Dirección pública de la wallet: ").strip()
        
        use_telegram = input("\n¿Deseas configurar notificaciones de Telegram? (s/n): ").lower() == 's'
        
        telegram_token = ""
        telegram_chat_id = ""
        
        if use_telegram:
            telegram_token = input("🤖 Token del bot de Telegram: ").strip()
            telegram_chat_id = input("💬 ID del chat de Telegram: ").strip()
        
        # Generar clave de encriptación
        import secrets
        encryption_key = secrets.token_urlsafe(32)
        
        # Crear archivo .env
        env_content = self.config_template.format(
            private_key=private_key,
            public_key=public_key,
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id,
            encryption_key=encryption_key
        )
        
        env_path = self.base_dir / ".env"
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        # Crear .env.example (sin datos sensibles)
        example_content = """# Template de configuración
# Copia este archivo a .env y completa los valores

SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
PRIVATE_KEY=tu_clave_privada_aqui
PUBLIC_KEY=tu_direccion_publica_aqui
TELEGRAM_BOT_TOKEN=tu_token_de_bot
TELEGRAM_CHAT_ID=tu_chat_id
ENCRYPTION_KEY=clave_de_encriptacion_generada
"""
        
        example_path = self.base_dir / ".env.example"
        with open(example_path, 'w') as f:
            f.write(example_content)
        
        # Crear config.py desde template
        self._create_config_py()
        
        # Establecer permisos seguros
        os.chmod(env_path, 0o600)
        
        print(f"\n✅ Archivos de configuración creados:")
        print(f"   📄 .env (configuración principal)")
        print(f"   📄 .env.example (template)")
        print(f"   📄 config.py (configuración Python)")
        print(f"\n⚠️  IMPORTANTE: La clave de encriptación generada es:")
        print(f"   {encryption_key}")
        print(f"\n💡 Guárdala en un lugar seguro. Sin ella, no podrás desencriptar tus claves.")
    
    def _create_config_py(self):
        """Crear archivo config.py"""
        config_py_content = '''"""
Configuración centralizada del bot de trading
ESTE ARCHIVO ES GENERADO AUTOMÁTICAMENTE
NO EDITAR MANUALMENTE - Usar variables de entorno en .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de Solana
SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
SOLANA_WS_URL = os.getenv('SOLANA_WS_URL', 'wss://api.mainnet-beta.solana.com')
COMMITMENT = os.getenv('COMMITMENT', 'confirmed')

# Configuración de Wallet
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
PUBLIC_KEY = os.getenv('PUBLIC_KEY')
WALLET_PROVIDER = os.getenv('WALLET_PROVIDER', 'phantom')

# Trading Configuration
MAX_CONCURRENT_TRADES = int(os.getenv('MAX_CONCURRENT_TRADES', '5'))
POSITION_SIZE_PERCENT = float(os.getenv('POSITION_SIZE_PERCENT', '0.10'))

print("✅ Configuración cargada desde variables de entorno")
'''
        
        config_path = self.base_dir / "config.py"
        with open(config_path, 'w') as f:
            f.write(config_py_content)
    
    def setup_backup_system(self):
        """Configurar sistema de backup"""
        print("💾 Configurando sistema de backup...")
        
        # Crear script de backup
        backup_script = """#!/usr/bin/env python3
"""
        
        backup_path = self.base_dir / "backup" / "auto_backup.py"
        with open(backup_path, 'w') as f:
            f.write(backup_script)
        
        # Hacerlo ejecutable
        os.chmod(backup_path, 0o755)
        
        # Crear crontab para backups automáticos
        cron_content = f"""# Backups automáticos del bot de trading
0 */6 * * * cd {self.base_dir} && python backup/auto_backup.py >> logs/backup.log 2>&1
0 0 * * * cd {self.base_dir} && find logs/ -name "*.log" -mtime +7 -delete
"""
        
        cron_path = self.base_dir / "backup" / "crontab.txt"
        with open(cron_path, 'w') as f:
            f.write(cron_content)
        
        print("✅ Sistema de backup configurado")
        print(f"📄 Instrucciones para crontab en: {cron_path}")
    
    def run_initial_tests(self):
        """Ejecutar pruebas iniciales"""
        print("🧪 Ejecutando pruebas iniciales...")
        
        tests = [
            ("Importar config", self._test_config_import),
            ("Verificar dependencias", self._test_dependencies),
            ("Verificar estructura", self._test_directory_structure),
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            try:
                result, message = test_func()
                if result:
                    print(f"  ✅ {test_name}: {message}")
                else:
                    print(f"  ❌ {test_name}: {message}")
                    all_passed = False
            except Exception as e:
                print(f"  ❌ {test_name}: Error - {e}")
                all_passed = False
        
        return all_passed
    
    def _test_config_import(self) -> tuple:
        """Probar importación de configuración"""
        try:
            # Intentar importar config.py
            import sys
            sys.path.insert(0, str(self.base_dir))
            
            import config
            return True, "Configuración cargada correctamente"
        except Exception as e:
            return False, f"Error: {e}"
    
    def _test_dependencies(self) -> tuple:
        """Probar dependencias clave"""
        try:
            import pandas as pd
            import numpy as np
            import aiohttp
            import torch
            
            return True, "Dependencias principales OK"
        except ImportError as e:
            return False, f"Falta dependencia: {e}"
    
    def _test_directory_structure(self) -> tuple:
        """Verificar estructura de directorios"""
        required_dirs = ["models", "logs", "backup", "data"]
        
        for dir_name in required_dirs:
            dir_path = self.base_dir / dir_name
            if not dir_path.exists():
                return False, f"Falta directorio: {dir_name}"
        
        return True, "Estructura completa"
    
    def create_run_script(self):
        """Crear script de ejecución principal"""
        print("🚀 Creando script de ejecución...")
        
        run_script = """#!/usr/bin/env python3
"""
        
        run_path = self.base_dir / "run_bot.py"
        with open(run_path, 'w') as f:
            f.write(run_script)
        
        # Hacerlo ejecutable
        os.chmod(run_path, 0o755)
        
        print(f"✅ Script creado: {run_path}")
    
    def generate_setup_report(self) -> Dict:
        """Generar reporte de instalación"""
        import platform
        
        return {
            "timestamp": self._get_timestamp(),
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "python_executable": sys.executable
            },
            "directories_created": self._list_created_directories(),
            "files_created": self._list_created_files(),
            "next_steps": [
                "1. Revisar el archivo .env y verificar la configuración",
                "2. Probar el bot en modo paper trading primero",
                "3. Configurar crontab para backups automáticos",
                "4. Revisar los logs en logs/ para monitoreo",
                "5. Unirse al canal de Telegram para notificaciones"
            ]
        }
    
    def _get_timestamp(self) -> str:
        """Obtener timestamp formateado"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _list_created_directories(self) -> List[str]:
        """Listar directorios creados"""
        directories = []
        for item in self.base_dir.iterdir():
            if item.is_dir():
                directories.append(item.name)
        return sorted(directories)
    
    def _list_created_files(self) -> List[str]:
        """Listar archivos creados"""
        files = []
        for item in self.base_dir.iterdir():
            if item.is_file():
                files.append(item.name)
        return sorted(files)
    
    def run(self):
        """Ejecutar instalación completa"""
        print("=" * 60)
        print("🤖 INSTALADOR DEL BOT DE TRADING AVANZADO")
        print("=" * 60)
        
        # Paso 1: Verificar prerrequisitos
        if not self.check_prerequisites():
            print("\n❌ Prerrequisitos no cumplidos. Por favor corrige los errores.")
            sys.exit(1)
        
        # Paso 2: Crear estructura
        self.create_directory_structure()
        
        # Paso 3: Instalar dependencias
        if not self.install_dependencies():
            print("\n❌ Error instalando dependencias. Revisa los mensajes anteriores.")
            sys.exit(1)
        
        # Paso 4: Configuración
        self.setup_configuration()
        
        # Paso 5: Backup system
        self.setup_backup_system()
        
        # Paso 6: Pruebas
        print("\n" + "=" * 60)
        print("🧪 VERIFICACIÓN FINAL")
        print("=" * 60)
        
        if not self.run_initial_tests():
            print("\n⚠️  Algunas pruebas fallaron. Revisa los errores.")
            response = input("¿Continuar de todos modos? (s/n): ").lower()
            if response != 's':
                print("Instalación cancelada.")
                sys.exit(1)
        
        # Paso 7: Script de ejecución
        self.create_run_script()
        
        # Paso 8: Reporte final
        report = self.generate_setup_report()
        
        print("\n" + "=" * 60)
        print("✅ INSTALACIÓN COMPLETADA")
        print("=" * 60)
        
        print(f"\n📅 Instalación completada el: {report['timestamp']}")
        print(f"💻 Sistema: {report['system']['platform']}")
        print(f"🐍 Python: {report['system']['python_version']}")
        
        print("\n📁 Directorios creados:")
        for dir_name in report['directories_created']:
            print(f"  📂 {dir_name}")
        
        print("\n📄 Archivos de configuración:")
        for file_name in report['files_created']:
            if file_name in ['.env', '.env.example', 'config.py', 'requirements_fixed_v2.txt']:
                print(f"  📄 {file_name}")
        
        print("\n📋 PRÓXIMOS PASOS:")
        for step in report['next_steps']:
            print(f"  {step}")
        
        print("\n" + "=" * 60)
        print("🚀 Para iniciar el bot:")
        print(f"   $ cd {self.base_dir}")
        print(f"   $ python run_bot.py")
        print("=" * 60)

def main():
    """Función principal"""
    try:
        installer = BotInstaller()
        installer.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ Instalación cancelada por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error durante la instalación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()