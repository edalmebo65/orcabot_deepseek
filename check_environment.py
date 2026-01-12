#!/usr/bin/env python3
"""
Verificador completo del entorno OrcaBot
Valida todas las dependencias, configuraciones y conexiones
"""
import os
import sys
import json
import platform
import subprocess
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnvironmentChecker:
    """Verificador completo del entorno"""
    
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.results = []
        self.errors = []
        self.warnings = []
        
    def _load_config(self):
        """Carga la configuración"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def check_all(self) -> bool:
        """Ejecuta todas las verificaciones"""
        print("\n" + "="*60)
        print("🔍 ORCABOT - VERIFICACIÓN COMPLETA DEL ENTORNO")
        print("="*60)
        
        # 1. Verificar sistema operativo
        self.check_os()
        
        # 2. Verificar Python
        self.check_python()
        
        # 3. Verificar dependencias
        self.check_dependencies()
        
        # 4. Verificar configuración
        self.check_configuration()
        
        # 5. Verificar Rust
        self.check_rust()
        
        # 6. Verificar conexiones
        self.check_connections()
        
        # 7. Verificar archivos y permisos
        self.check_files_permissions()
        
        # Mostrar resumen
        self.print_summary()
        
        return len(self.errors) == 0
    
    def check_os(self):
        """Verifica sistema operativo"""
        print("\n1. SISTEMA OPERATIVO")
        print("-" * 40)
        
        system = platform.system()
        release = platform.release()
        version = platform.version()
        
        self.results.append(("Sistema", system, "✅"))
        self.results.append(("Versión", f"{release} {version}", "✅"))
        
        # Verificar arquitectura
        arch = platform.machine()
        is_64bit = sys.maxsize > 2**32
        self.results.append(("Arquitectura", f"{arch} {'64-bit' if is_64bit else '32-bit'}", "✅" if is_64bit else "⚠️"))
        
        # Verificar recursos del sistema
        import psutil
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        self.results.append(("CPU Cores", str(cpu_count), "✅" if cpu_count >= 4 else "⚠️"))
        self.results.append(("Memoria RAM", f"{memory_gb:.1f} GB", "✅" if memory_gb >= 8 else "⚠️"))
        
        # Verificar espacio en disco
        disk = psutil.disk_usage('/')
        disk_gb = disk.free / (1024**3)
        self.results.append(("Espacio libre", f"{disk_gb:.1f} GB", "✅" if disk_gb >= 10 else "⚠️"))
    
    def check_python(self):
        """Verifica instalación de Python"""
        print("\n2. PYTHON")
        print("-" * 40)
        
        python_version = platform.python_version()
        python_impl = platform.python_implementation()
        
        # Verificar versión mínima 3.9
        major, minor, _ = map(int, python_version.split('.'))
        version_ok = major == 3 and minor >= 9
        
        self.results.append(("Versión", python_version, "✅" if version_ok else "❌"))
        self.results.append(("Implementación", python_impl, "✅"))
        
        # Verificar entorno virtual
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        self.results.append(("Entorno virtual", "Activado" if in_venv else "No activado", 
                           "✅" if in_venv else "⚠️"))
        
        # Verificar path de Python
        python_path = sys.executable
        self.results.append(("Ejecutable", python_path, "✅"))
    
    def check_dependencies(self):
        """Verifica dependencias de Python"""
        print("\n3. DEPENDENCIAS PYTHON")
        print("-" * 40)
        
        required = [
            ("numpy", "1.24.0"),
            ("pandas", "2.0.0"),
            ("requests", "2.31.0"),
            ("schedule", "1.2.0"),
            ("solana", "0.29.0"),
            ("cryptography", "41.0.0"),
        ]
        
        optional = [
            ("tensorflow", "2.13.0"),
            ("sklearn", "1.3.0"),
            ("aiohttp", "3.9.0"),
            ("websockets", "12.0"),
        ]
        
        print("Requeridas:")
        for package, min_version in required:
            self._check_package(package, min_version, required=True)
        
        print("\nOpcionales:")
        for package, min_version in optional:
            self._check_package(package, min_version, required=False)
    
    def _check_package(self, package: str, min_version: str, required: bool = True):
        """Verifica una dependencia específica"""
        try:
            spec = importlib.util.find_spec(package.replace("-", "_"))
            if spec is None:
                if required:
                    self.results.append((package, "No instalado", "❌"))
                    self.errors.append(f"Paquete requerido faltante: {package}")
                else:
                    self.results.append((package, "No instalado", "⚠️"))
                return
            
            # Obtener versión instalada
            module = __import__(package.replace("-", "_"))
            installed_version = getattr(module, '__version__', 'Desconocida')
            
            # Comparar versiones
            from packaging import version
            if installed_version != 'Desconocida' and version.parse(installed_version) >= version.parse(min_version):
                self.results.append((package, installed_version, "✅"))
            else:
                status = "❌" if required else "⚠️"
                self.results.append((package, f"{installed_version} < {min_version}", status))
                if required:
                    self.errors.append(f"Versión insuficiente: {package} {installed_version} < {min_version}")
                    
        except Exception as e:
            self.results.append((package, f"Error: {str(e)[:30]}", "❌" if required else "⚠️"))
    
    def check_configuration(self):
        """Verifica archivo de configuración"""
        print("\n4. CONFIGURACIÓN")
        print("-" * 40)
        
        if not os.path.exists(self.config_path):
            self.results.append(("Archivo config", "No encontrado", "❌"))
            self.errors.append(f"Archivo de configuración no encontrado: {self.config_path}")
            return
        
        self.results.append(("Archivo config", "Encontrado", "✅"))
        
        # Verificar estructura básica
        required_keys = ["trading_mode", "trading_pairs", "risk_parameters"]
        missing_keys = []
        
        for key in required_keys:
            if key not in self.config:
                missing_keys.append(key)
        
        if missing_keys:
            self.results.append(("Estructura config", f"Faltan: {missing_keys}", "❌"))
            self.errors.append(f"Claves faltantes en configuración: {missing_keys}")
        else:
            self.results.append(("Estructura config", "OK", "✅"))
        
        # Verificar valores específicos
        mode = self.config.get("trading_mode", "")
        if mode not in ["paper", "live", "backtest"]:
            self.results.append(("Modo trading", f"Inválido: {mode}", "❌"))
            self.errors.append(f"Modo de trading inválido: {mode}")
        else:
            self.results.append(("Modo trading", mode, "✅"))
        
        # Verificar pares de trading
        pairs = self.config.get("trading_pairs", [])
        if not pairs:
            self.results.append(("Pares trading", "No configurados", "❌"))
            self.errors.append("No hay pares de trading configurados")
        else:
            self.results.append(("Pares trading", f"{len(pairs)} configurados", "✅"))
            
            # Verificar cada par
            for i, pair in enumerate(pairs):
                pair_key = f"Par {i+1}"
                if all(k in pair for k in ["base", "quote", "min_amount", "max_amount"]):
                    self.results.append((pair_key, f"{pair['base']}/{pair['quote']}", "✅"))
                else:
                    self.results.append((pair_key, "Estructura inválida", "⚠️"))
    
    def check_rust(self):
        """Verifica instalación de Rust"""
        print("\n5. RUST")
        print("-" * 40)
        
        # Verificar si Rust está instalado
        try:
            result = subprocess.run(
                ["rustc", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                rust_version = result.stdout.strip()
                self.results.append(("Rustc", rust_version, "✅"))
            else:
                self.results.append(("Rustc", "No instalado", "❌"))
                self.errors.append("Rust no está instalado")
                return
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.results.append(("Rustc", "No instalado", "❌"))
            self.errors.append("Rust no está instalado")
            return
        
        # Verificar Cargo
        try:
            result = subprocess.run(
                ["cargo", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                cargo_version = result.stdout.strip()
                self.results.append(("Cargo", cargo_version, "✅"))
            else:
                self.results.append(("Cargo", "No instalado", "❌"))
                self.errors.append("Cargo no está instalado")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.results.append(("Cargo", "No instalado", "❌"))
            self.errors.append("Cargo no está instalado")
        
        # Verificar binario Orca Bridge
        rust_binary = self.config.get("rust_binary_path", "./target/release/orca_bridge")
        if os.path.exists(rust_binary):
            self.results.append(("Binario Bridge", "Encontrado", "✅"))
            
            # Verificar permisos de ejecución
            if os.access(rust_binary, os.X_OK):
                self.results.append(("Permisos binario", "Ejecutable", "✅"))
            else:
                self.results.append(("Permisos binario", "No ejecutable", "❌"))
                self.errors.append(f"Binario Rust no ejecutable: {rust_binary}")
        else:
            self.results.append(("Binario Bridge", "No encontrado", "⚠️"))
            self.warnings.append(f"Binario Rust no encontrado: {rust_binary}")
    
    def check_connections(self):
        """Verifica conexiones de red"""
        print("\n6. CONEXIONES")
        print("-" * 40)
        
        import requests
        from requests.exceptions import RequestException
        
        endpoints = [
            ("Solana RPC", self.config.get("solana", {}).get("rpc_endpoint", "https://api.mainnet-beta.solana.com")),
            ("Orca API", "https://api.orca.so"),
            ("Jupiter API", "https://quote-api.jup.ag"),
        ]
        
        for name, url in endpoints:
            try:
                if not url:
                    self.results.append((name, "No configurado", "⚠️"))
                    continue
                
                # Intentar conexión
                response = requests.get(url if "http" in url else f"https://{url}", timeout=10)
                
                if response.status_code < 400:
                    self.results.append((name, f"HTTP {response.status_code}", "✅"))
                else:
                    self.results.append((name, f"HTTP {response.status_code}", "⚠️"))
                    self.warnings.append(f"{name} respondió con error: HTTP {response.status_code}")
                    
            except RequestException as e:
                self.results.append((name, f"Error: {str(e)[:30]}", "❌"))
                self.errors.append(f"No se puede conectar a {name}: {url}")
            except Exception as e:
                self.results.append((name, f"Excepción: {str(e)[:30]}", "❌"))
    
    def check_files_permissions(self):
        """Verifica archivos y permisos necesarios"""
        print("\n7. ARCHIVOS Y PERMISOS")
        print("-" * 40)
        
        required_dirs = [
            ("logs", "./logs", False),
            ("models", "./models", False),
            ("backups", "./backups", False),
            ("config", os.path.dirname(self.config_path) or ".", True),
        ]
        
        required_files = [
            ("Configuración", self.config_path, True),
            ("Log principal", "orca_bot.log", False),
            ("Requirements", "requirements_fixed.txt", False),
        ]
        
        print("Directorios:")
        for name, path, required in required_dirs:
            if os.path.exists(path) and os.path.isdir(path):
                self.results.append((name, path, "✅"))
                
                # Verificar permisos de escritura
                if os.access(path, os.W_OK):
                    self.results.append((f"  ↳ Permisos {name}", "Escritura OK", "✅"))
                else:
                    self.results.append((f"  ↳ Permisos {name}", "Sin escritura", "❌"))
                    self.errors.append(f"Sin permisos de escritura en: {path}")
            else:
                status = "❌" if required else "⚠️"
                self.results.append((name, f"No existe: {path}", status))
                if required:
                    self.errors.append(f"Directorio requerido no existe: {path}")
        
        print("\nArchivos:")
        for name, path, required in required_files:
            if os.path.exists(path):
                self.results.append((name, path, "✅"))
                
                # Verificar permisos
                if os.access(path, os.R_OK):
                    self.results.append((f"  ↳ Permisos {name}", "Lectura OK", "✅"))
                else:
                    self.results.append((f"  ↳ Permisos {name}", "Sin lectura", "❌"))
                    self.errors.append(f"Sin permisos de lectura en: {path}")
            else:
                status = "❌" if required else "⚠️"
                self.results.append((name, f"No existe: {path}", status))
                if required:
                    self.errors.append(f"Archivo requerido no existe: {path}")
    
    def print_summary(self):
        """Muestra resumen de la verificación"""
        print("\n" + "="*60)
        print("📊 RESUMEN DE VERIFICACIÓN")
        print("="*60)
        
        # Mostrar todos los resultados
        max_name_len = max(len(name) for name, _, _ in self.results)
        
        for name, value, status in self.results:
            if not name.startswith("  ↳"):  # No indentar títulos principales
                print()
            print(f"{status} {name:{max_name_len}} : {value}")
        
        # Mostrar estadísticas
        print("\n" + "="*60)
        
        total = len(self.results)
        success = sum(1 for _, _, status in self.results if status == "✅")
        warnings = sum(1 for _, _, status in self.results if status == "⚠️")
        errors = sum(1 for _, _, status in self.results if status == "❌")
        
        print(f"Total verificaciones: {total}")
        print(f"✅ Correctas: {success}")
        print(f"⚠️  Advertencias: {warnings}")
        print(f"❌ Errores: {errors}")
        
        # Mostrar errores si los hay
        if self.errors:
            print("\n❌ ERRORES CRÍTICOS:")
            for error in self.errors:
                print(f"  • {error}")
        
        # Mostrar advertencias si las hay
        if self.warnings:
            print("\n⚠️  ADVERTENCIAS:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        print("\n" + "="*60)
        
        # Recomendación final
        if errors == 0 and warnings == 0:
            print("✅ ¡ENTORNO COMPLETAMENTE LISTO PARA ORCABOT!")
            print("   Ejecuta: python run_bot.py")
        elif errors == 0:
            print("✅ Entorno funcional con algunas advertencias")
            print("   Puedes proceder, pero revisa las advertencias")
        else:
            print("❌ Hay errores críticos que deben resolverse")
            print("   Corrige los errores antes de ejecutar OrcaBot")
        
        print("="*60)

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verificador de entorno OrcaBot')
    parser.add_argument('--config', default='config.json', help='Ruta al archivo de configuración')
    parser.add_argument('--fix', action='store_true', help='Intentar corregir problemas automáticamente')
    
    args = parser.parse_args()
    
    checker = EnvironmentChecker(args.config)
    success = checker.check_all()
    
    # Intentar corrección automática si se solicita
    if args.fix and not success:
        print("\n🛠️  INTENTANDO CORRECCIÓN AUTOMÁTICA...")
        fix_environment(checker.errors)
    
    # Retornar código de salida
    sys.exit(0 if success else 1)

def fix_environment(errors):
    """Intenta corregir problemas del entorno"""
    import subprocess
    import sys
    
    fixes_applied = 0
    
    for error in errors:
        if "Paquete requerido faltante" in error:
            # Extraer nombre del paquete
            package = error.split(":")[-1].strip()
            print(f"  Instalando {package}...")
            
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"    ✅ {package} instalado")
                fixes_applied += 1
            except subprocess.CalledProcessError:
                print(f"    ❌ Error instalando {package}")
        
        elif "Directorio requerido no existe" in error:
            # Extraer ruta del directorio
            import re
            match = re.search(r": (.*)$", error)
            if match:
                dir_path = match.group(1)
                print(f"  Creando directorio {dir_path}...")
                
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    print(f"    ✅ Directorio creado")
                    fixes_applied += 1
                except Exception as e:
                    print(f"    ❌ Error creando directorio: {e}")
    
    if fixes_applied > 0:
        print(f"\n✅ Se aplicaron {fixes_applied} correcciones")
        print("   Ejecuta nuevamente el verificador sin --fix")
    else:
        print("⚠️  No se pudieron aplicar correcciones automáticas")

if __name__ == "__main__":
    main()