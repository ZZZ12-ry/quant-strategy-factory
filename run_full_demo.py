"""
量化策略工厂 - 综合演示

一键运行完整流程：
1. 获取历史数据（带缓存）
2. 批量回测
3. 样本外验证
4. 模拟盘测试
5. 生成报告

⚠️ 重要：这是从学习到实盘的完整演示
"""
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 导入模块
from src.data.historical_data_fetcher import HistoricalDataFetcher
from src.data.data_cache import DataCache
from src.backtest.realistic_backtester import RealisticBacktester, TradingCosts
from src.validation.out_of_sample_validator import OutOfSampleValidator, SplitConfig
from src.trading.simulated_account import SimulatedTradingAccount, OrderType, OrderSide
from src.risk.risk_manager import RiskManager, PositionLimits, LossLimits


def run_full_demo():
    """运行完整演示流程"""
    
    print("\n" + "="*70)
    print("量化策略工厂 - 综合演示")
    print("="*70)
    print(f"开始时间：{datetime.now()}")
    
    # ========== Step 1: 获取历史数据 ==========
    print(f"\n{'='*70}")
    print("Step 1: 获取历史数据")
    print(f"{'='*70}")
    
    fetcher = HistoricalDataFetcher()
    cache = DataCache()
    
    # 测试品种
    test_symbols = ['RB2405', 'HC2405', 'CU2405']
    
    # 自动更新缓存
    cache.auto_update(fetcher, test_symbols, max_age_days=7)
    
    # 加载数据
    data_dict = {}
    for symbol in test_symbols:
        data = cache.load_data(symbol, max_age_days=30)
        if data is not None:
            data_dict[symbol] = data
    
    if not data_dict:
        print("\n[WARN] 无可用数据，使用模拟数据...")
        # 生成模拟数据
        np.random.seed(42)
        for symbol in test_symbols:
            n = 500
            close = 100 * np.exp(np.cumsum(np.random.randn(n) * 0.02))
            data = pd.DataFrame({
                'date': pd.date_range('2020-01-01', periods=n),
                'open': close * (1 + np.random.randn(n) * 0.005),
                'high': close * (1 + np.abs(np.random.randn(n) * 0.01)),
                'low': close * (1 - np.abs(np.random.randn(n) * 0.01)),
                'close': close,
                'volume': np.random.randint(10000, 50000, n),
                'symbol': symbol
            })
            data_dict[symbol] = data
    
    print(f"\n可用数据：{len(data_dict)} 个品种")
    
    # ========== Step 2: 批量回测 ==========
    print(f"\n{'='*70}")
    print("Step 2: 批量回测")
    print(f"{'='*70}")
    
    # 定义策略
    def simple_ma_strategy(data):
        """简单双均线策略"""
        if len(data) < 50:
            return {'total_return': 0, 'sharpe': 0, 'max_drawdown': 0}
        
        # 计算均线
        ma5 = data['close'].rolling(5).mean()
        ma20 = data['close'].rolling(20).mean()
        
        # 生成信号
        signals = np.where(ma5 > ma20, 1, -1)
        
        # 计算收益
        returns = data['close'].pct_change()
        strategy_returns = signals.shift(1) * returns
        
        # 绩效指标
        total_return = (1 + strategy_returns).prod() - 1
        sharpe = strategy_returns.mean() / (strategy_returns.std() + 1e-8) * np.sqrt(252)
        max_dd = ((1 + strategy_returns).cummax() - (1 + strategy_returns).cumsum()).max()
        
        return {
            'total_return': total_return * 100,
            'sharpe': sharpe,
            'max_drawdown': max_dd * 100
        }
    
    # 批量回测
    from src.data.historical_data_fetcher import BatchBacktester
    backtester = BatchBacktester(simple_ma_strategy, initial_capital=1000000)
    results = backtester.backtest_multiple(data_dict)
    
    # ========== Step 3: 样本外验证 ==========
    print(f"\n{'='*70}")
    print("Step 3: 样本外验证")
    print(f"{'='*70}")
    
    validator = OutOfSampleValidator(
        SplitConfig(
            train_ratio=0.6,
            walk_forward_window=252,
            walk_forward_step=63
        )
    )
    
    # 对第一个品种进行验证
    if data_dict:
        first_symbol = list(data_dict.keys())[0]
        first_data = data_dict[first_symbol]
        
        print(f"\n验证品种：{first_symbol}")
        
        walk_results = validator.walk_forward_analysis(
            first_data,
            lambda train, test: simple_ma_strategy(test),
            n_splits=3
        )
    
    # ========== Step 4: 模拟盘测试 ==========
    print(f"\n{'='*70}")
    print("Step 4: 模拟盘测试")
    print(f"{'='*70}")
    
    # 创建模拟账户
    account = SimulatedTradingAccount(
        initial_capital=1000000,
        commission_rate=0.0003,
        slippage=0.001
    )
    
    # 创建风控管理器
    risk_mgr = RiskManager(
        initial_capital=1000000,
        position_limits=PositionLimits(
            max_single_position=0.30,
            max_total_position=0.80
        ),
        loss_limits=LossLimits(
            max_daily_loss=0.05,
            max_drawdown=0.20
        )
    )
    
    # 模拟交易场景
    print(f"\n模拟交易场景...")
    
    # 场景 1: 买入开仓
    print(f"\n[场景 1] 买入开仓")
    if risk_mgr.check_position_limit(400000):
        order = account.submit_order(
            symbol='RB2405',
            side=OrderSide.BUY,
            volume=10,
            price=4000
        )
        if order:
            account.execute_order(order, market_price=4000)
    
    # 场景 2: 更新行情
    print(f"\n[场景 2] 更新行情")
    account.update_market_price('RB2405', 4100)
    
    # 场景 3: 平多仓
    print(f"\n[场景 3] 平多仓")
    order2 = account.submit_order(
        symbol='RB2405',
        side=OrderSide.CLOSE_LONG,
        volume=10,
        price=4100
    )
    if order2:
        account.execute_order(order2, market_price=4100)
    
    # 获取账户汇总
    summary = account.get_account_summary()
    
    print(f"\n账户汇总:")
    print(f"  初始资金：{summary['initial_capital']:,.0f}")
    print(f"  当前权益：{summary['equity']:,.0f}")
    print(f"  总收益率：{summary['total_return']:.2f}%")
    print(f"  最大回撤：{summary['max_drawdown']:.2f}%")
    print(f"  总手续费：{summary['total_commission']:.2f}")
    
    # ========== Step 5: 生成报告 ==========
    print(f"\n{'='*70}")
    print("Step 5: 生成报告")
    print(f"{'='*70}")
    
    # 导出模拟盘报告
    account.export_report('reports/simulated_trading_report.json')
    
    # 导出回测报告
    backtester.generate_report('reports/backtest_report.html')
    
    # ========== 总结 ==========
    print(f"\n{'='*70}")
    print("演示完成总结")
    print(f"{'='*70}")
    
    print(f"\n完成步骤:")
    print(f"  ✓ Step 1: 获取历史数据")
    print(f"  ✓ Step 2: 批量回测 ({len(data_dict)} 个品种)")
    print(f"  ✓ Step 3: 样本外验证")
    print(f"  ✓ Step 4: 模拟盘测试")
    print(f"  ✓ Step 5: 生成报告")
    
    print(f"\n生成文件:")
    print(f"  - reports/simulated_trading_report.json")
    print(f"  - reports/backtest_report.html")
    
    print(f"\n{'='*70}")
    print(f"[OK] 演示完成")
    print(f"{'='*70}")
    print(f"结束时间：{datetime.now()}")


if __name__ == "__main__":
    run_full_demo()
