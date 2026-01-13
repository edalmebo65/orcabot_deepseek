#!/usr/bin/env python3
"""
OrcaBot v3.5 - Integrado completamente con config.py
"""
import json
import logging
import asyncio
import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from collections import deque
import schedule
import sys
import os

# Importar integrador de configuración
sys.path.append('.')
from config_manager_integrated import config_integrator
from profit_optimizer import ProfitOptimizer, ProfitStrategy
from technical_indicators import tech_indicators

# Configuración inicial desde config_integrator
config = config_integrator.get_config()

# Configurar logging usando config.py
log_level = config.get('logging', {}).get('level', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.get('directories', {}).get('logs', 'logs') + '/bot_optimized.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Validar configuración
is_valid, errors = config_integrator.validate_config()
if not is_valid:
    logger.error("❌ Errores de configuración:")
    for error in errors:
        logger.error(f"  • {error}")
    logger.error("Corrige config.py antes de continuar")
    sys.exit(1)

# Imprimir reporte de configuración
logger.info(config_integrator.generate_config_report())

# Resto del código main_integrated.py continúa igual...
# [Todo el código anterior permanece igual, solo cambiando cómo se accede a la configuración]