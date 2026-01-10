# utils/backup_manager.py
import shutil
import zipfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

class BackupManager:
    """Gestor de backups automatizados"""
    
    def __init__(self, config):
        self.config = config
        self.backup_dir = config.base_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuración de backups
        self.backup_config = {
            'enabled': True,
            'interval_hours': 6,
            'retention_days': 30,
            'max_backups': 100,
            'compress': True,
            'include_logs': True,
            'include_data': True,
            'include_models': True,
            'include_config': True
        }
        
        # Historial de backups
        self.backup_history: List[Dict] = []
        self._load_backup_history()
    
    def create_backup(self, 
                     name: str = None,
                     description: str = "") -> Optional[Path]:
        """
        Crea un backup completo del sistema
        """
        if not self.backup_config['enabled']:
            self.config.logger.warning("Backups are disabled")
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = name or f"backup_{timestamp}"
            backup_path = self.backup_dir / backup_name
            
            # Crear directorio temporal
            temp_dir = self.backup_dir / f"temp_{timestamp}"
            temp_dir.mkdir(exist_ok=True)
            
            # Copiar archivos según configuración
            copied_files = []
            
            # Configuración
            if self.backup_config['include_config']:
                config_files = self._backup_config(temp_dir)
                copied_files.extend(config_files)
            
            # Logs
            if self.backup_config['include_logs']:
                log_files = self._backup_logs(temp_dir)
                copied_files.extend(log_files)
            
            # Datos
            if self.backup_config['include_data']:
                data_files = self._backup_data(temp_dir)
                copied_files.extend(data_files)
            
            # Modelos ML
            if self.backup_config['include_models']:
                model_files = self._backup_models(temp_dir)
                copied_files.extend(model_files)
            
            # Estado del sistema
            state_files = self._backup_state(temp_dir)
            copied_files.extend(state_files)
            
            # Crear metadata del backup
            metadata = {
                "name": backup_name,
                "timestamp": datetime.now().isoformat(),
                "description": description,
                "files_count": len(copied_files),
                "total_size_bytes": sum(f.stat().st_size for f in temp_dir.rglob("*") if f.is_file()),
                "config": self.backup_config,
                "system_info": self._get_system_info()
            }
            
            with open(temp_dir / "backup_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Comprimir si está configurado
            if self.backup_config['compress']:
                backup_file = backup_path.with_suffix(".zip")
                self._create_zip_backup(temp_dir, backup_file)
            else:
                backup_file = backup_path
                shutil.copytree(temp_dir, backup_file)
            
            # Calcular hash del backup
            backup_hash = self._calculate_file_hash(backup_file)
            
            # Limpiar directorio temporal
            shutil.rmtree(temp_dir)
            
            # Actualizar historial
            backup_record = {
                **metadata,
                "backup_path": str(backup_file),
                "backup_size_bytes": backup_file.stat().st_size,
                "backup_hash": backup_hash,
                "compressed": self.backup_config['compress']
            }
            
            self.backup_history.append(backup_record)
            self._save_backup_history()
            
            # Limpiar backups antiguos
            self._cleanup_old_backups()
            
            self.config.logger.info(
                f"✅ Backup created: {backup_name} "
                f"({len(copied_files)} files, {backup_file.stat().st_size / 1024 / 1024:.2f} MB)"
            )
            
            return backup_file
            
        except Exception as e:
            self.config.logger.error(f"Error creating backup: {e}")
            # Limpiar temporal si existe
            if 'temp_dir' in locals() and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return None
    
    def _backup_config(self, temp_dir: Path) -> List[Path]:
        """Copia archivos de configuración"""
        config_dir = temp_dir / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Archivos de configuración principales
        config_files = [
            self.config.base_dir / "config.py",
            self.config.base_dir / ".env.encrypted",
            self.config.base_dir / "requirements.txt"
        ]
        
        copied = []
        for config_file in config_files:
            if config_file.exists():
                dest = config_dir / config_file.name
                shutil.copy2(config_file, dest)
                copied.append(dest)
        
        return copied
    
    def _backup_logs(self, temp_dir: Path) -> List[Path]:
        """Copia archivos de log"""
        logs_dir = temp_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        copied = []
        
        if self.config.logs_dir.exists():
            for log_file in self.config.logs_dir.glob("*.log"):
                dest = logs_dir / log_file.name
                shutil.copy2(log_file, dest)
                copied.append(dest)
        
        return copied
    
    def _backup_data(self, temp_dir: Path) -> List[Path]:
        """Copia datos del sistema"""
        data_dir = temp_dir / "data"
        data_dir.mkdir(exist_ok=True)
        
        copied = []
        
        if self.config.data_dir.exists():
            # Copiar estructura completa
            for item in self.config.data_dir.rglob("*"):
                if item.is_file():
                    # Preservar estructura de directorios
                    relative = item.relative_to(self.config.data_dir)
                    dest = data_dir / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
                    copied.append(dest)
        
        return copied
    
    def _backup_models(self, temp_dir: Path) -> List[Path]:
        """Copia modelos ML"""
        models_dir = temp_dir / "models"
        models_dir.mkdir(exist_ok=True)
        
        copied = []
        
        if self.config.models_dir.exists():
            for model_file in self.config.models_dir.glob("*"):
                if model_file.is_file():
                    dest = models_dir / model_file.name
                    shutil.copy2(model_file, dest)
                    copied.append(dest)
        
        return copied
    
    def _backup_state(self, temp_dir: Path) -> List[Path]:
        """Copia estado del sistema"""
        state_dir = temp_dir / "state"
        state_dir.mkdir(exist_ok=True)
        
        state_path = self.config.base_dir / "state"
        copied = []
        
        if state_path.exists():
            for state_file in state_path.glob("*"):
                if state_file.is_file():
                    dest = state_dir / state_file.name
                    shutil.copy2(state_file, dest)
                    copied.append(dest)
        
        return copied
    
    def _create_zip_backup(self, source_dir: Path, zip_path: Path):
        """Crea backup comprimido en ZIP"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in source_dir.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(source_dir)
                    zipf.write(file, arcname)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcula hash SHA-256 de un archivo"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _get_system_info(self) -> Dict:
        """Obtiene información del sistema"""
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "cpu_count": psutil.cpu_count(),
            "total_memory_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
    
    def _load_backup_history(self):
        """Carga historial de backups"""
        history_file = self.backup_dir / "backup_history.json"
        
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    self.backup_history = json.load(f)
            except:
                self.backup_history = []
    
    def _save_backup_history(self):
        """Guarda historial de backups"""
        history_file = self.backup_dir / "backup_history.json"
        
        with open(history_file, 'w') as f:
            json.dump(self.backup_history, f, indent=2)
    
    def _cleanup_old_backups(self):
        """Limpia backups antiguos según política de retención"""
        if not self.backup_history:
            return
        
        cutoff_time = datetime.now() - timedelta(days=self.backup_config['retention_days'])
        
        # Identificar backups a eliminar
        backups_to_delete = []
        
        for backup in self.backup_history:
            backup_time = datetime.fromisoformat(backup['timestamp'])
            
            if backup_time < cutoff_time:
                backups_to_delete.append(backup)
        
        # Eliminar archivos y registros
        for backup in backups_to_delete:
            backup_path = Path(backup['backup_path'])
            
            if backup_path.exists():
                try:
                    backup_path.unlink()
                    self.config.logger.debug(f"Deleted old backup: {backup_path.name}")
                except Exception as e:
                    self.config.logger.error(f"Error deleting backup {backup_path}: {e}")
            
            self.backup_history.remove(backup)
        
        # Limitar número máximo de backups
        if len(self.backup_history) > self.backup_config['max_backups']:
            excess = len(self.backup_history) - self.backup_config['max_backups']
            for backup in self.backup_history[:excess]:
                backup_path = Path(backup['backup_path'])
                
                if backup_path.exists():
                    try:
                        backup_path.unlink()
                    except:
                        pass
                
                self.backup_history.remove(backup)
        
        # Guardar historial actualizado
        self._save_backup_history()
    
    def restore_backup(self, 
                      backup_path: Path,
                      restore_config: bool = True,
                      restore_data: bool = True,
                      restore_models: bool = True,
                      restore_logs: bool = False) -> bool:
        """
        Restaura sistema desde backup
        """
        try:
            # Verificar que el backup existe
            if not backup_path.exists():
                self.config.logger.error(f"Backup not found: {backup_path}")
                return False
            
            # Crear punto de restauración (backup actual)
            self.create_backup(
                name=f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Pre-restore backup"
            )
            
            # Extraer backup si está comprimido
            if backup_path.suffix == ".zip":
                temp_dir = self.backup_dir / f"restore_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                temp_dir.mkdir(exist_ok=True)
                
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                backup_root = temp_dir
            else:
                backup_root = backup_path
            
            # Restaurar componentes según configuración
            if restore_config:
                self._restore_config(backup_root)
            
            if restore_data:
                self._restore_data(backup_root)
            
            if restore_models:
                self._restore_models(backup_root)
            
            if restore_logs:
                self._restore_logs(backup_root)
            
            # Limpiar temporal si se creó
            if backup_path.suffix == ".zip":
                shutil.rmtree(temp_dir)
            
            self.config.logger.info(f"✅ System restored from backup: {backup_path.name}")
            return True
            
        except Exception as e:
            self.config.logger.error(f"Error restoring backup: {e}")
            return False
    
    def _restore_config(self, backup_root: Path):
        """Restaura configuración"""
        config_source = backup_root / "config"
        
        if config_source.exists():
            for config_file in config_source.glob("*"):
                if config_file.is_file():
                    dest = self.config.base_dir / config_file.name
                    shutil.copy2(config_file, dest)
    
    def _restore_data(self, backup_root: Path):
        """Restaura datos"""
        data_source = backup_root / "data"
        
        if data_source.exists():
            # Limpiar datos actuales
            if self.config.data_dir.exists():
                shutil.rmtree(self.config.data_dir)
            
            # Copiar datos del backup
            shutil.copytree(data_source, self.config.data_dir)
    
    def _restore_models(self, backup_root: Path):
        """Restaura modelos"""
        models_source = backup_root / "models"
        
        if models_source.exists():
            # Limpiar modelos actuales
            if self.config.models_dir.exists():
                shutil.rmtree(self.config.models_dir)
            
            # Copiar modelos del backup
            shutil.copytree(models_source, self.config.models_dir)
    
    def _restore_logs(self, backup_root: Path):
        """Restaura logs"""
        logs_source = backup_root / "logs"
        
        if logs_source.exists():
            for log_file in logs_source.glob("*.log"):
                dest = self.config.logs_dir / log_file.name
                shutil.copy2(log_file, dest)
    
    def get_backup_status(self) -> Dict:
        """Obtiene estado de backups"""
        total_size = 0
        for backup in self.backup_history:
            backup_path = Path(backup.get('backup_path', ''))
            if backup_path.exists():
                total_size += backup_path.stat().st_size
        
        return {
            "enabled": self.backup_config['enabled'],
            "total_backups": len(self.backup_history),
            "total_size_gb": total_size / 1024 / 1024 / 1024,
            "oldest_backup": self.backup_history[0]['timestamp'] if self.backup_history else None,
            "newest_backup": self.backup_history[-1]['timestamp'] if self.backup_history else None,
            "next_backup_in": self._get_next_backup_time(),
            "retention_days": self.backup_config['retention_days'],
            "max_backups": self.backup_config['max_backups']
        }
    
    def _get_next_backup_time(self) -> Optional[str]:
        """Calcula tiempo hasta próximo backup"""
        if not self.backup_history:
            return "Now"
        
        last_backup_time = datetime.fromisoformat(self.backup_history[-1]['timestamp'])
        next_backup_time = last_backup_time + timedelta(hours=self.backup_config['interval_hours'])
        
        if next_backup_time <= datetime.now():
            return "Overdue"
        
        time_remaining = next_backup_time - datetime.now()
        
        # Formatear tiempo restante
        hours, remainder = divmod(time_remaining.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        
        return f"{int(hours)}h {int(minutes)}m"
    
    def verify_backup(self, backup_path: Path) -> Dict:
        """Verifica integridad de un backup"""
        try:
            if not backup_path.exists():
                return {"valid": False, "error": "Backup not found"}
            
            # Buscar en historial
            backup_hash = None
            for backup in self.backup_history:
                if backup['backup_path'] == str(backup_path):
                    backup_hash = backup.get('backup_hash')
                    break
            
            if not backup_hash:
                return {"valid": False, "error": "Backup not in history"}
            
            # Calcular hash actual
            current_hash = self._calculate_file_hash(backup_path)
            
            # Verificar
            valid = current_hash == backup_hash
            
            result = {
                "valid": valid,
                "expected_hash": backup_hash,
                "current_hash": current_hash,
                "file_size_bytes": backup_path.stat().st_size,
                "last_modified": datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat()
            }
            
            if not valid:
                result["error"] = "Hash mismatch - backup may be corrupted"
            
            return result
            
        except Exception as e:
            return {"valid": False, "error": str(e)}