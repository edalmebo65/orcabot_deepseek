# core/ml/lstm_model.py
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from typing import Tuple
import joblib
from pathlib import Path

class LSTMTradingModel(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 128, 
                 num_layers: int = 3, dropout: float = 0.2):
        super(LSTMTradingModel, self).__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True,
            bidirectional=True
        )
        
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size*2,
            num_heads=4,
            dropout=dropout
        )
        
        self.fc1 = nn.Linear(hidden_size*2, 64)
        self.bn1 = nn.BatchNorm1d(64)
        self.dropout1 = nn.Dropout(dropout)
        
        self.fc2 = nn.Linear(64, 32)
        self.bn2 = nn.BatchNorm1d(32)
        self.dropout2 = nn.Dropout(dropout)
        
        self.fc3 = nn.Linear(32, 3)  # Compra, Venta, Hold
        self.softmax = nn.Softmax(dim=1)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Atención sobre secuencia temporal
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        
        # Usar último paso con atención
        last_step = attn_out[:, -1, :]
        
        # Capas fully connected
        x = self.fc1(last_step)
        x = self.bn1(x)
        x = torch.relu(x)
        x = self.dropout1(x)
        
        x = self.fc2(x)
        x = self.bn2(x)
        x = torch.relu(x)
        x = self.dropout2(x)
        
        x = self.fc3(x)
        return self.softmax(x)

class MLPipeline:
    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    def prepare_features(self, ohlcv_df: pd.DataFrame) -> np.ndarray:
        """
        Calcula todas las características técnicas
        """
        df = ohlcv_df.copy()
        
        # 1. Precios normalizados
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # 2. Indicadores de momentum
        df['rsi'] = self._calculate_rsi(df['close'])
        df['macd'], df['macd_signal'] = self._calculate_macd(df['close'])
        
        # 3. Volatilidad
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # 4. Aceleración y cambio
        df['acceleration'] = df['returns'].diff()
        df['velocity_ratio'] = df['returns'] / df['returns'].rolling(20).std()
        
        # 5. Volumen
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['obv'] = self._calculate_obv(df['close'], df['volume'])
        
        # 6. Patrones de velas
        df['candle_body'] = abs(df['close'] - df['open'])
        df['candle_ratio'] = df['candle_body'] / (df['high'] - df['low'])
        
        # Eliminar NaNs
        df = df.dropna()
        
        return df.values
    
    def train_incremental(self, new_data: pd.DataFrame):
        """
        Entrenamiento incremental con nuevos datos
        """
        # Cargar modelo existente o crear nuevo
        model_path = self.model_dir / "lstm_model.pth"
        if model_path.exists():
            self.model.load_state_dict(torch.load(model_path))
        
        # Preparar datos
        features = self.prepare_features(new_data)
        
        # Dividir en secuencias temporales
        sequences = self._create_sequences(features, seq_length=60)
        
        # Entrenamiento
        self.model.train()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss()
        
        for epoch in range(10):  # Pocas épocas para incremental
            for batch in sequences:
                inputs = torch.FloatTensor(batch).to(self.device)
                targets = self._generate_targets(batch)
                
                optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
        
        # Guardar incrementalmente
        torch.save(self.model.state_dict(), model_path)
        
        # Guardar datos históricos
        self._save_historical_data(new_data)