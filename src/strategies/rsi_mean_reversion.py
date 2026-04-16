"""
RSI 均值回归策略 - 超买超卖反转
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class RSIMeanReversionStrategy(BaseStrategy):
    """RSI 均值回归策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "rsi_period": 14,       # RSI 周期
            "oversold": 30,         # 超卖阈值
            "overbought": 70,       # 超买阈值
            "exit_rsi": 50,         # 平仓 RSI 水平
            "stop_loss_pct": 0.03,  # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "rsi_period": (7, 28),
            "oversold": (20, 40),
            "overbought": (60, 80),
            "stop_loss_pct": (0.02, 0.05),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.close_prices = {}
        self.entry_prices = {}
    
    def _calculate_rsi(self, prices: list) -> Optional[float]:
        """计算 RSI"""
        if len(prices) < self.params["rsi_period"] + 1:
            return None
        
        # 计算价格变化
        changes = np.diff(prices[-self.params["rsi_period"]-1:])
        
        gains = np.where(changes > 0, changes, 0)
        losses = np.where(changes < 0, -changes, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
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
        
        # 计算 RSI
        rsi = self._calculate_rsi(self.close_prices[symbol])
        if rsi is None:
            return None
        
        position = self.get_position(symbol)
        
        if position is None:
            # 开多：RSI 超卖
            if rsi < self.params["oversold"]:
                self.entry_prices[symbol]['long'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min((self.params["oversold"] - rsi) / 20, 1.0)
                )
            
            # 开空：RSI 超买
            elif rsi > self.params["overbought"]:
                self.entry_prices[symbol]['short'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min((rsi - self.params["overbought"]) / 20, 1.0)
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
                
                # RSI 回归中值平仓
                if rsi >= self.params["exit_rsi"]:
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
                
                # RSI 回归中值平仓
                if rsi <= self.params["exit_rsi"]:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
