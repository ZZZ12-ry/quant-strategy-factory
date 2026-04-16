"""
AI 模型训练框架 - 完整的机器学习流程
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

from src.ml.feature_library import FeatureLibrary
from src.ml.model_trainer import ModelTrainer


class AIModelTrainer:
    """AI 模型训练器 - 端到端训练流程"""
    
    def __init__(
        self,
        task_type: str = "binary",
        horizon: int = 5,
        threshold: float = 0.02
    ):
        """
        初始化 AI 训练器
        
        Args:
            task_type: 任务类型 (binary/multiclass/regression)
            horizon: 预测未来 N 天
            threshold: 涨跌幅阈值
        """
        self.task_type = task_type
        self.horizon = horizon
        self.threshold = threshold
        
        self.feature_lib = FeatureLibrary()
        self.trainer = None
        self.model = None
        self.feature_names = []
        self.metrics = {}
        self.best_model_type = None
    
    def prepare_data(
        self,
        data: pd.DataFrame,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """
        准备训练数据
        
        Args:
            data: OHLCV 数据
            train_ratio: 训练集比例
            val_ratio: 验证集比例
        
        Returns:
            X_train, y_train, X_test, y_test
        """
        print("\n[1/5] 准备数据...")
        
        # 计算特征
        print("  计算特征...")
        df_features = self.feature_lib.calculate_all(data)
        feature_names = self.feature_lib.get_feature_names()
        
        # 创建标签
        print("  创建标签...")
        labels = self._create_labels(df_features)
        
        # 对齐
        common_idx = df_features.index.intersection(labels.dropna().index)
        X = df_features.loc[common_idx, feature_names]
        y = labels.loc[common_idx]
        
        # 时间序列划分（不能随机划分！）
        train_size = int(len(X) * train_ratio)
        val_size = int(len(X) * val_ratio)
        
        X_train = X.iloc[:train_size]
        y_train = y.iloc[:train_size]
        X_val = X.iloc[train_size:train_size + val_size]
        y_val = y.iloc[train_size:train_size + val_size]
        X_test = X.iloc[train_size + val_size:]
        y_test = y.iloc[train_size + val_size:]
        
        self.feature_names = feature_names
        
        print(f"  总样本数：{len(X)}")
        print(f"  训练集：{len(X_train)} ({len(X_train)/len(X)*100:.1f}%)")
        print(f"  验证集：{len(X_val)} ({len(X_val)/len(X)*100:.1f}%)")
        print(f"  测试集：{len(X_test)} ({len(X_test)/len(X)*100:.1f}%)")
        
        # 类别分布
        if self.task_type != "regression":
            print(f"  正样本比例 (训练集): {y_train.mean():.2%}")
            print(f"  正样本比例 (测试集): {y_test.mean():.2%}")
        
        return X_train, y_train, X_test, y_test
    
    def _create_labels(self, df: pd.DataFrame) -> pd.Series:
        """创建预测标签"""
        future_return = df['close'].shift(-self.horizon) / df['close'] - 1
        
        if self.task_type == "binary":
            # 二分类：涨/跌
            labels = (future_return > 0).astype(int)
        
        elif self.task_type == "multiclass":
            # 三分类：涨/震荡/跌
            labels = pd.Series(0, index=df.index)  # 默认震荡
            labels[future_return > self.threshold] = 1  # 涨
            labels[future_return < -self.threshold] = -1  # 跌
        
        elif self.task_type == "regression":
            # 回归：直接预测收益率
            labels = future_return
        
        return labels
    
    def train_models(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        训练多个模型并对比
        
        Args:
            X_train, y_train: 训练数据
            X_test, y_test: 测试数据
            model_types: 要训练的模型类型列表
        
        Returns:
            训练结果字典
        """
        print("\n[2/5] 训练模型...")
        
        if model_types is None:
            model_types = ['random_forest', 'xgboost', 'lightgbm']
        
        model_params = {
            'random_forest': {'n_estimators': 100, 'max_depth': 5, 'random_state': 42},
            'xgboost': {'n_estimators': 100, 'max_depth': 5, 'random_state': 42, 'use_label_encoder': False},
            'lightgbm': {'n_estimators': 100, 'max_depth': 5, 'random_state': 42},
            'gradient_boosting': {'n_estimators': 100, 'max_depth': 5, 'random_state': 42},
            'decision_tree': {'max_depth': 5, 'random_state': 42},
        }
        
        results = []
        trained_models = {}
        
        for model_type in model_types:
            print(f"\n  训练 {model_type}...")
            
            try:
                trainer = ModelTrainer(task_type=self.task_type)
                params = model_params.get(model_type, {})
                
                metrics = trainer.train(
                    X_train=X_train, y_train=y_train,
                    X_test=X_test, y_test=y_test,
                    model_type=model_type,
                    **params
                )
                
                results.append({
                    'model_type': model_type,
                    'metrics': metrics,
                    'trainer': trainer
                })
                
                trained_models[model_type] = trainer
                
                # 打印结果
                if self.task_type == "regression":
                    print(f"    Train RMSE: {metrics.get('train_rmse', 0):.6f}")
                    print(f"    Test RMSE: {metrics.get('test_rmse', 0):.6f}")
                    print(f"    Train R²: {metrics.get('train_r2', 0):.4f}")
                    print(f"    Test R²: {metrics.get('test_r2', 0):.4f}")
                else:
                    print(f"    Train Accuracy: {metrics.get('train_accuracy', 0):.4f}")
                    print(f"    Test Accuracy: {metrics.get('test_accuracy', 0):.4f}")
                    if 'test_auc' in metrics:
                        print(f"    Test AUC: {metrics.get('test_auc', 0):.4f}")
            
            except Exception as e:
                print(f"    ❌ {model_type} 训练失败：{e}")
                continue
        
        # 选择最佳模型
        if results:
            if self.task_type == "regression":
                best = min(results, key=lambda x: x['metrics'].get('test_rmse', 999))
            else:
                best = max(results, key=lambda x: x['metrics'].get('test_accuracy', 0))
            
            self.best_model_type = best['model_type']
            self.trainer = best['trainer']
            self.model = best['trainer'].model
            self.metrics = best['metrics']
            
            print(f"\n  ✅ 最佳模型：{self.best_model_type}")
            if self.task_type == "regression":
                print(f"     Test RMSE: {self.metrics.get('test_rmse', 0):.6f}")
                print(f"     Test R²: {self.metrics.get('test_r2', 0):.4f}")
            else:
                print(f"     Test Accuracy: {self.metrics.get('test_accuracy', 0):.4f}")
        
        self.results = results
        return {
            'best_model': self.best_model_type,
            'all_results': results,
            'trained_models': trained_models
        }
    
    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """获取特征重要性"""
        if self.trainer is None:
            raise ValueError("请先训练模型")
        
        importance = self.trainer.get_feature_importance(top_n=top_n)
        return importance
    
    def save_model(self, filepath: str = "./models/ai_model.pkl"):
        """保存模型"""
        import os
        import pickle
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names,
                'task_type': self.task_type,
                'metrics': self.metrics,
                'best_model_type': self.best_model_type
            }, f)
        
        print(f"✅ 模型已保存：{filepath}")
    
    def load_model(self, filepath: str = "./models/ai_model.pkl"):
        """加载模型"""
        import pickle
        
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.feature_names = data['feature_names']
            self.task_type = data['task_type']
            self.metrics = data['metrics']
            self.best_model_type = data['best_model_type']
        
        print(f"✅ 模型已加载：{filepath}")


