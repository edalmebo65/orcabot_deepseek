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
python -c "
import solana
import solders
import anchorpy
import web3
import aiohttp
import aiogram
import orca
print('✅ Todas las dependencias instaladas correctamente')
"
pause