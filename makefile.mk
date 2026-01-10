# Makefile
.PHONY: help install setup test run clean monitor

help:
	@echo "Orca Trading Bot - Comandos disponibles:"
	@echo "  make install     - Instala dependencias"
	@echo "  make setup       - Configura entorno"
	@echo "  make test        - Ejecuta pruebas"
	@echo "  make run         - Inicia el bot"
	@echo "  make monitor     - Inicia monitor de performance"
	@echo "  make clean       - Limpia archivos temporales"
	@echo "  make backup      - Crea backup de configuración"

install:
	pip install -r requirements.txt
	pip install -e .

setup:
	@echo "🔧 Configurando entorno..."
	@read -p "¿Están exportadas las variables de sistema? (y/N): " confirm; \
	if [ "$$confirm" != "y" ]; then \
		echo "❌ Exporta las variables primero:"; \
		echo "   export HELIUS_RPC_URL=..."; \
		echo "   export PHANTOM_WALLET=..."; \
		exit 1; \
	fi
	python scripts/setup_environment.py

test:
	@echo "🧪 Ejecutando pruebas..."
	python -m pytest tests/ -v
	python scripts/test_blockchain.py

run:
	@echo "🚀 Iniciando Orca Bot..."
	python main.py

monitor:
	@echo "📊 Iniciando monitor..."
	python -m utils.performance_monitor

clean:
	@echo "🧹 Limpiando archivos temporales..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf logs/*.log
	rm -rf data/live/*
	rm -rf .pytest_cache

backup:
	@echo "💾 Creando backup..."
	tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz \
		config.py \
		.env.encrypted \
		state/ \
		models/ \
		--exclude="*.pyc" \
		--exclude="__pycache__"
	@echo "✅ Backup creado"

docker-build:
	@echo "🐳 Construyendo imagen Docker..."
	docker build -t orca-bot .

docker-run:
	@echo "🐳 Ejecutando en Docker..."
	docker run -d --name orca-bot \
		--env-file .env \
		-v $(pwd)/data:/app/data \
		-v $(pwd)/logs:/app/logs \
		orca-bot

update:
	@echo "🔄 Actualizando bot..."
	git pull origin main
	pip install -r requirements.txt --upgrade
	@echo "✅ Actualización completada"