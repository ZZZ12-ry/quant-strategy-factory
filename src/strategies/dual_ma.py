"""
双均线策略 - 经典趋势跟踪策略
"""
from typing import Dict, Any, Optional
import pandas as pd
from src.strategies.base import BaseStrategy, Signal


class DualMAStrategy(BaseStrategy):
    """双均线交叉策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "fast_ma": 10,      # 快线周期
            "slow_ma": 30,      # 慢线周期
            "use_ema": False,   # 使用 EMA 而非 SMA
            "stop_loss_pct": 0.05,  # 止损百分比
            "take_profit_pct": 0.10,  # 止盈百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "fast_ma": (5, 30),
            "slow_ma": (20, 100),
            "stop_loss_pct": (0.02, 0.10),
            "take_profit_pct": (0.05, 0.20),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.fast_ma_values = {}
        self.slow_ma_values = {}
        self.high_prices = {}  # 用于跟踪止损
        self.low_prices = {}   # 用于跟踪止盈
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        symbol = bar['symbol']
        close = bar['close']
        high = bar['high']
        low = bar['low']
        timestamp = bar['timestamp']
        
        # 初始化
        if symbol not in self.fast_ma_values:
            self.fast_ma_values[symbol] = []
            self.slow_ma_values[symbol] = []
            self.high_prices[symbol] = []
            self.low_prices[symbol] = []
        
        # 更新价格序列
        self.fast_ma_values[symbol].append(close)
        self.slow_ma_values[symbol].append(close)
        self.high_prices[symbol].append(high)
        self.low_prices[symbol].append(low)
        
        # 计算均线
        if len(self.fast_ma_values[symbol]) < self.params["slow_ma"]:
            return None
        
        fast_ma = sum(self.fast_ma_values[symbol][-self.params["fast_ma"]:]) / self.params["fast_ma"]
        slow_ma = sum(self.slow_ma_values[symbol][-self.params["slow_ma"]:]) / self.params["slow_ma"]
        fast_ma_prev = sum(self.fast_ma_values[symbol][-self.params["fast_ma"]-1:-1]) / self.params["fast_ma"]
        slow_ma_prev = sum(self.slow_ma_values[symbol][-self.params["slow_ma"]-1:-1]) / self.params["slow_ma"]
        
        # 持仓管理
        position = self.get_position(symbol)
        
        if position is None:
            # 开仓信号：金叉
            if fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma:
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min(abs(fast_ma - slow_ma) / slow_ma * 100, 1.0)
                )
            
            # 开仓信号：死叉
            elif fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma:
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min(abs(fast_ma - slow_ma) / slow_ma * 100, 1.0)
                )
        else:
            # 止损止盈检查
            if position.direction == "long":
                self.high_prices[symbol].append(high)
                highest = max(self.high_prices[symbol])
                
                # 止损
                if close < position.entry_price * (1 - self.params["stop_loss_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 止盈
                if close > position.entry_price * (1 + self.params["take_profit_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 死叉平仓
                if fast_ma_prev >= slow_ma_prev and fast_ma < slow_ma:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
            
            elif position.direction == "short":
                self.low_prices[symbol].append(low)
                lowest = min(self.low_prices[symbol])
                
                # 止损
                if close > position.entry_price * (1 + self.params["stop_loss_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 止盈
                if close < position.entry_price * (1 - self.params["take_profit_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 金叉平仓
                if fast_ma_prev <= slow_ma_prev and fast_ma > slow_ma:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
