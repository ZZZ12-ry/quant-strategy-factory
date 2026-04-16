"""策略模块 - 19 个策略模板"""
from src.strategies.base import BaseStrategy, Signal, Position

# 趋势跟踪策略
from src.strategies.dual_ma import DualMAStrategy
from src.strategies.turtle_trader import TurtleTraderStrategy
from src.strategies.channel_breakout import ChannelBreakoutStrategy
from src.strategies.macd_trend import MACDTrendStrategy
from src.strategies.aroon_trend import AroonTrendStrategy
from src.strategies.adx_trend import ADXTrendStrategy

# 均值回归策略
from src.strategies.bollinger_mr import BollingerMRStrategy
from src.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from src.strategies.mean_reversion import MeanReversionStrategy

# 震荡策略
from src.strategies.kdj_oscillator import KDJOscillatorStrategy
from src.strategies.awesome_oscillator import AwesomeOscillatorStrategy
from src.strategies.stochastic_trend import StochasticTrendStrategy

# 突破策略
from src.strategies.dual_thrust import DualThrustStrategy
from src.strategies.volatility_breakout import VolatilityBreakoutStrategy

# 动量策略
from src.strategies.momentum_rank import MomentumRankStrategy

# 形态识别
from src.strategies.pattern_recognition import PatternRecognitionStrategy

# 套利策略（新增）
from src.strategies.arbitrage_strategies import SpotFuturesArbitrage, CalendarSpreadArbitrage, CrossSectionalMomentum

# 多因子策略（新增）
from src.strategies.multifactor_strategy import MultiFactorStrategy, FactorTimingStrategy

# 强化学习策略（新增）
from src.strategies.rl_strategy import RLTradingStrategy, PPOStrategy

# 成交量策略（新增 - 基于论文）
from src.strategies.volume_night_day import VolumeNightDayStrategyV2

__all__ = [
    # 基础类
    "BaseStrategy",
    "Signal",
    "Position",
    
    # 趋势跟踪 (6)
    "DualMAStrategy",
    "TurtleTraderStrategy",
    "ChannelBreakoutStrategy",
    "MACDTrendStrategy",
    "AroonTrendStrategy",
    "ADXTrendStrategy",
    
    # 均值回归 (3)
    "BollingerMRStrategy",
    "RSIMeanReversionStrategy",
    "MeanReversionStrategy",
    
    # 震荡策略 (3)
    "KDJOscillatorStrategy",
    "AwesomeOscillatorStrategy",
    "StochasticTrendStrategy",
    
    # 突破策略 (2)
    "DualThrustStrategy",
    "VolatilityBreakoutStrategy",
    
    # 动量策略 (1)
    "MomentumRankStrategy",
    
    # 形态识别 (1)
    "PatternRecognitionStrategy",
    
    # 套利策略 (3) ⭐ 新增
    "SpotFuturesArbitrage",
    "CalendarSpreadArbitrage",
    "CrossSectionalMomentum",
    
    # 多因子策略 (2) ⭐ 新增
    "MultiFactorStrategy",
    "FactorTimingStrategy",
    
    # 强化学习策略 (2) ⭐ 新增
    "RLTradingStrategy",
    "PPOStrategy",
    
    # 成交量策略 (1) ⭐ 新增（基于论文）
    "VolumeNightDayStrategyV2",
]

# 策略总数：24 个
