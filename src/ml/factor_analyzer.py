"""
因子有效性检验框架
计算 IC/IR/因子衰减/因子相关性
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from scipy import stats


class FactorAnalyzer:
    """因子分析器"""
    
    def __init__(self):
        self.ic_history = []
        self.factor_data = None
    
    def calc_ic(self, factor_values: pd.Series, forward_returns: pd.Series, 
                method='spearman') -> float:
        """
        计算 IC (Information Coefficient)
        
        Args:
            factor_values: 因子值
            forward_returns: 未来收益
            method: 'pearson' 或 'spearman'
        
        Returns:
            IC 值
        """
        if method == 'pearson':
            ic, _ = stats.pearsonr(factor_values, forward_returns)
        else:  # spearman
            ic, _ = stats.spearmanr(factor_values, forward_returns)
        
        return ic if not np.isnan(ic) else 0.0
    
    def calc_ir(self, ic_series: List[float]) -> float:
        """
        计算 IR (Information Ratio)
        
        Args:
            ic_series: IC 时间序列
        
        Returns:
            IR 值
        """
        ic_mean = np.mean(ic_series)
        ic_std = np.std(ic_series)
        
        if ic_std == 0:
            return 0.0
        
        return ic_mean / ic_std
    
    def calc_factor_decay(self, factor_values: pd.Series, 
                          returns_matrix: pd.DataFrame,
                          periods: List[int] = [1, 5, 10, 20, 60]) -> Dict[int, float]:
        """
        计算因子衰减（不同持有期的 IC）
        
        Args:
            factor_values: 因子值
            returns_matrix: 收益矩阵（列为不同持有期收益）
            periods: 持有期列表
        
        Returns:
            各持有期的 IC
        """
        decay = {}
        
        for period in periods:
            if f'return_{period}d' in returns_matrix.columns:
                ic = self.calc_ic(factor_values, returns_matrix[f'return_{period}d'])
                decay[period] = ic
        
        return decay
    
    def calc_factor_correlation(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算因子相关性矩阵
        
        Args:
            factor_df: 多因子数据框
        
        Returns:
            相关性矩阵
        """
        return factor_df.corr()
    
    def analyze_factor(self, factor_name: str, factor_values: pd.Series,
                       returns: pd.Series) -> Dict:
        """
        完整因子分析
        
        Returns:
            包含 IC/IR/胜率等指标的字典
        """
        # IC
        ic = self.calc_ic(factor_values, returns)
        
        # 分组收益（按因子值分 5 组）
        quintiles = pd.qcut(factor_values, 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'], duplicates='drop')
        group_returns = returns.groupby(quintiles).mean()
        
        # 多空收益（Q5 - Q1）
        long_short_return = group_returns['Q5'] - group_returns['Q1']
        
        # 胜率
        factor_direction = factor_values.diff()
        return_direction = returns.shift(-1)
        win_rate = (factor_direction * return_direction > 0).mean()
        
        return {
            'factor_name': factor_name,
            'ic': ic,
            'ir': self.calc_ir([ic]),  # 单期 IR
            'win_rate': win_rate,
            'long_short_return': long_short_return,
            'q1_return': group_returns.get('Q1', 0),
            'q5_return': group_returns.get('Q5', 0),
        }
    
    def batch_analyze(self, factor_df: pd.DataFrame, returns: pd.Series) -> pd.DataFrame:
        """
        批量分析多个因子
        
        Args:
            factor_df: 多因子数据框（每列一个因子）
            returns: 未来收益
        
        Returns:
            各因子的分析结果
        """
        results = []
        
        for col in factor_df.columns:
            factor_values = factor_df[col].dropna()
            aligned_returns = returns.loc[factor_values.index]
            
            if len(factor_values) > 30:  # 至少 30 个样本
                result = self.analyze_factor(col, factor_values, aligned_returns)
                results.append(result)
        
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('ic', ascending=False)
        
        return df_results


def test_factor_analyzer():
    """测试因子分析器"""
    print("\n" + "="*70)
    print("因子有效性检验框架 - 测试")
    print("="*70)
    
    # 生成测试数据
    np.random.seed(42)
    n_samples = 500
    
    # 生成因子值（5 个因子）
    factor_data = pd.DataFrame({
        'momentum': np.random.randn(n_samples),
        'value': np.random.randn(n_samples),
        'quality': np.random.randn(n_samples),
        'volatility': np.random.randn(n_samples),
        'size': np.random.randn(n_samples),
    })
    
    # 生成未来收益（与 momentum 和 quality 正相关）
    returns = (0.5 * factor_data['momentum'] + 
               0.3 * factor_data['quality'] + 
               np.random.randn(n_samples) * 0.5)
    
    print(f"\n测试数据:")
    print(f"  样本数：{n_samples}")
    print(f"  因子数：{len(factor_data.columns)}")
    
    # 创建分析器
    analyzer = FactorAnalyzer()
    
    # 批量分析
    print(f"\n{'='*70}")
    print("因子分析结果")
    print(f"{'='*70}")
    
    results = analyzer.batch_analyze(factor_data, returns)
    
    print(f"\n{'因子':<15} {'IC':<10} {'IR':<10} {'胜率%':<10} {'多空收益%':<12}")
    print(f"{'-'*70}")
    
    for _, row in results.iterrows():
        print(f"{row['factor_name']:<15} {row['ic']:>8.4f} {row['ir']:>8.4f} "
              f"{row['win_rate']*100:>8.1f} {row['long_short_return']*100:>10.2f}")
    
    # 因子相关性
    print(f"\n{'='*70}")
    print("因子相关性矩阵")
    print(f"{'='*70}")
    
    corr_matrix = analyzer.calc_factor_correlation(factor_data)
    
    print(f"\n{corr_matrix.round(2)}")
    
    # 因子衰减
    print(f"\n{'='*70}")
    print("因子衰减分析 (Momentum)")
    print(f"{'='*70}")
    
    # 生成多期收益
    returns_matrix = pd.DataFrame({
        'return_1d': returns,
        'return_5d': returns.rolling(5).sum(),
        'return_10d': returns.rolling(10).sum(),
        'return_20d': returns.rolling(20).sum(),
    }).dropna()
    
    aligned_factor = factor_data['momentum'].loc[returns_matrix.index]
    
    decay = analyzer.calc_factor_decay(aligned_factor, returns_matrix, [1, 5, 10, 20])
    
    print(f"\n{'持有期 (天)':<15} {'IC':<10}")
    print(f"{'-'*30}")
    for period, ic in decay.items():
        print(f"{period:<15} {ic:>8.4f}")
    
    print(f"\n{'='*70}")
    print("[OK] 因子分析框架测试完成")
    print(f"{'='*70}")
    
    return results, corr_matrix, decay


if __name__ == "__main__":
    results, corr, decay = test_factor_analyzer()
