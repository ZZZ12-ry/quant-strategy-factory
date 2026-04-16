"""
Aroon 趋势策略 - 趋势强度指标
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class AroonTrendStrategy(BaseStrategy):
    """Aroon 趋势跟踪策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "aroon_period": 14,     # Aroon 周期
            "aroon_up_threshold": 70,   # 上涨阈值
            "aroon_down_threshold": 30, # 下跌阈值
            "stop_loss_pct": 0.03,      # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "aroon_period": (10, 25),
            "aroon_up_threshold": (60, 80),
            "aroon_down_threshold": (20, 40),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.high_prices = {}
        self.low_prices = {}
        self.entry_prices = {}
    
    def _calculate_aroon(self, symbol: str) -> tuple:
        """计算 Aroon Up/Down"""
        period = self.params["aroon_period"]
        
        if len(self.high_prices[symbol]) < period:
            return None, None
        
        # 最近 N 天的最高价和最低价
        recent_highs = self.high_prices[symbol][-period:]
        recent_lows = self.low_prices[symbol][-period:]
        
        # 找到最高价和最低价的索引
        highest_idx = np.argmax(recent_highs)
        lowest_idx = np.argmin(recent_lows)
        
        # 计算 Aroon
        aroon_up = ((period - 1 - highest_idx) / (period - 1)) * 100
        aroon_down = ((period - 1 - lowest_idx) / (period - 1)) * 100
        
        return aroon_up, aroon_down
    
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
            self.entry_prices[symbol] = {}
        
        # 更新价格
        self.high_prices[symbol].append(high)
        self.low_prices[symbol].append(low)
        
        # 计算 Aroon
        aroon_up, aroon_down = self._calculate_aroon(symbol)
        if aroon_up is None:
            return None
        
        position = self.get_position(symbol)
        
        if position is None:
            # 强势上涨：Aroon Up > 阈值 且 Aroon Down < 阈值
            if (aroon_up >= self.params["aroon_up_threshold"] and 
                aroon_down <= self.params["aroon_down_threshold"]):
                self.entry_prices[symbol]['long'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min((aroon_up - aroon_down) / 100, 1.0)
                )
            
            # 强势下跌：Aroon Down > 阈值 且 Aroon Up < 阈值
            elif (aroon_down >= self.params["aroon_up_threshold"] and 
                  aroon_up <= self.params["aroon_down_threshold"]):
                self.entry_prices[symbol]['short'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min((aroon_down - aroon_up) / 100, 1.0)
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
                
                # 趋势反转平仓
                if aroon_down > self.params["aroon_up_threshold"]:
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
                
                # 趋势反转平仓
                if aroon_up > self.params["aroon_up_threshold"]:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
