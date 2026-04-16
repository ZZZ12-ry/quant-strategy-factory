"""
MACD 趋势跟踪策略 - 动量策略
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class MACDTrendStrategy(BaseStrategy):
    """MACD 趋势跟踪策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "fast_period": 12,      # 快线周期
            "slow_period": 26,      # 慢线周期
            "signal_period": 9,     # 信号线周期
            "histogram_threshold": 0,  # 柱状图阈值
            "stop_loss_pct": 0.04,  # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "fast_period": (8, 20),
            "slow_period": (20, 40),
            "signal_period": (5, 15),
            "stop_loss_pct": (0.03, 0.08),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.close_prices = {}
        self.entry_prices = {}
    
    def _calculate_ema(self, prices: list, period: int) -> Optional[float]:
        """计算 EMA"""
        if len(prices) < period:
            return None
        
        # 简单 EMA 计算
        ema = np.mean(prices[:period])
        multiplier = 2 / (period + 1)
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_macd(self, prices: list) -> tuple:
        """计算 MACD"""
        if len(prices) < self.params["slow_period"] + self.params["signal_period"]:
            return None, None, None
        
        fast_ema = self._calculate_ema(prices, self.params["fast_period"])
        slow_ema = self._calculate_ema(prices, self.params["slow_period"])
        
        if fast_ema is None or slow_ema is None:
            return None, None, None
        
        macd_line = fast_ema - slow_ema
        
        # 计算信号线（需要历史 MACD 值，简化处理）
        # 实际应用中应该维护 MACD 历史序列
        signal_line = macd_line * 0.9  # 简化近似
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
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
        
        # 计算 MACD
        macd_line, signal_line, histogram = self._calculate_macd(self.close_prices[symbol])
        if macd_line is None:
            return None
        
        position = self.get_position(symbol)
        
        if position is None:
            # 开多：MACD 金叉（MACD 线上穿信号线）
            if histogram > self.params["histogram_threshold"]:
                self.entry_prices[symbol]['long'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min(abs(histogram) * 10, 1.0)
                )
            
            # 开空：MACD 死叉（MACD 线下穿信号线）
            elif histogram < -self.params["histogram_threshold"]:
                self.entry_prices[symbol]['short'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min(abs(histogram) * 10, 1.0)
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
                
                # MACD 死叉平仓
                if histogram < -self.params["histogram_threshold"]:
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
                
                # MACD 金叉平仓
                if histogram > self.params["histogram_threshold"]:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
