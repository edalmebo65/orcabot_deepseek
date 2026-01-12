class SecuritySystem:
    """Sistema de seguridad completo"""
    
    def __init__(self):
        # Encriptación AES-256 para claves privadas
        self.cipher = AESCipher(os.getenv('ENCRYPTION_KEY'))
        
        # 2FA para operaciones críticas
        self.two_fa = TwoFactorAuth()
        
        # Auditoría de todas las operaciones
        self.audit_log = AuditLogger()
        
        # Rate limiting para API calls
        self.rate_limiter = RateLimiter()
    
    def secure_private_key(self, raw_key: str) -> str:
        """Encriptar clave privada"""
        encrypted = self.cipher.encrypt(raw_key)
        return base64.b64encode(encrypted).decode()
    
    def validate_transaction(self, tx, amount) -> bool:
        """Validar transacción con múltiples checks"""
        checks = [
            self.check_amount_limit(amount),
            self.check_recipient(tx),
            self.check_frequency(),
            self.require_2fa_if_needed(amount),
        ]
        return all(checks)