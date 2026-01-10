# core/ml_engine/training_pipeline.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import joblib
from pathlib import Path
import json

from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import torch
import torch.nn as nn

class TrainingPipeline:
    """Pipeline de entrenamiento para modelos ML"""
    
    def __init__(self, config):
        self.config = config
        self.models_dir = config.models_dir
        
        # Configuración de entrenamiento
        self.training_config = {
            'test_size': 0.2,
            'validation_size': 0.1,
            'random_state': 42,
            'n_splits': 5,
            'sequence_length': config.ml_sequence_length,
            'batch_size': 32,
            'epochs': 50,
            'learning_rate': 0.001,
            'patience': 10  # Early stopping patience
        }
        
        # Modelos disponibles
        self.models = {}
        self.scalers = {}
        self.feature_importances = {}
    
    def prepare_training_data(self,
                            feature_sets: List[Dict],
                            test_size: float = None) -> Dict:
        """
        Prepara datos para entrenamiento
        """
        if test_size is None:
            test_size = self.training_config['test_size']
        
        # Combinar todos los feature sets
        X_list, y_list = [], []
        
        for feature_set in feature_sets:
            if 'features' in feature_set and 'labels' in feature_set:
                X_list.append(feature_set['features'])
                y_list.append(feature_set['labels'])
        
        if not X_list:
            raise ValueError("No training data available")
        
        X = np.concatenate(X_list, axis=0)
        y = np.concatenate(y_list, axis=0)
        
        # Dividir en train/validation/test
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, 
            test_size=test_size,
            random_state=self.training_config['random_state'],
            shuffle=False  # No shuffle para series temporales
        )
        
        validation_size = self.training_config['validation_size']
        val_ratio = validation_size / (1 - test_size)
        
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp,
            test_size=val_ratio,
            random_state=self.training_config['random_state'],
            shuffle=False
        )
        
        # Escalar características
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        X_test_scaled = scaler.transform(X_test)
        
        self.scalers['default'] = scaler
        
        return {
            'X_train': X_train_scaled,
            'X_val': X_val_scaled,
            'X_test': X_test_scaled,
            'y_train': y_train,
            'y_val': y_val,
            'y_test': y_test,
            'scaler': scaler,
            'data_stats': {
                'train_samples': len(X_train),
                'val_samples': len(X_val),
                'test_samples': len(X_test),
                'positive_ratio_train': np.mean(y_train),
                'positive_ratio_val': np.mean(y_val),
                'positive_ratio_test': np.mean(y_test)
            }
        }
    
    def train_lstm_model(self,
                        training_data: Dict,
                        input_size: int,
                        hidden_size: int = 128,
                        num_layers: int = 3) -> nn.Module:
        """
        Entrena modelo LSTM
        """
        from .lstm_predictor import MultiTimeframeLSTM
        
        # Crear secuencias para LSTM
        X_train_seq, y_train_seq = self._create_sequences(
            training_data['X_train'],
            training_data['y_train'],
            self.training_config['sequence_length']
        )
        
        X_val_seq, y_val_seq = self._create_sequences(
            training_data['X_val'],
            training_data['y_val'],
            self.training_config['sequence_length']
        )
        
        # Inicializar modelo
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = MultiTimeframeLSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            num_timeframes=1,  # Por ahora un solo timeframe
            dropout=0.2
        ).to(device)
        
        # Configurar entrenamiento
        criterion = nn.BCELoss()  # Binary Cross Entropy
        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=self.training_config['learning_rate']
        )
        
        # Early stopping
        best_val_loss = float('inf')
        patience_counter = 0
        
        # Entrenamiento
        train_losses, val_losses = [], []
        
        for epoch in range(self.training_config['epochs']):
            # Modo entrenamiento
            model.train()
            train_loss = 0.0
            
            # Mini-batch training
            for i in range(0, len(X_train_seq), self.training_config['batch_size']):
                batch_X = X_train_seq[i:i+self.training_config['batch_size']]
                batch_y = y_train_seq[i:i+self.training_config['batch_size']]
                
                # Convertir a tensores
                X_tensor = torch.FloatTensor(batch_X).to(device)
                y_tensor = torch.FloatTensor(batch_y).to(device).unsqueeze(1)
                
                # Forward pass
                optimizer.zero_grad()
                outputs = model([X_tensor])  # Lista con un solo tensor
                loss = criterion(outputs, y_tensor)
                
                # Backward pass
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                
                train_loss += loss.item()
            
            avg_train_loss = train_loss / (len(X_train_seq) / self.training_config['batch_size'])
            train_losses.append(avg_train_loss)
            
            # Validación
            model.eval()
            val_loss = 0.0
            
            with torch.no_grad():
                for i in range(0, len(X_val_seq), self.training_config['batch_size']):
                    batch_X = X_val_seq[i:i+self.training_config['batch_size']]
                    batch_y = y_val_seq[i:i+self.training_config['batch_size']]
                    
                    X_tensor = torch.FloatTensor(batch_X).to(device)
                    y_tensor = torch.FloatTensor(batch_y).to(device).unsqueeze(1)
                    
                    outputs = model([X_tensor])
                    loss = criterion(outputs, y_tensor)
                    val_loss += loss.item()
            
            avg_val_loss = val_loss / (len(X_val_seq) / self.training_config['batch_size'])
            val_losses.append(avg_val_loss)
            
            # Early stopping check
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                patience_counter = 0
                # Guardar mejor modelo
                self._save_model(model, 'lstm_best')
            else:
                patience_counter += 1
                if patience_counter >= self.training_config['patience']:
                    print(f"Early stopping at epoch {epoch+1}")
                    break
            
            # Log progreso
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{self.training_config['epochs']}, "
                      f"Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")
        
        # Cargar mejor modelo
        model = self._load_model('lstm_best')
        
        # Evaluar en test set
        test_metrics = self.evaluate_model(model, training_data['X_test'], training_data['y_test'])
        
        # Guardar métricas
        training_metrics = {
            'train_losses': train_losses,
            'val_losses': val_losses,
            'test_metrics': test_metrics,
            'num_epochs': epoch + 1,
            'best_val_loss': best_val_loss,
            'input_size': input_size,
            'hidden_size': hidden_size,
            'num_layers': num_layers
        }
        
        self._save_training_metrics(training_metrics, 'lstm')
        
        return model
    
    def _create_sequences(self, X: np.ndarray, y: np.ndarray, seq_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """Crea secuencias para modelos de series temporales"""
        X_seq, y_seq = [], []
        
        for i in range(len(X) - seq_length):
            X_seq.append(X[i:i+seq_length])
            y_seq.append(y[i+seq_length])
        
        return np.array(X_seq), np.array(y_seq)
    
    def train_random_forest(self, training_data: Dict) -> any:
        """
        Entrena modelo Random Forest (fallback)
        """
        from sklearn.ensemble import RandomForestClassifier
        
        # Inicializar modelo
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=self.training_config['random_state'],
            n_jobs=-1
        )
        
        # Entrenar
        model.fit(training_data['X_train'], training_data['y_train'])
        
        # Evaluar
        val_score = model.score(training_data['X_val'], training_data['y_val'])
        test_score = model.score(training_data['X_test'], training_data['y_test'])
        
        # Obtener importancia de características
        self.feature_importances['random_forest'] = model.feature_importances_
        
        # Guardar modelo
        self._save_model(model, 'random_forest')
        
        # Guardar métricas
        metrics = {
            'val_accuracy': val_score,
            'test_accuracy': test_score,
            'feature_importances': self.feature_importances['random_forest'].tolist()
        }
        
        self._save_training_metrics(metrics, 'random_forest')
        
        return model
    
    def evaluate_model(self, model, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Evalúa modelo en conjunto de test"""
        # Predecir
        if isinstance(model, nn.Module):
            # Modelo PyTorch
            device = next(model.parameters()).device
            model.eval()
            
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X_test).to(device)
                # Para LSTM, necesitamos secuencias
                if len(X_test.shape) == 2:
                    # Crear secuencias si no las hay
                    X_seq, y_seq = self._create_sequences(X_test, y_test, 1)
                    X_tensor = torch.FloatTensor(X_seq).to(device)
                    y_test = y_seq
                
                outputs = model([X_tensor])
                y_pred_proba = outputs.cpu().numpy().flatten()
                y_pred = (y_pred_proba > 0.5).astype(int)
        else:
            # Modelo scikit-learn
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            y_pred = model.predict(X_test)
        
        # Calcular métricas
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1_score': f1_score(y_test, y_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_test, y_pred_proba) if len(np.unique(y_test)) > 1 else 0.5,
            'prediction_distribution': {
                'mean': float(np.mean(y_pred_proba)),
                'std': float(np.std(y_pred_proba)),
                'min': float(np.min(y_pred_proba)),
                'max': float(np.max(y_pred_proba))
            }
        }
        
        return metrics
    
    def cross_validate(self, X: np.ndarray, y: np.ndarray, model_type: str = 'random_forest') -> Dict:
        """Validación cruzada temporal"""
        tscv = TimeSeriesSplit(n_splits=self.training_config['n_splits'])
        
        fold_metrics = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            # Escalar
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)
            
            # Entrenar modelo
            if model_type == 'random_forest':
                from sklearn.ensemble import RandomForestClassifier
                model = RandomForestClassifier(
                    n_estimators=50,
                    max_depth=5,
                    random_state=self.training_config['random_state']
                )
                model.fit(X_train_scaled, y_train)
                val_score = model.score(X_val_scaled, y_val)
            else:
                # Otros modelos
                val_score = 0.5
            
            fold_metrics.append({
                'fold': fold + 1,
                'train_samples': len(X_train),
                'val_samples': len(X_val),
                'val_accuracy': val_score
            })
        
        # Calcular métricas agregadas
        avg_accuracy = np.mean([m['val_accuracy'] for m in fold_metrics])
        std_accuracy = np.std([m['val_accuracy'] for m in fold_metrics])
        
        return {
            'fold_metrics': fold_metrics,
            'avg_accuracy': avg_accuracy,
            'std_accuracy': std_accuracy,
            'cv_score': avg_accuracy
        }
    
    def incremental_training(self,
                           new_data: Dict,
                           model_name: str = 'lstm',
                           learning_rate: float = 0.0001) -> bool:
        """
        Entrenamiento incremental con nuevos datos
        """
        try:
            # Cargar modelo existente
            model = self._load_model(model_name)
            
            if model is None:
                self.config.logger.warning(f"No existing model {model_name} for incremental training")
                return False
            
            # Preparar nuevos datos
            if 'features' not in new_data or 'labels' not in new_data:
                self.config.logger.error("New data must contain 'features' and 'labels'")
                return False
            
            X_new = new_data['features']
            y_new = new_data['labels']
            
            if len(X_new) < 10:
                self.config.logger.warning("Insufficient new data for incremental training")
                return False
            
            # Escalar nuevos datos
            scaler = self.scalers.get('default')
            if scaler is None:
                self.config.logger.warning("No scaler found for incremental training")
                return False
            
            X_new_scaled = scaler.transform(X_new)
            
            # Entrenamiento incremental
            if isinstance(model, nn.Module):
                # PyTorch model
                device = next(model.parameters()).device
                model.train()
                
                optimizer = torch.optim.Adam(
                    model.parameters(),
                    lr=learning_rate
                )
                criterion = nn.BCELoss()
                
                # Entrenar por pocas épocas
                for epoch in range(5):
                    epoch_loss = 0.0
                    
                    # Mini-batch training
                    for i in range(0, len(X_new_scaled), 32):
                        batch_X = X_new_scaled[i:i+32]
                        batch_y = y_new[i:i+32]
                        
                        X_tensor = torch.FloatTensor(batch_X).to(device)
                        y_tensor = torch.FloatTensor(batch_y).to(device).unsqueeze(1)
                        
                        optimizer.zero_grad()
                        outputs = model([X_tensor])
                        loss = criterion(outputs, y_tensor)
                        loss.backward()
                        optimizer.step()
                        
                        epoch_loss += loss.item()
                    
                    self.config.logger.debug(f"Incremental epoch {epoch+1}, Loss: {epoch_loss:.4f}")
                
                # Guardar modelo actualizado
                self._save_model(model, f"{model_name}_incremental")
                
            else:
                # scikit-learn model (partial_fit si está disponible)
                if hasattr(model, 'partial_fit'):
                    model.partial_fit(X_new_scaled, y_new)
                    self._save_model(model, f"{model_name}_incremental")
                else:
                    self.config.logger.warning(f"Model {model_name} does not support incremental training")
                    return False
            
            self.config.logger.info(f"Incremental training completed for {model_name}")
            return True
            
        except Exception as e:
            self.config.logger.error(f"Error in incremental training: {e}")
            return False
    
    def _save_model(self, model, name: str):
        """Guarda modelo"""
        model_path = self.models_dir / f"{name}.pth"
        
        if isinstance(model, nn.Module):
            # PyTorch model
            torch.save(model.state_dict(), model_path)
        else:
            # scikit-learn model
            joblib.dump(model, model_path)
        
        # Guardar scaler si existe
        scaler_path = self.models_dir / f"{name}_scaler.pkl"
        if 'default' in self.scalers:
            joblib.dump(self.scalers['default'], scaler_path)
    
    def _load_model(self, name: str):
        """Carga modelo"""
        model_path = self.models_dir / f"{name}.pth"
        
        if not model_path.exists():
            return None
        
        try:
            # Intentar cargar como PyTorch
            if name.startswith('lstm'):
                from .lstm_predictor import MultiTimeframeLSTM
                
                # Necesitamos conocer la arquitectura
                model = MultiTimeframeLSTM(
                    input_size=100,  # Placeholder, debería guardarse en metadata
                    hidden_size=128,
                    num_layers=3,
                    num_timeframes=1,
                    dropout=0.2
                )
                
                state_dict = torch.load(model_path, map_location='cpu')
                model.load_state_dict(state_dict)
                return model
            else:
                # scikit-learn model
                return joblib.load(model_path)
                
        except Exception as e:
            self.config.logger.error(f"Error loading model {name}: {e}")
            return None
    
    def _save_training_metrics(self, metrics: Dict, model_name: str):
        """Guarda métricas de entrenamiento"""
        metrics_path = self.models_dir / f"{model_name}_metrics.json"
        
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
    
    def get_training_summary(self) -> Dict:
        """Obtiene resumen de entrenamiento"""
        summary = {
            'available_models': [],
            'model_metrics': {},
            'last_training': None
        }
        
        # Buscar modelos disponibles
        for file in self.models_dir.glob('*.pth'):
            model_name = file.stem
            summary['available_models'].append(model_name)
            
            # Cargar métricas si existen
            metrics_file = self.models_dir / f"{model_name}_metrics.json"
            if metrics_file.exists():
                try:
                    with open(metrics_file, 'r') as f:
                        summary['model_metrics'][model_name] = json.load(f)
                except:
                    pass
        
        return summary