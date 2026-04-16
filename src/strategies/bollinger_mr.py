"""
布林带均值回归策略 - 经典均值回归策略
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class BollingerMRStrategy(BaseStrategy):
    """布林带均值回归策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "ma_period": 20,        # 中轨周期
            "std_dev": 2.0,         # 标准差倍数
            "exit_ma": True,        # 回归中轨平仓
            "stop_loss_pct": 0.03,  # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "ma_period": (10, 50),
            "std_dev": (1.5, 3.0),
            "stop_loss_pct": (0.02, 0.05),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.close_prices = {}
        self.entry_prices = {}
    
    def _calculate_bollinger(self, prices: list) -> tuple:
        """计算布林带"""
        if len(prices) < self.params["ma_period"]:
            return None, None, None
        
        ma = np.mean(prices[-self.params["ma_period"]:])
        std = np.std(prices[-self.params["ma_period"]:])
        upper = ma + self.params["std_dev"] * std
        lower = ma - self.params["std_dev"] * std
        
        return ma, upper, lower
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        symbol = bar['symbol']
        close = bar['close']
        timestamp = bar['timestamp']
        
        # 初始化
        if symbol not in self.close_prices:
            self.close_prices[symbol] = []
            self.entry_prices[symbol] = {}
        
        # 更新价格序列
        self.close_prices[symbol].append(close)
        
        # 计算布林带
        ma, upper, lower = self._calculate_bollinger(self.close_prices[symbol])
        if ma is None:
            return None
        
        position = self.get_position(symbol)
        
        if position is None:
            # 开多：价格跌破下轨
            if close < lower:
                self.entry_prices[symbol]['long'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min((lower - close) / (upper - lower + 1e-6) * 10, 1.0)
                )
            
            # 开空：价格突破上轨
            elif close > upper:
                self.entry_prices[symbol]['short'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min((close - upper) / (upper - lower + 1e-6) * 10, 1.0)
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
                
                # 回归中轨平仓
                if self.params["exit_ma"] and close >= ma:
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
                
                # 回归中轨平仓
                if self.params["exit_ma"] and close <= ma:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
