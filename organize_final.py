# organize_final.py
"""
Script final para organizar y verificar la implementación completa
"""
import os
import shutil
from pathlib import Path
import subprocess
import sys
from datetime import datetime

class FinalOrganizer:
    """Organizador final de la implementación"""
    
    def __init__(self):
        self.base_dir = Path.cwd()
        self.required_files = [
            # Archivos principales
            'run_bot.py',
            'config.py',
            'cleanup_organizer.py',
            'setup_installer.py',
            
            # Módulos ML y Trading
            'ml_trainer.py',
            'token_selector_enhanced.py',
            'gradual_trader_enhanced.py',
            'process_optimizer.py',
            
            # Seguridad y Monitoreo
            'security_enhancer.py',
            'financial_analytics.py',
            'telegram_notifier.py',
            'health_monitor.py',
            
            # Utilidades
            'organize_final.py',
            'requirements_fixed_v2.txt',
            '.env.example',
            'README.md'
        ]
        
        self.required_dirs = [
            'models',
            'metadata',
            'logs/audit',
            'logs/trading',
            'backup',
            'data/historical',
            'data/realtime',
            'config_backups'
        ]
    
    def verify_implementation(self) -> bool:
        """Verificar que toda la implementación esté completa"""
        print("🔍 Verificando implementación completa...")
        print("=" * 60)
        
        all_ok = True
        
        # Verificar archivos requeridos
        print("\n📄 ARCHIVOS REQUERIDOS:")
        for file_name in self.required_files:
            file_path = self.base_dir / file_name
            if file_path.exists():
                print(f"  ✅ {file_name}")
            else:
                print(f"  ❌ {file_name} - FALTANTE")
                all_ok = False
        
        # Verificar directorios requeridos
        print("\n📁 DIRECTORIOS REQUERIDOS:")
        for dir_path in self.required_dirs:
            full_path = self.base_dir / dir_path
            if full_path.exists():
                print(f"  ✅ {dir_path}")
            else:
                print(f"  ❌ {dir_path} - FALTANTE")
                all_ok = False
        
        # Verificar dependencias
        print("\n📦 DEPENDENCIAS:")
        try:
            import torch, pandas, aiohttp, cryptography
            print("  ✅ Dependencias principales instaladas")
        except ImportError as e:
            print(f"  ❌ Dependencias faltantes: {e}")
            all_ok = False
        
        return all_ok
    
    def create_readme(self):
        """Crear README completo"""
        readme_content = """# 🤖 OrcaBot DeepSeek - Bot de Trading Avanzado

Bot de trading automático para Solana con Machine Learning, gestión de riesgo avanzada y reingeniería automática.

## 🚀 Características Principales

### 🧠 Machine Learning Avanzado
- **Ensemble Models**: LSTM + Random Forest + Gradient Boosting
- **Entrenamiento incremental** cada 12 horas
- **40+ features técnicas** y on-chain
- **Predicciones en tiempo real** con confianza > 65% 

### 📊 Gestión de Riesgo Inteligente
- **Trading gradual** con máximo 5 operaciones simultáneas
- **Stop Loss dinámico** basado en ATR y soportes
- **Trailing Stop** que se activa al 0.2% de ganancia
- **Límites diarios/semanales/mensuales** de pérdidas

### 🔄 Reingeniería Automática
- **Optimización genética** de parámetros
- **Aprendizaje por refuerzo** (Reinforcement Learning)
- **Análisis estadístico** de patrones de trading
- **Ajuste automático** de estrategias

### 🛡️ Seguridad Bancaria
- **Encriptación AES-256-GCM** de claves privadas
- **Multi-signature** para transacciones grandes
- **Detección de anomalías** en tiempo real
- **Auditoría completa** de todas las operaciones

## 📋 Instalación Rápida

### Prerrequisitos
- Python 3.9 o superior
- 2 GB RAM mínimo, 4 GB recomendado
- Conexión a internet estable

### Instalación en 3 pasos:

```bash
# 1. Clonar repositorio
git clone https://github.com/edalmebo65/orcabot_deepseek.git
cd orcabot_deepseek

# 2. Ejecutar instalador automático
python setup_installer.py

# 3. Iniciar el bot
python run_bot.py """