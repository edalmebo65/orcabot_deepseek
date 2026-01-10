# Capital management
MAX_CAPITAL_PER_TRADE_PCT = Decimal('0.10')  # 10% per trade
MAX_CONCURRENT_OPERATIONS = 5                # Max simultaneous trades

# Risk management
STOP_LOSS_PCT = Decimal('0.02')              # 2% initial stop loss
TAKE_PROFIT_PCT = Decimal('0.05')            # 5% initial take profit
RISK_ZERO_BUFFER_PCT = Decimal('0.002')      # 0.2% risk zero buffer

# Timeframes
ACTIVE_TIMEFRAMES = ['5m', '15m', '1h']      # Analysis timeframes