"""
基于交易量昼夜效应的策略 v2
参考论文：Expected Return in Night and Day: The Role of Trading Volume

改进点：
1. 使用成交量变化率而非绝对阈值
2. 结合价格动量确认信号
3. 添加更严格的入场条件
"""
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from datetime import datetime
from src.strategies.base import BaseStrategy, Signal


class VolumeNightDayStrategyV2(BaseStrategy):
    """
    基于交易量昼夜效应的策略 v2
    
    核心逻辑（基于学术研究）：
    1. 异常成交量（相对于 20 日均量）预示价格趋势
    2. 量价配合时信号更可靠
    3. 成交量萎缩时退出
    
    改进：
    - 使用成交量 Z-Score 而非简单比率
    - 添加动量确认
    - 更严格的止损止盈
    """
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            'volume_ma_period': 20,      # 成交量均线周期
            'volume_zscore_threshold': 1.5,  # 成交量 Z-Score 阈值
            'price_ma_period': 20,       # 价格均线周期
            'momentum_period': 5,        # 动量周期
            'stop_loss_pct': 0.02,       # 止损百分比
            'take_profit_pct': 0.04,     # 止盈百分比
            'trailing_stop_pct': 0.015,  # 跟踪止损
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            'volume_ma_period': (15, 30),
            'volume_zscore_threshold': (1.0, 2.5),
            'price_ma_period': (10, 30),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.price_history = []
        self.volume_history = []
        self.entry_price = 0
        self.highest_price = 0
        self.lowest_price = 0
        
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """K 线回调"""
        # 更新历史数据
        self.price_history.append(bar['close'])
        self.volume_history.append(bar['volume'])
        
        min_periods = self.params['volume_ma_period'] + 10
        
        if len(self.price_history) < min_periods:
            return None
        
        # 计算成交量 Z-Score
        volume_ma = np.mean(self.volume_history[-self.params['volume_ma_period']:])
        volume_std = np.std(self.volume_history[-self.params['volume_ma_period']:])
        
        if volume_std == 0:
            volume_std = 1
        
        volume_zscore = (self.volume_history[-1] - volume_ma) / volume_std
        
        # 计算价格动量
        momentum = (self.price_history[-1] - self.price_history[-self.params['momentum_period']]) / self.price_history[-self.params['momentum_period']]
        
        # 价格相对于均线位置
        price_ma = np.mean(self.price_history[-self.params['price_ma_period']:])
        price_vs_ma = (self.price_history[-1] - price_ma) / price_ma
        
        timestamp = bar.get('timestamp', datetime.now())
        
        # 获取持仓状态
        has_long = 'position' in self.positions and self.positions['position'].direction == 'long'
        has_short = 'position' in self.positions and self.positions['position'].direction == 'short'
        
        # === 开仓逻辑 ===
        if not has_long and not has_short:
            # 放量 + 正动量 + 价格在均线上方 → 做多
            if (volume_zscore > self.params['volume_zscore_threshold'] and 
                momentum > 0.01 and 
                price_vs_ma > 0):
                
                self.update_position(
                    symbol='position',
                    direction='long',
                    volume=1,
                    entry_price=bar['close'],
                    entry_time=timestamp
                )
                self.entry_price = bar['close']
                self.highest_price = bar['close']
                
                return self.generate_signal(
                    symbol='volume_long',
                    timestamp=timestamp,
                    direction='long',
                    price=bar['close'],
                    volume=1,
                    strength=min(volume_zscore / 3, 1.0)
                )
            
            # 放量 + 负动量 + 价格在均线下方 → 做空
            elif (volume_zscore > self.params['volume_zscore_threshold'] and 
                  momentum < -0.01 and 
                  price_vs_ma < 0):
                
                self.update_position(
                    symbol='position',
                    direction='short',
                    volume=1,
                    entry_price=bar['close'],
                    entry_time=timestamp
                )
                self.entry_price = bar['close']
                self.lowest_price = bar['close']
                
                return self.generate_signal(
                    symbol='volume_short',
                    timestamp=timestamp,
                    direction='short',
                    price=bar['close'],
                    volume=1,
                    strength=min(volume_zscore / 3, 1.0)
                )
        
        # === 持仓管理 ===
        else:
            pos = self.positions['position']
            pnl_pct = (bar['close'] - pos.entry_price) / pos.entry_price
            
            if has_long:
                # 更新最高价
                self.highest_price = max(self.highest_price, bar['close'])
                
                # 止盈
                if pnl_pct >= self.params['take_profit_pct']:
                    self.close_position('position', bar['close'], timestamp)
                    return self.generate_signal(
                        symbol='volume_take_profit',
                        timestamp=timestamp,
                        direction='close_long',
                        price=bar['close'],
                        volume=pos.volume,
                        strength=1.0
                    )
                
                # 跟踪止损
                trailing_stop = self.highest_price * (1 - self.params['trailing_stop_pct'])
                if bar['close'] < trailing_stop:
                    self.close_position('position', bar['close'], timestamp)
                    return self.generate_signal(
                        symbol='volume_trailing_stop',
                        timestamp=timestamp,
                        direction='close_long',
                        price=bar['close'],
                        volume=pos.volume,
                        strength=1.0
                    )
                
                # 硬止损
                if pnl_pct <= -self.params['stop_loss_pct']:
                    self.close_position('position', bar['close'], timestamp)
                    return self.generate_signal(
                        symbol='volume_stop_loss',
                        timestamp=timestamp,
                        direction='close_long',
                        price=bar['close'],
                        volume=pos.volume,
                        strength=1.0
                    )
            
            elif has_short:
                # 更新最低价
                self.lowest_price = min(self.lowest_price, bar['close'])
                
                # 止盈
                if pnl_pct <= -self.params['take_profit_pct']:
                    self.close_position('position', bar['close'], timestamp)
                    return self.generate_signal(
                        symbol='volume_take_profit',
                        timestamp=timestamp,
                        direction='close_short',
                        price=bar['close'],
                        volume=pos.volume,
                        strength=1.0
                    )
                
                # 跟踪止损
                trailing_stop = self.lowest_price * (1 + self.params['trailing_stop_pct'])
                if bar['close'] > trailing_stop:
                    self.close_position('position', bar['close'], timestamp)
                    return self.generate_signal(
                        symbol='volume_trailing_stop',
                        timestamp=timestamp,
                        direction='close_short',
                        price=bar['close'],
                        volume=pos.volume,
                        strength=1.0
                    )
                
                # 硬止损
                if pnl_pct >= self.params['stop_loss_pct']:
                    self.close_position('position', bar['close'], timestamp)
                    return self.generate_signal(
                        symbol='volume_stop_loss',
                        timestamp=timestamp,
                        direction='close_short',
                        price=bar['close'],
                        volume=pos.volume,
                        strength=1.0
                    )
        
        return None


