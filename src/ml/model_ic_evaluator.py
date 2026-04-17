"""
模型预测 IC 评估器
- IC (Information Coefficient): 预测值与真实值的相关系数
- Rank IC: 排序后的相关系数
- ICIR: IC 除以 IC 标准差（信息比率）
- 分层回测：按预测值分组测试收益
"""
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime


class ModelICEvaluator:
    """模型预测 IC 评估器"""
    
    def __init__(self):
        self.ic_history = []
        self.metrics = {}
    
    def calc_ic(self, y_pred: np.ndarray, y_true: np.ndarray) -> Dict[str, float]:
        """
        计算 IC 指标
        
        Args:
            y_pred: 预测值（概率或分数）
            y_true: 真实值
        
        Returns:
            IC 指标字典
        """
        # Pearson IC
        ic = np.corrcoef(y_pred, y_true)[0, 1]
        
        # Spearman Rank IC
        from scipy.stats import spearmanr
        rank_ic, _ = spearmanr(y_pred, y_true)
        
        # 方向准确率
        pred_direction = (y_pred > 0.5).astype(int) if y_pred.max() <= 1 else (y_pred > 0).astype(int)
        direction_accuracy = (pred_direction == y_true).mean()
        
        return {
            'ic': ic if not np.isnan(ic) else 0,
            'rank_ic': rank_ic if not np.isnan(rank_ic) else 0,
            'direction_accuracy': direction_accuracy,
        }
    
    def calc_ic_time_series(self, y_pred_series: pd.Series, y_true_series: pd.Series,
                           periods: int = 20) -> pd.DataFrame:
        """
        计算滚动 IC 时间序列
        
        Args:
            y_pred_series: 预测值序列（带日期索引）
            y_true_series: 真实值序列（带日期索引）
            periods: 滚动窗口
        
        Returns:
            IC 时间序列 DataFrame
        """
        # 对齐索引
        df = pd.DataFrame({
            'pred': y_pred_series,
            'true': y_true_series
        }).dropna()
        
        # 滚动 IC
        rolling_ic = df['pred'].rolling(periods).corr(df['true'])
        rolling_rank_ic = df['pred'].rank().rolling(periods).corr(df['true'].rank())
        
        ic_df = pd.DataFrame({
            'ic': rolling_ic,
            'rank_ic': rolling_rank_ic,
        })
        
        # 统计信息
        self.metrics = {
            'mean_ic': ic_df['ic'].mean(),
            'std_ic': ic_df['ic'].std(),
            'icir': ic_df['ic'].mean() / ic_df['ic'].std() if ic_df['ic'].std() > 0 else 0,
            'mean_rank_ic': ic_df['rank_ic'].mean(),
            'std_rank_ic': ic_df['rank_ic'].std(),
            'rank_icir': ic_df['rank_ic'].mean() / ic_df['rank_ic'].std() if ic_df['rank_ic'].std() > 0 else 0,
            'ic_t_stat': ic_df['ic'].mean() / ic_df['ic'].std() * np.sqrt(len(ic_df)) if ic_df['ic'].std() > 0 else 0,
        }
        
        return ic_df
    
    def stratified_backtest(self, df: pd.DataFrame, pred_col: str = 'pred',
                           return_col: str = 'return', n_groups: int = 5) -> pd.DataFrame:
        """
        分层回测：按预测值分组测试收益
        
        Args:
            df: 包含预测值和收益的 DataFrame
            pred_col: 预测值列名
            return_col: 收益列名
            n_groups: 分组数
        
        Returns:
            分层回测结果
        """
        # 按预测值分位数分组
        df = df.copy()
        df['group'] = pd.qcut(df[pred_col], q=n_groups, labels=False, duplicates='drop')
        
        # 计算每组平均收益
        group_returns = df.groupby('group')[return_col].agg(['mean', 'std', 'count'])
        group_returns.columns = ['avg_return', 'std_return', 'count']
        
        # 计算多空收益（做多前 20%，做空后 20%）
        long_return = df[df['group'] == n_groups - 1][return_col].mean()
        short_return = df[df['group'] == 0][return_col].mean()
        long_short_return = long_return - short_return
        
        group_returns.loc['long_short'] = {
            'avg_return': long_short_return,
            'std_return': np.nan,
            'count': len(df)
        }
        
        # 累计收益
        cumulative_returns = []
        for group in range(n_groups):
            group_data = df[df['group'] == group]
            cumulative = (1 + group_data[return_col]).cumprod() - 1
            cumulative_returns.append(cumulative.iloc[-1] if len(cumulative) > 0 else 0)
        
        group_returns['cumulative_return'] = cumulative_returns + [np.nan]
        
        print(f"\n{'='*60}")
        print(f"分层回测结果")
        print(f"{'='*60}")
        print(f"\n{'组别':<8} {'平均收益':<12} {'标准差':<12} {'样本数':<10} {'累计收益':<12}")
        print(f"{'-'*60}")
        
        for idx, row in group_returns.iterrows():
            if idx == 'long_short':
                print(f"{str(idx):<8} {row['avg_return']:>10.4%} {'-':<12} {int(row['count']):<10} {'-':<12}")
            else:
                print(f"{int(idx):<8} {row['avg_return']:>10.4%} {row['std_return']:>10.4f} {int(row['count']):<10} {row['cumulative_return']:>10.4%}")
        
        print(f"\n多空收益 (Long-Short): {long_short_return:.4%}")
        print(f"{'='*60}\n")
        
        return group_returns
    
    def evaluate(self, y_pred: np.ndarray, y_true: np.ndarray,
                df_full: pd.DataFrame = None, pred_col: str = 'pred',
                return_col: str = 'return') -> Dict:
        """
        完整 IC 评估
        
        Args:
            y_pred: 预测值
            y_true: 真实值
            df_full: 完整 DataFrame（用于分层回测）
            pred_col: 预测值列名
            return_col: 收益列名
        
        Returns:
            评估结果字典
        """
        results = {}
        
        # 基础 IC
        ic_metrics = self.calc_ic(y_pred, y_true)
        results.update(ic_metrics)
        
        print(f"\n{'='*60}")
        print(f"模型预测 IC 评估")
        print(f"{'='*60}")
        print(f"\n基础指标:")
        print(f"  IC: {ic_metrics['ic']:.4f}")
        print(f"  Rank IC: {ic_metrics['rank_ic']:.4f}")
        print(f"  方向准确率：{ic_metrics['direction_accuracy']:.2%}")
        
        # 分层回测
        if df_full is not None and return_col in df_full.columns:
            stratified = self.stratified_backtest(df_full, pred_col, return_col)
            results['long_short_return'] = stratified.loc['long_short', 'avg_return']
        
        # IC 评估标准
        print(f"\nIC 评估标准:")
        ic_abs = abs(ic_metrics['ic'])
        if ic_abs > 0.1:
            print(f"  [EXCELLENT] 强预测能力 (IC > 0.1)")
        elif ic_abs > 0.05:
            print(f"  [GOOD] 中等预测能力 (IC > 0.05)")
        else:
            print(f"  [WEAK] 弱预测能力 (IC < 0.05)")
        
        print(f"{'='*60}\n")
        
        return results
    
    def report(self) -> str:
        """生成 IC 评估报告"""
        if not self.metrics:
            return "暂无评估数据"
        
        report = f"""
{'='*60}
模型 IC 评估报告
{'='*60}

IC 统计:
  平均 IC: {self.metrics.get('mean_ic', 0):.4f}
  IC 标准差：{self.metrics.get('std_ic', 0):.4f}
  ICIR: {self.metrics.get('icir', 0):.2f}
  
Rank IC 统计:
  平均 Rank IC: {self.metrics.get('mean_rank_ic', 0):.4f}
  Rank IC 标准差：{self.metrics.get('std_rank_ic', 0):.4f}
  Rank ICIR: {self.metrics.get('rank_icir', 0):.2f}

T 统计量：{self.metrics.get('ic_t_stat', 0):.2f}

评估标准:
  ICIR > 0.5: [EXCELLENT] 优秀
  ICIR > 0.2: [GOOD] 可用
  ICIR < 0.2: [NEEDS IMPROVEMENT] 需改进

{'='*60}
"""
        return report


