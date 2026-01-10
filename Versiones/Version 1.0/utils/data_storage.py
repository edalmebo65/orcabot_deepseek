# utils/data_storage.py
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import pickle
import gzip
import json
from typing import Dict, List, Optional

class HistoricalDataStorage:
    def __init__(self, historico_dir: Path):
        self.historico_dir = historico_dir
        self._setup_structure()
    
    def _setup_structure(self):
        """Crea estructura de directorios organizada"""
        subdirs = [
            "ohlcv",
            "ml_features",
            "trades",
            "models",
            "performance",
            "market_data"
        ]
        
        for subdir in subdirs:
            (self.historico_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    def save_ohlcv(self, 
                   symbol: str, 
                   timeframe: str,
                   data: pd.DataFrame,
                   compress: bool = True):
        """Guarda datos OHLCV de forma incremental"""
        filename = f"{symbol}_{timeframe}_{datetime.now().strftime('%Y%m')}.csv"
        filepath = self.historico_dir / "ohlcv" / filename
        
        # Cargar datos existentes si existen
        existing_data = None
        if filepath.exists():
            existing_data = pd.read_csv(filepath, index_col=0, parse_dates=True)
        
        # Combinar y eliminar duplicados
        if existing_data is not None:
            combined = pd.concat([existing_data, data])
            combined = combined[~combined.index.duplicated(keep='last')]
        else:
            combined = data
        
        # Guardar
        if compress:
            with gzip.open(f"{filepath}.gz", 'wt') as f:
                combined.to_csv(f)
        else:
            combined.to_csv(filepath)
        
        # Guardar metadatos
        self._save_metadata(symbol, timeframe, combined)
    
    def save_trade_record(self, trade_data: Dict):
        """Guarda registro detallado de operación"""
        trades_dir = self.historico_dir / "trades"
        
        # Archivo diario
        daily_file = trades_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        trade_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "trade_id": trade_data.get("trade_id"),
            "symbol": trade_data.get("symbol"),
            "side": trade_data.get("side"),
            "entry_price": trade_data.get("entry_price"),
            "exit_price": trade_data.get("exit_price"),
            "size": trade_data.get("size"),
            "pnl": trade_data.get("pnl"),
            "pnl_percentage": trade_data.get("pnl_percentage"),
            "fees": trade_data.get("fees"),
            "stop_loss": trade_data.get("stop_loss"),
            "take_profit": trade_data.get("take_profit"),
            "ml_confidence": trade_data.get("ml_confidence"),
            "risk_score": trade_data.get("risk_score"),
        }
        
        with open(daily_file, 'a') as f:
            f.write(json.dumps(trade_record) + '\n')
    
    def load_training_data(self, 
                          symbol: str,
                          lookback_days: int = 365) -> pd.DataFrame:
        """Carga datos para entrenamiento ML"""
        # Cargar todos los archivos OHLCV del símbolo
        ohlcv_dir = self.historico_dir / "ohlcv"
        pattern = f"{symbol}_*_*.csv"
        
        data_frames = []
        for file in ohlcv_dir.glob(pattern):
            # Verificar fecha del archivo
            file_date_str = file.stem.split('_')[-1]
            file_date = datetime.strptime(file_date_str, '%Y%m')
            
            if (datetime.now() - file_date).days <= lookback_days:
                df = pd.read_csv(file, index_col=0, parse_dates=True)
                data_frames.append(df)
        
        if not data_frames:
            return pd.DataFrame()
        
        return pd.concat(data_frames).sort_index()