def test_volume_strategy_v2():
    """测试成交量策略 v2"""
    print("\n" + "="*60)
    print("成交量昼夜效应策略 v2 - 回测")
    print("="*60)
    
    # 使用真实数据（螺纹钢期货）
    try:
        import akshare as ak
        print("\n正在获取真实期货数据...")
        df = ak.futures_zh_daily_sina(symbol="RB2405")
        df = df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low', 
            'close': 'close', 'volume': 'volume'
        })
        df['timestamp'] = pd.to_datetime(df['date'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"[OK] 获取到 {len(df)} 条真实数据")
        use_real_data = True
    except Exception as e:
        print(f"[WARN] 获取真实数据失败：{e}")
        print("使用模拟数据...")
        use_real_data = False
    
    if not use_real_data:
        # 生成更真实的测试数据（带趋势和波动聚集）
        np.random.seed(42)
        n_days = 500
        
        # 使用几何布朗运动生成价格
        returns = np.random.randn(n_days) * 0.02 + 0.0003  # 日均收益 0.03%
        close_prices = 100 * np.exp(np.cumsum(returns))
        
        # 成交量与价格变动相关（波动聚集）
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
    
    print(f"\n回测数据：{len(df)} 天")
    print(f"价格范围：{df['close'].min():.2f} - {df['close'].max():.2f}")
    print(f"成交量范围：{df['volume'].min()} - {df['volume'].max()}")
    
    # 创建策略
    strategy = VolumeNightDayStrategyV2(
        volume_ma_period=20,
        volume_zscore_threshold=1.5,
        price_ma_period=20,
        momentum_period=5,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        trailing_stop_pct=0.015
    )
    
    print(f"\n策略参数:")
    print(f"  成交量均线周期：{strategy.params['volume_ma_period']}")
    print(f"  成交量 Z-Score 阈值：{strategy.params['volume_zscore_threshold']}")
    print(f"  价格均线周期：{strategy.params['price_ma_period']}")
    print(f"  动量周期：{strategy.params['momentum_period']}")
    print(f"  止损：{strategy.params['stop_loss_pct']*100:.1f}%")
    print(f"  止盈：{strategy.params['take_profit_pct']*100:.1f}%")
    print(f"  跟踪止损：{strategy.params['trailing_stop_pct']*100:.1f}%")
    
    # 运行回测
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
                    'strength': signal.strength
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
    
    # 统计结果
    print(f"\n{'='*60}")
    print(f"回测结果")
    print(f"{'='*60}")
    print(f"总信号数：{len(signals)}")
    print(f"完成交易数：{len(trades)}")
    
    if trades:
        winning_trades = [t for t in trades if t['pnl_pct'] > 0]
        losing_trades = [t for t in trades if t['pnl_pct'] <= 0]
        
        win_rate = len(winning_trades) / len(trades) * 100
        avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) * 100 if winning_trades else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) * 100 if losing_trades else 0
        total_return = sum([t['pnl_pct'] for t in trades]) * 100
        
        # 最大回撤
        cumulative_returns = np.cumsum([t['pnl_pct'] for t in trades])
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (peak - cumulative_returns) / (peak + 1e-8)
        max_drawdown = np.max(drawdown) * 100
        
        print(f"\n交易统计:")
        print(f"  胜率：{win_rate:.1f}% ({len(winning_trades)}/{len(trades)})")
        print(f"  平均盈利：{avg_win:.2f}%")
        print(f"  平均亏损：{avg_loss:.2f}%")
        print(f"  盈亏比：{abs(avg_win / avg_loss):.2f}" if avg_loss != 0 else "  盈亏比：N/A")
        print(f"  总收益：{total_return:.2f}%")
        print(f"  最大回撤：{max_drawdown:.2f}%")
        
        # 夏普比率
        if len(trades) > 1:
            returns = [t['pnl_pct'] for t in trades]
            sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
            print(f"  夏普比率：{sharpe:.2f}")
        
        # 按退出类型统计
        exit_types = {}
        for t in trades:
            exit_type = t.get('exit_type', 'unknown')
            if exit_type not in exit_types:
                exit_types[exit_type] = []
            exit_types[exit_type].append(t['pnl_pct'])
        
        print(f"\n退出类型统计:")
        for exit_type, pnls in exit_types.items():
            print(f"  {exit_type}: {len(pnls)} 次，平均收益 {np.mean(pnls)*100:.2f}%")
    
    print("\n" + "="*60)
    
    return strategy, df, signals, trades


if __name__ == "__main__":
    strategy, data, signals, trades = test_volume_strategy_v2()
