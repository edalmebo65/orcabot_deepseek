# Modo normal
python main.py

# Modo debug
LOG_LEVEL=DEBUG python main.py

# Con monitorización
python -m utils.performance_monitor & python main.py