# Clonar repositorio
git clone https://github.com/edalmebo65/orcabot_deepseek.git
cd orcabot_deepseek

# Configurar entorno
conda create -n orcabot python=3.10
conda activate orcabot

# Instalar dependencias
pip install -r requirements.txt -r requirements-dev.txt

# Construir módulo Rust
python scripts/build_rust.py

# Ejecutar tests
pytest tests/ -v

# Ejecutar bot en modo desarrollo
python python/main.py --mode=dev --testnet