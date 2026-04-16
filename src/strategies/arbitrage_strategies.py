"""
套利策略 - 期现套利 / 跨期套利 / 跨品种套利
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from src.strategies.base import BaseStrategy, Signal


class SpotFuturesArbitrage(BaseStrategy):
    """
    期现套利策略
    
    原理：当期货价格与现货价格出现显著偏离时，
    做空高估的一方，做多低估的一方，等待价差回归
    
    适用：有对应现货的期货品种（黄金、白银、铜、螺纹钢等）
    """
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            'zscore_entry': 2.0,       # 开仓阈值（Z-Score）
            'zscore_exit': 0.5,        # 平仓阈值
            'lookback_window': 60,     # 历史窗口（天）
            'max_holding_days': 30,    # 最大持仓天数
            'stop_loss_zscore': 3.5,   # 止损 Z-Score
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            'zscore_entry': (1.5, 3.0),
            'zscore_exit': (0.0, 1.0),
            'lookback_window': (30, 120),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.spot_prices = []
        self.futures_prices = []
        self.spread_history = []
        self.entry_spread = None
        self.entry_zscore = None
        self.holding_days = 0
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        K 线回调
        
        Args:
            bar: 包含 spot_price 和 futures_price 的 K 线
        """
        # 更新价格历史
        self.spot_prices.append(bar.get('spot_price', bar['close']))
        self.futures_prices.append(bar['close'])
        
        # 计算价差
        spread = self.futures_prices[-1] - self.spot_prices[-1]
        self.spread_history.append(spread)
        
        # 需要足够的历史数据
        lookback = min(len(self.spread_history), self.params['lookback_window'])
        if lookback < 30:
            return None
        
        # 计算 Z-Score
        spread_array = np.array(self.spread_history[-lookback:])
        mean_spread = np.mean(spread_array)
        std_spread = np.std(spread_array)
        
        if std_spread == 0:
            return None
        
        current_zscore = (spread - mean_spread) / std_spread
        
        # 更新持仓天数
        if 'arbitrage' in self.positions:
            self.holding_days += 1
        
        # 平仓逻辑
        if 'arbitrage' in self.positions:
            pos = self.positions['arbitrage']
            
            # 价差回归平仓
            if abs(current_zscore) < self.params['zscore_exit']:
                return self._close_position(bar, pos, "spread_reverted")
            
            # 止损
            if abs(current_zscore) > self.params['stop_loss_zscore']:
                return self._close_position(bar, pos, "stop_loss")
            
            # 超时平仓
            if self.holding_days >= self.params['max_holding_days']:
                return self._close_position(bar, pos, "timeout")
        
        # 开仓逻辑
        else:
            # 期货高估：做空期货，做多现货
            if current_zscore > self.params['zscore_entry']:
                return self._open_short_spread(bar, current_zscore)
            
            # 期货低估：做多期货，做空现货
            elif current_zscore < -self.params['zscore_entry']:
                return self._open_long_spread(bar, current_zscore)
        
        return None
    
    def _open_short_spread(self, bar: pd.Series, zscore: float) -> Signal:
        """做空价差（空期货 + 多现货）"""
        self.entry_spread = self.futures_prices[-1] - self.spot_prices[-1]
        self.entry_zscore = zscore
        self.holding_days = 0
        
        # 模拟：期货做空
        volume = 1
        self.update_position(
            symbol='arbitrage',
            direction='short',
            volume=volume,
            entry_price=bar['close'],
            entry_time=bar['timestamp'] if 'timestamp' in bar else datetime.now()
        )
        
        return self.generate_signal(
            symbol='arbitrage_short',
            timestamp=bar['timestamp'] if 'timestamp' in bar else datetime.now(),
            direction='short',
            price=bar['close'],
            volume=volume,
            strength=min(abs(zscore) / 5, 1.0)
        )
    
    def _open_long_spread(self, bar: pd.Series, zscore: float) -> Signal:
        """做多价差（多期货 + 空现货）"""
        self.entry_spread = self.futures_prices[-1] - self.spot_prices[-1]
        self.entry_zscore = zscore
        self.holding_days = 0
        
        volume = 1
        self.update_position(
            symbol='arbitrage',
            direction='long',
            volume=volume,
            entry_price=bar['close'],
            entry_time=bar['timestamp'] if 'timestamp' in bar else datetime.now()
        )
        
        return self.generate_signal(
            symbol='arbitrage_long',
            timestamp=bar['timestamp'] if 'timestamp' in bar else datetime.now(),
            direction='long',
            price=bar['close'],
            volume=volume,
            strength=min(abs(zscore) / 5, 1.0)
        )
    
    def _close_position(self, bar: pd.Series, pos: Any, reason: str) -> Signal:
        """平仓"""
        pnl = self.close_position(
            symbol='arbitrage',
            exit_price=bar['close'],
            exit_time=bar['timestamp'] if 'timestamp' in bar else datetime.now()
        )
        
        direction = 'close_short' if pos.direction == 'short' else 'close_long'
        
        return self.generate_signal(
            symbol='arbitrage_close',
            timestamp=bar['timestamp'] if 'timestamp' in bar else datetime.now(),
            direction=direction,
            price=bar['close'],
            volume=pos.volume,
            strength=1.0
        )


