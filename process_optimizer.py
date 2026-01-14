# process_optimizer.py
"""
Sistema de reingeniería automática que optimiza parámetros basado en resultados
Implementa algoritmos genéticos y aprendizaje por refuerzo
"""
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
import hashlib
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from config import OPTIMIZATION, TRADING, RISK

@dataclass
class OptimizationResult:
    """Resultado de optimización"""
    parameters: Dict[str, float]
    fitness_score: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    total_return: float
    iteration: int
    timestamp: datetime

class GeneticAlgorithmOptimizer:
    """Optimizador basado en algoritmo genético"""
    def __init__(self, population_size: int = 50, generations: int = 100):
        self.population_size = population_size
        self.generations = generations
        self.parameter_ranges = OPTIMIZATION.PARAMETER_RANGES
        self.population = []
        self.fitness_scores = []
        self.best_solution = None
        self.best_fitness = -np.inf
        self.history = []
        
    def initialize_population(self):
        """Inicializar población aleatoria"""
        self.population = []
        
        for _ in range(self.population_size):
            individual = {}
            for param, (min_val, max_val) in self.parameter_ranges.items():
                if param == 'position_size':
                    individual[param] = np.random.uniform(min_val, max_val)
                elif param == 'stop_loss':
                    individual[param] = np.random.uniform(min_val, max_val)
                elif param == 'take_profit':
                    individual[param] = np.random.uniform(min_val, max_val)
                elif param == 'trailing_distance':
                    individual[param] = np.random.uniform(min_val, max_val)
                # Agregar más parámetros según sea necesario
            
            self.population.append(individual)
    
    async def evaluate_fitness(self, individual: Dict, trade_history: pd.DataFrame) -> float:
        """Evaluar fitness de un individuo"""
        if trade_history.empty:
            return 0.0
        
        # Simular estrategia con estos parámetros
        simulated_results = await self._simulate_strategy(individual, trade_history)
        
        if not simulated_results:
            return 0.0
        
        # Calcular métricas
        returns = simulated_results['returns']
        if len(returns) < 2:
            return 0.0
        
        # Sharpe Ratio (ponderado más)
        sharpe = self._calculate_sharpe_ratio(returns)
        
        # Win Rate
        win_rate = simulated_results['win_rate']
        
        # Profit Factor
        profit_factor = simulated_results['profit_factor']
        
        # Maximum Drawdown
        max_dd = simulated_results['max_drawdown']
        
        # Total Return
        total_return = simulated_results['total_return']
        
        # Función de fitness compuesta
        fitness = (
            sharpe * 0.35 +  # Sharpe ratio es importante
            win_rate * 0.25 +  # Win rate
            profit_factor * 0.20 +  # Profit factor
            (1 - max_dd) * 0.15 +  # Minimizar drawdown
            total_return * 0.05  # Retorno total
        )
        
        # Penalizar parámetros extremos
        fitness *= self._calculate_penalty_factor(individual)
        
        return max(fitness, 0)
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calcular Sharpe Ratio anualizado"""
        if len(returns) < 2 or np.std(returns) == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252  # Asumiendo retornos diarios
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        
        return sharpe
    
    async def _simulate_strategy(self, params: Dict, trade_history: pd.DataFrame) -> Optional[Dict]:
        """Simular estrategia con parámetros dados"""
        try:
            # Crear copia de datos
            df = trade_history.copy()
            
            if df.empty:
                return None
            
            # Aplicar parámetros a trades históricos
            # Esto es una simulación simplificada
            results = {
                'returns': [],
                'wins': 0,
                'losses': 0,
                'total_trades': 0,
                'total_profit': 0.0,
                'total_loss': 0.0,
                'equity_curve': [10000.0]  # Starting capital
            }
            
            # Simular cada trade con nuevos parámetros
            for _, trade in df.iterrows():
                # Modificar resultados basado en nuevos parámetros
                # Esta es una simplificación - en realidad necesitarías re-ejecutar la estrategia
                
                original_pnl = trade.get('pnl_percent', 0)
                
                # Ajustar P&L basado en nuevos parámetros
                # (esto es altamente simplificado)
                adjusted_pnl = original_pnl * self._adjust_for_parameters(original_pnl, params)
                
                results['returns'].append(adjusted_pnl / 100)  # Convertir a decimal
                
                if adjusted_pnl > 0:
                    results['wins'] += 1
                    results['total_profit'] += adjusted_pnl
                else:
                    results['losses'] += 1
                    results['total_loss'] += abs(adjusted_pnl)
                
                results['total_trades'] += 1
                
                # Actualizar curva de equity
                last_equity = results['equity_curve'][-1]
                new_equity = last_equity * (1 + adjusted_pnl / 100)
                results['equity_curve'].append(new_equity)
            
            if results['total_trades'] == 0:
                return None
            
            # Calcular métricas finales
            results['win_rate'] = results['wins'] / results['total_trades']
            
            if results['total_loss'] > 0:
                results['profit_factor'] = results['total_profit'] / results['total_loss']
            else:
                results['profit_factor'] = np.inf
            
            # Calcular drawdown máximo
            equity_curve = np.array(results['equity_curve'])
            peak = np.maximum.accumulate(equity_curve)
            drawdown = (peak - equity_curve) / peak
            results['max_drawdown'] = np.max(drawdown) if len(drawdown) > 0 else 0.0
            
            # Retorno total
            results['total_return'] = (equity_curve[-1] / equity_curve[0] - 1) * 100
            
            return results
            
        except Exception as e:
            print(f"⚠️ Error en simulación: {e}")
            return None
    
    def _adjust_for_parameters(self, original_pnl: float, params: Dict) -> float:
        """Ajustar P&L basado en nuevos parámetros"""
        # Esta función debería ser mucho más sofisticada en producción
        adjustment = 1.0
        
        # Mejor stop loss reduce pérdidas grandes
        if original_pnl < -10:  # Pérdida grande
            if params.get('stop_loss', 0.02) < 0.03:
                adjustment *= 0.7  # Mejora con stop loss más ajustado
        
        # Mejor take profit captura más ganancias
        if original_pnl > 5:  # Ganancia media
            if params.get('take_profit', 0.05) > 0.04:
                adjustment *= 1.2
        
        return adjustment
    
    def _calculate_penalty_factor(self, individual: Dict) -> float:
        """Calcular factor de penalización para parámetros extremos"""
        penalty = 1.0
        
        for param, value in individual.items():
            min_val, max_val = self.parameter_ranges.get(param, (0, 1))
            
            # Penalizar valores cerca de los extremos
            normalized = (value - min_val) / (max_val - min_val)
            
            if normalized < 0.1 or normalized > 0.9:
                penalty *= 0.8  # 20% de penalización
            elif normalized < 0.2 or normalized > 0.8:
                penalty *= 0.9  # 10% de penalización
        
        return penalty
    
    def selection(self):
        """Selección por torneo"""
        selected = []
        
        for _ in range(self.population_size):
            # Torneo de tamaño 3
            contestants = np.random.choice(
                range(self.population_size), 
                size=min(3, self.population_size), 
                replace=False
            )
            
            # Seleccionar el mejor
            best_idx = contestants[np.argmax([self.fitness_scores[i] for i in contestants])]
            selected.append(self.population[best_idx])
        
        self.population = selected
    
    def crossover(self, crossover_rate: float = 0.8):
        """Crossover de un punto"""
        new_population = []
        
        for i in range(0, self.population_size, 2):
            if i + 1 >= self.population_size:
                new_population.append(self.population[i])
                continue
            
            parent1 = self.population[i]
            parent2 = self.population[i + 1]
            
            if np.random.random() < crossover_rate:
                # Punto de crossover aleatorio
                params = list(parent1.keys())
                crossover_point = np.random.randint(1, len(params) - 1)
                
                child1 = {}
                child2 = {}
                
                for j, param in enumerate(params):
                    if j < crossover_point:
                        child1[param] = parent1[param]
                        child2[param] = parent2[param]
                    else:
                        child1[param] = parent2[param]
                        child2[param] = parent1[param]
                
                new_population.extend([child1, child2])
            else:
                new_population.extend([parent1, parent2])
        
        self.population = new_population[:self.population_size]
    
    def mutation(self, mutation_rate: float = 0.1):
        """Mutación gaussiana"""
        for i in range(self.population_size):
            if np.random.random() < mutation_rate:
                individual = self.population[i]
                
                # Seleccionar parámetro aleatorio para mutar
                param_to_mutate = np.random.choice(list(individual.keys()))
                
                min_val, max_val = self.parameter_ranges.get(param_to_mutate, (0, 1))
                
                # Mutación gaussiana
                current_val = individual[param_to_mutate]
                std = (max_val - min_val) * 0.1  # 10% del rango
                new_val = current_val + np.random.normal(0, std)
                
                # Asegurar que esté dentro de los límites
                new_val = np.clip(new_val, min_val, max_val)
                
                individual[param_to_mutate] = new_val
    
    async def optimize(self, trade_history: pd.DataFrame) -> OptimizationResult:
        """Ejecutar optimización"""
        print("🧬 Iniciando optimización con algoritmo genético...")
        
        self.initialize_population()
        
        for generation in range(self.generations):
            # Evaluar fitness
            self.fitness_scores = []
            for individual in self.population:
                fitness = await self.evaluate_fitness(individual, trade_history)
                self.fitness_scores.append(fitness)
            
            # Encontrar el mejor
            best_idx = np.argmax(self.fitness_scores)
            best_fitness = self.fitness_scores[best_idx]
            
            if best_fitness > self.best_fitness:
                self.best_fitness = best_fitness
                self.best_solution = self.population[best_idx].copy()
            
            # Guardar historia
            self.history.append({
                'generation': generation,
                'best_fitness': best_fitness,
                'avg_fitness': np.mean(self.fitness_scores),
                'best_parameters': self.population[best_idx]
            })
            
            # Operadores genéticos
            self.selection()
            self.crossover()
            self.mutation()
            
            if generation % 10 == 0:
                print(f"  Generación {generation:3d} | "
                      f"Mejor fitness: {best_fitness:.4f} | "
                      f"Promedio: {np.mean(self.fitness_scores):.4f}")
        
        # Evaluar la mejor solución
        best_results = await self._simulate_strategy(self.best_solution, trade_history)
        
        result = OptimizationResult(
            parameters=self.best_solution,
            fitness_score=self.best_fitness,
            sharpe_ratio=self._calculate_sharpe_ratio(np.array(best_results['returns'])) if best_results else 0.0,
            win_rate=best_results['win_rate'] if best_results else 0.0,
            profit_factor=best_results['profit_factor'] if best_results else 0.0,
            max_drawdown=best_results['max_drawdown'] if best_results else 0.0,
            total_return=best_results['total_return'] if best_results else 0.0,
            iteration=len(self.history),
            timestamp=datetime.now()
        )
        
        print(f"✅ Optimización completada. Mejor fitness: {self.best_fitness:.4f}")
        
        return result

class ReinforcementLearningOptimizer:
    """Optimizador basado en aprendizaje por refuerzo"""
    def __init__(self, state_size: int = 10, action_size: int = 4):
        self.state_size = state_size
        self.action_size = action_size
        self.q_table = np.zeros((state_size, action_size))
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.1
        self.epsilon_decay = 0.995
        self.min_epsilon = 0.01
    
    def get_state(self, market_conditions: Dict) -> int:
        """Convertir condiciones de mercado a estado discreto"""
        # Simplificado: en producción usarías una representación más compleja
        state = 0
        
        # Codificar condiciones de mercado
        if market_conditions.get('trend', 'neutral') == 'bullish':
            state += 1
        elif market_conditions.get('trend', 'neutral') == 'bearish':
            state += 2
        
        if market_conditions.get('volatility', 0) > 0.1:
            state += 3
        
        if market_conditions.get('volume', 0) > 1.5:
            state += 6
        
        return min(state, self.state_size - 1)
    
    def get_action(self, state: int) -> int:
        """Seleccionar acción usando epsilon-greedy"""
        if np.random.random() < self.epsilon:
            return np.random.randint(self.action_size)
        else:
            return np.argmax(self.q_table[state])
    
    def update_q_table(self, state: int, action: int, reward: float, next_state: int):
        """Actualizar Q-table"""
        best_next_action = np.argmax(self.q_table[next_state])
        td_target = reward + self.discount_factor * self.q_table[next_state][best_next_action]
        td_error = td_target - self.q_table[state][action]
        self.q_table[state][action] += self.learning_rate * td_error
    
    def decay_epsilon(self):
        """Reducir epsilon"""
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.min_epsilon)
    
    async def train_episode(self, market_data: pd.DataFrame):
        """Entrenar un episodio"""
        total_reward = 0
        
        for i in range(len(market_data) - 1):
            # Obtener estado actual
            current_conditions = self._extract_conditions(market_data.iloc[i])
            state = self.get_state(current_conditions)
            
            # Seleccionar acción
            action = self.get_action(state)
            
            # Ejecutar acción y obtener recompensa
            reward = await self._execute_action(action, market_data.iloc[i], market_data.iloc[i + 1])
            
            # Obtener siguiente estado
            next_conditions = self._extract_conditions(market_data.iloc[i + 1])
            next_state = self.get_state(next_conditions)
            
            # Actualizar Q-table
            self.update_q_table(state, action, reward, next_state)
            
            total_reward += reward
        
        # Decay epsilon
        self.decay_epsilon()
        
        return total_reward
    
    def _extract_conditions(self, data_point) -> Dict:
        """Extraer condiciones de mercado de un punto de datos"""
        return {
            'trend': 'bullish' if data_point.get('returns', 0) > 0 else 'bearish',
            'volatility': data_point.get('volatility', 0.05),
            'volume': data_point.get('volume_ratio', 1.0),
            'rsi': data_point.get('rsi', 50)
        }
    
    async def _execute_action(self, action: int, current_data, next_data) -> float:
        """Ejecutar acción y calcular recompensa"""
        # Acciones: 0 = aumentar posición, 1 = disminuir posición, 
        # 2 = mantener, 3 = salir
        
        current_price = current_data.get('price', 0)
        next_price = next_data.get('price', current_price)
        
        returns = (next_price - current_price) / current_price
        
        # Recompensa basada en acción y resultado
        if action == 0:  # Aumentar posición
            reward = returns * 10  # Amplificar ganancias/pérdidas
        elif action == 1:  # Disminuir posición
            reward = -returns * 5  # Penalizar si el mercado va en contra
        elif action == 2:  # Mantener
            reward = abs(returns) * 2  # Recompensar estabilidad
        else:  # Salir
            reward = -abs(returns) * 3  # Penalizar salidas prematuras
        
        return reward

class ProcessOptimizer:
    """Manager principal de optimización"""
    def __init__(self):
        self.ga_optimizer = GeneticAlgorithmOptimizer(
            population_size=OPTIMIZATION.GENETIC_ALGORITHM_POPULATION,
            generations=OPTIMIZATION.GENETIC_ALGORITHM_GENERATIONS
        )
        self.rl_optimizer = ReinforcementLearningOptimizer()
        self.optimization_history = []
        self.last_optimization = None
        
    async def run_optimization(self, trade_history: pd.DataFrame, market_data: pd.DataFrame) -> Dict:
        """Ejecutar optimización completa"""
        print("⚙️ Ejecutando reingeniería de procesos...")
        
        results = {}
        
        # 1. Optimización de parámetros con GA
        print("  🔄 Ejecutando optimización genética...")
        ga_result = await self.ga_optimizer.optimize(trade_history)
        results['genetic_algorithm'] = ga_result
        
        # 2. Optimización de estrategia con RL
        print("  🧠 Ejecutando aprendizaje por refuerzo...")
        rl_rewards = []
        for episode in range(10):  # 10 episodios de entrenamiento
            reward = await self.rl_optimizer.train_episode(market_data)
            rl_rewards.append(reward)
        
        results['reinforcement_learning'] = {
            'avg_reward': np.mean(rl_rewards),
            'final_epsilon': self.rl_optimizer.epsilon,
            'q_table_size': self.rl_optimizer.q_table.shape
        }
        
        # 3. Análisis estadístico
        print("  📊 Realizando análisis estadístico...")
        statistical_insights = await self._perform_statistical_analysis(trade_history)
        results['statistical_analysis'] = statistical_insights
        
        # 4. Recomendaciones de optimización
        print("  💡 Generando recomendaciones...")
        recommendations = await self._generate_recommendations(results, trade_history)
        results['recommendations'] = recommendations
        
        # Guardar resultados
        self.optimization_history.append({
            'timestamp': datetime.now(),
            'results': results
        })
        
        self.last_optimization = datetime.now()
        
        print("✅ Reingeniería completada")
        
        return results
    
    async def _perform_statistical_analysis(self, trade_history: pd.DataFrame) -> Dict:
        """Realizar análisis estadístico de trades"""
        if trade_history.empty:
            return {}
        
        analysis = {}
        
        # Análisis de P&L
        pnl_series = trade_history['pnl_percent'].dropna()
        
        if len(pnl_series) > 1:
            analysis['pnl_stats'] = {
                'mean': float(np.mean(pnl_series)),
                'median': float(np.median(pnl_series)),
                'std': float(np.std(pnl_series)),
                'skewness': float(stats.skew(pnl_series)),
                'kurtosis': float(stats.kurtosis(pnl_series)),
                'shapiro_p': float(stats.shapiro(pnl_series)[1]) if len(pnl_series) < 5000 else 0.0
            }
        
        # Análisis de duración
        if 'holding_time' in trade_history.columns:
            durations = pd.to_timedelta(trade_history['holding_time']).dt.total_seconds() / 3600
            analysis['duration_stats'] = {
                'mean_hours': float(np.mean(durations)),
                'median_hours': float(np.median(durations)),
                'optimal_range': self._find_optimal_duration(durations, pnl_series)
            }
        
        # Correlaciones
        numeric_cols = trade_history.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 1:
            correlation_matrix = trade_history[numeric_cols].corr()
            analysis['correlations'] = correlation_matrix.to_dict()
        
        return analysis
    
    def _find_optimal_duration(self, durations: np.ndarray, pnls: np.ndarray) -> Tuple[float, float]:
        """Encontrar rango de duración óptimo"""
        if len(durations) < 2:
            return 0.0, 0.0
        
        # Bin durations and calculate average P&L per bin
        bins = np.linspace(np.min(durations), np.max(durations), 10)
        bin_indices = np.digitize(durations, bins)
        
        avg_pnl_per_bin = []
        for i in range(1, len(bins)):
            mask = bin_indices == i
            if np.any(mask):
                avg_pnl_per_bin.append(np.mean(pnls[mask]))
            else:
                avg_pnl_per_bin.append(0)
        
        # Find bin with highest average P&L
        best_bin_idx = np.argmax(avg_pnl_per_bin)
        
        if best_bin_idx < len(bins) - 1:
            return float(bins[best_bin_idx]), float(bins[best_bin_idx + 1])
        
        return float(bins[0]), float(bins[-1])
    
    async def _generate_recommendations(self, optimization_results: Dict, trade_history: pd.DataFrame) -> List[str]:
        """Generar recomendaciones basadas en optimización"""
        recommendations = []
        
        # Recomendaciones basadas en GA
        if 'genetic_algorithm' in optimization_results:
            ga_result = optimization_results['genetic_algorithm']
            
            # Analizar parámetros óptimos
            params = ga_result.parameters
            
            recommendations.append(
                f"🔧 Ajustar tamaño de posición a {params.get('position_size', 0.1)*100:.1f}% "
                f"(actual: {TRADING.POSITION_SIZE_PERCENT*100:.1f}%)"
            )
            
            recommendations.append(
                f"🎯 Ajustar stop loss a {params.get('stop_loss', 0.02)*100:.1f}% "
                f"(actual: {TRADING.STOP_LOSS_PERCENT*100:.1f}%)"
            )
            
            recommendations.append(
                f"📈 Ajustar take profit a {params.get('take_profit', 0.05)*100:.1f}% "
                f"(actual: {TRADING.TAKE_PROFIT_PERCENT*100:.1f}%)"
            )
        
        # Recomendaciones basadas en análisis estadístico
        if 'statistical_analysis' in optimization_results:
            stats = optimization_results['statistical_analysis']
            
            if 'duration_stats' in stats:
                optimal_range = stats['duration_stats'].get('optimal_range', (0, 0))
                recommendations.append(
                    f"⏱️ Enfocarse en trades de {optimal_range[0]:.1f} a {optimal_range[1]:.1f} horas "
                    f"(duración promedio actual: {stats['duration_stats'].get('mean_hours', 0):.1f}h)"
                )
        
        # Recomendaciones basadas en patterns
        patterns = await self._detect_patterns(trade_history)
        recommendations.extend(patterns)
        
        return recommendations
    
    async def _detect_patterns(self, trade_history: pd.DataFrame) -> List[str]:
        """Detectar patrones en trades históricos"""
        patterns = []
        
        if trade_history.empty or len(trade_history) < 10:
            return patterns
        
        # Detectar días/turnos más rentables
        if 'entry_time' in trade_history.columns:
            trade_history['entry_hour'] = pd.to_datetime(trade_history['entry_time']).dt.hour
            trade_history['entry_day'] = pd.to_datetime(trade_history['entry_time']).dt.day_name()
            
            # Por hora del día
            hourly_performance = trade_history.groupby('entry_hour')['pnl_percent'].mean()
            best_hour = hourly_performance.idxmax()
            
            if not pd.isna(best_hour):
                patterns.append(
                    f"🕐 Mejor rendimiento en hora {int(best_hour)}:00 "
                    f"(+{hourly_performance.max():.2f}% promedio)"
                )
            
            # Por día de la semana
            daily_performance = trade_history.groupby('entry_day')['pnl_percent'].mean()
            best_day = daily_performance.idxmax()
            
            if not pd.isna(best_day):
                patterns.append(
                    f"📅 Mejor rendimiento los {best_day}s "
                    f"(+{daily_performance.max():.2f}% promedio)"
                )
        
        # Detectar patrones de reversión
        losing_streaks = 0
        max_losing_streak = 0
        
        for pnl in trade_history['pnl_percent']:
            if pnl < 0:
                losing_streaks += 1
                max_losing_streak = max(max_losing_streak, losing_streaks)
            else:
                losing_streaks = 0
        
        if max_losing_streak >= 3:
            patterns.append(
                f"⚠️ Se detectaron rachas de {max_losing_streak} pérdidas consecutivas. "
                f"Considerar cooldown después de 2 pérdidas."
            )
        
        return patterns
    
    async def get_optimization_report(self) -> Dict:
        """Generar reporte de optimización"""
        if not self.last_optimization:
            return {"status": "No optimizations performed yet"}
        
        report = {
            "last_optimization": self.last_optimization.isoformat(),
            "total_optimizations": len(self.optimization_history),
            "summary": {}
        }
        
        if self.optimization_history:
            latest = self.optimization_history[-1]['results']
            
            if 'genetic_algorithm' in latest:
                ga = latest['genetic_algorithm']
                report['summary']['genetic_algorithm'] = {
                    'fitness_score': ga.fitness_score,
                    'sharpe_ratio': ga.sharpe_ratio,
                    'win_rate': ga.win_rate,
                    'profit_factor': ga.profit_factor
                }
            
            if 'recommendations' in latest:
                report['recommendations'] = latest['recommendations']
        
        return report

# Instancia global
process_optimizer = ProcessOptimizer()

async def test_optimization():
    """Función de prueba"""
    print("🧪 Probando sistema de optimización...")
    
    # Crear datos de prueba
    np.random.seed(42)
    
    # Datos de trades simulados
    n_trades = 100
    trade_data = pd.DataFrame({
        'pnl_percent': np.random.normal(1, 3, n_trades),
        'holding_time': [f'{np.random.randint(1, 24)}:00:00' for _ in range(n_trades)],
        'entry_time': pd.date_range(end=datetime.now(), periods=n_trades, freq='H'),
        'confidence': np.random.uniform(0.6, 0.9, n_trades)
    })
    
    # Datos de mercado simulados
    market_data = pd.DataFrame({
        'price': np.cumsum(np.random.randn(1000)) + 100,
        'returns': np.random.normal(0, 0.01, 1000),
        'volatility': np.random.uniform(0.02, 0.15, 1000),
        'volume_ratio': np.random.uniform(0.5, 2.5, 1000),
        'rsi': np.random.uniform(30, 70, 1000)
    })
    
    # Ejecutar optimización
    results = await process_optimizer.run_optimization(trade_data, market_data)
    
    # Imprimir recomendaciones
    print("\n💡 RECOMENDACIONES GENERADAS:")
    print("=" * 60)
    for i, rec in enumerate(results.get('recommendations', []), 1):
        print(f"{i}. {rec}")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_optimization())