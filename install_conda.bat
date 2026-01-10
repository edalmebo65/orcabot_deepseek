@echo off
echo ============================================
echo INSTALACION ORCA BOT - CONDA ENVIRONMENT
echo ============================================

echo 1. Activando entorno conda...
call conda activate orcabot

echo 2. Verificando Python version...
python --version

echo 3. Instalando via conda (opcional, mas estable)...
conda install -c conda-forge numpy pandas scikit-learn matplotlib cryptography -y

echo 4. Instalando dependencias Python...
pip install --upgrade pip setuptools wheel

echo 5. Instalando Solana stack...
pip install solana==0.30.1 solders==0.18.0 anchorpy==0.16.0

echo 6. Instalando orca-py...
pip install git+https://github.com/orca-so/orca-py.git

echo 7. Instalando Web3 y blockchain...
pip install web3==6.11.1 ccxt==4.1.36

echo 8. Instalando async y networking...
pip install aiohttp==3.9.1 aiogram==2.25.1

echo 9. Instalando utilidades...
pip install python-dotenv pydantic rich loguru

echo.
echo ============================================
echo ✅ INSTALACION COMPLETADA
echo ============================================
echo Comandos:
echo   conda activate orcabot
echo   python main.py
echo   python check_env.py
echo ============================================
pause