"""
波动率突破策略 - 基于 ATR 的突破策略
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class VolatilityBreakoutStrategy(BaseStrategy):
    """波动率突破策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "atr_period": 14,       # ATR 周期
            "entry_multiplier": 2.0, # 入场倍数
            "exit_multiplier": 1.0,  # 出场倍数
            "trailing_stop": True,  # 跟踪止损
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "atr_period": (10, 20),
            "entry_multiplier": (1.5, 3.0),
            "exit_multiplier": (0.5, 1.5),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.high_prices = {}
        self.low_prices = {}
        self.close_prices = {}
        self.atr_values = {}
        self.entry_prices = {}
        self.highest_since_entry = {}
        self.lowest_since_entry = {}
    
    def _calculate_atr(self, symbol: str) -> Optional[float]:
        """计算 ATR"""
        period = self.params["atr_period"]
        
        if len(self.close_prices[symbol]) < period + 1:
            return None
        
        # 计算 TR
        tr_list = []
        for i in range(1, len(self.close_prices[symbol])):
            high_curr = self.high_prices[symbol][i]
            low_curr = self.low_prices[symbol][i]
            close_prev = self.close_prices[symbol][i-1]
            
            tr = max(high_curr - low_curr,
                    abs(high_curr - close_prev),
                    abs(low_curr - close_prev))
            tr_list.append(tr)
        
        # 计算 ATR
        atr = np.mean(tr_list[-period:])
        self.atr_values[symbol].append(atr)
        
        return atr
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        symbol = bar['symbol']
        close = bar['close']
        high = bar['high']
        low = bar['low']
        timestamp = bar['timestamp']
        
        # 初始化
        if symbol not in self.high_prices:
            self.high_prices[symbol] = []
            self.low_prices[symbol] = []
            self.close_prices[symbol] = []
            self.atr_values[symbol] = []
            self.entry_prices[symbol] = {}
            self.highest_since_entry[symbol] = []
            self.lowest_since_entry[symbol] = []
        
        # 更新价格
        self.high_prices[symbol].append(high)
        self.low_prices[symbol].append(low)
        self.close_prices[symbol].append(close)
        
        # 计算 ATR
        atr = self._calculate_atr(symbol)
        if atr is None:
            return None
        
        # 计算上下轨
        upper = self.close_prices[symbol][-2] + self.params["entry_multiplier"] * atr
        lower = self.close_prices[symbol][-2] - self.params["entry_multiplier"] * atr
        
        position = self.get_position(symbol)
        
        if position is None:
            # 向上突破开多
            if high > upper:
                self.entry_prices[symbol] = {'long': close}
                self.highest_since_entry[symbol] = [high]
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min((high - upper) / atr, 1.0)
                )
            
            # 向下突破开空
            elif low < lower:
                self.entry_prices[symbol] = {'short': close}
                self.lowest_since_entry[symbol] = [low]
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min((lower - low) / atr, 1.0)
                )
        else:
            # 更新极值
            if position.direction == "long":
                self.highest_since_entry[symbol].append(high)
                highest = max(self.highest_since_entry[symbol])
                
                # 跟踪止损
                if self.params["trailing_stop"]:
                    stop_price = highest - self.params["exit_multiplier"] * atr
                    if low < stop_price:
                        return self.generate_signal(
                            symbol=symbol,
                            timestamp=timestamp,
                            direction="close",
                            price=close,
                            volume=position.volume,
                            strength=1.0
                        )
                
                # 反向突破平仓
                reverse_level = self.close_prices[symbol][-2] - self.params["entry_multiplier"] * atr
                if low < reverse_level:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
            
            elif position.direction == "short":
                self.lowest_since_entry[symbol].append(low)
                lowest = min(self.lowest_since_entry[symbol])
                
                # 跟踪止损
                if self.params["trailing_stop"]:
                    stop_price = lowest + self.params["exit_multiplier"] * atr
                    if high > stop_price:
                        return self.generate_signal(
                            symbol=symbol,
                            timestamp=timestamp,
                            direction="close",
                            price=close,
                            volume=position.volume,
                            strength=1.0
                        )
                
                # 反向突破平仓
                reverse_level = self.close_prices[symbol][-2] + self.params["entry_multiplier"] * atr
                if high > reverse_level:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
