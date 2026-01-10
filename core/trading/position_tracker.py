# core/trading/position_tracker.py
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path

class PositionTracker:
    """Rastreador de posiciones en base de datos"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = config.base_dir / "data" / "positions.db"
        self._init_database()
    
    def _init_database(self):
        """Inicializa la base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de posiciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                asset_pair TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_time TIMESTAMP NOT NULL,
                position_size REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                trailing_stop REAL,
                risk_zero_price REAL,
                status TEXT NOT NULL,
                close_price REAL,
                close_time TIMESTAMP,
                pnl REAL,
                pnl_percentage REAL,
                close_reason TEXT,
                metadata TEXT
            )
        ''')
        
        # Tabla de histórico de precios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                position_id TEXT,
                timestamp TIMESTAMP,
                price REAL,
                pnl REAL,
                pnl_percentage REAL,
                FOREIGN KEY (position_id) REFERENCES positions (id)
            )
        ''')
        
        # Índices para mejor performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_asset ON positions(asset_pair)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_history_position ON price_history(position_id)')
        
        conn.commit()
        conn.close()
    
    def save_position(self, position_data: Dict) -> bool:
        """Guarda una posición en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO positions 
                (id, asset_pair, side, entry_price, entry_time, position_size, 
                 stop_loss, take_profit, trailing_stop, risk_zero_price, status,
                 close_price, close_time, pnl, pnl_percentage, close_reason, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position_data.get('id'),
                position_data.get('asset_pair'),
                position_data.get('side'),
                float(position_data.get('entry_price', 0)),
                position_data.get('entry_time'),
                float(position_data.get('position_size', 0)),
                float(position_data.get('stop_loss', 0)) if position_data.get('stop_loss') else None,
                float(position_data.get('take_profit', 0)) if position_data.get('take_profit') else None,
                float(position_data.get('trailing_stop', 0)) if position_data.get('trailing_stop') else None,
                float(position_data.get('risk_zero_price', 0)),
                position_data.get('status', 'OPEN'),
                float(position_data.get('close_price', 0)) if position_data.get('close_price') else None,
                position_data.get('close_time'),
                float(position_data.get('pnl', 0)) if position_data.get('pnl') else None,
                float(position_data.get('pnl_percentage', 0)) if position_data.get('pnl_percentage') else None,
                position_data.get('close_reason'),
                json.dumps(position_data.get('metadata', {}))
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.config.logger.error(f"Error saving position: {e}")
            return False
    
    def update_position_price(self, position_id: str, price: Decimal, pnl: Decimal, pnl_percentage: Decimal):
        """Actualiza precio y P&L de una posición"""
        try:
            # Guardar en histórico
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO price_history (position_id, timestamp, price, pnl, pnl_percentage)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                position_id,
                datetime.now().isoformat(),
                float(price),
                float(pnl),
                float(pnl_percentage)
            ))
            
            # Actualizar posición actual
            cursor.execute('''
                UPDATE positions 
                SET pnl = ?, pnl_percentage = ?
                WHERE id = ? AND status = 'OPEN'
            ''', (float(pnl), float(pnl_percentage), position_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.config.logger.error(f"Error updating position price: {e}")
    
    def close_position(self, position_id: str, close_data: Dict) -> bool:
        """Cierra una posición"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE positions 
                SET status = 'CLOSED',
                    close_price = ?,
                    close_time = ?,
                    pnl = ?,
                    pnl_percentage = ?,
                    close_reason = ?
                WHERE id = ?
            ''', (
                float(close_data.get('close_price', 0)),
                close_data.get('close_time'),
                float(close_data.get('pnl', 0)),
                float(close_data.get('pnl_percentage', 0)),
                close_data.get('close_reason'),
                position_id
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.config.logger.error(f"Error closing position: {e}")
            return False
    
    def get_active_positions(self) -> List[Dict]:
        """Obtiene posiciones activas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, asset_pair, side, entry_price, entry_time, position_size,
                       stop_loss, take_profit, trailing_stop, risk_zero_price, pnl, pnl_percentage
                FROM positions 
                WHERE status = 'OPEN'
                ORDER BY entry_time DESC
            ''')
            
            columns = [desc[0] for desc in cursor.description]
            positions = []
            
            for row in cursor.fetchall():
                position = dict(zip(columns, row))
                
                # Parsear JSON metadata
                if 'metadata' in position and position['metadata']:
                    position['metadata'] = json.loads(position['metadata'])
                
                positions.append(position)
            
            conn.close()
            return positions
            
        except Exception as e:
            self.config.logger.error(f"Error getting active positions: {e}")
            return []
    
    def get_position_history(self, 
                           limit: int = 100,
                           asset_pair: str = None) -> List[Dict]:
        """Obtiene historial de posiciones"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, asset_pair, side, entry_price, entry_time, position_size,
                       close_price, close_time, pnl, pnl_percentage, close_reason
                FROM positions 
                WHERE status = 'CLOSED'
            '''
            
            params = []
            
            if asset_pair:
                query += ' AND asset_pair = ?'
                params.append(asset_pair)
            
            query += ' ORDER BY close_time DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            
            columns = [desc[0] for desc in cursor.description]
            positions = []
            
            for row in cursor.fetchall():
                position = dict(zip(columns, row))
                positions.append(position)
            
            conn.close()
            return positions
            
        except Exception as e:
            self.config.logger.error(f"Error getting position history: {e}")
            return []
    
    def get_position_stats(self) -> Dict:
        """Obtiene estadísticas de posiciones"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total positions
            cursor.execute('SELECT COUNT(*) FROM positions')
            total_positions = cursor.fetchone()[0]
            
            # Active positions
            cursor.execute('SELECT COUNT(*) FROM positions WHERE status = "OPEN"')
            active_positions = cursor.fetchone()[0]
            
            # Total P&L
            cursor.execute('SELECT SUM(pnl) FROM positions WHERE status = "CLOSED"')
            total_pnl = cursor.fetchone()[0] or 0
            
            # Win rate
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
                FROM positions 
                WHERE status = "CLOSED"
            ''')
            result = cursor.fetchone()
            total_closed = result[0] or 0
            wins = result[1] or 0
            
            win_rate = 0
            if total_closed > 0:
                win_rate = wins / total_closed
            
            # Average P&L
            cursor.execute('SELECT AVG(pnl) FROM positions WHERE status = "CLOSED"')
            avg_pnl = cursor.fetchone()[0] or 0
            
            # Best and worst trades
            cursor.execute('''
                SELECT MAX(pnl), MIN(pnl) 
                FROM positions 
                WHERE status = "CLOSED"
            ''')
            best_worst = cursor.fetchone()
            best_pnl = best_worst[0] or 0
            worst_pnl = best_worst[1] or 0
            
            conn.close()
            
            return {
                "total_positions": total_positions,
                "active_positions": active_positions,
                "closed_positions": total_closed,
                "total_pnl": total_pnl,
                "win_rate": win_rate,
                "avg_pnl": avg_pnl,
                "best_pnl": best_pnl,
                "worst_pnl": worst_pnl
            }
            
        except Exception as e:
            self.config.logger.error(f"Error getting position stats: {e}")
            return {}
    
    def get_price_history(self, position_id: str) -> List[Dict]:
        """Obtiene histórico de precios de una posición"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, price, pnl, pnl_percentage
                FROM price_history
                WHERE position_id = ?
                ORDER BY timestamp ASC
            ''', (position_id,))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    "timestamp": row[0],
                    "price": row[1],
                    "pnl": row[2],
                    "pnl_percentage": row[3]
                })
            
            conn.close()
            return history
            
        except Exception as e:
            self.config.logger.error(f"Error getting price history: {e}")
            return []