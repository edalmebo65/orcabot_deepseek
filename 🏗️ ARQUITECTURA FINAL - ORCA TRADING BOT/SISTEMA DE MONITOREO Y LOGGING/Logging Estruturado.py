class StructuredLogger:
    """Logger estructurado para análisis posterior"""
    
    LOG_SCHEMA = {
        'timestamp': 'ISO8601',
        'level': 'INFO/WARN/ERROR',
        'component': 'trading/api/wallet',
        'action': 'trade/swap/balance_check',
        'details': 'dict con datos específicos',
        'performance': 'ms de ejecución',
        'success': 'bool',
    }
    
    def log_trade(self, trade_data):
        """Log estructurado de trade"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'INFO',
            'component': 'trading',
            'action': 'execute_trade',
            'details': {
                'pair': trade_data['pair'],
                'amount': trade_data['amount'],
                'price': trade_data['price'],
                'fee': trade_data['fee'],
            },
            'performance': trade_data['execution_time_ms'],
            'success': trade_data['success'],
        }
        self.write_log(log_entry)