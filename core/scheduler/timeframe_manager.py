# core/scheduler/timeframe_manager.py
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class TimeframeStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class TimeframeJob:
    """Trabajo programado para un timeframe"""
    timeframe: str
    next_execution: datetime
    interval: timedelta
    status: TimeframeStatus
    last_execution: Optional[datetime]
    executions_count: int
    error_count: int
    
    @property
    def is_due(self) -> bool:
        """Verifica si el trabajo está pendiente de ejecución"""
        return (self.status == TimeframeStatus.ACTIVE and 
                datetime.now() >= self.next_execution)

class TimeframeManager:
    """Gestor de timeframes y programación"""
    
    def __init__(self, config):
        self.config = config
        self.jobs: Dict[str, TimeframeJob] = {}
        self.is_running = False
        
        # Inicializar jobs basados en configuración
        self._initialize_jobs()
    
    def _initialize_jobs(self):
        """Inicializa jobs para cada timeframe activo"""
        timeframe_intervals = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        
        now = datetime.now()
        
        for timeframe in self.config.trading.active_timeframes:
            interval = timeframe_intervals.get(timeframe)
            if interval:
                # Alinear a intervalos regulares
                next_exec = self._align_to_interval(now, interval)
                
                self.jobs[timeframe] = TimeframeJob(
                    timeframe=timeframe,
                    next_execution=next_exec,
                    interval=interval,
                    status=TimeframeStatus.ACTIVE,
                    last_execution=None,
                    executions_count=0,
                    error_count=0
                )
        
        self.config.logger.info(f"Initialized {len(self.jobs)} timeframe jobs")
    
    def _align_to_interval(self, dt: datetime, interval: timedelta) -> datetime:
        """Alinea datetime al siguiente intervalo"""
        if interval.total_seconds() >= 86400:  # 1 día o más
            # Alinear a medianoche
            next_dt = dt.replace(hour=0, minute=0, second=0, microsecond=0) + interval
        elif interval.total_seconds() >= 3600:  # 1 hora o más
            # Alinear a la hora
            next_dt = dt.replace(minute=0, second=0, microsecond=0) + interval
        else:
            # Alinear al minuto
            total_seconds = int(interval.total_seconds())
            current_seconds = dt.minute * 60 + dt.second + dt.microsecond / 1_000_000
            
            intervals_passed = int(current_seconds / total_seconds)
            next_seconds = (intervals_passed + 1) * total_seconds
            
            next_dt = dt.replace(minute=0, second=0, microsecond=0) + timedelta(seconds=next_seconds)
        
        return next_dt
    
    async def start(self):
        """Inicia el gestor de timeframes"""
        self.is_running = True
        self.config.logger.info("🚀 Timeframe manager started")
        
        while self.is_running:
            try:
                # Verificar jobs pendientes
                due_jobs = [job for job in self.jobs.values() if job.is_due]
                
                for job in due_jobs:
                    # Ejecutar job
                    await self._execute_job(job)
                
                # Esperar antes de siguiente verificación
                await asyncio.sleep(1)
                
            except Exception as e:
                self.config.logger.error(f"Error in timeframe manager: {e}")
                await asyncio.sleep(5)
    
    async def _execute_job(self, job: TimeframeJob):
        """Ejecuta un job de timeframe"""
        try:
            self.config.logger.debug(f"Executing timeframe job: {job.timeframe}")
            
            # Actualizar estado del job
            job.last_execution = datetime.now()
            job.executions_count += 1
            
            # Aquí se ejecutaría la lógica específica del timeframe
            # Por ejemplo: análisis, trading, etc.
            
            # Programar siguiente ejecución
            job.next_execution = job.last_execution + job.interval
            
            self.config.logger.info(f"✅ Timeframe {job.timeframe} executed. "
                                  f"Next: {job.next_execution.strftime('%H:%M:%S')}")
            
        except Exception as e:
            job.error_count += 1
            self.config.logger.error(f"Error executing timeframe {job.timeframe}: {e}")
            
            # Si hay muchos errores, pausar el job
            if job.error_count >= 5:
                job.status = TimeframeStatus.PAUSED
                self.config.logger.warning(f"⏸️ Timeframe {job.timeframe} paused due to errors")
    
    def pause_timeframe(self, timeframe: str):
        """Pausa un timeframe"""
        if timeframe in self.jobs:
            self.jobs[timeframe].status = TimeframeStatus.PAUSED
            self.config.logger.info(f"⏸️ Timeframe {timeframe} paused")
    
    def resume_timeframe(self, timeframe: str):
        """Reanuda un timeframe"""
        if timeframe in self.jobs:
            self.jobs[timeframe].status = TimeframeStatus.ACTIVE
            self.config.logger.info(f"▶️ Timeframe {timeframe} resumed")
    
    def add_timeframe(self, timeframe: str, interval: timedelta):
        """Agrega un nuevo timeframe"""
        if timeframe in self.jobs:
            self.config.logger.warning(f"Timeframe {timeframe} already exists")
            return
        
        now = datetime.now()
        next_exec = self._align_to_interval(now, interval)
        
        self.jobs[timeframe] = TimeframeJob(
            timeframe=timeframe,
            next_execution=next_exec,
            interval=interval,
            status=TimeframeStatus.ACTIVE,
            last_execution=None,
            executions_count=0,
            error_count=0
        )
        
        self.config.logger.info(f"➕ Added timeframe {timeframe} with interval {interval}")
    
    def remove_timeframe(self, timeframe: str):
        """Elimina un timeframe"""
        if timeframe in self.jobs:
            del self.jobs[timeframe]
            self.config.logger.info(f"➖ Removed timeframe {timeframe}")
    
    def get_timeframe_status(self) -> List[Dict]:
        """Obtiene estado de todos los timeframes"""
        status_list = []
        
        for job in self.jobs.values():
            status_list.append({
                'timeframe': job.timeframe,
                'status': job.status.value,
                'next_execution': job.next_execution.isoformat() if job.next_execution else None,
                'last_execution': job.last_execution.isoformat() if job.last_execution else None,
                'executions_count': job.executions_count,
                'error_count': job.error_count,
                'interval_seconds': job.interval.total_seconds(),
                'is_due': job.is_due
            })
        
        return sorted(status_list, key=lambda x: x['timeframe'])
    
    def get_due_timeframes(self) -> List[str]:
        """Obtiene timeframes pendientes de ejecución"""
        return [job.timeframe for job in self.jobs.values() if job.is_due]
    
    def stop(self):
        """Detiene el gestor de timeframes"""
        self.is_running = False
        self.config.logger.info("🛑 Timeframe manager stopped")