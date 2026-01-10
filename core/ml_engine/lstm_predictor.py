# core/ml_engine/lstm_predictor.py
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict
from pathlib import Path
import joblib
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class MultiTimeframeLSTM(nn.Module):
    """LSTM para múltiples timeframes"""
    
    def __init__(self, 
                 input_size: int, 
                 hidden_size: int = 128,
                 num_layers: int = 3,
                 num_timeframes: int = 3,
                 dropout: float = 0.2):
        super(MultiTimeframeLSTM, self).__init__()
        
        self.num_timeframes = num_timeframes
        self.hidden_size = hidden_size
        
        # LSTM para cada timeframe
        self.lstms = nn.ModuleList([
            nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                dropout=dropout if num_layers > 1 else 0,
                batch_first=True,
                bidirectional=True
            ) for _ in range(num_timeframes)
        ])
        
        # Atención entre timeframes
        self.cross_timeframe_attention = nn.MultiheadAttention(
            embed_dim=hidden_size * 2,
            num_heads=4,
            dropout=dropout,
            batch_first=True
        )
        
        # Capas de fusión
        self.fusion_fc = nn.Linear(hidden_size * 2 * num_timeframes, hidden_size * 2)
        self.fusion_bn = nn.BatchNorm1d(hidden_size * 2)
        
        # Capas de predicción
        self.fc1 = nn.Linear(hidden_size * 2, 64)
        self.bn1 = nn.BatchNorm1d(64)
        self.dropout1 = nn.Dropout(dropout)
        
        self.fc2 = nn.Linear(64, 32)
        self.bn2 = nn.BatchNorm1d(32)
        self.dropout2 = nn.Dropout(dropout)
        
        self.fc3 = nn.Linear(32, 2)  # Probabilidad de compra/venta
        self.softmax = nn.Softmax(dim=1)
        
    def forward(self, x_timeframes: List[torch.Tensor]) -> torch.Tensor:
        """
        x_timeframes: Lista de tensores [batch, seq_len, features] para cada timeframe
        """
        lstm_outputs = []
        
        # Procesar cada timeframe
        for i, lstm in enumerate(self.lstms):
            lstm_out, _ = lstm(x_timeframes[i])
            # Tomar último paso
            lstm_outputs.append(lstm_out[:, -1, :])
        
        # Concatenar outputs
        combined = torch.cat(lstm_outputs, dim=1)
        
        # Fusión
        x = self.fusion_fc(combined)
        x = self.fusion_bn(x)
        x = torch.relu(x)
        
        # Capas fully connected
        x = self.fc1(x)
        x = self.bn1(x)
        x = torch.relu(x)
        x = self.dropout1(x)
        
        x = self.fc2(x)
        x = self.bn2(x)
        x = torch.relu(x)
        x = self.dropout2(x)
        
        x = self.fc3(x)
        probabilities = self.softmax(x)
        
        return probabilities

