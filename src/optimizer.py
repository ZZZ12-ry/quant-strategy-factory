"""
参数优化器 - 网格搜索和贝叶斯优化
"""
from typing import Dict, Any, List, Tuple, Optional, Callable
import pandas as pd
import numpy as np
from itertools import product
from tqdm import tqdm
from datetime import datetime


class Optimizer:
    """参数优化器"""
    
    def __init__(
        self,
        strategy_class,
        backtest_func: Callable = None,
        metric: str = "sharpe_ratio"
    ):
        """
        初始化优化器
        
        Args:
            strategy_class: 策略类
            backtest_func: 回测函数
            metric: 优化目标 (sharpe_ratio/total_return/max_drawdown)
        """
        self.strategy_class = strategy_class
        self.backtest_func = backtest_func
        self.metric = metric
        self.results = []
    
    def grid_search(
        self,
        param_grid: Dict[str, List],
        data: pd.DataFrame,
        symbol: str,
        n_jobs: int = 1
    ) -> Tuple[Dict[str, Any], Dict]:
        """
        网格搜索
        
        Args:
            param_grid: 参数网格 {"param_name": [values]}
            data: 回测数据
            symbol: 品种代码
            n_jobs: 并行数
        
        Returns:
            (best_params, best_result)
        """
        # 生成参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        all_combinations = list(product(*param_values))
        
        print(f"Grid search: {len(all_combinations)} combinations")
        
        best_params = None
        best_score = -np.inf
        best_result = None
        
        self.results = []
        
        for params in tqdm(all_combinations, desc="Grid Search"):
            param_dict = dict(zip(param_names, params))
            
            try:
                # 创建策略实例
                strategy = self.strategy_class(**param_dict)
                
                # 运行回测
                if self.backtest_func:
                    result = self.backtest_func(strategy, data, symbol)
                else:
                    from src.backtest_engine import BacktestEngine
                    engine = BacktestEngine(strategy)
                    result = engine.run(data, symbol)
                
                # 获取目标指标
                score = self._get_metric_value(result)
                
                self.results.append({
                    'params': param_dict,
                    'score': score,
                    'result': result
                })
                
                if score > best_score:
                    best_score = score
                    best_params = param_dict
                    best_result = result
            
            except Exception as e:
                print(f"Error with params {param_dict}: {e}")
                continue
        
        print(f"\nBest params: {best_params}")
        print(f"Best {self.metric}: {best_score:.4f}")
        
        return best_params, best_result
    
    def bayesian_optimize(
        self,
        param_bounds: Dict[str, Tuple],
        data: pd.DataFrame,
        symbol: str,
        n_iterations: int = 50,
        n_init: int = 10
    ) -> Tuple[Dict[str, Any], Dict]:
        """
        贝叶斯优化（使用 Optuna）
        
        Args:
            param_bounds: 参数边界 {"param_name": (min, max)}
            data: 回测数据
            symbol: 品种代码
            n_iterations: 迭代次数
            n_init: 初始随机搜索次数
        
        Returns:
            (best_params, best_result)
        """
        try:
            import optuna
        except ImportError:
            raise ImportError("Please install optuna: pip install optuna")
        
        def objective(trial):
            # 建议参数
            params = {}
            for param_name, (low, high) in param_bounds.items():
                if isinstance(low, int):
                    params[param_name] = trial.suggest_int(param_name, low, high)
                else:
                    params[param_name] = trial.suggest_float(param_name, low, high)
            
            try:
                # 创建策略实例
                strategy = self.strategy_class(**params)
                
                # 运行回测
                if self.backtest_func:
                    result = self.backtest_func(strategy, data, symbol)
                else:
                    from src.backtest_engine import BacktestEngine
                    engine = BacktestEngine(strategy)
                    result = engine.run(data, symbol)
                
                # 获取目标指标
                score = self._get_metric_value(result)
                
                self.results.append({
                    'params': params,
                    'score': score,
                    'result': result
                })
                
                return score
            
            except Exception as e:
                print(f"Error with params {params}: {e}")
                return -np.inf
        
        # 创建研究
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_iterations, show_progress_bar=True)
        
        best_params = study.best_params
        best_score = study.best_value
        
        print(f"\nBest params: {best_params}")
        print(f"Best {self.metric}: {best_score:.4f}")
        
        # 获取最佳结果
        best_result = None
        for r in self.results:
            if r['params'] == best_params:
                best_result = r['result']
                break
        
        return best_params, best_result
    
    def _get_metric_value(self, result) -> float:
        """获取指标值"""
        if self.metric == "sharpe_ratio":
            return result.sharpe_ratio
        elif self.metric == "total_return":
            return result.total_return
        elif self.metric == "max_drawdown":
            return -result.max_drawdown  # 越小越好
        elif self.metric == "calmar_ratio":
            if result.max_drawdown != 0:
                return result.annualized_return / abs(result.max_drawdown)
            return 0
        else:
            return result.sharpe_ratio
    
    def get_results_summary(self) -> pd.DataFrame:
        """获取结果汇总"""
        if not self.results:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.results)
        
        # 展开参数字典
        if 'params' in df.columns:
            params_df = pd.DataFrame(df['params'].tolist())
            df = pd.concat([params_df, df.drop('params', axis=1)], axis=1)
        
        # 排序
        df = df.sort_values('score', ascending=False)
        
        return df
    
    def plot_results(self, x_param: str, y_param: str = None):
        """绘制优化结果"""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("Please install matplotlib")
        
        df = self.get_results_summary()
        
        if len(df) == 0:
            print("No results to plot")
            return
        
        if y_param is None:
            # 单参数图
            if x_param not in df.columns:
                print(f"Parameter {x_param} not found")
                return
            
            plt.figure(figsize=(10, 6))
            plt.scatter(df[x_param], df['score'], alpha=0.6)
            plt.xlabel(x_param)
            plt.ylabel(self.metric)
            plt.title(f"Parameter Optimization: {x_param} vs {self.metric}")
            plt.grid(True, alpha=0.3)
            plt.show()
        else:
            # 双参数热力图
            if x_param not in df.columns or y_param not in df.columns:
                print(f"Parameters not found")
                return
            
            pivot = df.pivot_table(values='score', index=x_param, columns=y_param, aggfunc='mean')
            
            plt.figure(figsize=(10, 8))
            plt.imshow(pivot.values, cmap='viridis', aspect='auto')
            plt.colorbar(label=self.metric)
            plt.xlabel(y_param)
            plt.ylabel(x_param)
            plt.title(f"Parameter Optimization Heatmap")
            plt.xticks(range(len(pivot.columns)), pivot.columns, rotation=45)
            plt.yticks(range(len(pivot.index)), pivot.index)
            plt.tight_layout()
            plt.show()
