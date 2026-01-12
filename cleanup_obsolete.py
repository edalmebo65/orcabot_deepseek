#!/usr/bin/env python3
"""
Script para limpiar archivos obsoletos del proyecto OrcaBot
"""
import os
import shutil
import sys

def list_obsolete_files():
    """Lista archivos obsoletos identificados"""
    obsolete_files = [
        # Archivos duplicados o versiones antiguas
        "main.py",
        "run_bot_fixed.py",
        
        # Módulo Rust no compilado (inexistente)
        "orca_rust_bridge.pyd",
        
        # Scripts de instalación obsoletos
        "install_deps_no_conflict.py",
        "install_orca.py",
        
        # Archivos de instalación específicos de Windows
        "activate_env.bat",
        "install_conda.bat",
        "install_missing.bat",
        "install_missing_fixed.bat",
        "install_py312.bat",
        
        # Checkers específicos de versiones
        "check_py312.py",
        
        # Archivos de texto con información duplicada
        "Arquitectura_bot_deepseek.txt",
        "Arquitectura_final.txt",
        "Arquitectura_integrando_Rust.txt",
        "Caracteristicas_clave_implementadas.txt",
        "Happy Trading! 🚀.txt",
        "Installation.txt",
        "Orcabot_multioperation.txt",
        "comandos_telegram.txt",
        "🤖 Telegram Commands.txt",
        
        # Scripts de shell duplicados
        "Build Image.sh",
        "Exportar_variables_sistema.sh",
        "Install dependencies.sh",
        "Run Container.sh",
        "Run setup script.sh",
        "Run tests.sh",
        "Setup_variables_entorno.sh",
        "Start the bot.sh",
        "Test Suite.sh",
        "iniciar_bot.sh",
        
        # Documentos Word
        "Security Features.docx",
        "📚 Manual de Uso Completo.docx",
        
        # Makefile no utilizado
        "makefile.mk",
        
        # Requirements obsoletos
        "requirements.txt",
        "requirements_conda.txt",
        "requirements_py312.txt",
        
        # Otros archivos temporales o de desarrollo
        "editar_config.py",
        "environment.yml",
    ]
    
    # Archivos que pueden existir en el repo
    existing_obsolete = [f for f in obsolete_files if os.path.exists(f)]
    
    return existing_obsolete

def backup_file(filepath):
    """Crea backup de un archivo antes de eliminarlo"""
    backup_dir = "./backups/obsolete"
    os.makedirs(backup_dir, exist_ok=True)
    
    if os.path.exists(filepath):
        filename = os.path.basename(filepath)
        backup_path = os.path.join(backup_dir, filename)
        
        # Si ya existe un backup con ese nombre, agregar número
        counter = 1
        while os.path.exists(backup_path):
            name, ext = os.path.splitext(filename)
            backup_path = os.path.join(backup_dir, f"{name}_{counter}{ext}")
            counter += 1
        
        shutil.copy2(filepath, backup_path)
        return backup_path
    
    return None

def cleanup_obsolete_files(dry_run=False):
    """Elimina archivos obsoletos"""
    obsolete_files = list_obsolete_files()
    
    if not obsolete_files:
        print("✅ No hay archivos obsoletos para limpiar")
        return
    
    print("🗑️  LIMPIEZA DE ARCHIVOS OBSOLETOS")
    print("=" * 50)
    print(f"Encontrados {len(obsolete_files)} archivos obsoletos")
    print()
    
    deleted = []
    backed_up = []
    errors = []
    
    for filepath in obsolete_files:
        try:
            if dry_run:
                print(f"📄 [SIMULACIÓN] {filepath}")
                deleted.append(filepath)
                continue
            
            # Crear backup
            backup_path = backup_file(filepath)
            if backup_path:
                backed_up.append((filepath, backup_path))
            
            # Eliminar archivo
            if os.path.isdir(filepath):
                shutil.rmtree(filepath)
            else:
                os.remove(filepath)
            
            deleted.append(filepath)
            print(f"✅ Eliminado: {filepath}")
            
            if backup_path:
                print(f"   📦 Backup: {backup_path}")
            
        except Exception as e:
            errors.append((filepath, str(e)))
            print(f"❌ Error eliminando {filepath}: {e}")
    
    # Resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE LIMPIEZA")
    print(f"Archivos eliminados: {len(deleted)}")
    print(f"Archivos con backup: {len(backed_up)}")
    print(f"Errores: {len(errors)}")
    
    if backed_up:
        print("\n📦 BACKUPS CREADOS:")
        for original, backup in backed_up:
            print(f"  {original} -> {backup}")
    
    if errors:
        print("\n❌ ERRORES:")
        for filepath, error in errors:
            print(f"  {filepath}: {error}")
    
    if dry_run:
        print("\n⚠️  MODO SIMULACIÓN - No se eliminó nada realmente")
    else:
        print("\n✅ Limpieza completada")
    
    return deleted, backed_up, errors

