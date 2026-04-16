"""
测试所有 16 个策略
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from src.strategy_factory import StrategyFactory
from src.backtest_engine import BacktestEngine

def generate_sample_data(days=300):
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=days, freq='D')
    initial_price = 4000
    returns = np.random.normal(0.0005, 0.02, days)
    price_series = initial_price * np.cumprod(1 + returns)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'symbol': 'RB.SHF',
        'open': price_series * (1 + np.random.uniform(-0.005, 0.005, days)),
        'high': price_series * (1 + np.random.uniform(0, 0.02, days)),
        'low': price_series * (1 - np.random.uniform(0, 0.02, days)),
        'close': price_series,
        'volume': np.random.randint(1000, 10000, days)
    })
    return df

print("=" * 60)
print("Testing All 16 Strategies")
print("=" * 60)

data = generate_sample_data(300)
factory = StrategyFactory()
strategies = factory.list_strategies()

results = []

for strategy_name in strategies:
    try:
        strategy = factory.create(strategy_name)
        engine = BacktestEngine(strategy, initial_cash=1000000)
        result = engine.run(data, "RB.SHF")
        
        results.append({
            'name': strategy_name,
            'return': result.total_return,
            'sharpe': result.sharpe_ratio,
            'max_dd': result.max_drawdown,
            'trades': result.total_trades
        })
        
        print(f"  {strategy_name:20s} Return: {result.total_return:7.2f}%  Sharpe: {result.sharpe_ratio:6.2f}  Trades: {result.total_trades:3d}")
    
    except Exception as e:
        print(f"  {strategy_name:20s} ERROR: {str(e)}")

print("\n" + "=" * 60)
print("Top 5 by Sharpe Ratio:")
print("=" * 60)

results_sorted = sorted(results, key=lambda x: x['sharpe'], reverse=True)
for i, r in enumerate(results_sorted[:5]):
    print(f"  {i+1}. {r['name']:20s} Sharpe: {r['sharpe']:.2f}  Return: {r['return']:.1f}%")

print("\n" + "=" * 60)
print("All Tests Completed!")
print("=" * 60)
