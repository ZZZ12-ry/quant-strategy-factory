"""
基于论文《Expected Return in Night and Day: The Role of Trading Volume》的策略示例
"""
from src.strategy_factory import StrategyFactory
import pandas as pd
import numpy as np


def run_volume_strategy_demo():
    """运行成交量策略演示"""
    print("\n" + "="*70)
    print("基于学术论文的量化策略演示")
    print("论文：Expected Return in Night and Day: The Role of Trading Volume")
    print("="*70)
    
    # 1. 创建策略工厂
    factory = StrategyFactory()
    
    print(f"\n[1] 策略工厂已加载，共 {len(factory.list_strategies())} 个策略")
    
    # 2. 获取新策略
    print(f"\n[2] 可用策略分类:")
    categories = factory.get_strategy_categories()
    for cat, strategies in categories.items():
        print(f"    {cat}: {len(strategies)} 个")
        if cat == '成交量策略':
            for s in strategies:
                print(f"      -> {s} [NEW]")
    
    # 3. 创建成交量策略
    print(f"\n[3] 创建成交量策略...")
    strategy = factory.create(
        "VolumeNightDay",
        volume_ma_period=20,
        volume_zscore_threshold=1.5,
        price_ma_period=20,
        momentum_period=5,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        trailing_stop_pct=0.015
    )
    print(f"    [OK] 策略创建成功")
    print(f"    参数:")
    for key, value in strategy.params.items():
        print(f"      {key}: {value}")
    
    # 4. 获取数据
    print(f"\n[4] 获取回测数据...")
    try:
        import akshare as ak
        df = ak.futures_zh_daily_sina(symbol="RB2405")
        df = df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low',
            'close': 'close', 'volume': 'volume'
        })
        df['timestamp'] = pd.to_datetime(df['date'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"    [OK] 获取螺纹钢期货数据：{len(df)} 条")
    except Exception as e:
        print(f"    [WARN] 获取数据失败：{e}")
        print(f"    使用模拟数据...")
        np.random.seed(42)
        n_days = 300
        returns = np.random.randn(n_days) * 0.02 + 0.0003
        close_prices = 100 * np.exp(np.cumsum(returns))
        base_volume = np.random.randint(10000, 50000, n_days)
        vol_clustering = np.abs(returns) * 100000
        volume = (base_volume + vol_clustering).astype(int)
        df = pd.DataFrame({
            'open': close_prices * (1 + np.random.randn(n_days) * 0.005),
            'high': close_prices * (1 + np.abs(np.random.randn(n_days) * 0.01)),
            'low': close_prices * (1 - np.abs(np.random.randn(n_days) * 0.01)),
            'close': close_prices,
            'volume': volume,
            'timestamp': pd.date_range('2024-01-01', periods=n_days)
        })
    
    # 5. 运行回测
    print(f"\n[5] 运行回测...")
    signals = []
    trades = []
    current_trade = None
    
    for idx, row in df.iterrows():
        signal = strategy.on_bar(row)
        if signal:
            signals.append(signal)
            
            if signal.direction in ['long', 'short']:
                current_trade = {
                    'entry_time': signal.timestamp,
                    'entry_price': signal.price,
                    'direction': signal.direction
                }
            elif signal.direction in ['close_long', 'close_short', 'stop_loss', 'take_profit', 'trailing_stop']:
                if current_trade:
                    current_trade['exit_time'] = signal.timestamp
                    current_trade['exit_price'] = signal.price
                    current_trade['exit_type'] = signal.direction
                    current_trade['pnl_pct'] = (signal.price - current_trade['entry_price']) / current_trade['entry_price']
                    if current_trade['direction'] == 'short':
                        current_trade['pnl_pct'] = -current_trade['pnl_pct']
                    trades.append(current_trade)
                    current_trade = None
    
    # 6. 输出结果
    print(f"\n[6] 回测结果")
    print(f"    " + "="*60)
    print(f"    总信号数：{len(signals)}")
    print(f"    完成交易：{len(trades)}")
    
    if trades:
        winning = [t for t in trades if t['pnl_pct'] > 0]
        losing = [t for t in trades if t['pnl_pct'] <= 0]
        
        win_rate = len(winning) / len(trades) * 100
        avg_win = np.mean([t['pnl_pct'] for t in winning]) * 100
        avg_loss = np.mean([t['pnl_pct'] for t in losing]) * 100
        total_return = sum([t['pnl_pct'] for t in trades]) * 100
        
        returns = [t['pnl_pct'] for t in trades]
        sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252) if len(returns) > 1 else 0
        
        print(f"\n    交易统计:")
        print(f"      胜率：{win_rate:.1f}%")
        print(f"      平均盈利：{avg_win:.2f}%")
        print(f"      平均亏损：{avg_loss:.2f}%")
        if avg_loss != 0:
            print(f"      盈亏比：{abs(avg_win/avg_loss):.2f}")
        print(f"      总收益：{total_return:.2f}%")
        print(f"      夏普比率：{sharpe:.2f}")
        
        # 详细交易记录
        print(f"\n    交易明细（前 10 笔）:")
        for i, t in enumerate(trades[:10], 1):
            print(f"      {i}. {t['direction'].upper()} | "
                  f"入场：{t['entry_price']:.2f} -> "
                  f"出场：{t['exit_price']:.2f} | "
                  f"收益：{t['pnl_pct']*100:.2f}% | "
                  f"退出：{t['exit_type']}")
        if len(trades) > 10:
            print(f"      ... 还有 {len(trades)-10} 笔交易")
    
    print(f"\n    " + "="*60)
    print(f"[OK] 演示完成")
    
    return strategy, df, signals, trades


if __name__ == "__main__":
    strategy, data, signals, trades = run_volume_strategy_demo()
    
    print(f"\n提示:")
    print(f"    - 策略文件：src/strategies/volume_night_day.py")
    print(f"    - 论文参考：Expected Return in Night and Day: The Role of Trading Volume")
    print(f"    - 可以调整参数优化策略表现")
