# 1. Copiar template
cp .env.example .env

# 2. Editar .env con tus credenciales
nano .env  # o usar tu editor favorito

# 3. Ejecutar script de inicialización
chmod +x scripts/init_bot.sh
./scripts/init_bot.sh

# 4. Ejecutar el bot
python main.py