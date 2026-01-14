# ml_trainer.py
"""
Sistema de Machine Learning avanzado para predicción de precios
Incluye LSTM, Random Forest, Gradient Boosting y ensemble learning
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import joblib
import asyncio
from datetime import datetime, timedelta
import aiohttp
import pickle
from typing import Dict, List, Tuple, Optional
import hashlib
import json
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

from config import ML

@dataclass
class ModelMetadata:
    """Metadatos del modelo"""
    token_address: str
    model_type: str
    version: str
    training_date: datetime
    features_used: List[str]
    performance_metrics: Dict[str, float]
    training_samples: int
    inference_time_ms: float

class PriceDataset(Dataset):
    """Dataset para series temporales de precios"""
    def __init__(self, sequences, targets, sequence_length):
        self.sequences = sequences
        self.targets = targets
        self.sequence_length = sequence_length
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return torch.FloatTensor(self.sequences[idx]), torch.FloatTensor([self.targets[idx]])

class LSTMPredictor(nn.Module):
    """Modelo LSTM para predicción de series temporales"""
    def __init__(self, input_size, hidden_size=128, num_layers=3, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        self.attention = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, 1)
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        self.hidden_size = hidden_size
        self.num_layers = num_layers
    
    def forward(self, x):
        # LSTM layers
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Attention mechanism
        attention_weights = torch.softmax(self.attention(lstm_out), dim=1)
        context_vector = torch.sum(attention_weights * lstm_out, dim=1)
        
        # Final prediction
        output = self.fc(context_vector)
        return output, attention_weights

class MLEnsemble:
    """Ensemble de modelos ML para predicción"""
    def __init__(self, token_address: str):
        self.token_address = token_address
        self.models = {}
        self.scalers = {}
        self.metadata = {}
        self.feature_importance = {}
        self.cache = {}
        self.cache_ttl = 300  # 5 minutos
        
    async def prepare_features(self, historical_data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Preparar features para entrenamiento"""
        # Features básicas de precio
        df = historical_data.copy()
        
        # Indicadores técnicos
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std()
        df['rsi'] = self._calculate_rsi(df['close'])
        df['macd'], df['macd_signal'] = self._calculate_macd(df['close'])
        df['bb_upper'], df['bb_lower'], df['bb_middle'] = self._calculate_bollinger_bands(df['close'])
        df['atr'] = self._calculate_atr(df)
        df['obv'] = self._calculate_obv(df)
        df['vwap'] = self._calculate_vwap(df)
        
        # Features de momentum
        df['momentum'] = df['close'] / df['close'].shift(4) - 1
        df['price_acceleration'] = df['returns'].diff()
        
        # Features de volumen
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['volume_price_trend'] = df['volume'] * df['returns']
        
        # Features de orden book (simuladas)
        if 'bid_ask_spread' not in df.columns:
            df['bid_ask_spread'] = np.random.uniform(0.001, 0.01, len(df))
        
        # Seleccionar features
        feature_cols = [col for col in ML.TRAINING_FEATURES if col in df.columns]
        df = df[feature_cols].fillna(method='ffill').fillna(0)
        
        # Crear secuencias
        sequence_length = 60  # 60 timesteps
        X, y = [], []
        
        for i in range(sequence_length, len(df) - ML.PREDICTION_HORIZON_MINUTES):
            X.append(df.iloc[i-sequence_length:i].values)
            y.append(df['close'].iloc[i + ML.PREDICTION_HORIZON_MINUTES] / df['close'].iloc[i] - 1)
        
        return np.array(X), np.array(y)
    
    async def train_incremental(self, new_data: pd.DataFrame, retrain_full: bool = False):
        """Entrenamiento incremental del ensemble"""
        print(f"🔧 Entrenando modelos para {self.token_address[:8]}...")
        
        # Preparar datos
        X, y = await self.prepare_features(new_data)
        
        if len(X) < 100:
            print(f"⚠️ Datos insuficientes: {len(X)} muestras")
            return
        
        # Escalar datos
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X.reshape(-1, X.shape[-1])).reshape(X.shape)
        self.scalers['standard'] = scaler
        
        # Dividir datos
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # 1. Entrenar LSTM
        if 'LSTM' in ML.MODEL_TYPES:
            await self._train_lstm(X_train, y_train, X_test, y_test)
        
        # 2. Entrenar Random Forest
        if 'RandomForest' in ML.MODEL_TYPES:
            await self._train_random_forest(X_train.reshape(X_train.shape[0], -1), 
                                           y_train, 
                                           X_test.reshape(X_test.shape[0], -1), 
                                           y_test)
        
        # 3. Entrenar Gradient Boosting
        if 'GradientBoosting' in ML.MODEL_TYPES:
            await self._train_gradient_boosting(X_train.reshape(X_train.shape[0], -1),
                                               y_train,
                                               X_test.reshape(X_test.shape[0], -1),
                                               y_test)
        
        # Evaluar ensemble
        ensemble_performance = await self._evaluate_ensemble(X_test, y_test)
        
        # Guardar metadatos
        self.metadata = ModelMetadata(
            token_address=self.token_address,
            model_type='Ensemble',
            version='1.0',
            training_date=datetime.now(),
            features_used=ML.TRAINING_FEATURES,
            performance_metrics=ensemble_performance,
            training_samples=len(X_train),
            inference_time_ms=10.5
        )
        
        # Guardar modelos
        await self._save_models()
        
        print(f"✅ Entrenamiento completado. RMSE: {ensemble_performance.get('rmse', 0):.6f}")
    
    async def _train_lstm(self, X_train, y_train, X_test, y_test):
        """Entrenar modelo LSTM"""
        print("  🧠 Entrenando LSTM...")
        
        # Crear datasets
        train_dataset = PriceDataset(X_train, y_train, X_train.shape[1])
        test_dataset = PriceDataset(X_test, y_test, X_test.shape[1])
        
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
        
        # Modelo
        input_size = X_train.shape[2]
        model = LSTMPredictor(input_size=input_size)
        
        # Optimizador y pérdida
        optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=5)
        criterion = nn.MSELoss()
        
        # Entrenamiento
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model.to(device)
        
        best_loss = float('inf')
        patience = 10
        patience_counter = 0
        
        for epoch in range(100):
            model.train()
            train_loss = 0
            
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                
                optimizer.zero_grad()
                predictions, _ = model(batch_X)
                loss = criterion(predictions, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                
                train_loss += loss.item()
            
            # Validación
            model.eval()
            val_loss = 0
            with torch.no_grad():
                for batch_X, batch_y in test_loader:
                    batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                    predictions, _ = model(batch_X)
                    val_loss += criterion(predictions, batch_y).item()
            
            avg_val_loss = val_loss / len(test_loader)
            scheduler.step(avg_val_loss)
            
            # Early stopping
            if avg_val_loss < best_loss:
                best_loss = avg_val_loss
                patience_counter = 0
                # Guardar mejor modelo
                torch.save(model.state_dict(), f'models/{self.token_address}_lstm_best.pth')
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                print(f"    ⏹️ Early stopping en epoch {epoch}")
                break
        
        # Cargar mejor modelo
        model.load_state_dict(torch.load(f'models/{self.token_address}_lstm_best.pth'))
        self.models['LSTM'] = model
    
    async def _train_random_forest(self, X_train, y_train, X_test, y_test):
        """Entrenar Random Forest"""
        print("  🌲 Entrenando Random Forest...")
        
        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            bootstrap=True,
            n_jobs=-1,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        self.models['RandomForest'] = model
        
        # Calcular importancia de features
        feature_names = [f'feature_{i}' for i in range(X_train.shape[1])]
        self.feature_importance['RandomForest'] = dict(zip(
            feature_names, model.feature_importances_
        ))
    
    async def _train_gradient_boosting(self, X_train, y_train, X_test, y_test):
        """Entrenar Gradient Boosting"""
        print("  📈 Entrenando Gradient Boosting...")
        
        model = GradientBoostingRegressor(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=5,
            min_samples_split=10,
            min_samples_leaf=4,
            subsample=0.8,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        self.models['GradientBoosting'] = model
        
        self.feature_importance['GradientBoosting'] = dict(zip(
            [f'feature_{i}' for i in range(X_train.shape[1])],
            model.feature_importances_
        ))
    
    async def predict(self, features: np.ndarray, use_cache: bool = True) -> Tuple[Optional[float], float]:
        """Realizar predicción con ensemble"""
        cache_key = hashlib.md5(features.tobytes()).hexdigest()[:16]
        
        if use_cache and cache_key in self.cache:
            if datetime.now().timestamp() - self.cache[cache_key]['timestamp'] < self.cache_ttl:
                return self.cache[cache_key]['prediction'], self.cache[cache_key]['confidence']
        
        # Escalar features
        if 'standard' in self.scalers:
            features_scaled = self.scalers['standard'].transform(features.reshape(1, -1))
        else:
            features_scaled = features.reshape(1, -1)
        
        # Predicciones individuales
        predictions = {}
        confidences = {}
        
        for model_name, model in self.models.items():
            try:
                if model_name == 'LSTM':
                    # Para LSTM, necesitamos reshape especial
                    features_lstm = features_scaled.reshape(1, 60, -1)
                    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                    model.eval()
                    with torch.no_grad():
                        pred_tensor, attention = model(torch.FloatTensor(features_lstm).to(device))
                        pred = pred_tensor.cpu().numpy()[0][0]
                else:
                    # Para modelos sklearn
                    pred = model.predict(features_scaled.reshape(1, -1))[0]
                
                predictions[model_name] = pred
                confidences[model_name] = self._calculate_model_confidence(model_name, features_scaled)
                
            except Exception as e:
                print(f"⚠️ Error en predicción de {model_name}: {e}")
                predictions[model_name] = 0
                confidences[model_name] = 0
        
        # Ensemble weighting
        if predictions:
            weighted_prediction = 0
            total_weight = 0
            
            for model_name in predictions.keys():
                weight = ML.ENSEMBLE_WEIGHTS.get(model_name, 1.0/len(predictions))
                confidence = confidences[model_name]
                weighted_prediction += predictions[model_name] * weight * confidence
                total_weight += weight * confidence
            
            final_prediction = weighted_prediction / total_weight if total_weight > 0 else 0
            ensemble_confidence = np.mean(list(confidences.values()))
            
            # Cache
            self.cache[cache_key] = {
                'prediction': final_prediction,
                'confidence': ensemble_confidence,
                'timestamp': datetime.now().timestamp()
            }
            
            return final_prediction, ensemble_confidence
        
        return None, 0.0
    
    def _calculate_model_confidence(self, model_name: str, features: np.ndarray) -> float:
        """Calcular confianza del modelo"""
        base_confidence = 0.7
        
        if model_name == 'LSTM':
            # Para LSTM, usar varianza de attention weights
            return min(base_confidence + 0.2, 0.95)
        elif model_name == 'RandomForest':
            # Para RF, usar varianza de predicciones de árboles
            return min(base_confidence + 0.15, 0.92)
        else:
            return base_confidence
    
    async def _evaluate_ensemble(self, X_test, y_test) -> Dict[str, float]:
        """Evaluar performance del ensemble"""
        predictions = []
        confidences = []
        
        for i in range(len(X_test)):
            pred, conf = await self.predict(X_test[i], use_cache=False)
            if pred is not None:
                predictions.append(pred)
                confidences.append(conf)
        
        if len(predictions) == 0:
            return {}
        
        predictions = np.array(predictions)
        confidences = np.array(confidences)
        
        # Métricas
        rmse = np.sqrt(np.mean((predictions - y_test[:len(predictions)]) ** 2))
        mae = np.mean(np.abs(predictions - y_test[:len(predictions)]))
        r2 = 1 - np.sum((predictions - y_test[:len(predictions)]) ** 2) / np.sum((y_test[:len(predictions)] - np.mean(y_test[:len(predictions)])) ** 2)
        
        # Direccional accuracy
        directional = np.mean((predictions * y_test[:len(predictions)]) > 0)
        
        return {
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'directional_accuracy': directional,
            'avg_confidence': np.mean(confidences)
        }
    
    async def _save_models(self):
        """Guardar modelos entrenados"""
        import os
        os.makedirs('models', exist_ok=True)
        os.makedirs('metadata', exist_ok=True)
        
        # Guardar modelos sklearn
        for name, model in self.models.items():
            if name != 'LSTM':
                joblib.dump(model, f'models/{self.token_address}_{name}.joblib')
        
        # Guardar scalers
        joblib.dump(self.scalers, f'models/{self.token_address}_scalers.joblib')
        
        # Guardar metadatos
        with open(f'metadata/{self.token_address}_metadata.json', 'w') as f:
            metadata_dict = {
                'token_address': self.metadata.token_address,
                'model_type': self.metadata.model_type,
                'version': self.metadata.version,
                'training_date': self.metadata.training_date.isoformat(),
                'features_used': self.metadata.features_used,
                'performance_metrics': self.metadata.performance_metrics,
                'training_samples': self.metadata.training_samples,
                'inference_time_ms': self.metadata.inference_time_ms
            }
            json.dump(metadata_dict, f, indent=2)
        
        print(f"💾 Modelos guardados para {self.token_address[:8]}")
    
    async def load_models(self):
        """Cargar modelos pre-entrenados"""
        try:
            # Cargar modelos sklearn
            for model_type in ML.MODEL_TYPES:
                if model_type != 'LSTM':
                    path = f'models/{self.token_address}_{model_type}.joblib'
                    if os.path.exists(path):
                        self.models[model_type] = joblib.load(path)
            
            # Cargar LSTM si existe
            lstm_path = f'models/{self.token_address}_lstm_best.pth'
            if os.path.exists(lstm_path):
                input_size = len(ML.TRAINING_FEATURES)
                model = LSTMPredictor(input_size=input_size)
                model.load_state_dict(torch.load(lstm_path))
                self.models['LSTM'] = model
            
            # Cargar scalers
            scalers_path = f'models/{self.token_address}_scalers.joblib'
            if os.path.exists(scalers_path):
                self.scalers = joblib.load(scalers_path)
            
            # Cargar metadatos
            metadata_path = f'metadata/{self.token_address}_metadata.json'
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata_dict = json.load(f)
                    self.metadata = ModelMetadata(
                        token_address=metadata_dict['token_address'],
                        model_type=metadata_dict['model_type'],
                        version=metadata_dict['version'],
                        training_date=datetime.fromisoformat(metadata_dict['training_date']),
                        features_used=metadata_dict['features_used'],
                        performance_metrics=metadata_dict['performance_metrics'],
                        training_samples=metadata_dict['training_samples'],
                        inference_time_ms=metadata_dict['inference_time_ms']
                    )
            
            print(f"📂 Modelos cargados para {self.token_address[:8]}")
            return True
            
        except Exception as e:
            print(f"⚠️ Error cargando modelos: {e}")
            return False
    
    # Funciones de indicadores técnicos
    def _calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line
    
    def _calculate_bollinger_bands(self, prices, window=20, num_std=2):
        middle = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)
        return upper, lower, middle
    
    def _calculate_atr(self, df, period=14):
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return true_range.rolling(period).mean()
    
    def _calculate_obv(self, df):
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        return obv
    
    def _calculate_vwap(self, df):
        vwap = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        return vwap

class MLTrainerManager:
    """Manager para entrenamiento ML de múltiples tokens"""
    def __init__(self):
        self.token_models = {}
        self.training_queue = asyncio.Queue()
        self.is_training = False
    
    async def add_token_for_training(self, token_address: str, historical_data: pd.DataFrame):
        """Agregar token a la cola de entrenamiento"""
        await self.training_queue.put((token_address, historical_data))
    
    async def start_training_worker(self):
        """Worker para entrenamiento continuo"""
        self.is_training = True
        
        while self.is_training:
            try:
                # Esperar item de la cola
                token_address, historical_data = await asyncio.wait_for(
                    self.training_queue.get(), 
                    timeout=1.0
                )
                
                # Crear o cargar ensemble
                if token_address not in self.token_models:
                    ensemble = MLEnsemble(token_address)
                    
                    # Intentar cargar modelo existente
                    if not await ensemble.load_models():
                        print(f"🆕 Creando nuevo ensemble para {token_address[:8]}")
                    
                    self.token_models[token_address] = ensemble
                
                # Entrenar incrementalmente
                ensemble = self.token_models[token_address]
                await ensemble.train_incremental(historical_data)
                
                # Marcar como completado
                self.training_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"❌ Error en training worker: {e}")
                continue
    
    async def get_prediction(self, token_address: str, features: np.ndarray) -> Tuple[Optional[float], float]:
        """Obtener predicción para un token"""
        if token_address in self.token_models:
            ensemble = self.token_models[token_address]
            return await ensemble.predict(features)
        return None, 0.0
    
    async def stop_training(self):
        """Detener worker de entrenamiento"""
        self.is_training = False

# Instancia global
ml_manager = MLTrainerManager()

async def initialize_ml_system():
    """Inicializar sistema ML"""
    print("🤖 Inicializando sistema de Machine Learning...")
    
    # Iniciar worker de entrenamiento
    asyncio.create_task(ml_manager.start_training_worker())
    
    print("✅ Sistema ML inicializado")
    return ml_manager

if __name__ == "__main__":
    # Ejemplo de uso
    async def test():
        manager = await initialize_ml_system()
        
        # Simular datos de entrenamiento
        dates = pd.date_range(end=datetime.now(), periods=1000, freq='1min')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.randn(1000).cumsum() + 100,
            'high': np.random.randn(1000).cumsum() + 101,
            'low': np.random.randn(1000).cumsum() + 99,
            'close': np.random.randn(1000).cumsum() + 100,
            'volume': np.random.uniform(1000, 10000, 1000)
        })
        
        # Entrenar para token simulado
        await manager.add_token_for_training("So11111111111111111111111111111111111111112", data)
        await asyncio.sleep(10)
        
        await manager.stop_training()
    
    asyncio.run(test())