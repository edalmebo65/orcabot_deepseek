#!/usr/bin/env python3
"""
Verificación específica para entorno orcabot_deepseek
"""
import sys
import os
import platform
import json
from datetime import datetime
from pathlib import Path

class EnvChecker:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'environment': 'orcabot_deepseek',
            'checks': {}
        }
    
    def print_section(self, title):
        print(f"\n{'='*60}")
        print(f"📋 {title}")
        print(f"{'='*60}")
    
    def check_conda_env(self):
        """Verifica entorno Conda específico"""
        self.print_section("CONDA ENVIRONMENT")
        
        expected_env = "orcabot_deepseek"
        current_env = os.environ.get('CONDA_DEFAULT_ENV', 'No environment')
        
        print(f"Entorno esperado: {expected_env}")
        print(f"Entorno actual:   {current_env}")
        
        if current_env == expected_env:
            print(f"✅ ENTORNO CORRECTO: {expected_env}")
            self.results['checks']['conda_env'] = {'status': 'PASS', 'details': current_env}
            return True
        else:
            print(f"❌ ENTORNO INCORRECTO")
            print(f"   Ejecuta: conda activate {expected_env}")
            self.results['checks']['conda_env'] = {'status': 'FAIL', 'details': current_env}
            return False
    
    def check_python_version(self):
        """Verifica Python 3.10.19"""
        self.print_section("PYTHON VERSION")
        
        expected = (3, 10, 19)
        current = sys.version_info[:3]
        
        print(f"Versión esperada: Python {expected[0]}.{expected[1]}.{expected[2]}")
        print(f"Versión actual:   Python {current[0]}.{current[1]}.{current[2]}")
        print(f"Ejecutable:       {sys.executable}")
        
        if current == expected:
            print("✅ VERSIÓN DE PYTHON CORRECTA")
            self.results['checks']['python_version'] = {'status': 'PASS', 'details': f"{current}"}
            return True
        elif current[0:2] == expected[0:2]:  # Solo mayor.minor igual
            print("⚠️  Versión menor diferente, puede funcionar")
            self.results['checks']['python_version'] = {'status': 'WARNING', 'details': f"{current}"}
            return True
        else:
            print("❌ VERSIÓN DE PYTHON INCORRECTA")
            print(f"   Se requiere Python 3.10.x")
            self.results['checks']['python_version'] = {'status': 'FAIL', 'details': f"{current}"}
            return False
    
    def check_critical_modules(self):
        """Verifica módulos críticos instalados"""
        self.print_section("CRITICAL MODULES")
        
        modules_to_check = [
            ('solana', '0.30.1'),
            ('solders', '0.18.0'),
            ('anchorpy', '0.16.0'),
            ('web3', '6.11.1'),
            ('aiohttp', '3.9.1'),
            ('aiogram', '2.25.1'),
            ('cryptography', '41.0.7'),
            ('numpy', '1.24.4'),
            ('pandas', '2.0.3'),
        ]
        
        results = {}
        all_pass = True
        
        print(f"{'Módulo':20} {'Estado':8} {'Versión':15} {'Requerido':10}")
        print("-" * 60)
        
        for module_name, required_version in modules_to_check:
            try:
                module = __import__(module_name)
                
                # Obtener versión
                version = getattr(module, '__version__', 
                               getattr(module, 'VERSION', 
                               getattr(module, 'version', 'N/A')))
                
                # Verificar si cumple con versión requerida
                try:
                    from packaging import version as pkg_version
                    if version != 'N/A':
                        installed = pkg_version.parse(str(version))
                        required = pkg_version.parse(required_version)
                        status = "PASS" if installed >= required else "WARNING"
                    else:
                        status = "PASS"
                except:
                    status = "PASS"
                
                if status == "PASS":
                    print(f"✅ {module_name:18} OK         {str(version):15} {required_version:10}")
                else:
                    print(f"⚠️  {module_name:18} Versión    {str(version):15} {required_version:10}")
                    all_pass = False
                
                results[module_name] = {'status': status, 'version': str(version)}
                
            except ImportError as e:
                print(f"❌ {module_name:18} FALTANTE   {'N/A':15} {required_version:10}")
                results[module_name] = {'status': 'FAIL', 'error': str(e)}
                all_pass = False
            except Exception as e:
                print(f"⚠️  {module_name:18} ERROR      {str(e)[:20]:15} {required_version:10}")
                results[module_name] = {'status': 'ERROR', 'error': str(e)}
                all_pass = False
        
        self.results['checks']['modules'] = results
        return all_pass
    
    def check_orca_installation(self):
        """Verifica instalación específica de orca"""
        self.print_section("ORCA-PY INSTALLATION")
        
        orca_components = [
            'orca',
            'orca.whirlpool',
            'orca.whirlpool.accounts',
            'orca.whirlpool.constants',
            'orca.whirlpool.instructions',
        ]
        
        results = {}
        all_pass = True
        
        for component in orca_components:
            try:
                __import__(component)
                print(f"✅ {component}")
                results[component] = {'status': 'PASS'}
            except ImportError as e:
                print(f"❌ {component}: {str(e)[:50]}")
                results[component] = {'status': 'FAIL', 'error': str(e)}
                all_pass = False
            except Exception as e:
                print(f"⚠️  {component}: {type(e).__name__}")
                results[component] = {'status': 'WARNING', 'error': str(e)}
        
        # Verificar si es instalación desde GitHub
        try:
            import orca
            orca_path = orca.__file__
            if 'site-packages' in orca_path and 'orca-py' in orca_path:
                print(f"\n📦 Orca instalado desde: {orca_path}")
            else:
                print(f"\n📦 Orca instalado en: {orca_path}")
        except:
            pass
        
        self.results['checks']['orca'] = results
        return all_pass
    
    def check_project_structure(self):
        """Verifica estructura del proyecto"""
        self.print_section("PROJECT STRUCTURE")
        
        project_root = Path.cwd()
        print(f"Directorio del proyecto: {project_root}")
        
        required = {
            'directories': ['scripts', 'src', 'config', 'data', 'logs'],
            'files': ['main.py', 'requirements.txt', '.env.example', 'README.md']
        }
        
        print("\n📁 Directorios:")
        for dir_name in required['directories']:
            dir_path = project_root / dir_name
            if dir_path.exists():
                print(f"  ✅ {dir_name}/")
            else:
                print(f"  ⚠️  {dir_name}/ (faltante)")
        
        print("\n📄 Archivos:")
        for file_name in required['files']:
            file_path = project_root / file_name
            if file_path.exists():
                print(f"  ✅ {file_name}")
            else:
                print(f"  ⚠️  {file_name} (faltante)")
        
        return True
    
    def check_system_info(self):
        """Información del sistema"""
        self.print_section("SYSTEM INFORMATION")
        
        info = {
            'Platform': platform.platform(),
            'System': platform.system(),
            'Release': platform.release(),
            'Architecture': platform.architecture()[0],
            'Processor': platform.processor(),
            'Python Implementation': platform.python_implementation(),
        }
        
        for key, value in info.items():
            print(f"{key:25}: {value}")
        
        self.results['system_info'] = info
        return True
    
    def generate_report(self, checks_passed):
        """Genera reporte final"""
        self.print_section("FINAL REPORT")
        
        # Contar resultados
        total_checks = len(self.results['checks'])
        passed = sum(1 for check in self.results['checks'].values() 
                    if isinstance(check, dict) and check.get('status') == 'PASS')
        warnings = sum(1 for check in self.results['checks'].values() 
                      if isinstance(check, dict) and check.get('status') == 'WARNING')
        failed = sum(1 for check in self.results['checks'].values() 
                    if isinstance(check, dict) and check.get('status') == 'FAIL')
        
        print(f"📊 RESUMEN DE VERIFICACIÓN:")
        print(f"   • Checks totales: {total_checks}")
        print(f"   • ✅ Aprobados:   {passed}")
        print(f"   • ⚠️  Advertencias: {warnings}")
        print(f"   • ❌ Fallidos:    {failed}")
        
        print(f"\n🎯 ENTORNO: orcabot_deepseek")
        print(f"   • Estado: {'✅ LISTO' if checks_passed else '❌ REVISAR PROBLEMAS'}")
        
        # Recomendaciones
        if not checks_passed:
            print(f"\n🔧 ACCIONES RECOMENDADAS:")
            
            # Revisar entorno Conda
            env_check = self.results['checks'].get('conda_env', {})
            if env_check.get('status') == 'FAIL':
                print(f"   • Activar entorno: conda activate orcabot_deepseek")
            
            # Revisar módulos faltantes
            modules_check = self.results['checks'].get('modules', {})
            for module, data in modules_check.items():
                if data.get('status') == 'FAIL':
                    print(f"   • Instalar módulo: pip install {module}")
            
            # Revisar orca
            orca_check = self.results['checks'].get('orca', {})
            if any(v.get('status') == 'FAIL' for v in orca_check.values()):
                print(f"   • Reinstalar orca-py: pip install git+https://github.com/orca-so/orca-py.git")
        
        # Guardar reporte
        report_file = Path("environment_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Reporte guardado en: {report_file.absolute()}")
        
        return checks_passed
    
    def run_all_checks(self):
        """Ejecuta todas las verificaciones"""
        print("=" * 60)
        print("🔧 ORCABOT_DEEPSEEK - ENVIRONMENT CHECKER")
        print("=" * 60)
        print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Proyecto: {Path.cwd().name}")
        print("=" * 60)
        
        checks = [
            self.check_conda_env,
            self.check_python_version,
            self.check_critical_modules,
            self.check_orca_installation,
            self.check_project_structure,
            self.check_system_info,
        ]
        
        results = []
        for check in checks:
            try:
                result = check()
                results.append(result)
            except Exception as e:
                print(f"❌ Error en check: {e}")
                results.append(False)
        
        all_passed = all(results)
        self.generate_report(all_passed)
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ¡ENTORNO VERIFICADO Y LISTO PARA USO!")
        else:
            print("⚠️  HAY PROBLEMAS QUE RESOLVER ANTES DE CONTINUAR")
        print("=" * 60)
        
        return all_passed

def main():
    """Función principal"""
    checker = EnvChecker()
    success = checker.run_all_checks()
    
    if success:
        print("\n✅ Puedes continuar con:")
        print("   python main.py")
    else:
        print("\n❌ Corrige los problemas antes de ejecutar el bot")
    
    # Preguntar si abrir el reporte
    try:
        response = input("\n¿Abrir reporte JSON? (s/n): ").strip().lower()
        if response in ['s', 'si', 'sí', 'y', 'yes']:
            report_file = Path("environment_report.json")
            if report_file.exists():
                import webbrowser
                webbrowser.open(f"file://{report_file.absolute()}")
    except:
        pass
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())