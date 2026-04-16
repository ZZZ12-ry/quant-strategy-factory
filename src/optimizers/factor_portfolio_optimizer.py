"""
因子组合优化器
使用 ML 模型进行因子选择和权重优化
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from src.ml.barra_factors import BarraFactors
from src.ml.factor_analyzer import FactorAnalyzer


class FactorPortfolioOptimizer:
    """因子组合优化器"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.barra = BarraFactors()
        self.analyzer = FactorAnalyzer()
        self.factor_data = None
        self.returns = None
    
    def prepare_data(self, lookback: int = 60):
        """准备因子数据和收益"""
        print("\n准备因子数据...")
        
        # 计算因子
        self.factor_data = self.barra.calculate_all(self.data)
        
        # 计算未来收益
        for period in [1, 5, 10, 20]:
            self.factor_data[f'future_return_{period}d'] = (
                self.factor_data['close'].shift(-period) / self.factor_data['close'] - 1
            )
        
        # 去除 NaN
        self.factor_data = self.factor_data.dropna()
        
        print(f"  有效样本：{len(self.factor_data)}")
        print(f"  因子数量：{len(self.barra.get_factor_names())}")
        
        return self.factor_data
    
    def select_factors_by_ic(self, threshold: float = 0.05, 
                             period: int = 5) -> List[str]:
        """
        根据 IC 选择有效因子
        
        Args:
            threshold: IC 阈值
            period: 持有期
        
        Returns:
            有效因子列表
        """
        print(f"\n选择 IC > {threshold} 的因子（{period}日收益）...")
        
        factor_names = self.barra.get_factor_names()
        valid_factors = []
        ic_results = {}
        
        for factor_name in factor_names:
            if factor_name in self.factor_data.columns:
                factor_values = self.factor_data[factor_name]
                returns = self.factor_data[f'future_return_{period}d']
                
                ic = self.analyzer.calc_ic(factor_values, returns)
                ic_results[factor_name] = ic
                
                if abs(ic) > threshold:
                    valid_factors.append(factor_name)
        
        print(f"  有效因子数：{len(valid_factors)}")
        
        # 按 IC 排序
        df_ic = pd.DataFrame({
            'factor': list(ic_results.keys()),
            'ic': list(ic_results.values())
        })
        df_ic = df_ic.sort_values('ic', ascending=False)
        
        print(f"\nTop 10 因子:")
        print(f"{'因子':<30} {'IC':<10}")
        print(f"{'-'*45}")
        for _, row in df_ic.head(10).iterrows():
            print(f"{row['factor']:<30} {row['ic']:>8.4f}")
        
        return valid_factors, ic_results
    
    def optimize_weights(self, factors: List[str], 
                         method='equal',
                         ic_dict: Dict = None) -> Dict[str, float]:
        """
        优化因子权重
        
        Args:
            factors: 因子列表
            method: 'equal' (等权), 'ic' (IC 加权), 'ir' (IR 加权)
            ic_dict: IC 字典
        
        Returns:
            因子权重字典
        """
        print(f"\n优化因子权重（方法：{method}）...")
        
        if method == 'equal':
            # 等权
            weights = {f: 1.0 / len(factors) for f in factors}
        
        elif method == 'ic':
            if ic_dict is None:
                raise ValueError("IC 加权需要提供 ic_dict")
            
            # IC 绝对值加权
            ic_values = {f: abs(ic_dict.get(f, 0)) for f in factors}
            total_ic = sum(ic_values.values())
            
            if total_ic > 0:
                weights = {f: ic_values[f] / total_ic for f in factors}
            else:
                weights = {f: 1.0 / len(factors) for f in factors}
        
        elif method == 'ir':
            # TODO: 实现 IR 加权
            weights = {f: 1.0 / len(factors) for f in factors}
        
        print(f"  因子数量：{len(weights)}")
        
        # 打印权重分布
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        print(f"\n权重分布:")
        for factor, weight in sorted_weights[:10]:
            print(f"  {factor}: {weight:.4f}")
        
        return weights
    
    def calculate_portfolio_score(self, weights: Dict[str, float]) -> pd.Series:
        """
        计算组合综合得分
        
        Args:
            weights: 因子权重
        
        Returns:
            综合得分序列
        """
        # 因子标准化
        normalized_factors = {}
        
        for factor_name in weights.keys():
            if factor_name in self.factor_data.columns:
                factor_series = self.factor_data[factor_name]
                # Z-Score
                zscore = (factor_series - factor_series.mean()) / (factor_series.std() + 1e-8)
                # 截断
                zscore = zscore.clip(-3, 3)
                normalized_factors[factor_name] = zscore
        
        # 加权综合
        portfolio_score = pd.Series(0, index=self.factor_data.index)
        
        for factor_name, weight in weights.items():
            if factor_name in normalized_factors:
                portfolio_score += weight * normalized_factors[factor_name]
        
        return portfolio_score
    
    def backtest_strategy(self, portfolio_score: pd.Series,
                          threshold: float = 0.5,
                          rebalance_period: int = 5) -> Dict:
        """
        回测因子组合策略
        
        Returns:
            绩效指标
        """
        print(f"\n回测因子组合策略...")
        
        trades = []
        position = None
        equity = 1.0
        equity_curve = [1.0]
        
        for i in range(0, len(portfolio_score), rebalance_period):
            score = portfolio_score.iloc[i]
            price = self.factor_data['close'].iloc[i]
            
            # 开仓逻辑
            if position is None:
                if score > threshold:
                    position = {'direction': 'long', 'entry_price': price, 'entry_idx': i}
                elif score < -threshold:
                    position = {'direction': 'short', 'entry_price': price, 'entry_idx': i}
            
            # 平仓逻辑
            else:
                should_close = False
                
                # 得分反转
                if position['direction'] == 'long' and score < 0:
                    should_close = True
                elif position['direction'] == 'short' and score > 0:
                    should_close = True
                
                if should_close:
                    exit_price = price
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                    if position['direction'] == 'short':
                        pnl_pct = -pnl_pct
                    
                    # 扣除手续费
                    pnl_pct -= 0.0006
                    
                    trades.append(pnl_pct)
                    equity *= (1 + pnl_pct)
                    equity_curve.append(equity)
                    position = None
                    
                    # 反向开仓
                    if score > threshold:
                        position = {'direction': 'long', 'entry_price': price, 'entry_idx': i}
                    elif score < -threshold:
                        position = {'direction': 'short', 'entry_price': price, 'entry_idx': i}
        
        # 计算绩效
        if not trades:
            return {}
        
        metrics = {
            'total_return': (equity - 1) * 100,
            'sharpe': np.mean(trades) / (np.std(trades) + 1e-8) * np.sqrt(252),
            'win_rate': len([t for t in trades if t > 0]) / len(trades) * 100,
            'max_drawdown': self._calc_max_drawdown(equity_curve),
            'total_trades': len(trades),
            'avg_trade': np.mean(trades) * 100,
        }
        
        return metrics
    
    def _calc_max_drawdown(self, equity_curve: List[float]) -> float:
        """计算最大回撤"""
        equity = np.array(equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak
        return np.max(drawdown) * 100
    
    def run_full_optimization(self) -> Dict:
        """运行完整优化流程"""
        print("\n" + "="*70)
        print("因子组合优化 - 完整流程")
        print("="*70)
        
        # 1. 准备数据
        self.prepare_data()
        
        # 2. 选择有效因子
        valid_factors, ic_dict = self.select_factors_by_ic(threshold=0.05, period=5)
        
        if len(valid_factors) < 5:
            print("  [WARN] 有效因子太少，降低阈值...")
            valid_factors, ic_dict = self.select_factors_by_ic(threshold=0.03, period=5)
        
        # 3. 优化权重
        weights_equal = self.optimize_weights(valid_factors, method='equal')
        weights_ic = self.optimize_weights(valid_factors, method='ic', ic_dict=ic_dict)
        
        # 4. 计算组合得分
        score_equal = self.calculate_portfolio_score(weights_equal)
        score_ic = self.calculate_portfolio_score(weights_ic)
        
        # 5. 回测对比
        print(f"\n{'='*70}")
        print("策略对比")
        print(f"{'='*70}")
        
        metrics_equal = self.backtest_strategy(score_equal, threshold=0.5, rebalance_period=5)
        metrics_ic = self.backtest_strategy(score_ic, threshold=0.5, rebalance_period=5)
        
        print(f"\n{'指标':<20} {'等权':<15} {'IC 加权':<15}")
        print(f"{'-'*55}")
        print(f"{'总收益%':<20} {metrics_equal.get('total_return',0):>12.2f} {metrics_ic.get('total_return',0):>12.2f}")
        print(f"{'夏普比率':<20} {metrics_equal.get('sharpe',0):>12.2f} {metrics_ic.get('sharpe',0):>12.2f}")
        print(f"{'胜率%':<20} {metrics_equal.get('win_rate',0):>12.1f} {metrics_ic.get('win_rate',0):>12.1f}")
        print(f"{'最大回撤%':<20} {metrics_equal.get('max_drawdown',0):>12.2f} {metrics_ic.get('max_drawdown',0):>12.2f}")
        print(f"{'交易次数':<20} {metrics_equal.get('total_trades',0):>12} {metrics_ic.get('total_trades',0):>12}")
        
        # 6. 最佳方案
        if metrics_ic.get('sharpe', 0) > metrics_equal.get('sharpe', 0):
            best_method = 'IC 加权'
            best_metrics = metrics_ic
            best_weights = weights_ic
        else:
            best_method = '等权'
            best_metrics = metrics_equal
            best_weights = weights_equal
        
        print(f"\n{'='*70}")
        print(f"最佳方案：{best_method}")
        print(f"{'='*70}")
        print(f"  总收益：{best_metrics.get('total_return',0):.2f}%")
        print(f"  夏普比率：{best_metrics.get('sharpe',0):.2f}")
        print(f"  胜率：{best_metrics.get('win_rate',0):.1f}%")
        print(f"  最大回撤：{best_metrics.get('max_drawdown',0):.2f}%")
        
        return {
            'best_method': best_method,
            'best_metrics': best_metrics,
            'best_weights': best_weights,
            'valid_factors': valid_factors,
            'ic_dict': ic_dict,
        }


def test_factor_optimizer():
    """测试因子组合优化器"""
    print("\n" + "="*70)
    print("因子组合优化器 - 测试")
    print("="*70)
    
    # 获取数据
    try:
        import akshare as ak
        df = ak.futures_zh_daily_sina(symbol="RB2405")
        df = df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low',
            'close': 'close', 'volume': 'volume'
        })
        df['timestamp'] = pd.to_datetime(df['date'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"\n[OK] 获取螺纹钢数据：{len(df)} 条")
    except:
        np.random.seed(42)
        n = 300
        close = 100 * np.exp(np.cumsum(np.random.randn(n) * 0.02))
        df = pd.DataFrame({
            'open': close * (1 + np.random.randn(n) * 0.005),
            'high': close * (1 + np.abs(np.random.randn(n) * 0.01)),
            'low': close * (1 - np.abs(np.random.randn(n) * 0.01)),
            'close': close,
            'volume': np.random.randint(10000, 50000, n),
            'timestamp': pd.date_range('2024-01-01', periods=n)
        })
        print(f"\n[SIM] 使用模拟数据：{len(df)} 条")
    
    # 创建优化器
    optimizer = FactorPortfolioOptimizer(df)
    
    # 运行优化
    results = optimizer.run_full_optimization()
    
    print(f"\n{'='*70}")
    print("[OK] 因子组合优化测试完成")
    print(f"{'='*70}")
    
    return optimizer, results


if __name__ == "__main__":
    optimizer, results = test_factor_optimizer()
