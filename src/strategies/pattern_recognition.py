"""
形态识别策略 - K 线形态识别
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal


class PatternRecognitionStrategy(BaseStrategy):
    """K 线形态识别策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "min_body_ratio": 0.6,   # 最小实体比例
            "min_shadow_ratio": 0.3, # 最小影线比例
            "confirmation": True,    # 需要确认 K 线
            "stop_loss_pct": 0.03,   # 止损百分比
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "min_body_ratio": (0.5, 0.8),
            "min_shadow_ratio": (0.2, 0.5),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.open_prices = {}
        self.high_prices = {}
        self.low_prices = {}
        self.close_prices = {}
        self.entry_prices = {}
        self.pending_signals = {}
    
    def _detect_patterns(self, symbol: str) -> Optional[str]:
        """检测 K 线形态"""
        if len(self.close_prices[symbol]) < 3:
            return None
        
        # 获取最近 3 根 K 线
        opens = self.open_prices[symbol][-3:]
        highs = self.high_prices[symbol][-3:]
        lows = self.low_prices[symbol][-3:]
        closes = self.close_prices[symbol][-3:]
        
        # 计算每根 K 线的特征
        bodies = [abs(c - o) for o, c in zip(opens, closes)]
        ranges = [h - l for h, l in zip(highs, lows)]
        upper_shadows = [h - max(o, c) for h, o, c in zip(highs, opens, closes)]
        lower_shadows = [min(o, c) - l for l, o, c in zip(lows, opens, closes)]
        
        # 检测锤子线（Hammer）
        if (bodies[-1] / ranges[-1] >= self.params["min_body_ratio"] and
            lower_shadows[-1] / bodies[-1] >= 2 and
            upper_shadows[-1] / bodies[-1] < 0.5):
            return "hammer"
        
        # 检测上吊线（Hanging Man）
        if (bodies[-1] / ranges[-1] >= self.params["min_body_ratio"] and
            lower_shadows[-1] / bodies[-1] >= 2 and
            upper_shadows[-1] / bodies[-1] < 0.5 and
            closes[-1] < opens[-1]):
            return "hanging_man"
        
        # 检测吞没形态（Engulfing）
        if (closes[-1] > opens[-1] and closes[-2] < opens[-2] and  # 阳包阴
            closes[-1] > opens[-2] and opens[-1] < closes[-2]):
            return "bullish_engulfing"
        
        if (closes[-1] < opens[-1] and closes[-2] > opens[-2] and  # 阴包阳
            closes[-1] < opens[-2] and opens[-1] > closes[-2]):
            return "bearish_engulfing"
        
        # 检测晨星（Morning Star）
        if (closes[-3] < opens[-3] and  # 第一根阴线
            bodies[-2] / ranges[-2] < 0.3 and  # 第二根小 K 线
            closes[-1] > opens[-1] and  # 第三根阳线
            closes[-1] > (closes[-3] + opens[-3]) / 2):  # 深入第一根实体
            return "morning_star"
        
        # 检测暮星（Evening Star）
        if (closes[-3] > opens[-3] and  # 第一根阳线
            bodies[-2] / ranges[-2] < 0.3 and  # 第二根小 K 线
            closes[-1] < opens[-1] and  # 第三根阴线
            closes[-1] < (closes[-3] + opens[-3]) / 2):  # 深入第一根实体
            return "evening_star"
        
        return None
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        symbol = bar['symbol']
        close = bar['close']
        high = bar['high']
        low = bar['low']
        open_price = bar['open']
        timestamp = bar['timestamp']
        
        # 初始化
        if symbol not in self.open_prices:
            self.open_prices[symbol] = []
            self.high_prices[symbol] = []
            self.low_prices[symbol] = []
            self.close_prices[symbol] = []
            self.entry_prices[symbol] = {}
            self.pending_signals[symbol] = None
        
        # 更新价格
        self.open_prices[symbol].append(open_price)
        self.high_prices[symbol].append(high)
        self.low_prices[symbol].append(low)
        self.close_prices[symbol].append(close)
        
        # 检测形态
        pattern = self._detect_patterns(symbol)
        
        position = self.get_position(symbol)
        
        if position is None:
            # 看涨形态
            if pattern in ["hammer", "bullish_engulfing", "morning_star"]:
                # 需要确认
                if self.params["confirmation"]:
                    self.pending_signals[symbol] = ('long', close)
                    return None
                else:
                    self.entry_prices[symbol]['long'] = close
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="long",
                        price=close,
                        volume=1,
                        strength=0.8
                    )
            
            # 看跌形态
            elif pattern in ["hanging_man", "bearish_engulfing", "evening_star"]:
                if self.params["confirmation"]:
                    self.pending_signals[symbol] = ('short', close)
                    return None
                else:
                    self.entry_prices[symbol]['short'] = close
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="short",
                        price=close,
                        volume=1,
                        strength=0.8
                    )
        else:
            # 确认信号
            if self.pending_signals[symbol]:
                direction, _ = self.pending_signals[symbol]
                
                if direction == 'long' and close > self.pending_signals[symbol][1]:
                    self.entry_prices[symbol]['long'] = close
                    self.pending_signals[symbol] = None
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="long",
                        price=close,
                        volume=1,
                        strength=0.8
                    )
                
                elif direction == 'short' and close < self.pending_signals[symbol][1]:
                    self.entry_prices[symbol]['short'] = close
                    self.pending_signals[symbol] = None
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="short",
                        price=close,
                        volume=1,
                        strength=0.8
                    )
            
            # 止损检查
            if position.direction == "long":
                entry = self.entry_prices[symbol].get('long', position.entry_price)
                
                if close < entry * (1 - self.params["stop_loss_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 出现反向形态平仓
                if pattern in ["hanging_man", "bearish_engulfing", "evening_star"]:
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
                
                if close > entry * (1 + self.params["stop_loss_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                
                # 出现反向形态平仓
                if pattern in ["hammer", "bullish_engulfing", "morning_star"]:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
