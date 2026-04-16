"""
动量排名策略 - 多品种动量轮动
"""
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class MomentumRankStrategy(BaseStrategy):
    """动量排名轮动策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "momentum_period": 20,  # 动量计算周期
            "top_n": 3,             # 持有前 N 个品种
            "rebalance_period": 5,  # 调仓周期
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "momentum_period": (10, 50),
            "top_n": (1, 5),
            "rebalance_period": (3, 10),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.close_prices = {}
        self.momentum_values = {}
        self.bar_count = 0
        self.current_holdings = set()
    
    def _calculate_momentum(self, symbol: str) -> Optional[float]:
        """计算动量"""
        if len(self.close_prices[symbol]) < self.params["momentum_period"]:
            return None
        
        momentum = (self.close_prices[symbol][-1] - 
                   self.close_prices[symbol][-self.params["momentum_period"]]) / \
                   self.close_prices[symbol][-self.params["momentum_period"]]
        
        return momentum
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        symbol = bar['symbol']
        close = bar['close']
        timestamp = bar['timestamp']
        
        # 初始化
        if symbol not in self.close_prices:
            self.close_prices[symbol] = []
            self.momentum_values[symbol] = None
        
        # 更新价格
        self.close_prices[symbol].append(close)
        
        # 计算动量
        momentum = self._calculate_momentum(symbol)
        if momentum is not None:
            self.momentum_values[symbol] = momentum
        
        self.bar_count += 1
        
        # 未到调仓日
        if self.bar_count % self.params["rebalance_period"] != 0:
            return None
        
        # 计算所有品种动量
        valid_momentum = {
            sym: mom for sym, mom in self.momentum_values.items()
            if mom is not None and len(self.close_prices[sym]) >= self.params["momentum_period"]
        }
        
        if len(valid_momentum) < self.params["top_n"]:
            return None
        
        # 动量排名
        ranked = sorted(valid_momentum.items(), key=lambda x: x[1], reverse=True)
        top_symbols = [sym for sym, _ in ranked[:self.params["top_n"]]]
        
        signals = []
        
        # 平仓不在 top_n 的持仓
        for holding in list(self.current_holdings):
            if holding not in top_symbols:
                position = self.get_position(holding)
                if position:
                    signals.append(self.generate_signal(
                        symbol=holding,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    ))
        
        # 开仓新的 top_n
        for sym in top_symbols:
            if sym not in self.current_holdings:
                position = self.get_position(sym)
                if not position:
                    signals.append(self.generate_signal(
                        symbol=sym,
                        timestamp=timestamp,
                        direction="long",
                        price=close,
                        volume=1,
                        strength=valid_momentum[sym]
                    ))
        
        # 更新持仓
        self.current_holdings = set(top_symbols)
        
        # 返回第一个信号（简化处理）
        return signals[0] if signals else None
