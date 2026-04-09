"""
策略基类 - 所有策略的父类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd


@dataclass
class Signal:
    """交易信号"""
    timestamp: datetime
    symbol: str
    direction: str  # "long" / "short" / "close"
    price: float
    volume: int
    strength: float  # 信号强度 0-1


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    direction: str  # "long" / "short"
    volume: int
    entry_price: float
    entry_time: datetime
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, **params):
        self.params = self.default_params()
        self.params.update(params)
        self.positions: Dict[str, Position] = {}
        self.signals: List[Signal] = []
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        """返回策略默认参数"""
        return {}
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        """返回参数优化空间（用于贝叶斯优化）"""
        return {}
    
    @abstractmethod
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        K 线数据回调
        
        Args:
            bar: 单根 K 线数据，包含 open/high/low/close/volume 等
        
        Returns:
            Signal: 交易信号（如果没有信号则返回 None）
        """
        pass
    
    def on_tick(self, tick: pd.Series) -> Optional[Signal]:
        """
        Tick 数据回调（可选实现）
        
        Args:
            tick: Tick 数据
        
        Returns:
            Signal: 交易信号
        """
        return None
    
    def generate_signal(
        self,
        symbol: str,
        timestamp: datetime,
        direction: str,
        price: float,
        volume: int,
        strength: float = 1.0
    ) -> Signal:
        """生成交易信号"""
        signal = Signal(
            timestamp=timestamp,
            symbol=symbol,
            direction=direction,
            price=price,
            volume=volume,
            strength=strength
        )
        self.signals.append(signal)
        return signal
    
    def update_position(
        self,
        symbol: str,
        direction: str,
        volume: int,
        entry_price: float,
        entry_time: datetime
    ):
        """更新持仓"""
        self.positions[symbol] = Position(
            symbol=symbol,
            direction=direction,
            volume=volume,
            entry_price=entry_price,
            entry_time=entry_time
        )
    
    def close_position(self, symbol: str, exit_price: float, exit_time: datetime) -> float:
        """平仓并计算盈亏"""
        if symbol not in self.positions:
            return 0.0
        
        pos = self.positions[symbol]
        if pos.direction == "long":
            pnl = (exit_price - pos.entry_price) * pos.volume
        else:
            pnl = (pos.entry_price - exit_price) * pos.volume
        
        pos.realized_pnl += pnl
        del self.positions[symbol]
        return pnl
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)
    
    def reset(self):
        """重置策略状态"""
        self.positions.clear()
        self.signals.clear()
    
    def __repr__(self):
        return f"{self.__class__.__name__}({self.params})"
