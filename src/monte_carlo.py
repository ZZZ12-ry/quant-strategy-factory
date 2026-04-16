"""
Monte Carlo 压力测试 - 评估策略稳健性
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from tqdm import tqdm
from dataclasses import dataclass


@dataclass
class MonteCarloResult:
    """Monte Carlo 回测结果"""
    original_sharpe: float
    mean_sharpe: float
    std_sharpe: float
    min_sharpe: float
    max_sharpe: float
    percentile_5: float
    percentile_95: float
    robustness_score: float  # 稳健性评分 0-1
    num_simulations: int
    trade_shuffle_results: List[float]
    candle_shuffle_results: List[float]
    
    def is_robust(self, threshold: float = 0.5) -> bool:
        """判断策略是否稳健"""
        return self.robustness_score >= threshold


class MonteCarloEngine:
    """Monte Carlo 压力测试引擎"""
    
    def __init__(
        self,
        strategy,
        backtest_engine_class = None,
        num_simulations: int = 500
    ):
        """
        初始化 Monte Carlo 引擎
        
        Args:
            strategy: 策略实例
            backtest_engine_class: 回测引擎类
            num_simulations: 模拟次数
        """
        self.strategy = strategy
        self.num_simulations = num_simulations
        
        if backtest_engine_class is None:
            from src.backtest_engine import BacktestEngine
            backtest_engine_class = BacktestEngine
        
        self.backtest_engine_class = backtest_engine_class
    
    def run(
        self,
        data: pd.DataFrame,
        symbol: str,
        method: str = "both"
    ) -> MonteCarloResult:
        """
        运行 Monte Carlo 测试
        
        Args:
            data: 回测数据
            symbol: 品种代码
            method: 测试方法 (trade/candle/both)
        
        Returns:
            MonteCarloResult
        """
        # 原始回测
        original_strategy = self._clone_strategy()
        original_engine = self.backtest_engine_class(original_strategy)
        original_result = original_engine.run(data, symbol)
        original_sharpe = original_result.sharpe_ratio
        
        print(f"Original Sharpe Ratio: {original_sharpe:.4f}")
        
        trade_shuffle_results = []
        candle_shuffle_results = []
        
        # 交易顺序打乱测试
        if method in ["trade", "both"]:
            print("Running trade order shuffle...")
            trade_shuffle_results = self._shuffle_trades(
                original_result.trades,
                original_result.equity_curve,
                original_result.initial_cash
            )
        
        # K 线重采样测试
        if method in ["candle", "both"]:
            print("Running candle shuffle...")
            candle_shuffle_results = self._shuffle_candles(
                data,
                symbol
            )
        
        # 合并结果
        all_results = []
        if trade_shuffle_results:
            all_results.extend(trade_shuffle_results)
        if candle_shuffle_results:
            all_results.extend(candle_shuffle_results)
        
        if not all_results:
            raise ValueError("No simulations ran")
        
        # 计算统计量
        mean_sharpe = np.mean(all_results)
        std_sharpe = np.std(all_results)
        min_sharpe = np.min(all_results)
        max_sharpe = np.max(all_results)
        percentile_5 = np.percentile(all_results, 5)
        percentile_95 = np.percentile(all_results, 95)
        
        # 稳健性评分
        # 基于原始夏普与模拟分布的比较
        robustness_score = self._calculate_robustness(
            original_sharpe,
            mean_sharpe,
            std_sharpe,
            percentile_5
        )
        
        return MonteCarloResult(
            original_sharpe=original_sharpe,
            mean_sharpe=mean_sharpe,
            std_sharpe=std_sharpe,
            min_sharpe=min_sharpe,
            max_sharpe=max_sharpe,
            percentile_5=percentile_5,
            percentile_95=percentile_95,
            robustness_score=robustness_score,
            num_simulations=len(all_results),
            trade_shuffle_results=trade_shuffle_results,
            candle_shuffle_results=candle_shuffle_results
        )
    
    def _clone_strategy(self):
        """克隆策略实例"""
        params = self.strategy.params.copy()
        return self.strategy.__class__(**params)
    
    def _shuffle_trades(
        self,
        trades: List[Dict],
        equity_curve: List[float],
        initial_cash: float
    ) -> List[float]:
        """
        交易顺序打乱测试
        
        原理：随机打乱交易顺序，检验策略收益是否依赖特定交易时序
        """
        sharpe_ratios = []
        
        # 提取单笔交易盈亏
        trade_pnls = []
        for i, trade in enumerate(trades):
            if trade['action'] in ['close_long', 'close_short']:
                # 简化：从权益曲线推算
                pass
        
        # 简化版本：对权益曲线收益率进行重采样
        if len(equity_curve) < 20:
            return []
        
        returns = pd.Series(equity_curve).pct_change().dropna()
        
        for _ in tqdm(range(self.num_simulations // 2), desc="Trade Shuffle", leave=False):
            # 有放回抽样
            shuffled_returns = returns.sample(n=len(returns), replace=True).values
            
            # 计算累积收益
            cumulative = (1 + pd.Series(shuffled_returns)).cumprod()
            
            # 计算夏普比率
            if len(cumulative) > 10 and cumulative.std() != 0:
                sharpe = (cumulative.mean() / cumulative.std()) * np.sqrt(252)
                sharpe_ratios.append(sharpe)
        
        return sharpe_ratios
    
    def _shuffle_candles(
        self,
        data: pd.DataFrame,
        symbol: str
    ) -> List[float]:
        """
        K 线重采样测试
        
        原理：对 K 线进行有放回抽样，检验策略在不同市场路径下的表现
        """
        sharpe_ratios = []
        
        for _ in tqdm(range(self.num_simulations // 2), desc="Candle Shuffle", leave=False):
            # 有放回抽样 K 线
            sampled_data = data.sample(n=len(data), replace=True).sort_index().reset_index(drop=True)
            
            # 运行回测
            try:
                strategy = self._clone_strategy()
                engine = self.backtest_engine_class(strategy)
                result = engine.run(sampled_data, symbol)
                
                if result.sharpe_ratio is not None and not np.isnan(result.sharpe_ratio):
                    sharpe_ratios.append(result.sharpe_ratio)
            except:
                continue
        
        return sharpe_ratios
    
    def _calculate_robustness(
        self,
        original: float,
        mean: float,
        std: float,
        percentile_5: float
    ) -> float:
        """
        计算稳健性评分
        
        评分逻辑：
        1. 原始夏普 > 模拟均值 → 加分
        2. 5 分位数 > 0 → 加分（大部分情况盈利）
        3. 标准差小 → 加分（结果稳定）
        """
        score = 0.0
        
        # 原始表现优于模拟平均
        if original > mean:
            score += 0.3
        
        # 5 分位数为正（95% 的情况盈利）
        if percentile_5 > 0:
            score += 0.4
        
        # 标准差小（结果稳定）
        if std < 0.5:
            score += 0.3
        elif std < 1.0:
            score += 0.15
        
        return min(score, 1.0)
    
    def plot_distribution(self, results: MonteCarloResult):
        """绘制结果分布"""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("Please install matplotlib")
        
        all_results = results.trade_shuffle_results + results.candle_shuffle_results
        
        plt.figure(figsize=(12, 6))
        
        # 分布直方图
        plt.subplot(1, 2, 1)
        plt.hist(all_results, bins=30, alpha=0.7, edgecolor='black')
        plt.axvline(results.original_sharpe, color='red', linestyle='--', 
                   label=f'Original: {results.original_sharpe:.2f}')
        plt.axvline(results.mean_sharpe, color='green', linestyle='-', 
                   label=f'Mean: {results.mean_sharpe:.2f}')
        plt.axvline(results.percentile_5, color='orange', linestyle=':', 
                   label=f'5th: {results.percentile_5:.2f}')
        plt.xlabel('Sharpe Ratio')
        plt.ylabel('Frequency')
        plt.title('Monte Carlo Simulation Distribution')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 箱线图
        plt.subplot(1, 2, 2)
        plt.boxplot([all_results], vert=True, patch_artist=True)
        plt.ylabel('Sharpe Ratio')
        plt.title('Monte Carlo Results Box Plot')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
