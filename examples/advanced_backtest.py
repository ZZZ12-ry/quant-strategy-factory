"""
高级回测示例 - 展示完整功能
"""
import sys
sys.path.insert(0, '..')

from src.strategy_factory import StrategyFactory
from src.backtest_engine import BacktestEngine
from src.optimizer import Optimizer
from src.monte_carlo import MonteCarloEngine
from src.portfolio_analyzer import PortfolioAnalyzer
from src.report_generator import ReportGenerator
from src.data.data_manager import DataManager
import pandas as pd
import numpy as np
from datetime import datetime


def generate_sample_data(symbol: str = "RB.SHF", days: int = 500) -> pd.DataFrame:
    """生成模拟数据用于测试"""
    np.random.seed(42)
    
    dates = pd.date_range(start="2024-01-01", periods=days, freq='D')
    
    # 生成随机价格序列（几何布朗运动）
    initial_price = 4000
    returns = np.random.normal(0.0005, 0.02, days)  # 日收益均值 0.05%，波动 2%
    price_series = initial_price * np.cumprod(1 + returns)
    
    # 生成 OHLCV
    df = pd.DataFrame({
        'timestamp': dates,
        'symbol': symbol,
        'open': price_series * (1 + np.random.uniform(-0.005, 0.005, days)),
        'high': price_series * (1 + np.random.uniform(0, 0.02, days)),
        'low': price_series * (1 - np.random.uniform(0, 0.02, days)),
        'close': price_series,
        'volume': np.random.randint(1000, 10000, days)
    })
    
    return df


def main():
    print("=" * 60)
    print("量化策略工厂 - 高级回测示例")
    print("=" * 60)
    
    # 1. 生成/加载数据
    print("\n[1/6] 加载数据...")
    data = generate_sample_data("RB.SHF", 500)
    print(f"数据范围：{data['timestamp'].min()} ~ {data['timestamp'].max()}")
    print(f"数据条数：{len(data)}")
    
    # 2. 创建策略工厂
    print("\n[2/6] 创建策略...")
    factory = StrategyFactory()
    print(f"可用策略：{factory.list_strategies()}")
    
    # 3. 运行多个策略回测
    print("\n[3/6] 运行策略回测...")
    results = {}
    
    for strategy_name in ["DualMA", "BollingerMR", "RSIMR"]:
        print(f"\n  回测策略：{strategy_name}")
        strategy = factory.create(strategy_name)
        
        engine = BacktestEngine(
            strategy=strategy,
            initial_cash=1000000,
            commission_rate=0.0003,
            slippage=1.0
        )
        
        result = engine.run(data, "RB.SHF")
        results[strategy_name] = result
        
        print(f"    总收益：{result.total_return:.2f}%")
        print(f"    夏普比率：{result.sharpe_ratio:.2f}")
        print(f"    最大回撤：{result.max_drawdown:.2f}%")
    
    # 4. 参数优化示例
    print("\n[4/6] 参数优化示例 (DualMA)...")
    strategy_class = factory._strategies["DualMA"]
    
    optimizer = Optimizer(
        strategy_class=strategy_class,
        metric="sharpe_ratio"
    )
    
    # 小范围网格搜索示例
    param_grid = {
        "fast_ma": [5, 10, 15],
        "slow_ma": [20, 30, 40]
    }
    
    best_params, best_result = optimizer.grid_search(
        param_grid=param_grid,
        data=data,
        symbol="RB.SHF"
    )
    
    print(f"最优参数：{best_params}")
    
    # 5. Monte Carlo 压力测试
    print("\n[5/6] Monte Carlo 压力测试...")
    best_strategy = strategy_class(**best_params)
    
    mc_engine = MonteCarloEngine(
        strategy=best_strategy,
        num_simulations=200
    )
    
    mc_result = mc_engine.run(data, "RB.SHF", method="candle")
    
    print(f"原始夏普：{mc_result.original_sharpe:.2f}")
    print(f"模拟均值：{mc_result.mean_sharpe:.2f}")
    print(f"5 分位数：{mc_result.percentile_5:.2f}")
    print(f"稳健性评分：{mc_result.robustness_score:.2f}")
    print(f"策略稳健：{'是' if mc_result.is_robust() else '否'}")
    
    # 6. 组合分析
    print("\n[6/6] 组合分析...")
    analyzer = PortfolioAnalyzer()
    
    for name, result in results.items():
        analyzer.add_strategy(name, result)
    
    # 优化权重
    optimal_weights = analyzer.optimize_weights(method="sharpe")
    print("最优权重配置:")
    for name, weight in optimal_weights.items():
        print(f"  {name}: {weight:.1%}")
    
    # 生成组合报告
    portfolio_result = analyzer.analyze()
    print(f"\n组合夏普比率：{portfolio_result.portfolio_sharpe:.2f}")
    print(f"分散化比率：{portfolio_result.diversification_ratio:.2f}")
    
    # 7. 生成报告
    print("\n[生成报告...]")
    report_gen = ReportGenerator(output_dir="./reports")
    
    for name, result in results.items():
        filepath = report_gen.save_report(
            result=result,
            strategy_name=name,
            format="markdown"
        )
        print(f"  {name}: {filepath}")
    
    print("\n" + "=" * 60)
    print("回测完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
