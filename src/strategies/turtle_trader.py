"""
海龟交易策略 - 经典趋势跟踪系统
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class TurtleTraderStrategy(BaseStrategy):
    """海龟交易策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "entry_period": 20,      # 入场周期（唐奇安通道）
            "exit_period": 10,       # 离场周期
            "atr_period": 20,        # ATR 周期
            "stop_loss_atr": 2.0,    # 止损 ATR 倍数
            "profit_exit_atr": 2.5,  # 止盈 ATR 倍数
            "max_position_pct": 0.02, # 单笔最大仓位（总资金百分比）
            "risk_level": 0.01,      # 风险等级（每单位风险）
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "entry_period": (10, 50),
            "exit_period": (5, 30),
            "atr_period": (10, 30),
            "stop_loss_atr": (1.5, 3.0),
            "max_position_pct": (0.01, 0.05),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.high_prices = {}
        self.low_prices = {}
        self.atr_values = {}
        self.entry_prices = {}
        self.units_held = {}
    
    def _calculate_atr(self, symbol: str) -> float:
        """计算 ATR"""
        if len(self.high_prices[symbol]) < self.params["atr_period"] + 1:
            return 0.0
        
        highs = self.high_prices[symbol][-self.params["atr_period"]:]
        lows = self.low_prices[symbol][-self.params["atr_period"]:]
        closes = self.high_prices[symbol][:-1][-self.params["atr_period"]:]  # 用 high 近似 close
        
        tr_values = []
        for i in range(len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i]),
                abs(lows[i] - closes[i])
            )
            tr_values.append(tr)
        
        return sum(tr_values) / len(tr_values)
    
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
            self.atr_values[symbol] = []
            self.entry_prices[symbol] = []
            self.units_held[symbol] = 0
        
        # 更新价格序列
        self.high_prices[symbol].append(high)
        self.low_prices[symbol].append(low)
        
        # 计算 ATR
        atr = self._calculate_atr(symbol)
        if atr == 0:
            return None
        
        self.atr_values[symbol].append(atr)
        
        # 计算唐奇安通道
        if len(self.high_prices[symbol]) < self.params["entry_period"]:
            return None
        
        highest_high = max(self.high_prices[symbol][-self.params["entry_period"]:])
        lowest_low = min(self.low_prices[symbol][-self.params["entry_period"]:])
        
        # 持仓管理
        position = self.get_position(symbol)
        
        if position is None:
            # 入场信号：突破 N 日高点
            if close > highest_high and self.units_held[symbol] == 0:
                self.entry_prices[symbol].append(close)
                self.units_held[symbol] += 1
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min((close - highest_high) / highest_high * 100, 1.0)
                )
            
            # 入场信号：跌破 N 日低点
            elif close < lowest_low and self.units_held[symbol] == 0:
                self.entry_prices[symbol].append(close)
                self.units_held[symbol] -= 1
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min((lowest_low - close) / lowest_low * 100, 1.0)
                )
        else:
            # 计算止损价
            if position.direction == "long":
                stop_loss = position.entry_price - self.params["stop_loss_atr"] * atr
                profit_exit = position.entry_price + self.params["profit_exit_atr"] * atr
                
                # 止损
                if close <= stop_loss:
                    self.units_held[symbol] = 0
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 止盈
                if close >= profit_exit:
                    self.units_held[symbol] = 0
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 离场信号：跌破 N 日低点
                exit_low = min(self.low_prices[symbol][-self.params["exit_period"]:])
                if close < exit_low:
                    self.units_held[symbol] = 0
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
            
            elif position.direction == "short":
                stop_loss = position.entry_price + self.params["stop_loss_atr"] * atr
                profit_exit = position.entry_price - self.params["profit_exit_atr"] * atr
                
                # 止损
                if close >= stop_loss:
                    self.units_held[symbol] = 0
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 止盈
                if close <= profit_exit:
                    self.units_held[symbol] = 0
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 离场信号：突破 N 日高点
                exit_high = max(self.high_prices[symbol][-self.params["exit_period"]:])
                if close > exit_high:
                    self.units_held[symbol] = 0
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
