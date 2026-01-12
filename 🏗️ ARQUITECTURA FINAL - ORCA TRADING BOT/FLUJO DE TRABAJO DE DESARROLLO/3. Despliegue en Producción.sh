# Usando Docker
docker-compose build
docker-compose up -d

# Monitoreo
docker-compose logs -f orca-bot

# Backup
python scripts/backup.py --full

# Actualización
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d