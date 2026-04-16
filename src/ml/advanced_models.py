"""
高级 ML 模型集成
XGBoost / LightGBM / CatBoost
"""
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np


class AdvancedMLModels:
    """高级 ML 模型集合"""
    
    def __init__(self):
        self.model = None
        self.model_type = None
        self.feature_importance = None
    
    def create_xgboost(self, **params) -> Any:
        """
        创建 XGBoost 模型
        
        Args:
            **params: XGBoost 参数
                - n_estimators: 树的数量
                - max_depth: 树的最大深度
                - learning_rate: 学习率
                - subsample: 样本采样比例
                - colsample_bytree: 特征采样比例
                - reg_alpha: L1 正则化
                - reg_lambda: L2 正则化
        """
        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError("请安装 XGBoost: pip install xgboost")
        
        default_params = {
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42,
            'n_jobs': -1,
        }
        
        # 合并参数
        final_params = {**default_params, **params}
        
        self.model = xgb.XGBClassifier(**final_params)
        self.model_type = 'xgboost'
        
        return self.model
    
    def create_lightgbm(self, **params) -> Any:
        """
        创建 LightGBM 模型
        
        Args:
            **params: LightGBM 参数
                - n_estimators: 树的数量
                - max_depth: 树的最大深度
                - learning_rate: 学习率
                - num_leaves: 叶子节点数
                - subsample: 样本采样比例
                - colsample_bytree: 特征采样比例
                - reg_alpha: L1 正则化
                - reg_lambda: L2 正则化
        """
        try:
            import lightgbm as lgb
        except ImportError:
            raise ImportError("请安装 LightGBM: pip install lightgbm")
        
        default_params = {
            'n_estimators': 100,
            'max_depth': -1,
            'learning_rate': 0.1,
            'num_leaves': 31,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42,
            'n_jobs': -1,
            'verbose': -1,
        }
        
        final_params = {**default_params, **params}
        
        self.model = lgb.LGBMClassifier(**final_params)
        self.model_type = 'lightgbm'
        
        return self.model
    
    def create_catboost(self, **params) -> Any:
        """
        创建 CatBoost 模型
        
        Args:
            **params: CatBoost 参数
                - iterations: 迭代次数
                - depth: 树深度
                - learning_rate: 学习率
                - l2_leaf_reg: L2 正则化
                - random_strength: 随机强度
        """
        try:
            import catboost as cb
        except ImportError:
            raise ImportError("请安装 CatBoost: pip install catboost")
        
        default_params = {
            'iterations': 100,
            'depth': 6,
            'learning_rate': 0.1,
            'l2_leaf_reg': 1.0,
            'random_strength': 1.0,
            'random_state': 42,
            'verbose': 0,
        }
        
        final_params = {**default_params, **params}
        
        self.model = cb.CatBoostClassifier(**final_params)
        self.model_type = 'catboost'
        
        return self.model
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: pd.DataFrame = None, y_val: pd.Series = None,
              **fit_params) -> Dict[str, float]:
        """
        训练模型
        
        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_val: 验证特征（可选）
            y_val: 验证标签（可选）
            **fit_params: 训练参数（如 eval_set, early_stopping_rounds 等）
        
        Returns:
            评估指标字典
        """
        if self.model is None:
            raise ValueError("请先创建模型 (create_xgboost/create_lightgbm/create_catboost)")
        
        # 训练
        if X_val is not None and y_val is not None:
            self.model.fit(X_train, y_train, eval_set=[(X_val, y_val)], **fit_params)
        else:
            self.model.fit(X_train, y_train, **fit_params)
        
        # 评估
        metrics = {}
        
        # 训练集表现
        y_pred_train = self.model.predict(X_train)
        y_proba_train = self.model.predict_proba(X_train)[:, 1] if hasattr(self.model, 'predict_proba') else None
        
        metrics.update(self._calc_metrics(y_train, y_pred_train, y_proba_train, prefix='train'))
        
        # 验证集表现
        if X_val is not None:
            y_pred_val = self.model.predict(X_val)
            y_proba_val = self.model.predict_proba(X_val)[:, 1] if hasattr(self.model, 'predict_proba') else None
            
            metrics.update(self._calc_metrics(y_val, y_pred_val, y_proba_val, prefix='val'))
        
        # 特征重要性
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = pd.DataFrame({
                'feature': X_train.columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
        
        return metrics
    
    def _calc_metrics(self, y_true, y_pred, y_proba=None, prefix=''):
        """计算评估指标"""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        metrics = {
            f'{prefix}_accuracy': accuracy_score(y_true, y_pred),
            f'{prefix}_precision': precision_score(y_true, y_pred, average='weighted', zero_division=0),
            f'{prefix}_recall': recall_score(y_true, y_pred, average='weighted', zero_division=0),
            f'{prefix}_f1': f1_score(y_true, y_pred, average='weighted', zero_division=0),
        }
        
        if y_proba is not None and len(np.unique(y_true)) == 2:
            try:
                metrics[f'{prefix}_auc'] = roc_auc_score(y_true, y_proba)
            except:
                metrics[f'{prefix}_auc'] = 0.5
        
        return metrics
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """预测"""
        if self.model is None:
            raise ValueError("模型未训练")
        return self.model.predict(X)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """预测概率"""
        if self.model is None:
            raise ValueError("模型未训练")
        if not hasattr(self.model, 'predict_proba'):
            raise ValueError("模型不支持概率预测")
        return self.model.predict_proba(X)
    
    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """获取特征重要性"""
        if self.feature_importance is None:
            raise ValueError("请先训练模型")
        return self.feature_importance.head(top_n)
    
    def save_model(self, filepath: str):
        """保存模型"""
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'model_type': self.model_type,
                'feature_importance': self.feature_importance,
            }, f)
    
    def load_model(self, filepath: str):
        """加载模型"""
        import pickle
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.model_type = data['model_type']
            self.feature_importance = data['feature_importance']


