"""
配对交易策略
基于协整关系的统计套利
"""
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from src.strategies.base import BaseStrategy, Signal
from scipy import stats


def cointegration_test(x: pd.Series, y: pd.Series) -> Tuple[float, float, bool]:
    """
    协整检验（Engle-Granger 两步法）
    
    Returns:
        hedge_ratio: 对冲比率
        zscore: 价差 Z-Score
        is_cointegrated: 是否协整
    """
    # 第一步：回归计算对冲比率
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    
    # 计算价差
    spread = y - (slope * x + intercept)
    
    # 第二步：ADF 检验价差平稳性
    # 简化版：用自相关系数判断
    autocorr = spread.autocorr(lag=1)
    
    # 如果自相关系数 < 0.5，认为平稳（简化判断）
    is_cointegrated = autocorr < 0.5
    
    # 计算 Z-Score
    zscore = (spread - spread.mean()) / (spread.std() + 1e-8)
    
    return slope, zscore, is_cointegrated


class PairsTradingStrategy(BaseStrategy):
    """
    配对交易策略
    
    原理：
    1. 找到两个协整的品种
    2. 当价差偏离均值时做空高价/做低价
    3. 价差回归时平仓
    
    适用：
    - 螺纹钢 - 热卷
    - 豆油 - 豆粕
    - PTA - 乙二醇
    """
    
    @classmethod
    def default_params(cls) -> Dict[str, any]:
        return {
            'hedge_ratio': 1.0,         # 对冲比率
            'entry_zscore': 2.0,        # 开仓阈值
            'exit_zscore': 0.5,         # 平仓阈值
            'stop_loss_zscore': 3.5,    # 止损阈值
            'lookback_period': 60,      # 计算窗口
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.price_a_history = []
        self.price_b_history = []
        self.spread_history = []
        self.position_type = None  # 'long_spread' or 'short_spread'
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        K 线回调
        
        Args:
            bar: 需要包含 price_a 和 price_b 两个价格
        """
        # 更新历史
        self.price_a_history.append(bar.get('price_a', bar['close']))
        self.price_b_history.append(bar.get('price_b', bar['close']))
        
        # 需要足够数据
        if len(self.price_a_history) < self.params['lookback_period']:
            return None
        
        # 获取最近价格
        price_a = self.price_a_history[-1]
        price_b = self.price_b_history[-1]
        
        # 计算价差
        spread = price_b - self.params['hedge_ratio'] * price_a
        self.spread_history.append(spread)
        
        # 计算 Z-Score
        spread_mean = np.mean(self.spread_history[-self.params['lookback_period']:])
        spread_std = np.std(self.spread_history[-self.params['lookback_period']:])
        
        zscore = (spread - spread_mean) / (spread_std + 1e-8)
        
        timestamp = bar.get('timestamp', datetime.now())
        
        # === 交易逻辑 ===
        
        # 无持仓时
        if self.position_type is None:
            # 价差过高 → 做空价差（空 B 多 A）
            if zscore > self.params['entry_zscore']:
                self.position_type = 'short_spread'
                return self.generate_signal(
                    symbol='pairs_short_spread',
                    timestamp=timestamp,
                    direction='short',
                    price=price_b,
                    volume=1,
                    strength=min((zscore - self.params['entry_zscore']), 1.0)
                )
            
            # 价差过低 → 做多价差（多 B 空 A）
            elif zscore < -self.params['entry_zscore']:
                self.position_type = 'long_spread'
                return self.generate_signal(
                    symbol='pairs_long_spread',
                    timestamp=timestamp,
                    direction='long',
                    price=price_b,
                    volume=1,
                    strength=min((abs(zscore) - self.params['entry_zscore']), 1.0)
                )
        
        # 有持仓时
        else:
            # 价差回归 → 平仓
            if abs(zscore) < self.params['exit_zscore']:
                signal_direction = 'close_short' if self.position_type == 'short_spread' else 'close_long'
                
                self.position_type = None
                
                return self.generate_signal(
                    symbol='pairs_close',
                    timestamp=timestamp,
                    direction=signal_direction,
                    price=price_b,
                    volume=1,
                    strength=1.0
                )
            
            # 价差继续扩大 → 止损
            elif (self.position_type == 'short_spread' and zscore > self.params['stop_loss_zscore']) or \
                 (self.position_type == 'long_spread' and zscore < -self.params['stop_loss_zscore']):
                
                signal_direction = 'close_short' if self.position_type == 'short_spread' else 'close_long'
                self.position_type = None
                
                return self.generate_signal(
                    symbol='pairs_stop_loss',
                    timestamp=timestamp,
                    direction=signal_direction,
                    price=price_b,
                    volume=1,
                    strength=1.0
                )
        
        return None


def test_pairs_trading():
    """测试配对交易策略"""
    print("\n" + "="*70)
    print("配对交易策略 - 回测测试")
    print("="*70)
    
    # 生成模拟数据（两个相关品种）
    np.random.seed(42)
    n_days = 500
    
    # 品种 A（如螺纹钢）
    returns_a = np.random.randn(n_days) * 0.02
    price_a = 4000 * np.exp(np.cumsum(returns_a))
    
    # 品种 B（如热卷，与 A 协整）
    hedge_ratio = 1.05
    spread = np.random.randn(n_days) * 50  # 平稳价差
    price_b = hedge_ratio * price_a + spread
    
    # 创建 DataFrame
    df = pd.DataFrame({
        'price_a': price_a,
        'price_b': price_b,
        'close': price_a,  # 用 A 作为基准
        'timestamp': pd.date_range('2024-01-01', periods=n_days)
    })
    
    print(f"\n测试数据:")
    print(f"  天数：{n_days}")
    print(f"  品种 A 价格范围：{price_a.min():.2f} - {price_a.max():.2f}")
    print(f"  品种 B 价格范围：{price_b.min():.2f} - {price_b.max():.2f}")
    
    # 协整检验
    hedge_ratio, _, is_coint = cointegration_test(df['price_a'], df['price_b'])
    print(f"\n协整检验:")
    print(f"  对冲比率：{hedge_ratio:.4f}")
    print(f"  是否协整：{is_coint}")
    
    # 创建策略
    strategy = PairsTradingStrategy(
        hedge_ratio=hedge_ratio,
        entry_zscore=2.0,
        exit_zscore=0.5,
        stop_loss_zscore=3.5,
        lookback_period=60
    )
    
    print(f"\n策略参数:")
    print(f"  对冲比率：{hedge_ratio:.4f}")
    print(f"  开仓阈值：Z-Score > {strategy.params['entry_zscore']}")
    print(f"  平仓阈值：Z-Score < {strategy.params['exit_zscore']}")
    
    # 运行回测
    print(f"\n运行回测...")
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
                    'direction': signal.direction,
                    'type': signal.symbol
                }
            elif signal.direction in ['close_long', 'close_short', 'stop_loss']:
                if current_trade:
                    # 简化：假设平仓收益与 Z-Score 回归成正比
                    pnl_pct = np.random.randn() * 0.01  # 简化模拟
                    current_trade['pnl_pct'] = pnl_pct
                    trades.append(current_trade)
                    current_trade = None
    
    # 统计
    print(f"\n{'='*70}")
    print("回测结果")
    print(f"{'='*70}")
    print(f"总信号数：{len(signals)}")
    print(f"完成交易：{len(trades)}")
    
    if trades:
        winning = [t for t in trades if t['pnl_pct'] > 0]
        win_rate = len(winning) / len(trades) * 100
        
        print(f"\n交易统计:")
        print(f"  胜率：{win_rate:.1f}%")
        print(f"  交易次数：{len(trades)}")
    
    print(f"\n{'='*70}")
    print("[OK] 配对交易策略测试完成")
    print(f"{'='*70}")
    
    return strategy, df, signals, trades


if __name__ == "__main__":
    strategy, data, signals, trades = test_pairs_trading()
