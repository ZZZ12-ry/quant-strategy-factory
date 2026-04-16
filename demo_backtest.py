"""
示例：双均线策略回测螺纹钢
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from src.strategy_factory import StrategyFactory
from src.backtest_engine import BacktestEngine
from src.report_generator import ReportGenerator

print("=" * 60)
print("双均线策略回测示例")
print("=" * 60)

# ==================== 1. 准备数据 ====================
print("\n[1/4] 准备数据...")

# 生成模拟数据（实际使用时从数据源获取）
np.random.seed(42)
dates = pd.date_range(start="2024-01-01", periods=365, freq='D')
returns = np.random.normal(0.0005, 0.02, 365)
price_series = 4000 * np.cumprod(1 + returns)

data = pd.DataFrame({
    'timestamp': dates,
    'symbol': 'RB.SHF',
    'open': price_series * (1 + np.random.uniform(-0.005, 0.005, 365)),
    'high': price_series * (1 + np.random.uniform(0, 0.02, 365)),
    'low': price_series * (1 - np.random.uniform(0, 0.02, 365)),
    'close': price_series,
    'volume': np.random.randint(1000, 10000, 365)
})

print(f"  数据范围：{data['timestamp'].min().date()} ~ {data['timestamp'].max().date()}")
print(f"  数据条数：{len(data)}")

# ==================== 2. 创建策略 ====================
print("\n[2/4] 创建策略...")

factory = StrategyFactory()
strategy = factory.create("DualMA", fast_ma=10, slow_ma=30)

print(f"  策略名称：DualMA (双均线)")
print(f"  策略参数：fast_ma=10, slow_ma=30")

# ==================== 3. 运行回测 ====================
print("\n[3/4] 运行回测...")

engine = BacktestEngine(
    strategy=strategy,
    initial_cash=1000000,      # 初始资金 100 万
    commission_rate=0.0003,    # 手续费万分之三
    slippage=1.0               # 滑点 1 跳
)

result = engine.run(data, "RB.SHF")

print(f"  回测完成！")

# ==================== 4. 查看结果 ====================
print("\n[4/4] 查看回测结果")
print("\n" + "=" * 60)
print("回测报告 - DualMA (螺纹钢)")
print("=" * 60)

print("\n【基本信息】")
print(f"  策略名称：{result.strategy_name}")
print(f"  回测品种：{result.symbol}")
print(f"  回测周期：{result.start_date[:10]} ~ {result.end_date[:10]}")
print(f"  初始资金：{result.initial_cash:,.0f}")
print(f"  最终资金：{result.final_cash:,.0f}")

print("\n【业绩指标】")
print(f"  总收益率：{result.total_return:.2f}%")
print(f"  年化收益：{result.annualized_return:.2f}%")
print(f"  夏普比率：{result.sharpe_ratio:.2f}")
print(f"  最大回撤：{result.max_drawdown:.2f}%")
print(f"  卡玛比率：{result.annualized_return / abs(result.max_drawdown) if result.max_drawdown != 0 else 0:.2f}")

print("\n【交易统计】")
print(f"  总交易次数：{result.total_trades}")
print(f"  胜率：{result.win_rate:.2f}%")
print(f"  盈亏比：{result.profit_loss_ratio:.2f}")
print(f"  平均每笔收益：{result.avg_trade_return:.2f}")
print(f"  最长连亏：{result.max_consecutive_losses} 次")

print("\n【权益曲线】")
print(f"  初始：{result.equity_curve[0]:,.0f}")
print(f"  最终：{result.equity_curve[-1]:,.0f}")
print(f"  最高：{max(result.equity_curve):,.0f}")
print(f"  最低：{min(result.equity_curve):,.0f}")

# ==================== 5. 保存报告 ====================
print("\n" + "=" * 60)
print("保存报告...")

report_gen = ReportGenerator(output_dir="./reports")
filepath = report_gen.save_report(
    result=result,
    strategy_name="DualMA",
    format="markdown"
)

print(f"  报告已保存：{filepath}")

print("\n" + "=" * 60)
print("回测完成！")
print("=" * 60)

# ==================== 6. 可视化 (可选) ====================
print("\n【可选】是否绘制权益曲线图？(y/n)")
# 实际使用时可以：
# import matplotlib.pyplot as plt
# plt.figure(figsize=(12, 6))
# plt.plot(result.equity_curve)
# plt.title('DualMA Strategy Equity Curve')
# plt.xlabel('Days')
# plt.ylabel('Equity')
# plt.grid(True, alpha=0.3)
# plt.show()
