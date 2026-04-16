"""
Awesome Oscillator 策略 - 动量 oscillator 策略
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class AwesomeOscillatorStrategy(BaseStrategy):
    """Awesome Oscillator 动量策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "fast_period": 5,       # 快线周期
            "slow_period": 34,      # 慢线周期
            "saucer_confirm": True, # 碟形确认
            "stop_loss_pct": 0.03,  # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "fast_period": (3, 10),
            "slow_period": (20, 50),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.high_prices = {}
        self.low_prices = {}
        self.ao_values = {}
        self.entry_prices = {}
    
    def _calculate_ao(self, symbol: str) -> Optional[float]:
        """计算 Awesome Oscillator"""
        if len(self.high_prices[symbol]) < self.params["slow_period"]:
            return None
        
        # 计算中点 (H+L)/2
        midpoints = [(h + l) / 2 for h, l in zip(
            self.high_prices[symbol], 
            self.low_prices[symbol]
        )]
        
        # 计算 SMA
        fast_sma = np.mean(midpoints[-self.params["fast_period"]:])
        slow_sma = np.mean(midpoints[-self.params["slow_period"]:])
        
        ao = fast_sma - slow_sma
        self.ao_values[symbol].append(ao)
        
        return ao
    
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
            self.ao_values[symbol] = []
            self.entry_prices[symbol] = {}
        
        # 更新价格
        self.high_prices[symbol].append(high)
        self.low_prices[symbol].append(low)
        
        # 计算 AO
        ao = self._calculate_ao(symbol)
        if ao is None:
            return None
        
        # 至少需要 3 个 AO 值来判断形态
        if len(self.ao_values[symbol]) < 3:
            return None
        
        ao_curr = self.ao_values[symbol][-1]
        ao_prev = self.ao_values[symbol][-2]
        ao_prev2 = self.ao_values[symbol][-3]
        
        position = self.get_position(symbol)
        
        if position is None:
            # 零线穿越（金叉）
            if ao_prev < 0 and ao_curr > 0:
                self.entry_prices[symbol]['long'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min(abs(ao_curr) * 10, 1.0)
                )
            
            # 零线穿越（死叉）
            elif ao_prev > 0 and ao_curr < 0:
                self.entry_prices[symbol]['short'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min(abs(ao_curr) * 10, 1.0)
                )
            
            # 碟形买入（Saucer）- 在零线上方
            if self.params["saucer_confirm"]:
                if ao_curr > 0 and ao_prev > 0 and ao_prev2 > 0:
                    if ao_prev2 > ao_prev < ao_curr:  # 中间低
                        self.entry_prices[symbol]['long'] = close
                        return self.generate_signal(
                            symbol=symbol,
                            timestamp=timestamp,
                            direction="long",
                            price=close,
                            volume=1,
                            strength=0.7
                        )
            
            # 碟形卖出 - 在零线下方
            if self.params["saucer_confirm"]:
                if ao_curr < 0 and ao_prev < 0 and ao_prev2 < 0:
                    if ao_prev2 < ao_prev > ao_curr:  # 中间高
                        self.entry_prices[symbol]['short'] = close
                        return self.generate_signal(
                            symbol=symbol,
                            timestamp=timestamp,
                            direction="short",
                            price=close,
                            volume=1,
                            strength=0.7
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
                
                # AO 转负平仓
                if ao_curr < 0:
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
                
                # AO 转正平仓
                if ao_curr > 0:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