class CalendarSpreadArbitrage(BaseStrategy):
    """
    跨期套利策略
    
    原理：同一品种不同到期月份的合约之间存在价差关系，
    当价差偏离历史正常水平时进行套利
    
    适用：期货品种的近月和远月合约
    """
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            'zscore_entry': 2.0,        # 开仓阈值
            'zscore_exit': 0.5,         # 平仓阈值
            'lookback_window': 60,      # 历史窗口
            'max_holding_days': 20,     # 最大持仓
            'near_month': 1,            # 近月合约
            'far_month': 2,             # 远月合约
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            'zscore_entry': (1.5, 3.0),
            'zscore_exit': (0.0, 1.0),
            'lookback_window': (30, 120),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.near_prices = []
        self.far_prices = []
        self.spread_history = []
        self.entry_spread = None
        self.holding_days = 0
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        K 线回调 - 需要包含近月和远月合约价格
        
        Args:
            bar: 包含 near_price 和 far_price 的 K 线
        """
        # 更新价格历史
        self.near_prices.append(bar.get('near_price', bar['close']))
        self.far_prices.append(bar.get('far_price', bar.get('far_price', bar['close'] * 1.01)))
        
        # 计算价差（远月 - 近月）
        spread = self.far_prices[-1] - self.near_prices[-1]
        self.spread_history.append(spread)
        
        # 需要足够的历史数据
        lookback = min(len(self.spread_history), self.params['lookback_window'])
        if lookback < 30:
            return None
        
        # 计算 Z-Score
        spread_array = np.array(self.spread_history[-lookback:])
        mean_spread = np.mean(spread_array)
        std_spread = np.std(spread_array)
        
        if std_spread == 0:
            return None
        
        current_zscore = (spread - mean_spread) / std_spread
        
        # 更新持仓天数
        if 'spread' in self.positions:
            self.holding_days += 1
        
        # 平仓逻辑
        if 'spread' in self.positions:
            pos = self.positions['spread']
            
            # 价差回归
            if abs(current_zscore) < self.params['zscore_exit']:
                return self._close_position(bar, pos, "spread_reverted")
            
            # 止损
            if abs(current_zscore) > 3.0:
                return self._close_position(bar, pos, "stop_loss")
            
            # 超时
            if self.holding_days >= self.params['max_holding_days']:
                return self._close_position(bar, pos, "timeout")
        
        # 开仓逻辑
        else:
            # 价差过高：做空价差（空远月 + 多近月）
            if current_zscore > self.params['zscore_entry']:
                return self._open_short_spread(bar, current_zscore)
            
            # 价差过低：做多价差（多远月 + 空近月）
            elif current_zscore < -self.params['zscore_entry']:
                return self._open_long_spread(bar, current_zscore)
        
        return None
    
    def _open_short_spread(self, bar: pd.Series, zscore: float) -> Signal:
        """做空价差"""
        self.entry_spread = self.far_prices[-1] - self.near_prices[-1]
        self.holding_days = 0
        
        volume = 1
        self.update_position(
            symbol='spread',
            direction='short',
            volume=volume,
            entry_price=bar.get('far_price', bar['close']),
            entry_time=bar['timestamp'] if 'timestamp' in bar else datetime.now()
        )
        
        return self.generate_signal(
            symbol='calendar_spread_short',
            timestamp=bar['timestamp'] if 'timestamp' in bar else datetime.now(),
            direction='short',
            price=bar.get('far_price', bar['close']),
            volume=volume,
            strength=min(abs(zscore) / 5, 1.0)
        )
    
    def _open_long_spread(self, bar: pd.Series, zscore: float) -> Signal:
        """做多价差"""
        self.entry_spread = self.far_prices[-1] - self.near_prices[-1]
        self.holding_days = 0
        
        volume = 1
        self.update_position(
            symbol='spread',
            direction='long',
            volume=volume,
            entry_price=bar.get('far_price', bar['close']),
            entry_time=bar['timestamp'] if 'timestamp' in bar else datetime.now()
        )
        
        return self.generate_signal(
            symbol='calendar_spread_long',
            timestamp=bar['timestamp'] if 'timestamp' in bar else datetime.now(),
            direction='long',
            price=bar.get('far_price', bar['close']),
            volume=volume,
            strength=min(abs(zscore) / 5, 1.0)
        )
    
    def _close_position(self, bar: pd.Series, pos: Any, reason: str) -> Signal:
        """平仓"""
        pnl = self.close_position(
            symbol='spread',
            exit_price=bar.get('far_price', bar['close']),
            exit_time=bar['timestamp'] if 'timestamp' in bar else datetime.now()
        )
        
        return self.generate_signal(
            symbol='calendar_spread_close',
            timestamp=bar['timestamp'] if 'timestamp' in bar else datetime.now(),
            direction='close',
            price=bar.get('far_price', bar['close']),
            volume=pos.volume,
            strength=1.0
        )


class CrossSectionalMomentum(BaseStrategy):
    """
    横截面动量策略（多品种轮动）
    
    原理：在一篮子品种中，做多强势品种，做空弱势品种
    
    适用：多品种组合（如 10-20 个期货品种）
    """
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            'momentum_period': 20,     # 动量计算周期
            'top_n': 3,                 # 做多数量
            'bottom_n': 3,              # 做空数量
            'rebalance_period': 5,      # 调仓周期
            'volatility_adjust': True,  # 波动率调整
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            'momentum_period': (10, 60),
            'top_n': (1, 5),
            'bottom_n': (1, 5),
            'rebalance_period': (3, 10),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.price_history = {}
        self.days_since_rebalance = 0
        self.current_longs = []
        self.current_shorts = []
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        K 线回调 - 需要包含 symbol 字段
        
        Args:
            bar: 包含 symbol 和 close 的 K 线
        """
        symbol = bar.get('symbol', 'UNKNOWN')
        
        # 更新价格历史
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(bar['close'])
        
        # 保持历史长度
        max_len = self.params['momentum_period'] + 10
        if len(self.price_history[symbol]) > max_len:
            self.price_history[symbol] = self.price_history[symbol][-max_len:]
        
        # 调仓日
        self.days_since_rebalance += 1
        if self.days_since_rebalance < self.params['rebalance_period']:
            return None
        
        self.days_since_rebalance = 0
        
        # 计算所有品种的动量
        momentum_scores = {}
        for sym, prices in self.price_history.items():
            if len(prices) >= self.params['momentum_period']:
                # 动量 = 过去 N 天的收益率
                momentum = (prices[-1] - prices[-self.params['momentum_period']]) / prices[-self.params['momentum_period']]
                
                # 波动率调整
                if self.params['volatility_adjust']:
                    returns = np.diff(prices[-self.params['momentum_period']:]) / prices[-self.params['momentum_period']:-1]
                    volatility = np.std(returns)
                    if volatility > 0:
                        momentum = momentum / volatility
                
                momentum_scores[sym] = momentum
        
        # 需要足够的品种
        if len(momentum_scores) < (self.params['top_n'] + self.params['bottom_n']):
            return None
        
        # 排序
        sorted_symbols = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        
        new_longs = [s[0] for s in sorted_symbols[:self.params['top_n']]]
        new_shorts = [s[0] for s in sorted_symbols[-self.params['bottom_n']:]]
        
        signals = []
        
        # 平掉不再强势的多头
        for sym in self.current_longs:
            if sym not in new_longs:
                if sym in self.positions:
                    pos = self.positions[sym]
                    self.close_position(
                        symbol=sym,
                        exit_price=bar['close'] if sym == symbol else bar['close'],
                        exit_time=bar['timestamp'] if 'timestamp' in bar else datetime.now()
                    )
        
        # 平掉不再弱势的空头
        for sym in self.current_shorts:
            if sym not in new_shorts:
                if sym in self.positions:
                    pos = self.positions[sym]
                    self.close_position(
                        symbol=sym,
                        exit_price=bar['close'] if sym == symbol else bar['close'],
                        exit_time=bar['timestamp'] if 'timestamp' in bar else datetime.now()
                    )
        
        # 开新多头
        for sym in new_longs:
            if sym not in self.current_longs:
                # 这里需要对应品种的价格，简化处理
                self.update_position(
                    symbol=sym,
                    direction='long',
                    volume=1,
                    entry_price=bar['close'],
                    entry_time=bar['timestamp'] if 'timestamp' in bar else datetime.now()
                )
        
        # 开新空头
        for sym in new_shorts:
            if sym not in self.current_shorts:
                self.update_position(
                    symbol=sym,
                    direction='short',
                    volume=1,
                    entry_price=bar['close'],
                    entry_time=bar['timestamp'] if 'timestamp' in bar else datetime.now()
                )
        
        self.current_longs = new_longs
        self.current_shorts = new_shorts
        
        # 返回调仓信号
        return self.generate_signal(
            symbol='portfolio_rebalance',
            timestamp=bar['timestamp'] if 'timestamp' in bar else datetime.now(),
            direction='rebalance',
            price=bar['close'],
            volume=len(new_longs) + len(new_shorts),
            strength=1.0
        )
