@echo off
echo ============================================
echo ACTIVANDO ENTORNO ORCABOT_DEEPSEEK
echo ============================================

echo 1. Activando entorno conda...
call conda activate orcabot_deepseek

if errorlevel 1 (
    echo ❌ Error activando el entorno
    echo Intentando crear el entorno desde environment.yml...
    
    conda env create -f environment.yml
    if errorlevel 1 (
        echo ❌ Error creando entorno
        echo Creando entorno manualmente...
        conda create -n orcabot_deepseek python=3.10.19 -y
        call conda activate orcabot_deepseek
    ) else (
        call conda activate orcabot_deepseek
    )
)

echo 2. Verificando Python...
python --version

echo 3. Directorio actual: %CD%

echo.
echo ============================================
echo ✅ ENTORNO ACTIVADO: orcabot_deepseek
echo ============================================
echo Comandos disponibles:
echo   python main.py              - Ejecutar bot principal
echo   python check_env.py         - Verificar entorno
echo   python start_bot.py         - Launcher interactivo
echo   conda list                  - Ver paquetes instalados
echo   pip install <paquete>       - Instalar paquete adicional
echo ===========================================%

:: Mantener la ventana abierta
pause