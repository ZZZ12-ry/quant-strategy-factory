"""
真实数据回测示例 - 使用 Akshare
测试新增的套利策略和多因子策略
"""
import pandas as pd
import numpy as np
from datetime import datetime

print("\n" + "="*60)
print("真实数据回测示例")
print("="*60)

# 检查是否安装 akshare
try:
    import akshare as ak
    HAS_AKSHARE = True
    print("\n[OK] Akshare 已安装")
except ImportError:
    HAS_AKSHARE = False
    print("\n[WARN] Akshare 未安装")
    print("  安装命令：pip install akshare")
    print("\n  使用模拟数据演示...")

# === 获取真实数据或生成模拟数据 ===
if HAS_AKSHARE:
    print("\n正在获取真实期货数据...")
    try:
        # 获取螺纹钢期货数据
        df = ak.futures_zh_daily_sina(symbol="RB2405")
        print(f"[OK] 获取到 {len(df)} 条数据")
        
        # 数据清洗
        df = df.rename(columns={
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })
        df['timestamp'] = pd.to_datetime(df['date'])
        df['symbol'] = 'RB2405'
        df = df.sort_values('timestamp').reset_index(drop=True)
        
    except Exception as e:
        print(f"[WARN] 获取数据失败：{e}")
        print("  切换到模拟数据...")
        HAS_AKSHARE = False

if not HAS_AKSHARE:
    # 生成模拟数据
    print("\n生成模拟数据...")
    np.random.seed(42)
    n_days = 300
    
    df = pd.DataFrame({
        'open': 4000 + np.cumsum(np.random.randn(n_days)),
        'high': 4000 + np.cumsum(np.abs(np.random.randn(n_days))) + 50,
        'low': 4000 + np.cumsum(-np.abs(np.random.randn(n_days))) - 50,
        'close': 4000 + np.cumsum(np.random.randn(n_days)),
        'volume': np.random.randint(10000, 100000, n_days),
        'timestamp': pd.date_range('2023-01-01', periods=n_days),
        'symbol': 'RB_TEST'
    })
    df['close'] = df['close'].clip(lower=3000)
    print(f"[OK] 生成 {len(df)} 条模拟数据")

# === 测试 1: 双均线策略（基准） ===
print("\n" + "-"*60)
print("测试 1: 双均线策略（基准）")
print("-"*60)

from src.strategy_factory import StrategyFactory
factory = StrategyFactory()

strategy = factory.create("DualMA", fast_ma=10, slow_ma=30)

signals = []
for idx, row in df.iterrows():
    signal = strategy.on_bar(row)
    if signal:
        signals.append(signal)

print(f"生成信号数：{len(signals)}")
print(f"买入信号：{len([s for s in signals if s.direction == 'long'])}")
print(f"卖出信号：{len([s for s in signals if s.direction == 'short'])}")

# === 测试 2: 期现套利策略（新增） ===
print("\n" + "-"*60)
print("测试 2: 期现套利策略（新增）")
print("-"*60)

# 生成现货价格（模拟）
df['spot_price'] = df['close'] - 50 - np.random.randn(len(df)) * 10

strategy = factory.create("SpotFuturesArbitrage", 
                         zscore_entry=2.0,
                         zscore_exit=0.5,
                         lookback_window=60)

signals = []
for idx, row in df.iterrows():
    signal = strategy.on_bar(row)
    if signal:
        signals.append(signal)

print(f"生成信号数：{len(signals)}")
print(f"开仓信号：{len([s for s in signals if 'long' in s.direction or 'short' in s.direction])}")
print(f"平仓信号：{len([s for s in signals if 'close' in s.direction])}")

# === 测试 3: RL 交易策略（新增） ===
print("\n" + "-"*60)
print("测试 3: RL 交易策略（新增）")
print("-"*60)

strategy = factory.create("RLTrading",
                         lookback_window=20,
                         training_episodes=50)

signals = []
for idx, row in df.iterrows():
    signal = strategy.on_bar(row)
    if signal:
        signals.append(signal)

print(f"生成信号数：{len(signals)}")
print(f"RL 策略已在线学习")

# === 总结 ===
print("\n" + "="*60)
print("回测完成总结")
print("="*60)

print("\n策略表现对比:")
print("  1. 双均线策略 - 传统趋势跟踪")
print("  2. 期现套利策略 - 市场中性套利（新增）")
print("  3. RL 交易策略 - 强化学习（新增）")

print("\n下一步建议:")
print("  1. 使用更多历史数据回测")
print("  2. 添加交易成本和滑点")
print("  3. 计算策略收益指标")
print("  4. 对比多个品种")

print("\n" + "="*60)
