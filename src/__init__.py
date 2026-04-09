"""量化策略工厂"""
from src.strategy_factory import StrategyFactory
from src.backtest_engine import BacktestEngine, BacktestResult

__version__ = "0.1.0"
__author__ = "Coral"

__all__ = [
    "StrategyFactory",
    "BacktestEngine",
    "BacktestResult",
]