def compare_models(X_train, y_train, X_test, y_test):
    """
    对比不同模型的表现
    
    Returns:
        包含各模型表现的 DataFrame
    """
    print("\n" + "="*70)
    print("模型对比实验")
    print("="*70)
    
    results = []
    
    # 1. XGBoost
    print("\n[1/3] 训练 XGBoost...")
    adv = AdvancedMLModels()
    adv.create_xgboost(n_estimators=100, max_depth=5, learning_rate=0.1)
    metrics_xgb = adv.train(X_train, y_train, X_test, y_test, early_stopping_rounds=10, verbose=False)
    metrics_xgb['model'] = 'XGBoost'
    results.append(metrics_xgb)
    print(f"  验证集 AUC: {metrics_xgb.get('val_auc', 0):.4f}")
    
    # 2. LightGBM
    print("\n[2/3] 训练 LightGBM...")
    adv = AdvancedMLModels()
    adv.create_lightgbm(n_estimators=100, max_depth=-1, learning_rate=0.1, num_leaves=31)
    metrics_lgb = adv.train(X_train, y_train, X_test, y_test, early_stopping_rounds=10, verbose=False)
    metrics_lgb['model'] = 'LightGBM'
    results.append(metrics_lgb)
    print(f"  验证集 AUC: {metrics_lgb.get('val_auc', 0):.4f}")
    
    # 3. CatBoost
    print("\n[3/3] 训练 CatBoost...")
    adv = AdvancedMLModels()
    adv.create_catboost(iterations=100, depth=6, learning_rate=0.1)
    metrics_cb = adv.train(X_train, y_train, X_test, y_test, verbose=False)
    metrics_cb['model'] = 'CatBoost'
    results.append(metrics_cb)
    print(f"  验证集 AUC: {metrics_cb.get('val_auc', 0):.4f}")
    
    # 对比结果
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('val_auc', ascending=False)
    
    print(f"\n{'='*70}")
    print("模型对比结果")
    print(f"{'='*70}")
    print(f"{'模型':<12} {'训练 AUC':<12} {'验证 AUC':<12} {'训练准确率':<12} {'验证准确率':<12}")
    print(f"{'-'*70}")
    
    for _, row in df_results.iterrows():
        print(f"{row['model']:<12} {row.get('train_auc',0):>10.4f} {row.get('val_auc',0):>10.4f} "
              f"{row.get('train_accuracy',0):>10.4f} {row.get('val_accuracy',0):>10.4f}")
    
    best_model = df_results.iloc[0]['model']
    print(f"\n最佳模型：{best_model}")
    
    return df_results


def test_advanced_models():
    """测试高级模型"""
    print("\n" + "="*70)
    print("高级 ML 模型测试")
    print("="*70)
    
    # 生成测试数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 20
    
    X = pd.DataFrame(np.random.randn(n_samples, n_features),
                     columns=[f'feature_{i}' for i in range(n_features)])
    
    # 创建标签（与部分特征相关）
    y = (X['feature_0'] + X['feature_1'] * 2 + np.random.randn(n_samples) * 0.5 > 0).astype(int)
    
    # 划分训练测试集
    split_idx = int(n_samples * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"\n数据集:")
    print(f"  训练集：{len(X_train)} 样本")
    print(f"  测试集：{len(X_test)} 样本")
    print(f"  特征数：{n_features}")
    print(f"  正样本比例：{y_train.mean()*100:.1f}%")
    
    # 模型对比
    df_results = compare_models(X_train, y_train, X_test, y_test)
    
    # 特征重要性分析
    print(f"\n{'='*70}")
    print("特征重要性分析 (XGBoost)")
    print(f"{'='*70}")
    
    adv = AdvancedMLModels()
    adv.create_xgboost(n_estimators=100, max_depth=5)
    adv.train(X_train, y_train, verbose=False)
    
    importance = adv.get_feature_importance(top_n=10)
    
    print(f"\n{'特征':<15} {'重要性':<10}")
    print(f"{'-'*30}")
    for _, row in importance.iterrows():
        print(f"{row['feature']:<15} {row['importance']:.4f}")
    
    print(f"\n{'='*70}")
    print("[OK] 测试完成")
    print(f"{'='*70}")
    
    return df_results, importance


if __name__ == "__main__":
    results, importance = test_advanced_models()
