"""
因子中性化模块
消除行业/市值/Beta 等风格暴露
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from scipy import stats


class FactorNeutralizer:
    """因子中性化器"""
    
    def __init__(self):
        self.neutralization_factors = []
    
    def neutralize(self, factor_values: pd.Series, 
                   neutralization_vars: pd.DataFrame,
                   method='regression') -> pd.Series:
        """
        因子中性化
        
        Args:
            factor_values: 待中性化的因子值
            neutralization_vars: 中性化变量（如市值、行业 Beta 等）
            method: 'regression' (回归残差) 或 'stratify' (分层)
        
        Returns:
            中性化后的因子
        """
        if method == 'regression':
            return self._neutralize_regression(factor_values, neutralization_vars)
        elif method == 'stratify':
            return self._neutralize_stratify(factor_values, neutralization_vars)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _neutralize_regression(self, factor_values: pd.Series,
                                neutralization_vars: pd.DataFrame) -> pd.Series:
        """
        回归残差法中性化
        
        原理：因子对中性化变量回归，取残差作为中性化因子
        """
        # 对齐数据
        aligned = pd.DataFrame({
            'factor': factor_values
        }).join(neutralization_vars, how='inner').dropna()
        
        if len(aligned) < 30:
            print(f"  [WARN] 样本数不足 ({len(aligned)}), 跳过中性化")
            return factor_values
        
        y = aligned['factor'].values
        X = aligned.drop('factor', axis=1).values
        
        # 添加截距项
        X_with_intercept = np.column_stack([np.ones(len(X)), X])
        
        # OLS 回归
        try:
            beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
            
            # 计算预测值
            y_pred = X_with_intercept @ beta
            
            # 残差 = 实际值 - 预测值
            residuals = y - y_pred
            
            # 将残差放回原索引
            neutralized = pd.Series(residuals, index=aligned.index)
            
            # 重新标准化（均值为 0，标准差为 1）
            neutralized = (neutralized - neutralized.mean()) / (neutralized.std() + 1e-8)
            
            return neutralized
            
        except Exception as e:
            print(f"  [WARN] 回归失败：{e}")
            return factor_values
    
    def _neutralize_stratify(self, factor_values: pd.Series,
                              neutralization_vars: pd.DataFrame) -> pd.Series:
        """
        分层法中性化
        
        原理：按中性化变量分组，组内标准化
        """
        # 对齐数据
        aligned = pd.DataFrame({
            'factor': factor_values
        }).join(neutralization_vars, how='inner').dropna()
        
        # 按第一列分组（通常是行业或市值分位）
        group_col = aligned.columns[1]
        
        # 组内标准化
        neutralized = aligned.groupby(group_col)['factor'].transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-8)
        )
        
        return neutralized
    
    def neutralize_market_cap(self, factor_values: pd.Series,
                              market_cap: pd.Series) -> pd.Series:
        """
        市值中性化
        
        Args:
            factor_values: 因子值
            market_cap: 市值（可用成交量或价格代理）
        
        Returns:
            市值中性化后的因子
        """
        return self.neutralize(factor_values, pd.DataFrame({'size': market_cap}))
    
    def neutralize_beta(self, factor_values: pd.Series,
                        market_returns: pd.Series) -> pd.Series:
        """
        Beta 中性化
        
        Args:
            factor_values: 因子值
            market_returns: 市场收益（可用品种指数收益代理）
        
        Returns:
            Beta 中性化后的因子
        """
        return self.neutralize(factor_values, pd.DataFrame({'beta': market_returns}))
    
    def neutralize_industry(self, factor_values: pd.Series,
                            industry_dummy: pd.DataFrame) -> pd.Series:
        """
        行业中性化
        
        Args:
            factor_values: 因子值
            industry_dummy: 行业哑变量（One-Hot 编码）
        
        Returns:
            行业中性化后的因子
        """
        return self.neutralize(factor_values, industry_dummy)
    
    def neutralize_multiple(self, factor_values: pd.Series,
                            neutralization_dict: Dict[str, pd.Series]) -> pd.Series:
        """
        多变量中性化
        
        Args:
            factor_values: 因子值
            neutralization_dict: {变量名：变量值}
        
        Returns:
            多变量中性化后的因子
        """
        neutralization_df = pd.DataFrame(neutralization_dict)
        return self.neutralize(factor_values, neutralization_df)


def test_factor_neutralization():
    """测试因子中性化"""
    print("\n" + "="*70)
    print("因子中性化测试")
    print("="*70)
    
    # 生成测试数据
    np.random.seed(42)
    n_samples = 500
    
    # 原始因子（与市值相关）
    market_cap = np.random.randn(n_samples) * 10 + 100
    raw_factor = 0.5 * market_cap + np.random.randn(n_samples) * 5
    
    # 未来收益（与原始因子无关，与中性化因子有关）
    future_return = np.random.randn(n_samples) * 0.02
    
    df = pd.DataFrame({
        'raw_factor': raw_factor,
        'market_cap': market_cap,
        'future_return': future_return,
        'timestamp': pd.date_range('2024-01-01', periods=n_samples)
    })
    
    print(f"\n测试数据:")
    print(f"  样本数：{n_samples}")
    print(f"  原始因子与市值相关性：{np.corrcoef(raw_factor, market_cap)[0,1]:.4f}")
    
    # 创建中性化器
    neutralizer = FactorNeutralizer()
    
    # 市值中性化
    print(f"\n进行市值中性化...")
    df['neutralized_factor'] = neutralizer.neutralize_market_cap(
        df['raw_factor'], 
        df['market_cap']
    )
    
    # 检验中性化效果
    neutralized = df['neutralized_factor'].values
    
    print(f"\n中性化效果:")
    print(f"  中性化后因子与市值相关性：{np.corrcoef(neutralized, market_cap)[0,1]:.4f}")
    print(f"  中性化后因子均值：{neutralized.mean():.6f}")
    print(f"  中性化后因子标准差：{neutralized.std():.6f}")
    
    # IC 对比
    from src.ml.factor_analyzer import FactorAnalyzer
    analyzer = FactorAnalyzer()
    
    ic_raw = analyzer.calc_ic(df['raw_factor'], df['future_return'])
    ic_neutralized = analyzer.calc_ic(df['neutralized_factor'], df['future_return'])
    
    print(f"\nIC 对比:")
    print(f"  原始因子 IC: {ic_raw:.4f}")
    print(f"  中性化因子 IC: {ic_neutralized:.4f}")
    
    # 多变量中性化
    print(f"\n进行多变量中性化（市值 +Beta）...")
    beta = np.random.randn(n_samples)
    
    df['neutralized_multi'] = neutralizer.neutralize_multiple(
        df['raw_factor'],
        {
            'size': df['market_cap'],
            'beta': beta
        }
    )
    
    print(f"\n多变量中性化效果:")
    print(f"  与市值相关性：{np.corrcoef(df['neutralized_multi'], market_cap)[0,1]:.4f}")
    print(f"  与 Beta 相关性：{np.corrcoef(df['neutralized_multi'], beta)[0,1]:.4f}")
    
    print(f"\n{'='*70}")
    print("[OK] 因子中性化测试完成")
    print(f"{'='*70}")
    
    return neutralizer, df


if __name__ == "__main__":
    neutralizer, data = test_factor_neutralization()