def analyze_project_structure():
    """Analiza estructura actual del proyecto"""
    print("\n📁 ESTRUCTURA ACTUAL DEL PROYECTO")
    print("=" * 50)
    
    structure = {}
    
    for root, dirs, files in os.walk("."):
        # Ignorar directorios ocultos y virtual envs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env', 'node_modules']]
        
        level = root.replace(".", "").count(os.sep)
        indent = " " * 2 * level
        
        if root != ".":
            print(f"{indent}📂 {os.path.basename(root)}/")
        
        subindent = " " * 2 * (level + 1)
        
        for file in files:
            if not file.startswith('.') and file not in ['__pycache__']:
                ext = os.path.splitext(file)[1]
                
                # Iconos por tipo de archivo
                icon = "📄"
                if ext in ['.py', '.rs', '.js', '.ts']:
                    icon = "🐍" if ext == '.py' else "🦀" if ext == '.rs' else "📜"
                elif ext in ['.json', '.toml', '.yaml', '.yml']:
                    icon = "⚙️"
                elif ext in ['.md', '.txt', '.rst']:
                    icon = "📝"
                elif ext in ['.log']:
                    icon = "📋"
                elif ext in ['.sh', '.bat']:
                    icon = "🖥️"
                
                print(f"{subindent}{icon} {file}")

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Limpia archivos obsoletos del proyecto OrcaBot'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula la limpieza sin eliminar nada'
    )
    
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Analiza estructura del proyecto'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Elimina sin confirmación'
    )
    
    args = parser.parse_args()
    
    print("🤖 ORCABOT - LIMPIEZA DE ARCHIVOS OBSOLETOS")
    print("=" * 60)
    
    if args.analyze:
        analyze_project_structure()
        return
    
    if not args.force and not args.dry_run:
        print("\n⚠️  Esta acción eliminará archivos permanentemente.")
        print("   Se crearán backups en ./backups/obsolete/")
        
        confirm = input("\n¿Continuar? (s/n): ").strip().lower()
        if confirm != 's':
            print("❌ Operación cancelada")
            return
    
    deleted, backed_up, errors = cleanup_obsolete_files(args.dry_run)
    
    # Mostrar recomendaciones finales
    if not args.dry_run and deleted:
        print("\n💡 RECOMENDACIONES:")
        print("   1. Verifica que el bot funcione correctamente")
        print("   2. Los backups están en ./backups/obsolete/")
        print("   3. Puedes restaurar archivos si es necesario")
        print("\n   Estructura recomendada final:")
        print("   📂 orcabot_deepseek/")
        print("     ├── 📄 config.json")
        print("     ├── 📄 run_bot.py")
        print("     ├── 📄 main_integrated.py")
        print("     ├── 📄 rust_bridge_fixed.py")
        print("     ├── 📄 requirements_fixed.txt")
        print("     ├── 📄 check_environment.py")
        print("     ├── 📂 rust/")
        print("     │   └── 📂 orca_bridge/")
        print("     ├── 📂 logs/")
        print("     ├── 📂 models/")
        print("     └── 📂 backups/")

if __name__ == "__main__":
    main()