"""
组合分析器 - 多策略组合分析
"""
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class PortfolioResult:
    """组合回测结果"""
    strategies: Dict[str, Any]
    weights: Dict[str, float]
    portfolio_return: float
    portfolio_sharpe: float
    portfolio_max_drawdown: float
    correlation_matrix: pd.DataFrame
    diversification_ratio: float


class PortfolioAnalyzer:
    """组合分析器"""
    
    def __init__(self):
        self.strategies: Dict[str, Any] = {}
        self.results: Dict[str, Any] = {}
        self.weights: Dict[str, float] = {}
    
    def add_strategy(
        self,
        name: str,
        result: Any,
        weight: float = None
    ):
        """
        添加策略到组合
        
        Args:
            name: 策略名称
            result: 回测结果
            weight: 权重（可选）
        """
        self.strategies[name] = result
        
        if weight is not None:
            self.weights[name] = weight
        else:
            # 默认等权重
            n = len(self.strategies)
            for s in self.strategies:
                self.weights[s] = 1.0 / n
    
    def analyze(self) -> PortfolioResult:
        """
        分析组合
        
        Returns:
            PortfolioResult
        """
        if len(self.strategies) == 0:
            raise ValueError("No strategies added")
        
        # 计算组合收益
        portfolio_return = 0.0
        for name, result in self.results.items():
            weight = self.weights.get(name, 1.0 / len(self.results))
            portfolio_return += weight * result.total_return
        
        # 计算策略间相关性
        correlation_matrix = self._calculate_correlation()
        
        # 计算组合夏普比率
        portfolio_sharpe = self._calculate_portfolio_sharpe()
        
        # 计算组合最大回撤
        portfolio_max_drawdown = self._calculate_portfolio_drawdown()
        
        # 计算分散化比率
        diversification_ratio = self._calculate_diversification_ratio()
        
        return PortfolioResult(
            strategies=self.strategies,
            weights=self.weights,
            portfolio_return=portfolio_return,
            portfolio_sharpe=portfolio_sharpe,
            portfolio_max_drawdown=portfolio_max_drawdown,
            correlation_matrix=correlation_matrix,
            diversification_ratio=diversification_ratio
        )
    
    def _calculate_correlation(self) -> pd.DataFrame:
        """计算策略收益相关性"""
        # 简化：使用总收益率计算相关性
        names = list(self.strategies.keys())
        returns = [self.strategies[name].total_return for name in names]
        
        # 创建伪相关性矩阵（实际应该用权益曲线）
        corr_matrix = pd.DataFrame(
            np.eye(len(names)),
            index=names,
            columns=names
        )
        
        return corr_matrix
    
    def _calculate_portfolio_sharpe(self) -> float:
        """计算组合夏普比率"""
        # 简化计算
        weighted_sharpe = 0.0
        for name, result in self.strategies.items():
            weight = self.weights.get(name, 1.0 / len(self.strategies))
            weighted_sharpe += weight * result.sharpe_ratio
        
        # 考虑分散化效应
        diversification_bonus = 0.1 * (len(self.strategies) - 1)
        
        return weighted_sharpe + diversification_bonus
    
    def _calculate_portfolio_drawdown(self) -> float:
        """计算组合最大回撤"""
        # 简化：取加权平均
        weighted_dd = 0.0
        for name, result in self.strategies.items():
            weight = self.weights.get(name, 1.0 / len(self.strategies))
            weighted_dd += weight * abs(result.max_drawdown)
        
        # 分散化降低回撤
        diversification_reduction = 0.1 * (len(self.strategies) - 1)
        
        return -(weighted_dd - diversification_reduction)
    
    def _calculate_diversification_ratio(self) -> float:
        """计算分散化比率"""
        # 分散化比率 = 组合夏普 / 加权平均夏普
        weighted_sharpe = 0.0
        for name, result in self.strategies.items():
            weight = self.weights.get(name, 1.0 / len(self.strategies))
            weighted_sharpe += weight * result.sharpe_ratio
        
        portfolio_sharpe = self._calculate_portfolio_sharpe()
        
        if weighted_sharpe == 0:
            return 1.0
        
        return portfolio_sharpe / weighted_sharpe
    
    def optimize_weights(
        self,
        method: str = "equal",
        target: str = "sharpe"
    ) -> Dict[str, float]:
        """
        优化策略权重
        
        Args:
            method: 优化方法 (equal/sharpe/risk_parity)
            target: 优化目标
        
        Returns:
            最优权重
        """
        n = len(self.strategies)
        
        if method == "equal":
            # 等权重
            return {name: 1.0/n for name in self.strategies}
        
        elif method == "sharpe":
            # 按夏普比率加权
            sharpes = {name: max(0, result.sharpe_ratio) 
                      for name, result in self.strategies.items()}
            total_sharpe = sum(sharpes.values())
            
            if total_sharpe == 0:
                return {name: 1.0/n for name in self.strategies}
            
            return {name: sharpe/total_sharpe for name, sharpe in sharpes.items()}
        
        elif method == "risk_parity":
            # 风险平价（简化版：按波动率倒数加权）
            # 实际应该用协方差矩阵
            risks = {name: abs(result.max_drawdown) 
                    for name, result in self.strategies.items()}
            inv_risks = {name: 1.0/max(risk, 0.01) for name, risk in risks.items()}
            total_inv_risk = sum(inv_risks.values())
            
            return {name: inv_risk/total_inv_risk for name, inv_risk in inv_risks.items()}
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def get_summary(self) -> pd.DataFrame:
        """获取组合摘要"""
        data = []
        for name, result in self.strategies.items():
            weight = self.weights.get(name, 0)
            data.append({
                'Strategy': name,
                'Weight': weight,
                'Return': result.total_return,
                'Sharpe': result.sharpe_ratio,
                'MaxDD': result.max_drawdown,
                'WinRate': result.win_rate
            })
        
        return pd.DataFrame(data)
