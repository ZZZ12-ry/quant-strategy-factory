"""
Stochastic 随机指标策略
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class StochasticTrendStrategy(BaseStrategy):
    """Stochastic 随机指标策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "k_period": 14,         # %K 周期
            "d_period": 3,          # %D 周期
            "oversold": 20,         # 超卖阈值
            "overbought": 80,       # 超买阈值
            "stop_loss_pct": 0.03,  # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "k_period": (10, 20),
            "d_period": (2, 5),
            "oversold": (15, 30),
            "overbought": (70, 85),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.high_prices = {}
        self.low_prices = {}
        self.close_prices = {}
        self.k_values = {}
        self.d_values = {}
        self.entry_prices = {}
    
    def _calculate_stochastic(self, symbol: str) -> tuple:
        """计算 Stochastic %K 和 %D"""
        if len(self.close_prices[symbol]) < self.params["k_period"]:
            return None, None
        
        # 计算 %K
        highest = max(self.high_prices[symbol][-self.params["k_period"]:])
        lowest = min(self.low_prices[symbol][-self.params["k_period"]:])
        current_close = self.close_prices[symbol][-1]
        
        if highest == lowest:
            k = 50
        else:
            k = (current_close - lowest) / (highest - lowest) * 100
        
        self.k_values[symbol].append(k)
        
        # 计算 %D（%K 的移动平均）
        if len(self.k_values[symbol]) < self.params["d_period"]:
            d = k
        else:
            d = np.mean(self.k_values[symbol][-self.params["d_period"]:])
        
        self.d_values[symbol].append(d)
        
        return k, d
    
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
            self.k_values[symbol] = []
            self.d_values[symbol] = []
            self.entry_prices[symbol] = {}
        
        # 更新价格
        self.high_prices[symbol].append(high)
        self.low_prices[symbol].append(low)
        self.close_prices[symbol].append(close)
        
        # 计算 Stochastic
        k, d = self._calculate_stochastic(symbol)
        if k is None:
            return None
        
        # 需要足够的历史数据
        if len(self.k_values[symbol]) < 3:
            return None
        
        k_curr = self.k_values[symbol][-1]
        k_prev = self.k_values[symbol][-2]
        d_curr = self.d_values[symbol][-1]
        d_prev = self.d_values[symbol][-2]
        
        position = self.get_position(symbol)
        
        if position is None:
            # 超卖区金叉买入
            if (k_prev < self.params["oversold"] and k_curr > self.params["oversold"] and
                k_curr > d_curr):
                self.entry_prices[symbol]['long'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min((k_curr - self.params["oversold"]) / 20, 1.0)
                )
            
            # 超买区死叉卖出
            elif (k_prev > self.params["overbought"] and k_curr < self.params["overbought"] and
                  k_curr < d_curr):
                self.entry_prices[symbol]['short'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min((self.params["overbought"] - k_curr) / 20, 1.0)
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
                
                # 超买区平仓
                if k_curr > self.params["overbought"]:
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
                
                # 超卖区平仓
                if k_curr < self.params["oversold"]:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
