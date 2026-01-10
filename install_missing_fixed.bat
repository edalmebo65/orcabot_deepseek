@echo off
echo ============================================
echo INSTALANDO DEPENDENCIAS FALTANTES
echo ============================================

echo 1. Verificando entorno...
call conda activate orcabot_deepseek
python --version

echo 2. Instalando dependencias de Solana...
echo Instalando solana...
pip install solana==0.30.1

echo Instalando solders...
pip install solders==0.18.0

echo Instalando anchorpy...
pip install anchorpy==0.16.0

echo 3. Instalando Web3...
pip install web3==6.11.1

echo 4. Instalando async...
pip install aiohttp==3.9.1
pip install aiogram==2.25.1

echo 5. Instalando orca-py desde GitHub...
pip install git+https://github.com/orca-so/orca-py.git

echo 6. Instalando dependencias adicionales...
pip install ccxt==4.1.36
pip install python-dotenv==1.0.0
pip install pydantic==2.4.2
pip install rich==13.5.3
pip install loguru==0.7.2

echo.
echo ============================================
echo ✅ INSTALACIÓN COMPLETADA
echo ============================================
echo Verificando instalación...

REM Usar un archivo Python temporal para la verificación
echo import solana > verify_temp.py
echo import solders >> verify_temp.py
echo import anchorpy >> verify_temp.py
echo import web3 >> verify_temp.py
echo import aiohttp >> verify_temp.py
echo import aiogram >> verify_temp.py
echo import orca >> verify_temp.py
echo print('✅ Todas las dependencias instaladas correctamente') >> verify_temp.py

python verify_temp.py
del verify_temp.py

echo.
echo Para verificar completo, ejecuta: python check_env.py
pause