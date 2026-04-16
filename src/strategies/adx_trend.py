"""
ADX 趋势强度策略 - 平均趋向指数
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class ADXTrendStrategy(BaseStrategy):
    """ADX 趋势强度策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "adx_period": 14,       # ADX 周期
            "adx_threshold": 25,    # ADX 阈值（趋势强度）
            "di_period": 14,        # DI 周期
            "stop_loss_pct": 0.03,  # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "adx_period": (10, 20),
            "adx_threshold": (20, 35),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.high_prices = {}
        self.low_prices = {}
        self.close_prices = {}
        self.adx_values = {}
        self.plus_di = {}
        self.minus_di = {}
        self.entry_prices = {}
    
    def _calculate_adx(self, symbol: str) -> tuple:
        """计算 ADX, +DI, -DI"""
        period = self.params["adx_period"]
        
        if len(self.close_prices[symbol]) < period + 1:
            return None, None, None
        
        # 计算 TR, +DM, -DM
        tr_list = []
        plus_dm_list = []
        minus_dm_list = []
        
        for i in range(1, len(self.close_prices[symbol])):
            high_curr = self.high_prices[symbol][i]
            low_curr = self.low_prices[symbol][i]
            close_curr = self.close_prices[symbol][i]
            high_prev = self.high_prices[symbol][i-1]
            low_prev = self.low_prices[symbol][i-1]
            close_prev = self.close_prices[symbol][i-1]
            
            # True Range
            tr = max(high_curr - low_curr, 
                    abs(high_curr - close_prev), 
                    abs(low_curr - close_prev))
            tr_list.append(tr)
            
            # +DM, -DM
            up_move = high_curr - high_prev
            down_move = low_prev - low_curr
            
            if up_move > down_move and up_move > 0:
                plus_dm_list.append(up_move)
            else:
                plus_dm_list.append(0)
            
            if down_move > up_move and down_move > 0:
                minus_dm_list.append(down_move)
            else:
                minus_dm_list.append(0)
        
        if len(tr_list) < period:
            return None, None, None
        
        # 计算 smoothed TR, +DM, -DM
        tr_smooth = sum(tr_list[-period:])
        plus_dm_smooth = sum(plus_dm_list[-period:])
        minus_dm_smooth = sum(minus_dm_list[-period:])
        
        # 计算 +DI, -DI
        plus_di = (plus_dm_smooth / tr_smooth) * 100 if tr_smooth > 0 else 0
        minus_di = (minus_dm_smooth / tr_smooth) * 100 if tr_smooth > 0 else 0
        
        # 计算 DX
        if plus_di + minus_di > 0:
            dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
        else:
            dx = 0
        
        # 计算 ADX（DX 的平均）
        self.adx_values[symbol].append(dx)
        if len(self.adx_values[symbol]) < period:
            adx = dx
        else:
            adx = np.mean(self.adx_values[symbol][-period:])
        
        self.plus_di[symbol].append(plus_di)
        self.minus_di[symbol].append(minus_di)
        
        return adx, plus_di, minus_di
    
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
            self.adx_values[symbol] = []
            self.plus_di[symbol] = []
            self.minus_di[symbol] = []
            self.entry_prices[symbol] = {}
        
        # 更新价格
        self.high_prices[symbol].append(high)
        self.low_prices[symbol].append(low)
        self.close_prices[symbol].append(close)
        
        # 计算 ADX
        adx, plus_di, minus_di = self._calculate_adx(symbol)
        if adx is None:
            return None
        
        position = self.get_position(symbol)
        
        if position is None:
            # 强上涨趋势：ADX > 阈值 且 +DI > -DI
            if adx > self.params["adx_threshold"] and plus_di > minus_di:
                self.entry_prices[symbol]['long'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min((plus_di - minus_di) / 50, 1.0)
                )
            
            # 强下跌趋势：ADX > 阈值 且 -DI > +DI
            elif adx > self.params["adx_threshold"] and minus_di > plus_di:
                self.entry_prices[symbol]['short'] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min((minus_di - plus_di) / 50, 1.0)
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
                
                # 趋势减弱平仓
                if minus_di > plus_di:
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
                
                # 趋势减弱平仓
                if plus_di > minus_di:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
