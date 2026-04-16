"""
KDJ 震荡策略 - 随机指标策略
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class KDJOscillatorStrategy(BaseStrategy):
    """KDJ 震荡策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "n_period": 9,          # RSV 周期
            "k_period": 3,          # K 值周期
            "d_period": 3,          # D 值周期
            "oversold": 20,         # 超卖阈值
            "overbought": 80,       # 超买阈值
            "stop_loss_pct": 0.03,  # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "n_period": (5, 14),
            "k_period": (2, 5),
            "d_period": (2, 5),
            "oversold": (15, 30),
            "overbought": (70, 85),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.high_prices = {}
        self.low_prices = {}
        self.close_prices = {}
        self.entry_prices = {}
        self.kdj_values = {}
    
    def _calculate_kdj(self, symbol: str) -> tuple:
        """计算 KDJ"""
        if len(self.close_prices[symbol]) < self.params["n_period"]:
            return None, None, None
        
        # 计算 RSV
        recent_n = self.params["n_period"]
        highest = max(self.high_prices[symbol][-recent_n:])
        lowest = min(self.low_prices[symbol][-recent_n:])
        current_close = self.close_prices[symbol][-1]
        
        if highest == lowest:
            rsv = 50
        else:
            rsv = (current_close - lowest) / (highest - lowest) * 100
        
        # 初始化 KDJ 序列
        if symbol not in self.kdj_values or len(self.kdj_values[symbol]) == 0:
            self.kdj_values[symbol] = []
        
        # 计算 K, D, J
        if len(self.kdj_values[symbol]) == 0:
            k = rsv
            d = rsv
        else:
            prev_k, prev_d, _ = self.kdj_values[symbol][-1]
            k = (2/3) * prev_k + (1/3) * rsv
            d = (2/3) * prev_d + (1/3) * k
        
        j = 3 * k - 2 * d
        
        self.kdj_values[symbol].append((k, d, j))
        
        return k, d, j
    
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
            self.entry_prices[symbol] = {}
            self.kdj_values[symbol] = []
        
        # 更新价格序列
        self.high_prices[symbol].append(high)
        self.low_prices[symbol].append(low)
        self.close_prices[symbol].append(close)
        
        # 计算 KDJ
        k, d, j = self._calculate_kdj(symbol)
        if k is None:
            return None
        
        position = self.get_position(symbol)
        
        if position is None:
            # 开多：KDJ 超卖区金叉
            if k < self.params["oversold"] and d < self.params["oversold"] and k > d:
                self.entry_prices[symbol]['long'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min((self.params["oversold"] - k) / 20, 1.0)
                )
            
            # 开空：KDJ 超买区死叉
            elif k > self.params["overbought"] and d > self.params["overbought"] and k < d:
                self.entry_prices[symbol]['short'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min((k - self.params["overbought"]) / 20, 1.0)
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
                
                # KDJ 超买区平仓
                if k > self.params["overbought"]:
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
                
                # KDJ 超卖区平仓
                if k < self.params["oversold"]:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
