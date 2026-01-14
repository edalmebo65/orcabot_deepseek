# security_enhancer.py
"""
Sistema de seguridad avanzado con encriptación, auditoría y protección
Implementa AES-256, multi-signature, y detección de anomalías
"""
import os
import json
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio
import aiofiles
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import hmac
import struct
import pickle

from config import SECURITY

@dataclass
class SecurityEvent:
    """Evento de seguridad registrado"""
    timestamp: datetime
    event_type: str
    severity: str  # INFO, WARNING, CRITICAL
    description: str
    source: str
    metadata: Dict = None
    user: str = "system"
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class KeyManager:
    """Gestor de claves encriptadas con rotación automática"""
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or SECURITY.ENCRYPTION_KEY
        self.encrypted_keys = {}
        self.key_versions = {}
        self.current_version = "v1"
        
        if not self.master_key or len(self.master_key) < 32:
            raise ValueError("Master key must be at least 32 characters")
    
    def _derive_key(self, salt: bytes, key_length: int = 32) -> bytes:
        """Derivar clave usando PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=key_length,
            salt=salt,
            iterations=480000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
    
    def encrypt_private_key(self, private_key: str, key_name: str = "default") -> str:
        """Encriptar clave privada usando AES-256-GCM"""
        try:
            # Generar salt único
            salt = os.urandom(16)
            
            # Derivar clave de encriptación
            encryption_key = self._derive_key(salt)
            
            # Generar nonce único
            nonce = os.urandom(12)
            
            # Crear cipher AES-GCM
            cipher = Cipher(
                algorithms.AES(encryption_key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Encriptar datos
            encrypted_data = encryptor.update(private_key.encode()) + encryptor.finalize()
            
            # Combinar todos los componentes
            encrypted_package = salt + nonce + encryptor.tag + encrypted_data
            
            # Guardar versión
            self.key_versions[key_name] = {
                'version': self.current_version,
                'encrypted_at': datetime.now().isoformat(),
                'salt': base64.b64encode(salt).decode(),
                'nonce': base64.b64encode(nonce).decode()
            }
            
            # Guardar clave encriptada
            encrypted_b64 = base64.b64encode(encrypted_package).decode()
            self.encrypted_keys[key_name] = encrypted_b64
            
            return encrypted_b64
            
        except Exception as e:
            raise Exception(f"Error encrypting private key: {e}")
    
    def decrypt_private_key(self, encrypted_b64: str, key_name: str = "default") -> str:
        """Desencriptar clave privada"""
        try:
            # Decodificar paquete encriptado
            encrypted_package = base64.b64decode(encrypted_b64)
            
            # Extraer componentes
            salt = encrypted_package[:16]
            nonce = encrypted_package[16:28]
            tag = encrypted_package[28:44]
            encrypted_data = encrypted_package[44:]
            
            # Derivar clave de encriptación
            encryption_key = self._derive_key(salt)
            
            # Crear cipher AES-GCM
            cipher = Cipher(
                algorithms.AES(encryption_key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Desencriptar datos
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            return decrypted_data.decode()
            
        except Exception as e:
            raise Exception(f"Error decrypting private key: {e}")
    
    def rotate_key(self, key_name: str = "default") -> str:
        """Rotar clave encriptada"""
        if key_name not in self.encrypted_keys:
            raise ValueError(f"Key {key_name} not found")
        
        # Desencriptar con clave vieja
        old_encrypted = self.encrypted_keys[key_name]
        decrypted = self.decrypt_private_key(old_encrypted, key_name)
        
        # Encriptar con nueva versión
        new_version = f"v{int(self.current_version[1:]) + 1}"
        self.current_version = new_version
        
        new_encrypted = self.encrypt_private_key(decrypted, key_name)
        
        # Mantener versión anterior por un tiempo
        backup_key = f"{key_name}_backup_{datetime.now().strftime('%Y%m%d')}"
        self.encrypted_keys[backup_key] = old_encrypted
        
        return new_encrypted
    
    async def save_to_file(self, filepath: str = "backup/encrypted_keys.json"):
        """Guardar claves encriptadas a archivo"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = {
            'encrypted_keys': self.encrypted_keys,
            'key_versions': self.key_versions,
            'current_version': self.current_version,
            'last_updated': datetime.now().isoformat()
        }
        
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps(data, indent=2))
    
    async def load_from_file(self, filepath: str = "backup/encrypted_keys.json"):
        """Cargar claves encriptadas desde archivo"""
        try:
            async with aiofiles.open(filepath, 'r') as f:
                data = json.loads(await f.read())
            
            self.encrypted_keys = data.get('encrypted_keys', {})
            self.key_versions = data.get('key_versions', {})
            self.current_version = data.get('current_version', 'v1')
            
        except FileNotFoundError:
            print(f"⚠️ Key file {filepath} not found, starting fresh")
        except Exception as e:
            raise Exception(f"Error loading key file: {e}")