class LSTMPredictor:
    """Predictor LSTM para trading"""
    
    def __init__(self, config):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.scalers = {}
        self.feature_columns = None
        
        # Cargar modelo si existe
        self.load_model()
    
    def prepare_features(self, 
                        ohlcv_data: Dict[str, pd.DataFrame]) -> List[np.ndarray]:
        """
        Prepara características para múltiples timeframes
        """
        features_timeframes = []
        
        for timeframe, df in ohlcv_data.items():
            if df.empty:
                continue
            
            # Calcular indicadores técnicos
            df_features = self._calculate_technical_indicators(df)
            
            # Normalizar
            if timeframe not in self.scalers:
                self.scalers[timeframe] = StandardScaler()
                scaled = self.scalers[timeframe].fit_transform(df_features)
            else:
                scaled = self.scalers[timeframe].transform(df_features)
            
            # Crear secuencias
            sequences = self._create_sequences(scaled, self.config.ml_sequence_length)
            features_timeframes.append(sequences)
        
        return features_timeframes
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula todos los indicadores técnicos"""
        df = df.copy()
        
        # 1. Precios y retornos
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['price_acceleration'] = df['returns'].diff()
        
        # 2. RSI
        df['rsi'] = self._calculate_rsi(df['close'])
        
        # 3. MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = self._calculate_macd(df['close'])
        
        # 4. Bollinger Bands
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # 5. Volumen
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['volume_acceleration'] = df['volume_ratio'].diff()
        
        # 6. Velocidad y aceleración de precios
        df['price_velocity'] = df['returns'].rolling(5).mean()
        df['price_acceleration'] = df['price_velocity'].diff()
        
        # 7. Soporte y resistencia
        df['support'], df['resistance'] = self._calculate_support_resistance(df)
        
        # 8. Ratio riesgo/beneficio
        df['risk_reward_ratio'] = self._calculate_risk_reward_ratio(df)
        
        return df.dropna()
    
    def predict_probabilities(self, 
                            asset_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Predice probabilidades de éxito para un activo
        Returns: {'buy_probability': 0.85, 'confidence': 0.92, 'timeframe_scores': {...}}
        """
        try:
            if self.model is None:
                return {'buy_probability': 0.5, 'confidence': 0.5, 'timeframe_scores': {}}
            
            # Preparar características
            features = self.prepare_features(asset_data)
            
            if not features or len(features[0]) == 0:
                return {'buy_probability': 0.5, 'confidence': 0.5, 'timeframe_scores': {}}
            
            # Convertir a tensores
            tensors = [torch.FloatTensor(f[-1:]).to(self.device) for f in features]  # Última secuencia
            
            # Predecir
            self.model.eval()
            with torch.no_grad():
                probabilities = self.model(tensors)
                buy_prob = probabilities[0, 1].item()  # Probabilidad de compra
            
            # Calcular confianza basada en consistencia entre timeframes
            timeframe_scores = {}
            for i, (timeframe, _) in enumerate(asset_data.items()):
                if i < len(features):
                    # Score basado en señal clara
                    signal_strength = abs(features[i][-1, -1, 0])  # Último retorno
                    timeframe_scores[timeframe] = min(signal_strength * 10, 1.0)
            
            confidence = np.mean(list(timeframe_scores.values())) if timeframe_scores else 0.5
            
            return {
                'buy_probability': buy_prob,
                'confidence': confidence,
                'timeframe_scores': timeframe_scores,
                'model_used': True
            }
            
        except Exception as e:
            print(f"Error en predicción: {e}")
            return {'buy_probability': 0.5, 'confidence': 0.5, 'timeframe_scores': {}, 'error': str(e)}
    
    def train_incremental(self, 
                         new_data: Dict[str, Dict[str, pd.DataFrame]],
                         labels: Dict[str, int]):
        """
        Entrenamiento incremental con nuevos datos
        labels: 1 para operación exitosa, 0 para fallida
        """
        try:
            # Preparar datos de entrenamiento
            X_timeframes = []
            y = []
            
            for asset_id, timeframes_data in new_data.items():
                features = self.prepare_features(timeframes_data)
                if features and len(features[0]) > 0:
                    # Tomar la última secuencia de cada timeframe
                    seqs = [f[-1:] for f in features]
                    X_timeframes.append(seqs)
                    y.append(labels.get(asset_id, 0))
            
            if len(y) < 10:  # Mínimo muestras para entrenar
                return False
            
            # Entrenar modelo
            self.model.train()
            optimizer = optim.Adam(self.model.parameters(), lr=0.001)
            criterion = nn.CrossEntropyLoss()
            
            for epoch in range(10):  # Pocas épocas para incremental
                total_loss = 0
                
                for i in range(len(X_timeframes)):
                    # Preparar batch
                    batch_X = [
                        torch.FloatTensor(X_timeframes[i][j]).to(self.device)
                        for j in range(len(self.config.trading.active_timeframes))
                    ]
                    batch_y = torch.LongTensor([y[i]]).to(self.device)
                    
                    # Forward
                    optimizer.zero_grad()
                    outputs = self.model(batch_X)
                    loss = criterion(outputs, batch_y)
                    
                    # Backward
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    optimizer.step()
                    
                    total_loss += loss.item()
                
                print(f"Epoch {epoch+1}, Loss: {total_loss/len(X_timeframes):.4f}")
            
            # Guardar modelo
            self.save_model()
            
            return True
            
        except Exception as e:
            print(f"Error en entrenamiento incremental: {e}")
            return False
    
    def save_model(self):
        """Guarda modelo y scalers"""
        if self.model:
            torch.save(self.model.state_dict(), self.config.models_dir / "lstm_model.pth")
        
        # Guardar scalers
        for timeframe, scaler in self.scalers.items():
            joblib.dump(scaler, self.config.models_dir / f"scaler_{timeframe}.pkl")
    
    def load_model(self):
        """Carga modelo existente"""
        model_path = self.config.models_dir / "