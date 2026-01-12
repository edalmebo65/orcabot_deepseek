METRICS = {
    # Performance
    'trades_per_hour': 'int',
    'avg_execution_time_ms': 'float',
    'api_latency_p95': 'float',
    
    # Profitability
    'total_pnl': 'float',
    'win_rate': 'float',
    'sharpe_ratio': 'float',
    'max_drawdown': 'float',
    
    # Risk
    'position_size_ratio': 'float',
    'slippage_avg': 'float',
    'failed_transactions': 'int',
    
    # Market
    'liquidity_depth': 'dict',
    'price_disparity': 'float',
    'volatility_index': 'float',
}