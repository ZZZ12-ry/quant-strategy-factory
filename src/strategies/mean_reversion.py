"""
均值回归策略 - 价格偏离均线回归
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class MeanReversionStrategy(BaseStrategy):
    """均值回归策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "ma_period": 20,        # 均线周期
            "entry_std": 2.0,       # 入场标准差倍数
            "exit_std": 0.5,        # 出场标准差倍数
            "stop_loss_pct": 0.03,  # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "ma_period": (10, 50),
            "entry_std": (1.5, 3.0),
            "exit_std": (0, 1.0),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.close_prices = {}
        self.entry_prices = {}
    
    def _calculate_zscore(self, prices: list) -> Optional[float]:
        """计算 Z-Score"""
        if len(prices) < self.params["ma_period"]:
            return None
        
        ma = np.mean(prices[-self.params["ma_period"]:])
        std = np.std(prices[-self.params["ma_period"]:])
        
        if std == 0:
            return 0
        
        zscore = (prices[-1] - ma) / std
        return zscore
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        symbol = bar['symbol']
        close = bar['close']
        timestamp = bar['timestamp']
        
        # 初始化
        if symbol not in self.close_prices:
            self.close_prices[symbol] = []
            self.entry_prices[symbol] = {}
        
        # 更新价格
        self.close_prices[symbol].append(close)
        
        # 计算 Z-Score
        zscore = self._calculate_zscore(self.close_prices[symbol])
        if zscore is None:
            return None
        
        position = self.get_position(symbol)
        
        if position is None:
            # 价格低于下轨开多
            if zscore < -self.params["entry_std"]:
                self.entry_prices[symbol]['long'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min(abs(zscore) / 3, 1.0)
                )
            
            # 价格高于上轨开空
            elif zscore > self.params["entry_std"]:
                self.entry_prices[symbol]['short'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min(abs(zscore) / 3, 1.0)
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
                
                # 回归均值平仓
                if zscore > -self.params["exit_std"]:
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
                
                # 回归均值平仓
                if zscore < self.params["exit_std"]:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
