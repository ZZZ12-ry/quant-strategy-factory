"""
模型训练器 - 支持多种 ML 模型
参考：Qlib RD-Agent 自动化建模
"""
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


class ModelTrainer:
    """模型训练器"""
    
    def __init__(self, task_type: str = "binary"):
        """
        初始化训练器
        
        Args:
            task_type: 任务类型 (binary/multiclass/regression)
        """
        self.task_type = task_type
        self.model = None
        self.feature_names = []
        self.metrics = {}
    
    def create_model(self, model_type: str = "random_forest", **params) -> Any:
        """
        创建模型
        
        Args:
            model_type: 模型类型
            **params: 模型参数
        
        Returns:
            模型实例
        """
        try:
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
            from sklearn.linear_model import LogisticRegression, LinearRegression
            from sklearn.svm import SVC, SVR
            from sklearn.neural_network import MLPClassifier, MLPRegressor
            from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
        except ImportError:
            raise ImportError("Please install scikit-learn: pip install scikit-learn")
        
        model_map = {
            "random_forest": (RandomForestClassifier if self.task_type != "regression" 
                             else RandomForestRegressor),
            "gradient_boosting": (GradientBoostingClassifier if self.task_type != "regression" 
                                  else lambda **p: None),  # GBRT needs separate import
            "logistic_regression": LogisticRegression,
            "linear_regression": LinearRegression,
            "svm": (SVC if self.task_type != "regression" else SVR),
            "mlp": (MLPClassifier if self.task_type != "regression" else MLPRegressor),
            "decision_tree": (DecisionTreeClassifier if self.task_type != "regression" 
                             else DecisionTreeRegressor),
        }
        
        if model_type not in model_map:
            raise ValueError(f"Unknown model type: {model_type}")
        
        model_class = model_map[model_type]
        
        # 默认参数
        default_params = {
            "random_forest": {"n_estimators": 100, "max_depth": 5, "random_state": 42},
            "gradient_boosting": {"n_estimators": 100, "max_depth": 3, "random_state": 42},
            "logistic_regression": {"max_iter=1000": 1000, "random_state": 42},
            "linear_regression": {},
            "svm": {"kernel": "rbf", "random_state": 42},
            "mlp": {"hidden_layer_sizes": (100,), "max_iter": 500, "random_state": 42},
            "decision_tree": {"max_depth": 5, "random_state": 42},
        }
        
        merged_params = {**default_params.get(model_type, {}), **params}
        
        self.model = model_class(**merged_params)
        return self.model
    
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame = None,
        y_test: pd.Series = None,
        model_type: str = "random_forest",
        **model_params
    ) -> Dict[str, float]:
        """
        训练模型
        
        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_test: 测试特征（可选）
            y_test: 测试标签（可选）
            model_type: 模型类型
            **model_params: 模型参数
        
        Returns:
            评估指标
        """
        # 创建模型
        self.create_model(model_type, **model_params)
        
        # 存储特征名称
        self.feature_names = X_train.columns.tolist()
        
        # 训练
        self.model.fit(X_train, y_train)
        
        # 评估
        metrics = {}
        
        # 训练集表现
        y_pred_train = self.model.predict(X_train)
        metrics.update(self._calculate_metrics(y_train, y_pred_train, prefix="train"))
        
        # 测试集表现
        if X_test is not None and y_test is not None:
            y_pred_test = self.model.predict(X_test)
            metrics.update(self._calculate_metrics(y_test, y_pred_test, prefix="test"))
        
        self.metrics = metrics
        
        return metrics
    
    def _calculate_metrics(self, y_true, y_pred, prefix: str = "") -> Dict[str, float]:
        """计算评估指标"""
        try:
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, mean_squared_error, r2_score
        except ImportError:
            raise ImportError("Please install scikit-learn")
        
        metrics = {}
        
        if self.task_type == "regression":
            metrics[f'{prefix}_mse'] = mean_squared_error(y_true, y_pred)
            metrics[f'{prefix}_rmse'] = np.sqrt(metrics[f'{prefix}_mse'])
            metrics[f'{prefix}_r2'] = r2_score(y_true, y_pred)
        else:
            metrics[f'{prefix}_accuracy'] = accuracy_score(y_true, y_pred)
            metrics[f'{prefix}_precision'] = precision_score(y_true, y_pred, average='weighted', zero_division=0)
            metrics[f'{prefix}_recall'] = recall_score(y_true, y_pred, average='weighted', zero_division=0)
            metrics[f'{prefix}_f1'] = f1_score(y_true, y_pred, average='weighted', zero_division=0)
            
            if len(np.unique(y_true)) == 2:
                try:
                    metrics[f'{prefix}_auc'] = roc_auc_score(y_true, y_pred)
                except:
                    metrics[f'{prefix}_auc'] = 0.5
        
        return metrics
    
    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """获取因子重要性"""
        if self.model is None:
            raise ValueError("Model not trained")
        
        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': importance
            }).sort_values('importance', ascending=False)
            
            return importance_df.head(top_n)
        else:
            return pd.DataFrame()
    
    def save_model(self, filepath: str):
        """保存模型"""
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names,
                'task_type': self.task_type,
                'metrics': self.metrics
            }, f)
    
    def load_model(self, filepath: str):
        """加载模型"""
        import pickle
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.feature_names = data['feature_names']
            self.task_type = data['task_type']
            self.metrics = data['metrics']
