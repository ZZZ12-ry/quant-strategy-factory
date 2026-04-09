"""
策略工厂 - 统一管理所有策略模板
"""
from typing import Dict, Type, Any, List
from src.strategies.base import BaseStrategy


class StrategyFactory:
    """策略工厂 - 创建和管理策略实例"""
    
    def __init__(self):
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        self._register_builtin_strategies()
    
    def _register_builtin_strategies(self):
        """注册内置策略"""
        # 延迟导入，避免循环依赖
        from src.strategies.dual_ma import DualMAStrategy
        from src.strategies.turtle_trader import TurtleTraderStrategy
        from src.strategies.channel_breakout import ChannelBreakoutStrategy
        
        self.register("DualMA", DualMAStrategy)
        self.register("TurtleTrader", TurtleTraderStrategy)
        self.register("ChannelBreakout", ChannelBreakoutStrategy)
    
    def register(self, name: str, strategy_class: Type[BaseStrategy]):
        """注册策略"""
        self._strategies[name] = strategy_class
    
    def list_strategies(self) -> List[str]:
        """列出所有可用策略"""
        return list(self._strategies.keys())
    
    def get_params(self, name: str) -> Dict[str, Any]:
        """获取策略默认参数"""
        if name not in self._strategies:
            raise ValueError(f"未知策略：{name}")
        return self._strategies[name].default_params()
    
    def create(self, name: str, **kwargs) -> BaseStrategy:
        """创建策略实例"""
        if name not in self._strategies:
            raise ValueError(f"未知策略：{name}，可用策略：{self.list_strategies()}")
        
        strategy_class = self._strategies[name]
        return strategy_class(**kwargs)


# 全局单例
strategy_factory = StrategyFactory()
