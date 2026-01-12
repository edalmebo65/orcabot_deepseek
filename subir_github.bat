#!/bin/bash
# script_push_github.sh
# Script para subir archivos modificados de OrcaBot Optimizado a GitHub

echo "🚀 INICIANDO SUBIDA A GITHUB..."
echo "Repositorio: https://github.com/edalmebo65/orcabot_deepseek.git"
echo "="*60

# 1. Verificar que estamos en el directorio correcto
if [ ! -f "main_integrated.py" ]; then
    echo "❌ ERROR: No se encuentra main_integrated.py"
    echo "   Ejecuta este script desde el directorio principal de OrcaBot"
    exit 1
fi

# 2. Lista de archivos nuevos/modificados
ARCHIVOS_MODIFICADOS=(
    # Archivos principales optimizados
    "profit_optimizer.py"
    "main_integrated.py"
    "ml_trainer_advanced.py"
    "config_optimized.json"
    
    # Archivos de configuración
    "config_manager.py"
    "requirements_optimized.txt"
    
    # Scripts de utilidad
    "setup_orcabot.py"
    "cleanup_obsolete.py"
    
    # Archivos README y documentación
    "README_OPTIMIZED.md"
    "performance_report_template.md"
)

ARCHIVOS_NUEVOS=(
    # Directorios nuevos
    "models/advanced/"
    "logs/optimized/"
    "data/optimized/"
    "backup/optimized/"
    "reports/"
    
    # Archivos de configuración optimizada
    "strategies/"
    "arbitrage/"
    "compounding/"
)

# 3. Verificar si git está instalado
if ! command -v git &> /dev/null; then
    echo "❌ ERROR: Git no está instalado"
    echo "   Instala git con: sudo apt-get install git"
    exit 1
fi

# 4. Configurar git (si no está configurado)
echo "🔧 Configurando Git..."
git config --global user.name "OrcaBot Optimizer"
git config --global user.email "optimizer@orcabot.com"

# 5. Inicializar repositorio si no existe
if [ ! -d ".git" ]; then
    echo "📦 Inicializando repositorio Git..."
    git init
    
    # Configurar remoto
    git remote add origin https://github.com/edalmebo65/orcabot_deepseek.git
    
    # Configurar rama principal
    git branch -M main
fi

# 6. Verificar conexión con GitHub
echo "🔗 Verificando conexión con GitHub..."
if ! git ls-remote https://github.com/edalmebo65/orcabot_deepseek.git &> /dev/null; then
    echo "⚠️  No se puede conectar a GitHub. Verifica:"
    echo "   1. Que el repositorio exista"
    echo "   2. Que tengas permisos de escritura"
    echo "   3. Tu conexión a internet"
    
    read -p "¿Continuar sin verificación? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi

# 7. Crear directorios necesarios
echo "📁 Creando estructura de directorios..."
for dir in "${ARCHIVOS_NUEVOS[@]}"; do
    if [[ $dir == */ ]]; then
        mkdir -p "$dir"
        echo "   ✅ Directorio creado: $dir"
    fi
done

# 8. Crear archivos README optimizados
echo "📝 Creando documentación optimizada..."

# README principal optimizado
cat > README_OPTIMIZED.md << 'EOF'
# 🚀 OrcaBot DeepSeek - Versión Optimizada

## 📊 Sistema de Maximización de Ganancias

### Características Principales:
- **Retorno Anual Objetivo**: 80%+
- **Win Rate Mínimo**: 60%+
- **Sharpe Ratio Mínimo**: 1.5+
- **Drawdown Máximo Diario**: 2%

### Estrategias Implementadas:

#### 1. Take Profit Parcial Inteligente
```python
# 50% @ 3% profit, 25% @ 5% profit, 25% trailing stop
partial_take_profits = [
    (0.03, 0.50),
    (0.05, 0.25), 
    (0.08, 0.25)  # Trailing desde +8%
]