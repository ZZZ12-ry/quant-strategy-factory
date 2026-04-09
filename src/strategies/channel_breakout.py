"""
通道突破策略 - 基于价格通道突破的趋势跟踪
"""
from typing import Dict, Any, Optional
import pandas as pd
from src.strategies.base import BaseStrategy, Signal


class ChannelBreakoutStrategy(BaseStrategy):
    """通道突破策略"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "lookback_period": 20,    # 通道周期
            "entry_threshold": 0.0,   # 入场阈值（突破百分比）
            "exit_period": 10,        # 离场周期
            "stop_loss_pct": 0.05,    # 止损百分比
            "use_volume_filter": True, # 使用成交量过滤
            "volume_ratio": 1.5,      # 成交量放大倍数
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "lookback_period": (10, 50),
            "exit_period": (5, 30),
            "stop_loss_pct": (0.03, 0.10),
            "volume_ratio": (1.0, 3.0),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.high_prices = {}
        self.low_prices = {}
        self.volumes = {}
        self.entry_prices = {}
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        symbol = bar['symbol']
        close = bar['close']
        high = bar['high']
        low = bar['low']
        volume = bar.get('volume', 0)
        timestamp = bar['timestamp']
        
        # 初始化
        if symbol not in self.high_prices:
            self.high_prices[symbol] = []
            self.low_prices[symbol] = []
            self.volumes[symbol] = []
            self.entry_prices[symbol] = None
        
        # 更新价格序列
        self.high_prices[symbol].append(high)
        self.low_prices[symbol].append(low)
        self.volumes[symbol].append(volume)
        
        # 数据不足
        if len(self.high_prices[symbol]) < self.params["lookback_period"]:
            return None
        
        # 计算通道
        upper_channel = max(self.high_prices[symbol][-self.params["lookback_period"]:])
        lower_channel = min(self.low_prices[symbol][-self.params["lookback_period"]:])
        
        # 成交量过滤
        volume_ok = True
        if self.params["use_volume_filter"]:
            avg_volume = sum(self.volumes[symbol][-10:]) / 10
            volume_ok = volume > avg_volume * self.params["volume_ratio"]
        
        # 持仓管理
        position = self.get_position(symbol)
        
        if position is None:
            # 入场信号：突破上轨
            if high > upper_channel * (1 + self.params["entry_threshold"]) and volume_ok:
                self.entry_prices[symbol] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=min((high - upper_channel) / upper_channel * 100, 1.0)
                )
            
            # 入场信号：跌破下轨
            elif low < lower_channel * (1 - self.params["entry_threshold"]) and volume_ok:
                self.entry_prices[symbol] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=min((lower_channel - low) / lower_channel * 100, 1.0)
                )
        else:
            # 止损止盈
            if position.direction == "long":
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
                
                # 离场：跌破 N 日低点
                exit_low = min(self.low_prices[symbol][-self.params["exit_period"]:])
                if close < exit_low:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
            
            elif position.direction == "short":
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
                
                # 离场：突破 N 日高点
                exit_high = max(self.high_prices[symbol][-self.params["exit_period"]:])
                if close > exit_high:
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
