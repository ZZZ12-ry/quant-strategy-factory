"""
策略工厂 - 统一管理所有策略模板（23 个）
"""
from typing import Dict, Type, Any, List
from src.strategies.base import BaseStrategy


class StrategyFactory:
    """策略工厂 - 创建和管理策略实例"""
    
    def __init__(self):
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        self._register_builtin_strategies()
    
    def _register_builtin_strategies(self):
        """注册内置策略 (23 个)"""
        # 延迟导入，避免循环依赖
        
        # === 原有 16 个策略 ===
        from src.strategies.dual_ma import DualMAStrategy
        from src.strategies.turtle_trader import TurtleTraderStrategy
        from src.strategies.channel_breakout import ChannelBreakoutStrategy
        from src.strategies.bollinger_mr import BollingerMRStrategy
        from src.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
        from src.strategies.macd_trend import MACDTrendStrategy
        from src.strategies.kdj_oscillator import KDJOscillatorStrategy
        from src.strategies.dual_thrust import DualThrustStrategy
        from src.strategies.awesome_oscillator import AwesomeOscillatorStrategy
        from src.strategies.aroon_trend import AroonTrendStrategy
        from src.strategies.stochastic_trend import StochasticTrendStrategy
        from src.strategies.adx_trend import ADXTrendStrategy
        from src.strategies.mean_reversion import MeanReversionStrategy
        from src.strategies.momentum_rank import MomentumRankStrategy
        from src.strategies.volatility_breakout import VolatilityBreakoutStrategy
        from src.strategies.pattern_recognition import PatternRecognitionStrategy
        
        # === 新增策略 ===
        from src.strategies.arbitrage_strategies import SpotFuturesArbitrage, CalendarSpreadArbitrage, CrossSectionalMomentum
        from src.strategies.multifactor_strategy import MultiFactorStrategy, FactorTimingStrategy
        from src.strategies.rl_strategy import RLTradingStrategy, PPOStrategy
        
        # 趋势跟踪策略 (6 个)
        self.register("DualMA", DualMAStrategy)
        self.register("TurtleTrader", TurtleTraderStrategy)
        self.register("ChannelBreakout", ChannelBreakoutStrategy)
        self.register("MACDTrend", MACDTrendStrategy)
        self.register("AroonTrend", AroonTrendStrategy)
        self.register("ADXTrend", ADXTrendStrategy)
        
        # 均值回归策略 (3 个)
        self.register("BollingerMR", BollingerMRStrategy)
        self.register("RSIMR", RSIMeanReversionStrategy)
        self.register("MeanReversion", MeanReversionStrategy)
        
        # 震荡策略 (3 个)
        self.register("KDJ", KDJOscillatorStrategy)
        self.register("AwesomeOsc", AwesomeOscillatorStrategy)
        self.register("Stochastic", StochasticTrendStrategy)
        
        # 突破策略 (2 个)
        self.register("DualThrust", DualThrustStrategy)
        self.register("VolatilityBreakout", VolatilityBreakoutStrategy)
        
        # 动量策略 (1 个)
        self.register("MomentumRank", MomentumRankStrategy)
        
        # 形态识别 (1 个)
        self.register("PatternRecognition", PatternRecognitionStrategy)
        
        # === 新增策略 (7 个) ===
        
        # 套利策略 (3 个)
        self.register("SpotFuturesArbitrage", SpotFuturesArbitrage)
        self.register("CalendarSpreadArbitrage", CalendarSpreadArbitrage)
        self.register("CrossSectionalMomentum", CrossSectionalMomentum)
        
        # 多因子策略 (2 个)
        self.register("MultiFactor", MultiFactorStrategy)
        self.register("FactorTiming", FactorTimingStrategy)
        
        # 强化学习策略 (2 个)
        self.register("RLTrading", RLTradingStrategy)
        self.register("PPO", PPOStrategy)
        
        # 成交量策略 (1 个) ⭐ 新增（基于论文）
        from src.strategies.volume_night_day import VolumeNightDayStrategyV2
        self.register("VolumeNightDay", VolumeNightDayStrategyV2)
    
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
    
    def get_strategy_categories(self) -> Dict[str, List[str]]:
        """获取策略分类"""
        return {
            '趋势跟踪': ['DualMA', 'TurtleTrader', 'ChannelBreakout', 'MACDTrend', 'AroonTrend', 'ADXTrend'],
            '均值回归': ['BollingerMR', 'RSIMR', 'MeanReversion'],
            '震荡策略': ['KDJ', 'AwesomeOsc', 'Stochastic'],
            '突破策略': ['DualThrust', 'VolatilityBreakout'],
            '动量策略': ['MomentumRank'],
            '形态识别': ['PatternRecognition'],
            '套利策略': ['SpotFuturesArbitrage', 'CalendarSpreadArbitrage', 'CrossSectionalMomentum'],  # ⭐ 新增
            '多因子策略': ['MultiFactor', 'FactorTiming'],  # ⭐ 新增
            '强化学习': ['RLTrading', 'PPO'],  # ⭐ 新增
            '成交量策略': ['VolumeNightDay'],  # ⭐ 新增（基于论文）
        }


# 全局单例
strategy_factory = StrategyFactory()
