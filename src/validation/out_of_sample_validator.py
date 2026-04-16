"""
样本外验证框架
防止过拟合的核心方法

[WARN] 重要：这是评估策略真实能力的关键步骤
"""
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class SplitConfig:
    """数据分割配置"""
    train_ratio: float = 0.60      # 训练集 60%
    validation_ratio: float = 0.20  # 验证集 20%
    test_ratio: float = 0.20       # 测试集 20%
    walk_forward_window: int = 252  # 滚动窗口（1 年交易日）
    walk_forward_step: int = 63     # 滚动步长（1 季度）


class OutOfSampleValidator:
    """
    样本外验证器
    
    核心方法：
    1. 训练集/验证集/测试集分割
    2. 滚动回测（Walk Forward）
    3. 参数稳定性检验
    4. 过拟合检测
    """
    
    def __init__(self, config: SplitConfig = None):
        self.config = config or SplitConfig()
        self.results = {}
    
    def split_data(self, 
                   data: pd.DataFrame,
                   method='time_series') -> Dict[str, pd.DataFrame]:
        """
        分割数据
        
        Args:
            data: 完整数据集
            method: 'time_series' (时间序列分割)
        
        Returns:
            训练集/验证集/测试集
        """
        n = len(data)
        
        if method == 'time_series':
            # 时间序列分割（保持时间顺序）
            train_end = int(n * self.config.train_ratio)
            val_end = int(n * (self.config.train_ratio + self.config.validation_ratio))
            
            train_data = data.iloc[:train_end].copy()
            val_data = data.iloc[train_end:val_end].copy()
            test_data = data.iloc[val_end:].copy()
            
            return {
                'train': train_data,
                'validation': val_data,
                'test': test_data
            }
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def walk_forward_analysis(self,
                             data: pd.DataFrame,
                             strategy_func,
                             n_splits: int = 5) -> Dict:
        """
        滚动回测分析（Walk Forward Analysis）
        
        原理：
        1. 用前 N 年数据训练
        2. 用后 1 年数据测试
        3. 滚动窗口，重复 N 次
        4. 检验策略稳定性
        
        Args:
            data: 完整数据集
            strategy_func: 策略回测函数
            n_splits: 分割次数
        
        Returns:
            各期绩效指标
        """
        n = len(data)
        window_size = self.config.walk_forward_window
        step_size = self.config.walk_forward_step
        
        results = []
        
        print(f"\n滚动回测分析")
        print(f"  总样本数：{n}")
        print(f"  训练窗口：{window_size} 天")
        print(f"  测试窗口：{step_size} 天")
        print(f"  滚动次数：{n_splits}")
        
        for i in range(n_splits):
            # 计算窗口
            train_start = i * step_size
            train_end = train_start + window_size
            test_end = train_end + step_size
            
            if test_end > n:
                break
            
            # 分割数据
            train_data = data.iloc[train_start:train_end]
            test_data = data.iloc[train_end:test_end]
            
            # 回测
            try:
                metrics = strategy_func(train_data, test_data)
                metrics['fold'] = i + 1
                metrics['train_period'] = f"{train_start}-{train_end}"
                metrics['test_period'] = f"{train_end}-{test_end}"
                results.append(metrics)
                
                print(f"  Fold {i+1}: 收益率 {metrics.get('total_return', 0):.2f}%")
                
            except Exception as e:
                print(f"  Fold {i+1}: 失败 - {e}")
        
        # 统计分析
        if results:
            df_results = pd.DataFrame(results)
            
            # 计算稳定性指标
            mean_return = df_results['total_return'].mean()
            std_return = df_results['total_return'].std()
            cv = std_return / abs(mean_return) if mean_return != 0 else 999  # 变异系数
            
            print(f"\n稳定性分析:")
            print(f"  平均收益：{mean_return:.2f}%")
            print(f"  收益标准差：{std_return:.2f}%")
            print(f"  变异系数：{cv:.2f} (越小越稳定)")
            
            # 过拟合检测
            if cv > 2.0:
                print(f"  [WARN] 警告：策略稳定性差，可能过拟合")
            elif cv > 1.0:
                print(f"  [WARN] 注意：策略稳定性一般")
            else:
                print(f"  [OK] 策略稳定性良好")
        
        return {
            'folds': results,
            'summary': pd.DataFrame(results) if results else pd.DataFrame()
        }
    
    def parameter_stability_test(self,
                                data: pd.DataFrame,
                                strategy_func,
                                param_grid: Dict[str, List],
                                n_folds: int = 5) -> pd.DataFrame:
        """
        参数稳定性检验
        
        原理：
        1. 多组参数分别回测
        2. 检验最优参数是否稳定
        3. 防止参数过拟合
        
        Args:
            data: 数据集
            strategy_func: 策略函数
            param_grid: 参数网格
            n_folds: 折叠数
        
        Returns:
            各参数组合的表现
        """
        from itertools import product
        
        print(f"\n参数稳定性检验")
        print(f"  参数组合数：{np.prod([len(v) for v in param_grid.values()])}")
        
        results = []
        
        # 生成参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        for combo in product(*param_values):
            params = dict(zip(param_names, combo))
            
            # 滚动回测
            validator = OutOfSampleValidator()
            walk_results = validator.walk_forward_analysis(
                data,
                lambda train, test: strategy_func(train, test, **params),
                n_splits=n_folds
            )
            
            if walk_results['folds']:
                avg_return = np.mean([r['total_return'] for r in walk_results['folds']])
                std_return = np.std([r['total_return'] for r in walk_results['folds']])
                
                results.append({
                    **params,
                    'avg_return': avg_return,
                    'std_return': std_return,
                    'stability': avg_return / (std_return + 1e-8)
                })
        
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('stability', ascending=False)
        
        # 打印 Top 5
        print(f"\nTop 5 参数组合:")
        print(df_results.head(5).to_string())
        
        return df_results
    
    def overfitting_detection(self,
                             in_sample_metrics: Dict,
                             out_of_sample_metrics: Dict) -> Dict:
        """
        过拟合检测
        
        原理：
        1. 对比样本内和样本外表现
        2. 如果差异过大，说明过拟合
        
        Args:
            in_sample_metrics: 样本内绩效
            out_of_sample_metrics: 样本外绩效
        
        Returns:
            过拟合检测结果
        """
        # 计算差异
        return_diff = in_sample_metrics.get('total_return', 0) - out_of_sample_metrics.get('total_return', 0)
        sharpe_diff = in_sample_metrics.get('sharpe', 0) - out_of_sample_metrics.get('sharpe', 0)
        
        # 过拟合评分
        overfit_score = 0
        
        if abs(return_diff) > 10:  # 收益差异>10%
            overfit_score += 2
        elif abs(return_diff) > 5:
            overfit_score += 1
        
        if abs(sharpe_diff) > 1:  # 夏普差异>1
            overfit_score += 2
        elif abs(sharpe_diff) > 0.5:
            overfit_score += 1
        
        # 判断
        if overfit_score >= 3:
            conclusion = "[DANGER] 严重过拟合"
        elif overfit_score >= 2:
            conclusion = "[WARN] 可能过拟合"
        else:
            conclusion = "[OK] 无明显过拟合"
        
        return {
            'return_difference': return_diff,
            'sharpe_difference': sharpe_diff,
            'overfit_score': overfit_score,
            'conclusion': conclusion,
            'in_sample_return': in_sample_metrics.get('total_return', 0),
            'out_of_sample_return': out_of_sample_metrics.get('total_return', 0)
        }


