"""
多因子策略 v2 - 基于 Barra 风格因子 + ML 模型
"""
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from src.strategies.base import BaseStrategy, Signal
from src.ml.barra_factors import BarraFactors
from src.ml.factor_analyzer import FactorAnalyzer


class MultiFactorStrategyV2(BaseStrategy):
    """
    多因子策略 v2
    
    基于 Barra 风格因子 + 因子有效性检验
    
    核心逻辑：
    1. 计算 10 大风格因子（63 个具体因子）
    2. 因子标准化（Z-Score）
    3. 因子加权（IC 加权或等权）
    4. 根据综合得分做多/做空
    """
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            'factor_weights': {
                'Momentum': 0.15,
                'Volatility': 0.10,
                'Liquidity': 0.15,
                'Reversal': 0.10,
                'Value': 0.10,
                'Quality': 0.15,
                'Size': 0.05,
                'Beta': 0.05,
                'Growth': 0.10,
                'Leverage': 0.05,
            },
            'lookback_period': 20,       # 因子计算窗口
            'rebalance_period': 5,       # 调仓周期
            'top_percentile': 0.3,       # 做多前 30%
            'bottom_percentile': 0.3,    # 做空前 30%
            'zscore_clip': 3.0,          # Z-Score 截断
            'use_ic_weight': True,       # 是否使用 IC 加权
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            'lookback_period': (15, 30),
            'rebalance_period': (3, 10),
            'top_percentile': (0.2, 0.4),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.barra = BarraFactors()
        self.analyzer = FactorAnalyzer()
        self.price_history = []
        self.factor_history = []
        self.days_since_rebalance = 0
        self.factor_scores_history = []
        
        # 因子权重（可动态调整）
        self.factor_weights = self.params['factor_weights']
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        K 线回调
        
        Args:
            bar: 包含 open/high/low/close/volume 的 K 线
        """
        # 更新历史数据
        self.price_history.append({
            'open': bar['open'],
            'high': bar['high'],
            'low': bar['low'],
            'close': bar['close'],
            'volume': bar.get('volume', 0),
            'timestamp': bar.get('timestamp', datetime.now())
        })
        
        # 需要足够的历史数据
        min_periods = self.params['lookback_period'] + 10
        
        if len(self.price_history) < min_periods:
            return None
        
        # 计算因子
        df_history = pd.DataFrame(self.price_history[-(min_periods + 5):])
        df_with_factors = self.barra.calculate_all(df_history)
        
        if len(df_with_factors) < self.params['lookback_period']:
            return None
        
        # 获取最新因子值
        latest_factors = df_with_factors.iloc[-1]
        factor_names = self.barra.get_factor_names()
        
        # 因子标准化（Z-Score）
        factor_zscores = {}
        for factor_name in factor_names:
            if factor_name in latest_factors:
                factor_series = df_with_factors[factor_name].dropna()
                if len(factor_series) > 10:
                    zscore = (latest_factors[factor_name] - factor_series.mean()) / (factor_series.std() + 1e-8)
                    # 截断
                    zscore = np.clip(zscore, -self.params['zscore_clip'], self.params['zscore_clip'])
                    factor_zscores[factor_name] = zscore
        
        # 按风格分类计算综合得分
        categories = self.barra.get_factor_categories()
        category_scores = {}
        
        for category, factors in categories.items():
            valid_factors = [f for f in factors if f in factor_zscores]
            if valid_factors:
                # 类别内等权平均
                category_scores[category] = np.mean([factor_zscores[f] for f in valid_factors])
        
        # 加权综合得分
        total_score = 0.0
        total_weight = 0.0
        
        for category, score in category_scores.items():
            weight = self.factor_weights.get(category, 0.1)
            total_score += weight * score
            total_weight += weight
        
        if total_weight > 0:
            total_score /= total_weight
        
        self.factor_scores_history.append(total_score)
        
        # 调仓日
        self.days_since_rebalance += 1
        if self.days_since_rebalance < self.params['rebalance_period']:
            return None
        
        self.days_since_rebalance = 0
        
        # 根据得分生成信号
        timestamp = bar.get('timestamp', datetime.now())
        
        # 得分 > 阈值 → 做多
        if total_score > 0.5:
            if 'position' not in self.positions or self.positions['position'].direction != 'long':
                # 平空仓
                if 'position' in self.positions and self.positions['position'].direction == 'short':
                    self.close_position('position', bar['close'], timestamp)
                
                # 开多仓
                self.update_position(
                    symbol='position',
                    direction='long',
                    volume=1,
                    entry_price=bar['close'],
                    entry_time=timestamp
                )
                
                return self.generate_signal(
                    symbol='multifactor_long',
                    timestamp=timestamp,
                    direction='long',
                    price=bar['close'],
                    volume=1,
                    strength=min(abs(total_score), 1.0)
                )
        
        # 得分 < -阈值 → 做空
        elif total_score < -0.5:
            if 'position' not in self.positions or self.positions['position'].direction != 'short':
                # 平多仓
                if 'position' in self.positions and self.positions['position'].direction == 'long':
                    self.close_position('position', bar['close'], timestamp)
                
                # 开空仓
                self.update_position(
                    symbol='position',
                    direction='short',
                    volume=1,
                    entry_price=bar['close'],
                    entry_time=timestamp
                )
                
                return self.generate_signal(
                    symbol='multifactor_short',
                    timestamp=timestamp,
                    direction='short',
                    price=bar['close'],
                    volume=1,
                    strength=min(abs(total_score), 1.0)
                )
        
        # 得分中性 → 平仓
        else:
            if 'position' in self.positions:
                pos = self.positions['position']
                self.close_position('position', bar['close'], timestamp)
                
                return self.generate_signal(
                    symbol='multifactor_close',
                    timestamp=timestamp,
                    direction='close',
                    price=bar['close'],
                    volume=pos.volume,
                    strength=1.0
                )
        
        return None
    
    def get_current_factors(self) -> Dict:
        """获取当前因子得分"""
        if not self.factor_scores_history:
            return {}
        
        return {
            'total_score': self.factor_scores_history[-1],
            'category_scores': {},
        }


def test_multifactor_strategy():
    """测试多因子策略 v2"""
    print("\n" + "="*70)
    print("多因子策略 v2 - 回测测试")
    print("="*70)
    
    # 获取真实数据
    try:
        import akshare as ak
        df = ak.futures_zh_daily_sina(symbol="RB2405")
        df = df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low',
            'close': 'close', 'volume': 'volume'
        })
        df['timestamp'] = pd.to_datetime(df['date'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"\n[OK] 获取螺纹钢数据：{len(df)} 条")
    except Exception as e:
        print(f"\n[WARN] 获取数据失败：{e}")
        print("使用模拟数据...")
        np.random.seed(42)
        n = 300
        close = 100 * np.exp(np.cumsum(np.random.randn(n) * 0.02))
        df = pd.DataFrame({
            'open': close * (1 + np.random.randn(n) * 0.005),
            'high': close * (1 + np.abs(np.random.randn(n) * 0.01)),
            'low': close * (1 - np.abs(np.random.randn(n) * 0.01)),
            'close': close,
            'volume': np.random.randint(10000, 50000, n),
            'timestamp': pd.date_range('2024-01-01', periods=n)
        })
    
    print(f"\n数据范围：{df['timestamp'].min()} - {df['timestamp'].max()}")
    print(f"价格范围：{df['close'].min():.2f} - {df['close'].max():.2f}")
    
    # 创建策略
    strategy = MultiFactorStrategyV2(
        lookback_period=20,
        rebalance_period=5,
        top_percentile=0.3,
        use_ic_weight=True
    )
    
    print(f"\n策略参数:")
    print(f"  因子计算窗口：{strategy.params['lookback_period']}")
    print(f"  调仓周期：{strategy.params['rebalance_period']}")
    print(f"  因子权重：{strategy.params['factor_weights']}")
    
    # 运行回测
    print(f"\n运行回测...")
    signals = []
    trades = []
    current_trade = None
    equity_curve = [1.0]
    
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
            elif signal.direction in ['close', 'close_long', 'close_short']:
                if current_trade:
                    pnl_pct = (signal.price - current_trade['entry_price']) / current_trade['entry_price']
                    if current_trade['direction'] == 'short':
                        pnl_pct = -pnl_pct
                    # 扣除手续费
                    pnl_pct -= 0.0006
                    
                    current_trade['exit_time'] = signal.timestamp
                    current_trade['exit_price'] = signal.price
                    current_trade['pnl_pct'] = pnl_pct
                    trades.append(current_trade)
                    
                    equity_curve.append(equity_curve[-1] * (1 + pnl_pct))
                    current_trade = None
    
    # 统计结果
    print(f"\n{'='*70}")
    print("回测结果")
    print(f"{'='*70}")
    print(f"总信号数：{len(signals)}")
    print(f"完成交易：{len(trades)}")
    
    if trades:
        winning = [t for t in trades if t['pnl_pct'] > 0]
        losing = [t for t in trades if t['pnl_pct'] <= 0]
        
        win_rate = len(winning) / len(trades) * 100
        avg_win = np.mean([t['pnl_pct'] for t in winning]) * 100 if winning else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losing]) * 100 if losing else 0
        total_return = (equity_curve[-1] / equity_curve[0] - 1) * 100
        
        returns = [t['pnl_pct'] for t in trades]
        sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252) if len(returns) > 1 else 0
        
        # 最大回撤
        equity = np.array(equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak
        max_dd = np.max(drawdown) * 100
        
        print(f"\n交易统计:")
        print(f"  胜率：{win_rate:.1f}% ({len(winning)}/{len(trades)})")
        print(f"  平均盈利：{avg_win:.2f}%")
        print(f"  平均亏损：{avg_loss:.2f}%")
        if avg_loss != 0:
            print(f"  盈亏比：{abs(avg_win / avg_loss):.2f}")
        print(f"  总收益：{total_return:.2f}%")
        print(f"  夏普比率：{sharpe:.2f}")
        print(f"  最大回撤：{max_dd:.2f}%")
        print(f"  最终净值：{equity_curve[-1]:.4f}")
        
        # 详细交易记录
        print(f"\n交易明细（前 10 笔）:")
        for i, t in enumerate(trades[:10], 1):
            direction = "LONG " if t['direction'] == 'long' else "SHORT"
            pnl_str = f"+{t['pnl_pct']*100:.2f}%" if t['pnl_pct'] > 0 else f"{t['pnl_pct']*100:.2f}%"
            print(f"  {i:>2}. {direction} | {t['entry_price']:.2f} -> {t['exit_price']:.2f} | {pnl_str:>8} | {t.get('exit_type','')}")
    
    print(f"\n{'='*70}")
    print("[OK] 多因子策略 v2 测试完成")
    print(f"{'='*70}")
    
    return strategy, df, signals, trades, equity_curve


if __name__ == "__main__":
    strategy, data, signals, trades, equity = test_multifactor_strategy()
