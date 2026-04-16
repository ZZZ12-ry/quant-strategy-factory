"""
成交量策略参数优化器
使用网格搜索和贝叶斯优化找到最佳参数
"""
from src.strategies.volume_night_day import VolumeNightDayStrategyV2
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from itertools import product


class StrategyOptimizer:
    """策略参数优化器"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.results = []
    
    def backtest(self, strategy: VolumeNightDayStrategyV2) -> Dict:
        """运行回测并返回绩效指标"""
        strategy.reset()
        trades = []
        current_trade = None
        
        for idx, row in self.data.iterrows():
            signal = strategy.on_bar(row)
            if signal:
                if signal.direction in ['long', 'short']:
                    current_trade = {
                        'entry_price': signal.price,
                        'direction': signal.direction
                    }
                elif signal.direction in ['close_long', 'close_short', 'stop_loss', 'take_profit', 'trailing_stop']:
                    if current_trade:
                        current_trade['exit_price'] = signal.price
                        current_trade['pnl_pct'] = (signal.price - current_trade['entry_price']) / current_trade['entry_price']
                        if current_trade['direction'] == 'short':
                            current_trade['pnl_pct'] = -current_trade['pnl_pct']
                        # 扣除交易成本（双边 0.03%）
                        current_trade['pnl_pct'] -= 0.0006
                        trades.append(current_trade)
                        current_trade = None
        
        if not trades:
            return {
                'total_return': 0,
                'sharpe': 0,
                'win_rate': 0,
                'max_drawdown': 0,
                'total_trades': 0
            }
        
        # 计算绩效指标
        returns = [t['pnl_pct'] for t in trades]
        cumulative = np.cumsum(returns)
        
        total_return = cumulative[-1] * 100
        sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252) if len(returns) > 1 else 0
        
        winning = [r for r in returns if r > 0]
        win_rate = len(winning) / len(returns) * 100
        
        # 最大回撤
        peak = np.maximum.accumulate(cumulative)
        drawdown = (peak - cumulative) / (peak + 1e-8)
        max_drawdown = np.max(drawdown) * 100
        
        return {
            'total_return': total_return,
            'sharpe': sharpe,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'total_trades': len(trades),
            'avg_win': np.mean(winning) * 100 if winning else 0,
            'avg_loss': np.mean([r for r in returns if r < 0]) * 100 if any(r < 0 for r in returns) else 0
        }
    
    def grid_search(self, param_grid: Dict) -> pd.DataFrame:
        """网格搜索最优参数"""
        print("\n" + "="*70)
        print("网格搜索参数优化")
        print("="*70)
        
        # 生成参数组合
        keys = param_grid.keys()
        values = [param_grid[k] if isinstance(param_grid[k], list) else [param_grid[k]] for k in keys]
        combinations = list(product(*values))
        
        print(f"\n参数组合数：{len(combinations)}")
        print(f"参数范围:")
        for key, value in param_grid.items():
            if isinstance(value, list):
                print(f"  {key}: {value}")
        
        # 遍历所有组合
        results = []
        for i, combo in enumerate(combinations, 1):
            params = dict(zip(keys, combo))
            strategy = VolumeNightDayStrategyV2(**params)
            metrics = self.backtest(strategy)
            metrics.update(params)
            results.append(metrics)
            
            if i % 10 == 0 or i == len(combinations):
                print(f"进度：{i}/{len(combinations)} - 最佳收益：{max([r['total_return'] for r in results]):.2f}%")
        
        # 转换为 DataFrame
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('total_return', ascending=False)
        
        # 输出 Top 10
        print(f"\n{'='*70}")
        print("Top 10 参数组合")
        print(f"{'='*70}")
        
        for idx, row in df_results.head(10).iterrows():
            print(f"\n排名 {idx+1}:")
            print(f"  总收益：{row['total_return']:.2f}%")
            print(f"  夏普比率：{row['sharpe']:.2f}")
            print(f"  胜率：{row['win_rate']:.1f}%")
            print(f"  最大回撤：{row['max_drawdown']:.2f}%")
            print(f"  交易次数：{row['total_trades']}")
            print(f"  参数:")
            for key in param_grid.keys():
                print(f"    {key}: {row[key]}")
        
        self.results = results
        return df_results
    
    def optimize_sharpe(self, param_grid: Dict) -> Dict:
        """以夏普比率为目标优化"""
        print("\n[优化目标] 最大化夏普比率")
        df_results = self.grid_search(param_grid)
        best = df_results.loc[df_results['sharpe'].idxmax()]
        return best.to_dict()
    
    def optimize_return(self, param_grid: Dict) -> Dict:
        """以总收益为目标优化"""
        print("\n[优化目标] 最大化总收益")
        df_results = self.grid_search(param_grid)
        best = df_results.loc[df_results['total_return'].idxmax()]
        return best.to_dict()
    
    def optimize_calmar(self, param_grid: Dict) -> Dict:
        """以卡玛比率（收益/回撤）为目标优化"""
        print("\n[优化目标] 最大化卡玛比率（收益/回撤）")
        df_results = self.grid_search(param_grid)
        df_results['calmar'] = df_results['total_return'] / (df_results['max_drawdown'] + 1e-8)
        best = df_results.loc[df_results['calmar'].idxmax()]
        return best.to_dict()


def test_optimizer():
    """测试优化器"""
    print("\n" + "="*70)
    print("成交量策略参数优化器 - 测试")
    print("="*70)
    
    # 获取数据
    try:
        import akshare as ak
        print("\n获取真实数据...")
        df = ak.futures_zh_daily_sina(symbol="RB2405")
        df = df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low',
            'close': 'close', 'volume': 'volume'
        })
        df['timestamp'] = pd.to_datetime(df['date'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"[OK] 获取到 {len(df)} 条数据")
    except Exception as e:
        print(f"[WARN] 获取数据失败：{e}")
        print("使用模拟数据...")
        np.random.seed(42)
        n_days = 300
        returns = np.random.randn(n_days) * 0.02 + 0.0003
        close_prices = 100 * np.exp(np.cumsum(returns))
        base_volume = np.random.randint(10000, 50000, n_days)
        volume = (base_volume + np.abs(returns) * 100000).astype(int)
        df = pd.DataFrame({
            'open': close_prices * (1 + np.random.randn(n_days) * 0.005),
            'high': close_prices * (1 + np.abs(np.random.randn(n_days) * 0.01)),
            'low': close_prices * (1 - np.abs(np.random.randn(n_days) * 0.01)),
            'close': close_prices,
            'volume': volume,
            'timestamp': pd.date_range('2024-01-01', periods=n_days)
        })
    
    # 创建优化器
    optimizer = StrategyOptimizer(df)
    
    # 定义参数范围
    param_grid = {
        'volume_ma_period': [15, 20, 25],
        'volume_zscore_threshold': [1.0, 1.5, 2.0],
        'price_ma_period': [15, 20, 25],
        'stop_loss_pct': [0.015, 0.02, 0.025],
        'take_profit_pct': [0.03, 0.04, 0.05],
    }
    
    # 运行优化
    print(f"\n开始优化...")
    print(f"参数组合：{3*3*3*3*3} = 243 种")
    
    # 优化夏普比率
    best_sharpe = optimizer.optimize_sharpe(param_grid)
    
    print(f"\n{'='*70}")
    print("最优参数（夏普比率最大化）")
    print(f"{'='*70}")
    print(f"夏普比率：{best_sharpe['sharpe']:.2f}")
    print(f"总收益：{best_sharpe['total_return']:.2f}%")
    print(f"胜率：{best_sharpe['win_rate']:.1f}%")
    print(f"最大回撤：{best_sharpe['max_drawdown']:.2f}%")
    print(f"\n最佳参数:")
    for key in param_grid.keys():
        print(f"  {key}: {best_sharpe[key]}")
    
    return optimizer, best_sharpe


if __name__ == "__main__":
    optimizer, best_params = test_optimizer()