def test_out_of_sample_validator():
    """测试样本外验证框架"""
    print("\n" + "="*70)
    print("样本外验证框架 - 测试")
    print("="*70)
    
    # 生成模拟数据
    np.random.seed(42)
    n = 1000
    
    # 有趋势的价格序列
    returns = np.random.randn(n) * 0.02 + 0.0003
    prices = 100 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'close': prices,
        'timestamp': pd.date_range('2020-01-01', periods=n)
    })
    
    print(f"\n测试数据:")
    print(f"  样本数：{n}")
    print(f"  时间跨度：{df['timestamp'].min()} - {df['timestamp'].max()}")
    
    # 创建验证器
    validator = OutOfSampleValidator(
        SplitConfig(
            train_ratio=0.6,
            validation_ratio=0.2,
            test_ratio=0.2,
            walk_forward_window=252,
            walk_forward_step=63
        )
    )
    
    # 分割数据
    splits = validator.split_data(df)
    
    print(f"\n数据分割:")
    print(f"  训练集：{len(splits['train'])} 天 ({len(splits['train'])/n*100:.1f}%)")
    print(f"  验证集：{len(splits['validation'])} 天 ({len(splits['validation'])/n*100:.1f}%)")
    print(f"  测试集：{len(splits['test'])} 天 ({len(splits['test'])/n*100:.1f}%)")
    
    # 定义简化策略函数
    def simple_strategy(train_data, test_data):
        """简单趋势策略"""
        # 训练集计算均线
        ma = train_data['close'].mean()
        
        # 测试集交易
        test_returns = test_data['close'].pct_change()
        signals = np.where(test_data['close'] > ma, 1, -1)
        
        # 简化收益
        total_return = (signals[:-1] * test_returns.iloc[1:]).sum() * 100
        
        return {
            'total_return': total_return,
            'sharpe': total_return / (test_returns.std() * np.sqrt(252) + 1e-8)
        }
    
    # 滚动回测
    print(f"\n{'='*70}")
    print("滚动回测分析")
    print(f"{'='*70}")
    
    walk_results = validator.walk_forward_analysis(df, simple_strategy, n_splits=5)
    
    # 过拟合检测
    print(f"\n{'='*70}")
    print("过拟合检测")
    print(f"{'='*70}")
    
    in_sample_metrics = {'total_return': 15.0, 'sharpe': 1.5}
    out_of_sample_metrics = {'total_return': 8.0, 'sharpe': 0.8}
    
    detection = validator.overfitting_detection(in_sample_metrics, out_of_sample_metrics)
    
    print(f"  样本内收益：{detection['in_sample_return']:.2f}%")
    print(f"  样本外收益：{detection['out_of_sample_return']:.2f}%")
    print(f"  收益差异：{detection['return_difference']:.2f}%")
    print(f"  过拟合评分：{detection['overfit_score']}")
    print(f"  结论：{detection['conclusion']}")
    
    print(f"\n{'='*70}")
    print("[OK] 样本外验证框架测试完成")
    print(f"{'='*70}")
    
    return validator, walk_results, detection


if __name__ == "__main__":
    validator, results, detection = test_out_of_sample_validator()