def train_ai_model(data: pd.DataFrame, task_type: str = "binary"):
    """
    一键训练 AI 模型
    
    Args:
        data: OHLCV 数据
        task_type: 任务类型
    
    Returns:
        AIModelTrainer 实例
    """
    print("=" * 60)
    print("AI 模型训练")
    print("=" * 60)
    
    # 创建训练器
    trainer = AIModelTrainer(task_type=task_type)
    
    # 准备数据
    X_train, y_train, X_test, y_test = trainer.prepare_data(data)
    
    # 训练模型
    trainer.train_models(X_train, y_train, X_test, y_test)
    
    # 特征重要性
    print("\n[3/5] 特征重要性分析...")
    importance = trainer.get_feature_importance(top_n=15)
    print("\n  Top 15 重要特征:")
    for idx, row in importance.iterrows():
        print(f"    {row['feature']:25s} {row['importance']:.4f}")
    
    # 保存模型
    print("\n[4/5] 保存模型...")
    trainer.save_model()
    
    print("\n" + "=" * 60)
    print("AI 模型训练完成")
    print("=" * 60)
    
    return trainer


if __name__ == "__main__":
    # 测试
    from src.data.data_fetcher import DataFetcher
    
    print("加载数据...")
    fetcher = DataFetcher(source="akshare")
    data = fetcher.fetch_stock_data("000001", "20220101", "20231231")
    
    if len(data) > 0:
        print(f"数据量：{len(data)}")
        trainer = train_ai_model(data, task_type="binary")
    else:
        print("❌ 数据获取失败")
