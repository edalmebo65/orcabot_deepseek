# cleanup_organizer.py
"""
Script para organizar el repositorio moviendo archivos innecesarios a backup
"""
import os
import shutil
import argparse
from datetime import datetime

class RepoOrganizer:
    def __init__(self):
        self.backup_dir = "backup/old_files"
        self.essential_files = {
            'main_integrated.py',
            'config_manager.py', 
            'balance_checker.py',
            'token_selector.py',
            'gradual_trader.py',
            'requirements_fixed_v2.txt',
            '.env.example',
            'README.md',
            'cleanup_organizer.py'
        }
        
        self.new_essential_files = {
            'config.py',
            'ml_trainer.py',
            'token_selector_enhanced.py',
            'gradual_trader_enhanced.py',
            'process_optimizer.py',
            'security_enhancer.py',
            'arbitrage_engine.py',
            'hedging_system.py',
            'fee_optimizer.py',
            'financial_analytics.py',
            'portfolio_manager.py',
            'risk_manager.py',
            'telegram_notifier.py',
            'health_monitor.py',
            'backtest_engine.py',
            'setup_installer.py',
            'run_bot.py'
        }
        
    def create_backup_structure(self):
        """Crear estructura de directorios de backup"""
        os.makedirs(self.backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.backup_dir, f"backup_{timestamp}")
    
    def identify_files_to_move(self):
        """Identificar archivos que no son esenciales"""
        all_files = os.listdir('.')
        files_to_move = []
        
        for file in all_files:
            if (file.endswith('.py') or file.endswith('.txt') or file.endswith('.md')) and \
               file not in self.essential_files and \
               file not in self.new_essential_files and \
               not file.startswith('.'):
                files_to_move.append(file)
        
        return files_to_move
    
    def move_files_to_backup(self, files, backup_path):
        """Mover archivos a backup"""
        for file in files:
            try:
                if os.path.exists(file):
                    shutil.move(file, os.path.join(backup_path, file))
                    print(f"✓ Movido: {file} → {backup_path}/")
            except Exception as e:
                print(f"✗ Error moviendo {file}: {e}")
    
    def create_readme_backup(self, backup_path, moved_files):
        """Crear README del backup"""
        readme_content = f"""# Backup creado el {datetime.now()}

## Archivos movidos:
{chr(10).join(f'- {f}' for f in moved_files)}

## Razón:
Estos archivos fueron reemplazados por versiones mejoradas con:
- Machine Learning avanzado (LSTM + Random Forest)
- Gestión de riesgo mejorada
- Sistema de reingeniería automática
- Características avanzadas de trading
"""
        
        with open(os.path.join(backup_path, "README.md"), 'w') as f:
            f.write(readme_content)
    
    def run(self, dry_run=False):
        """Ejecutar la organización"""
        print("🔍 Analizando estructura del repositorio...")
        
        files_to_move = self.identify_files_to_move()
        
        if not files_to_move:
            print("✅ No hay archivos para mover.")
            return
        
        print(f"\n📋 Archivos a mover ({len(files_to_move)}):")
        for file in files_to_move:
            print(f"  - {file}")
        
        if dry_run:
            print("\n🔧 Modo simulación - No se moverán archivos.")
            return
        
        backup_path = self.create_backup_structure()
        print(f"\n📦 Creando backup en: {backup_path}")
        
        self.move_files_to_backup(files_to_move, backup_path)
        self.create_readme_backup(backup_path, files_to_move)
        
        print(f"\n✅ Backup completado: {len(files_to_move)} archivos movidos")
        print(f"📁 Ubicación: {backup_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Organizar archivos del bot')
    parser.add_argument('--dry-run', action='store_true', help='Mostrar qué se movería sin hacer cambios')
    args = parser.parse_args()
    
    organizer = RepoOrganizer()
    organizer.run(dry_run=args.dry_run)