class AuditLogger:
    """Sistema de logging de auditoría"""
    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = log_dir
        self.current_log = None
        os.makedirs(log_dir, exist_ok=True)
        
        # Rotación diaria de logs
        self._rotate_log_if_needed()
    
    def _rotate_log_if_needed(self):
        """Rotar archivo de log si es un nuevo día"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.current_log = os.path.join(self.log_dir, f"audit_{today}.log")
    
    async def log_event(self, event: SecurityEvent):
        """Registrar evento de seguridad"""
        # Rotar si es necesario
        self._rotate_log_if_needed()
        
        # Convertir evento a línea de log
        log_line = self._format_log_line(event)
        
        # Escribir asíncronamente
        async with aiofiles.open(self.current_log, 'a') as f:
            await f.write(log_line + '\n')
        
        # También escribir a stdout si es crítico
        if event.severity == "CRITICAL":
            print(f"🚨 CRITICAL SECURITY EVENT: {event.description}")
    
    def _format_log_line(self, event: SecurityEvent) -> str:
        """Formatear línea de log"""
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")
        return (f"{timestamp} | {event.severity:8} | {event.event_type:20} | "
                f"{event.source:15} | {event.user:10} | {event.description}")
    
    async def search_events(self, 
                          start_time: datetime = None, 
                          end_time: datetime = None,
                          event_type: str = None,
                          severity: str = None) -> List[SecurityEvent]:
        """Buscar eventos de auditoría"""
        events = []
        
        # Buscar en todos los archivos de log
        for filename in os.listdir(self.log_dir):
            if filename.startswith("audit_") and filename.endswith(".log"):
                filepath = os.path.join(self.log_dir, filename)
                
                async with aiofiles.open(filepath, 'r') as f:
                    lines = await f.readlines()
                
                for line in lines:
                    event = self._parse_log_line(line.strip())
                    if event:
                        # Aplicar filtros
                        if start_time and event.timestamp < start_time:
                            continue
                        if end_time and event.timestamp > end_time:
                            continue
                        if event_type and event.event_type != event_type:
                            continue
                        if severity and event.severity != severity:
                            continue
                        
                        events.append(event)
        
        # Ordenar por timestamp
        events.sort(key=lambda x: x.timestamp)
        
        return events
    
    def _parse_log_line(self, line: str) -> Optional[SecurityEvent]:
        """Parsear línea de log a SecurityEvent"""
        try:
            parts = line.split(" | ")
            if len(parts) < 6:
                return None
            
            timestamp = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S.%f")
            severity = parts[1].strip()
            event_type = parts[2].strip()
            source = parts[3].strip()
            user = parts[4].strip()
            description = parts[5].strip()
            
            return SecurityEvent(
                timestamp=timestamp,
                event_type=event_type,
                severity=severity,
                description=description,
                source=source,
                user=user
            )
        except:
            return None

class AnomalyDetector:
    """Detector de anomalías en tiempo real"""
    def __init__(self):
        self.baselines = {}
        self.anomaly_history = []
        self.suspicious_patterns = [
            "rapid_fire_trades",  # Múltiples trades en segundos
            "unusual_volume",     # Volumen anormalmente alto
            "price_manipulation", # Patrones sospechosos de precio
            "failed_auth",        # Múltiples autenticaciones fallidas
            "unusual_time"        # Actividad en horas no habituales
        ]
    
    async def analyze_transaction(self, tx_data: Dict) -> Tuple[bool, List[str]]:
        """Analizar transacción en busca de anomalías"""
        anomalies = []
        
        # 1. Verificar frecuencia de transacciones
        if await self._check_rapid_fire(tx_data):
            anomalies.append("rapid_fire_trades")
        
        # 2. Verificar volumen inusual
        if await self._check_unusual_volume(tx_data):
            anomalies.append("unusual_volume")
        
        # 3. Verificar horario
        if await self._check_unusual_time(tx_data):
            anomalies.append("unusual_time")
        
        # 4. Verificar destino sospechoso
        if await self._check_suspicious_destination(tx_data):
            anomalies.append("suspicious_destination")
        
        # 5. Verificar monto inusual
        if await self._check_unusual_amount(tx_data):
            anomalies.append("unusual_amount")
        
        is_anomaly = len(anomalies) > 0
        
        if is_anomaly:
            self.anomaly_history.append({
                'timestamp': datetime.now(),
                'tx_data': tx_data,
                'anomalies': anomalies
            })
        
        return is_anomaly, anomalies
    
    async def _check_rapid_fire(self, tx_data: Dict) -> bool:
        """Detectar múltiples transacciones en poco tiempo"""
        # Implementar lógica de detección
        return False
    
    async def _check_unusual_volume(self, tx_data: Dict) -> bool:
        """Detectar volumen anormal"""
        # Implementar lógica de detección
        return False
    
    async def _check_unusual_time(self, tx_data: Dict) -> bool:
        """Detectar actividad en horas no habituales"""
        hour = datetime.now().hour
        # Horario habitual: 9 AM - 5 PM UTC
        if hour < 9 or hour > 17:
            return True
        return False
    
    async def _check_suspicious_destination(self, tx_data: Dict) -> bool:
        """Verificar destinos sospechosos"""
        # Lista de direcciones sospechosas (debería venir de DB/API)
        suspicious_addresses = []
        destination = tx_data.get('to', '')
        
        return destination in suspicious_addresses
    
    async def _check_unusual_amount(self, tx_data: Dict) -> bool:
        """Detectar montos inusuales"""
        amount = tx_data.get('amount', 0)
        
        # Establecer baseline dinámico
        if 'amount' not in self.baselines:
            self.baselines['amount'] = {'mean': 1000, 'std': 500}
        
        baseline = self.baselines['amount']
        z_score = abs(amount - baseline['mean']) / baseline['std'] if baseline['std'] > 0 else 0
        
        # Si el monto está a más de 3 desviaciones estándar
        return z_score > 3
    
    async def update_baseline(self, metric: str, value: float):
        """Actualizar línea base para una métrica"""
        if metric not in self.baselines:
            self.baselines[metric] = {'mean': value, 'std': 0, 'count': 1}
        else:
            baseline = self.baselines[metric]
            n = baseline['count']
            
            # Actualizar media incrementalmente
            new_mean = (baseline['mean'] * n + value) / (n + 1)
            
            # Actualizar varianza (algoritmo online)
            if n == 1:
                new_std = 0
            else:
                delta = value - baseline['mean']
                delta2 = value - new_mean
                new_var = ((n - 1) * baseline['std']**2 + delta * delta2) / n
                new_std = np.sqrt(new_var) if new_var > 0 else 0
            
            baseline['mean'] = new_mean
            baseline['std'] = new_std
            baseline['count'] = n + 1

class MultiSigManager:
    """Gestor de transacciones multi-firma"""
    def __init__(self, required_signatures: int = 2):
        self.required_signatures = required_signatures
        self.pending_transactions = {}
        self.authorized_signers = set()
    
    def add_signer(self, public_key: str):
        """Agregar firmante autorizado"""
        self.authorized_signers.add(public_key)
    
    def remove_signer(self, public_key: str):
        """Remover firmante"""
        if public_key in self.authorized_signers:
            self.authorized_signers.remove(public_key)
    
    async def create_transaction(self, tx_data: Dict, initiator: str) -> str:
        """Crear nueva transacción pendiente de múltiples firmas"""
        if initiator not in self.authorized_signers:
            raise PermissionError("Initiator not authorized")
        
        # Crear ID único para la transacción
        tx_id = hashlib.sha256(
            json.dumps(tx_data, sort_keys=True).encode() + 
            initiator.encode() + 
            str(datetime.now().timestamp()).encode()
        ).hexdigest()[:16]
        
        # Inicializar transacción
        self.pending_transactions[tx_id] = {
            'data': tx_data,
            'signatures': {initiator: True},
            'created_at': datetime.now(),
            'status': 'pending',
            'initiator': initiator
        }
        
        return tx_id
    
    async def sign_transaction(self, tx_id: str, signer: str) -> bool:
        """Firmar transacción pendiente"""
        if signer not in self.authorized_signers:
            return False
        
        if tx_id not in self.pending_transactions:
            return False
        
        tx = self.pending_transactions[tx_id]
        
        # Agregar firma
        tx['signatures'][signer] = True
        
        # Verificar si tenemos suficientes firmas
        if len(tx['signatures']) >= self.required_signatures:
            tx['status'] = 'approved'
            tx['approved_at'] = datetime.now()
            
            # Ejecutar transacción
            await self._execute_approved_transaction(tx_id)
            
            return True
        
        return False
    
    async def _execute_approved_transaction(self, tx_id: str):
        """Ejecutar transacción aprobada"""
        tx = self.pending_transactions[tx_id]
        
        # Aquí iría la lógica para ejecutar la transacción en blockchain
        print(f"✅ Ejecutando transacción multi-firma {tx_id}")
        
        # Simular ejecución
        await asyncio.sleep(1)
        
        # Marcar como completada
        tx['status'] = 'executed'
        tx['executed_at'] = datetime.now()
    
    async def get_transaction_status(self, tx_id: str) -> Dict:
        """Obtener estado de transacción"""
        if tx_id in self.pending_transactions:
            tx = self.pending_transactions[tx_id].copy()
            tx['signature_count'] = len(tx['signatures'])
            tx['signatures_needed'] = self.required_signatures - tx['signature_count']
            return tx
        
        return {'status': 'not_found'}

class SecurityManager:
    """Manager principal de seguridad"""
    def __init__(self):
        self.key_manager = KeyManager()
        self.audit_logger = AuditLogger()
        self.anomaly_detector = AnomalyDetector()
        self.multi_sig_manager = MultiSigManager(required_signatures=2)
        self.backup_interval = SECURITY.BACKUP_INTERVAL_HOURS
        self.last_backup = None
        self.backup_task = None
        
        # Configurar signers iniciales
        self._setup_initial_signers()
    
    def _setup_initial_signers(self):
        """Configurar firmantes iniciales"""
        # En producción, esto vendría de configuración
        self.multi_sig_manager.add_signer("owner_public_key_1")
        self.multi_sig_manager.add_signer("owner_public_key_2")
    
    async def initialize(self):
        """Inicializar sistema de seguridad"""
        print("🛡️ Inicializando sistema de seguridad...")
        
        # Cargar claves existentes
        try:
            await self.key_manager.load_from_file()
            print("✅ Claves de encriptación cargadas")
        except Exception as e:
            print(f"⚠️ No se pudieron cargar claves: {e}")
        
        # Iniciar backup automático
        self.backup_task = asyncio.create_task(self._backup_loop())
        
        # Registrar evento de inicio
        await self.audit_logger.log_event(SecurityEvent(
            timestamp=datetime.now(),
            event_type="system_start",
            severity="INFO",
            description="Security system initialized",
            source="security_manager"
        ))
        
        print("✅ Sistema de seguridad inicializado")
    
    async def shutdown(self):
        """Apagar sistema de seguridad"""
        if self.backup_task:
            self.backup_task.cancel()
        
        # Realizar backup final
        await self._perform_backup()
        
        # Registrar evento de apagado
        await self.audit_logger.log_event(SecurityEvent(
            timestamp=datetime.now(),
            event_type="system_shutdown",
            severity="INFO",
            description="Security system shutting down",
            source="security_manager"
        ))
    
    async def _backup_loop(self):
        """Loop de backup automático"""
        while True:
            try:
                await asyncio.sleep(self.backup_interval * 3600)
                await self._perform_backup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Error en backup automático: {e}")
    
    async def _perform_backup(self):
        """Realizar backup de datos de seguridad"""
        print("💾 Realizando backup de seguridad...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backup/security_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Backup de claves encriptadas
            await self.key_manager.save_to_file(f"{backup_dir}/encrypted_keys.json")
            
            # Backup de logs de auditoría
            logs_backup = []
            events = await self.audit_logger.search_events(
                start_time=datetime.now() - timedelta(days=7)
            )
            
            for event in events:
                logs_backup.append(asdict(event))
            
            with open(f"{backup_dir}/audit_logs.json", 'w') as f:
                json.dump(logs_backup, f, indent=2, default=str)
            
            # Backup de anomalías detectadas
            with open(f"{backup_dir}/anomalies.json", 'w') as f:
                json.dump(self.anomaly_detector.anomaly_history, f, indent=2, default=str)
            
            self.last_backup = datetime.now()
            
            # Registrar evento de backup
            await self.audit_logger.log_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="backup_completed",
                severity="INFO",
                description=f"Security backup completed to {backup_dir}",
                source="security_manager"
            ))
            
            print(f"✅ Backup completado: {backup_dir}")
            
        except Exception as e:
            print(f"❌ Error en backup: {e}")
            
            await self.audit_logger.log_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="backup_failed",
                severity="WARNING",
                description=f"Security backup failed: {str(e)}",
                source="security_manager"
            ))
    
    async def encrypt_and_store_key(self, private_key: str, key_name: str = "default") -> str:
        """Encriptar y almacenar clave privada"""
        try:
            encrypted = self.key_manager.encrypt_private_key(private_key, key_name)
            
            # Guardar inmediatamente
            await self.key_manager.save_to_file()
            
            # Registrar evento
            await self.audit_logger.log_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="key_encrypted",
                severity="INFO",
                description=f"Private key encrypted and stored as '{key_name}'",
                source="key_manager",
                user="system"
            ))
            
            return encrypted
            
        except Exception as e:
            await self.audit_logger.log_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="key_encryption_failed",
                severity="CRITICAL",
                description=f"Failed to encrypt private key: {str(e)}",
                source="key_manager",
                user="system"
            ))
            raise
    
    async def decrypt_and_use_key(self, key_name: str = "default") -> str:
        """Desencriptar y usar clave privada"""
        try:
            if key_name not in self.key_manager.encrypted_keys:
                raise ValueError(f"Key '{key_name}' not found")
            
            encrypted = self.key_manager.encrypted_keys[key_name]
            decrypted = self.key_manager.decrypt_private_key(encrypted, key_name)
            
            # Registrar evento
            await self.audit_logger.log_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="key_decrypted",
                severity="INFO",
                description=f"Private key '{key_name}' decrypted for use",
                source="key_manager",
                user="system"
            ))
            
            return decrypted
            
        except Exception as e:
            await self.audit_logger.log_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="key_decryption_failed",
                severity="CRITICAL",
                description=f"Failed to decrypt private key '{key_name}': {str(e)}",
                source="key_manager",
                user="system"
            ))
            raise
    
    async def check_transaction_security(self, tx_data: Dict) -> Tuple[bool, List[str]]:
        """Verificar seguridad de transacción"""
        # Detectar anomalías
        is_anomaly, anomalies = await self.anomaly_detector.analyze_transaction(tx_data)
        
        if is_anomaly:
            # Registrar anomalía
            await self.audit_logger.log_event(SecurityEvent(
                timestamp=datetime.now(),
                event_type="anomaly_detected",
                severity="WARNING",
                description=f"Transaction anomaly detected: {', '.join(anomalies)}",
                source="anomaly_detector",
                metadata={'tx_data': tx_data, 'anomalies': anomalies}
            ))
        
        return not is_anomaly, anomalies
    
    async def create_multi_sig_transaction(self, tx_data: Dict, initiator: str) -> str:
        """Crear transacción multi-firma"""
        # Verificar seguridad primero
        is_secure, anomalies = await self.check_transaction_security(tx_data)
        
        if not is_secure and 'suspicious_destination' in anomalies:
            raise SecurityError("Transaction to suspicious destination")
        
        # Crear transacción
        tx_id = await self.multi_sig_manager.create_transaction(tx_data, initiator)
        
        # Registrar evento
        await self.audit_logger.log_event(SecurityEvent(
            timestamp=datetime.now(),
            event_type="multi_sig_created",
            severity="INFO",
            description=f"Multi-signature transaction created: {tx_id}",
            source="multi_sig_manager",
            user=initiator,
            metadata={'tx_id': tx_id, 'tx_data': tx_data}
        ))
        
        return tx_id
    
    async def get_security_report(self) -> Dict:
        """Generar reporte de seguridad"""
        # Obtener eventos recientes
        recent_events = await self.audit_logger.search_events(
            start_time=datetime.now() - timedelta(hours=24)
        )
        
        # Contar por severidad
        severity_counts = {'INFO': 0, 'WARNING': 0, 'CRITICAL': 0}
        for event in recent_events:
            severity_counts[event.severity] += 1
        
        return {
            'last_backup': self.last_backup.isoformat() if self.last_backup else None,
            'encrypted_keys_count': len(self.key_manager.encrypted_keys),
            'multi_sig_pending': len(self.multi_sig_manager.pending_transactions),
            'anomalies_detected': len(self.anomaly_detector.anomaly_history),
            'recent_events': {
                'total': len(recent_events),
                'by_severity': severity_counts
            },
            'key_versions': self.key_manager.key_versions
        }

class SecurityError(Exception):
    """Excepción de seguridad"""
    pass

# Instancia global
security_manager = SecurityManager()

async def test_security_system():
    """Función de prueba"""
    print("🧪 Probando sistema de seguridad...")
    
    await security_manager.initialize()
    
    try:
        # Encriptar clave de prueba
        test_key = "test_private_key_1234567890"
        encrypted = await security_manager.encrypt_and_store_key(test_key, "test_key")
        print(f"✅ Clave encriptada: {encrypted[:50]}...")
        
        # Desencriptar clave
        decrypted = await security_manager.decrypt_and_use_key("test_key")
        print(f"✅ Clave desencriptada: {decrypted}")
        
        # Verificar que coincidan
        assert test_key == decrypted, "Keys don't match!"
        
        # Crear transacción multi-firma
        tx_data = {
            'to': 'destination_wallet',
            'amount': 1000,
            'token': 'USDC'
        }
        
        tx_id = await security_manager.create_multi_sig_transaction(
            tx_data, 
            "owner_public_key_1"
        )
        print(f"✅ Transacción multi-firma creada: {tx_id}")
        
        # Obtener reporte
        report = await security_manager.get_security_report()
        print(f"📊 Reporte de seguridad: {report['recent_events']['total']} eventos recientes")
        
    finally:
        await security_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(test_security_system())