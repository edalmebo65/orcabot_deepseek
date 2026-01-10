@echo off
echo ====================================================
echo INSTALADOR ORCA BOT - PYTHON 3.12
echo ====================================================

echo 1. Verificando Python 3.12...
python --version | findstr "3.12" > nul
if errorlevel 1 (
    echo ❌ No se encuentra Python 3.12
    echo Descargar desde: https://www.python.org/downloads/release/python-3120/
    pause
    exit /b 1
)

echo 2. Configurando entorno virtual...
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

echo Activando entorno...
call venv\Scripts\activate.bat

echo 3. Actualizando herramientas base...
python -m pip install --upgrade pip setuptools wheel

echo 4. Instalando dependencias en orden crítico...

echo 4.1. Dependencias de sistema (puede requerir build tools)...
pip install cryptography==42.0.5

echo 4.2. Instalando solana stack...
pip install solana solders anchorpy

echo 4.3. Instalando orca-py desde GitHub...
pip install "orca-py @ git+https://github.com/orca-so/orca-py.git"

echo 4.4. Instalando web3 y blockchain...
pip install web3 eth-account eth-typing

echo 4.5. Instalando async y networking...
pip install aiohttp aiogram httpx websockets

echo 4.6. Instalando data science...
pip install numpy pandas scikit-learn matplotlib

echo 4.7. Instalando trading...
pip install ccxt ta

echo 4.8. Instalando utilidades...
pip install python-dotenv pydantic rich loguru

echo 5. Verificando instalación...
python -c "
import sys
print(f'Python: {sys.version}')
deps = ['solana', 'solders', 'anchorpy', 'web3', 'aiogram', 'cryptography']
for dep in deps:
    try:
        __import__(dep)
        print(f'✅ {dep}')
    except:
        print(f'❌ {dep}')
"

echo.
echo ====================================================
echo ✅ INSTALACIÓN COMPLETADA
echo ====================================================
echo Comandos:
echo   venv\Scripts\activate  - Activar entorno
echo   python main.py         - Ejecutar bot
echo   pip list               - Ver dependencias
echo.
pause