def test_ic_evaluator():
    """测试 IC 评估器"""
    print("\n" + "="*70)
    print("模型 IC 评估器测试")
    print("="*70)
    
    # 生成测试数据
    np.random.seed(42)
    n_samples = 500
    
    # 生成预测值（有一定预测能力）
    y_pred = np.random.randn(n_samples) * 0.5
    
    # 生成真实值（与预测值相关）
    y_true = (y_pred * 0.3 + np.random.randn(n_samples) * 0.7 > 0).astype(int)
    
    # 生成收益
    returns = y_pred * 0.02 + np.random.randn(n_samples) * 0.01
    
    # 创建 DataFrame
    dates = pd.date_range('2024-01-01', periods=n_samples, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'pred': y_pred,
        'true': y_true,
        'return': returns
    }).set_index('date')
    
    print(f"\n数据集:")
    print(f"  样本数：{n_samples}")
    print(f"  日期范围：{dates[0]} 至 {dates[-1]}")
    
    # 评估
    evaluator = ModelICEvaluator()
    results = evaluator.evaluate(
        y_pred=y_pred,
        y_true=y_true,
        df_full=df,
        pred_col='pred',
        return_col='return'
    )
    
    # 滚动 IC
    ic_ts = evaluator.calc_ic_time_series(df['pred'], df['true'], periods=20)
    
    print(evaluator.report())
    
    print(f"\n[OK] 测试完成")
    
    return evaluator, results


if __name__ == "__main__":
    evaluator, results = test_ic_evaluator()
