"""
示例：基础回测 - 使用双均线策略回测螺纹钢
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.strategy_factory import StrategyFactory
from src.backtest_engine import BacktestEngine


def generate_mock_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """生成模拟 K 线数据"""
    np.random.seed(42)
    
    dates = pd.date_range(start="2024-01-01", periods=days, freq='D')
    
    # 生成随机价格（随机游走）
    prices = [4000]  # 初始价格
    for _ in range(days - 1):
        change = np.random.randn() * 50  # 每日波动
        prices.append(prices[-1] + change)
    
    prices = np.array(prices)
    
    # 生成 OHLCV
    data = pd.DataFrame({
        'timestamp': dates,
        'symbol': symbol,
        'open': prices + np.random.randn(days) * 10,
        'high': prices + np.abs(np.random.randn(days) * 30),
        'low': prices - np.abs(np.random.randn(days) * 30),
        'close': prices,
        'volume': np.random.randint(1000, 10000, days)
    })
    
    # 确保 high >= close >= low
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)
    
    return data


def main():
    print("=" * 60)
    print("量化策略工厂 - 基础回测示例")
    print("=" * 60)
    
    # 1. 创建策略
    factory = StrategyFactory()
    print(f"\n可用策略：{factory.list_strategies()}")
    
    strategy = factory.create("DualMA", fast_ma=10, slow_ma=30)
    print(f"已创建策略：{strategy}")
    
    # 2. 生成模拟数据
    print("\n生成模拟数据...")
    data = generate_mock_data("RB", days=365)
    print(f"数据范围：{data['timestamp'].min()} ~ {data['timestamp'].max()}")
    print(f"数据条数：{len(data)}")
    
    # 3. 创建回测引擎
    engine = BacktestEngine(
        strategy=strategy,
        initial_cash=1000000,
        commission_rate=0.0003,
        slippage=1.0,
        contract_multiplier=10  # 螺纹钢乘数
    )
    
    # 4. 运行回测
    print("\n运行回测...")
    results = engine.run(data, symbol="RB")
    
    # 5. 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"策略名称：{results.strategy_name}")
    print(f"回测品种：{results.symbol}")
    print(f"回测周期：{results.start_date} ~ {results.end_date}")
    print(f"初始资金：{results.initial_cash:,.0f}")
    print(f"最终资金：{results.final_cash:,.0f}")
    print(f"总收益率：{results.total_return:.2f}%")
    print(f"年化收益：{results.annualized_return:.2f}%")
    print(f"夏普比率：{results.sharpe_ratio:.2f}")
    print(f"最大回撤：{results.max_drawdown:.2f}%")
    print(f"总交易次数：{results.total_trades}")
    print(f"胜率：{results.win_rate:.2f}%")
    print(f"盈亏比：{results.profit_loss_ratio:.2f}")
    print(f"平均每笔收益：{results.avg_trade_return:,.2f}")
    print(f"最长连亏：{results.max_consecutive_losses} 次")
    print("=" * 60)
    
    # 6. 保存结果
    import json
    output = {
        "strategy_name": results.strategy_name,
        "symbol": results.symbol,
        "total_return": results.total_return,
        "annualized_return": results.annualized_return,
        "sharpe_ratio": results.sharpe_ratio,
        "max_drawdown": results.max_drawdown,
        "total_trades": results.total_trades,
        "win_rate": results.win_rate,
        "profit_loss_ratio": results.profit_loss_ratio,
    }
    
    with open("backtest_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n结果已保存到 backtest_result.json")


if __name__ == "__main__":
    main()
