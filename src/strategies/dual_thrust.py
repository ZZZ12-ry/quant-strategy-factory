"""
Dual Thrust 策略 - 经典日内突破策略
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class DualThrustStrategy(BaseStrategy):
    """Dual Thrust 日内突破策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "lookback_days": 4,     # 回溯天数
            "k1": 0.4,              # 多头突破系数
            "k2": 0.4,              # 空头突破系数
            "exit_hour": 14,        # 平仓时间（小时）
            "stop_loss_pct": 0.02,  # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "lookback_days": (2, 10),
            "k1": (0.2, 0.6),
            "k2": (0.2, 0.6),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.daily_data = {}  # 每日数据
        self.entry_prices = {}
    
    def _calculate_range(self, data: list) -> tuple:
        """计算价格区间"""
        if len(data) < self.params["lookback_days"]:
            return None, None
        
        # 计算 HH, HC, LC, LL
        hh = max([d['high'] for d in data[-self.params["lookback_days"]:]])
        hc = max([d['close'] for d in data[-self.params["lookback_days"]:]])
        lc = min([d['close'] for d in data[-self.params["lookback_days"]:]])
        ll = min([d['low'] for d in data[-self.params["lookback_days"]:]])
        
        # 计算 Range
        range_hc = hh - lc
        range_lc = hc - ll
        range_val = max(range_hc, range_lc)
        
        return range_val, hh, ll
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        symbol = bar['symbol']
        close = bar['close']
        high = bar['high']
        low = bar['low']
        timestamp = bar['timestamp']
        
        # 初始化
        if symbol not in self.daily_data:
            self.daily_data[symbol] = []
            self.entry_prices[symbol] = {}
        
        # 存储日线数据
        self.daily_data[symbol].append({
            'timestamp': timestamp,
            'open': bar['open'],
            'high': high,
            'low': low,
            'close': close
        })
        
        # 计算 Range
        range_val, hh, ll = self._calculate_range(self.daily_data[symbol])
        if range_val is None:
            return None
        
        # 计算上下轨
        upper = self.daily_data[symbol][-1]['open'] + self.params["k1"] * range_val
        lower = self.daily_data[symbol][-1]['open'] - self.params["k2"] * range_val
        
        position = self.get_position(symbol)
        
        if position is None:
            # 向上突破开多
            if high > upper:
                self.entry_prices[symbol] = {'long': close}
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min((high - upper) / range_val, 1.0)
                )
            
            # 向下突破开空
            elif low < lower:
                self.entry_prices[symbol] = {'short': close}
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min((lower - low) / range_val, 1.0)
                )
        else:
            # 止损检查
            if position.direction == "long":
                entry = self.entry_prices[symbol].get('long', position.entry_price)
                
                # 止损
                if close < entry * (1 - self.params["stop_loss_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 时间平仓（简化：用收盘价判断）
                if timestamp.hour >= self.params["exit_hour"]:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
            
            elif position.direction == "short":
                entry = self.entry_prices[symbol].get('short', position.entry_price)
                
                # 止损
                if close > entry * (1 + self.params["stop_loss_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 时间平仓
                if timestamp.hour >= self.params["exit_hour"]:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
