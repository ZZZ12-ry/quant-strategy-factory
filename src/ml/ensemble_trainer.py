"""
集成学习训练器 - Stacking / Blending / Voting
参考：Kaggle 集成学习最佳实践
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


class EnsembleTrainer:
    """集成学习训练器 - 支持 Stacking/Blending/Voting"""
    
    def __init__(self, task_type: str = "binary"):
        """
        初始化集成训练器
        
        Args:
            task_type: 任务类型 (binary/multiclass/regression)
        """
        self.task_type = task_type
        self.base_models = {}
        self.meta_model = None
        self.oof_predictions = {}
        self.test_predictions = {}
        self.model_weights = {}
    
    def add_base_model(
        self,
        name: str,
        model: Any,
        model_type: str = "sklearn"
    ):
        """
        添加基模型
        
        Args:
            name: 模型名称
            model: 模型实例
            model_type: 模型类型 (sklearn/xgboost/lightgbm/pytorch)
        """
        self.base_models[name] = {
            'model': model,
            'type': model_type,
            'oof': None,
            'test_pred': None
        }
    
    def train_stacking(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame = None,
        y_val: pd.Series = None,
        n_folds: int = 5,
        meta_model_type: str = "logistic_regression",
        save_oof: bool = True
    ) -> Dict[str, float]:
        """
        Stacking 集成训练
        
        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_val: 验证特征（可选）
            y_val: 验证标签（可选）
            n_folds: 折数
            meta_model_type: 元模型类型
            save_oof: 保存 OOF 预测
        
        Returns:
            评估指标
        """
        try:
            from sklearn.model_selection import KFold, StratifiedKFold
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import accuracy_score, roc_auc_score
        except ImportError:
            raise ImportError("Please install scikit-learn")
        
        print(f"📚 开始 Stacking 训练 - 基模型:{len(self.base_models)}, 折数:{n_folds}")
        
        n_samples = len(X_train)
        
        # 创建 K 折交叉验证
        if self.task_type == "regression":
            kfold = KFold(n_splits=n_folds, shuffle=True, random_state=42)
        else:
            kfold = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
        
        # 存储 OOF 预测
        oof_predictions = np.zeros((n_samples, len(self.base_models)))
        
        if X_val is not None:
            test_predictions = np.zeros((len(X_val), len(self.base_models)))
        else:
            test_predictions = None
        
        # 训练每个基模型
        for model_idx, (model_name, model_info) in enumerate(self.base_models.items()):
            print(f"  训练基模型 {model_idx + 1}/{len(self.base_models)}: {model_name}")
            
            model = model_info['model']
            model_oof = np.zeros(n_samples)
            model_test = np.zeros(len(X_val)) if X_val is not None else None
            
            # K 折训练
            for fold_idx, (train_idx, val_idx) in enumerate(kfold.split(X_train, y_train)):
                X_tr, X_val_fold = X_train.iloc[train_idx], X_train.iloc[val_idx]
                y_tr, y_val_fold = y_train.iloc[train_idx], y_train.iloc[val_idx]
                
                # 训练
                model.fit(X_tr, y_tr)
                
                # 验证集预测
                if hasattr(model, 'predict_proba'):
                    model_oof[val_idx] = model.predict_proba(X_val_fold)[:, 1]
                else:
                    model_oof[val_idx] = model.predict(X_val_fold)
                
                # 测试集预测
                if X_val is not None:
                    if hasattr(model, 'predict_proba'):
                        model_test += model.predict_proba(X_val)[:, 1] / n_folds
                    else:
                        model_test += model.predict(X_val) / n_folds
            
            # 保存预测
            oof_predictions[:, model_idx] = model_oof
            self.base_models[model_name]['oof'] = model_oof
            
            if test_predictions is not None:
                test_predictions[:, model_idx] = model_test
                self.base_models[model_name]['test_pred'] = model_test
            
            # 评估单模型
            if self.task_type != "regression":
                try:
                    auc = roc_auc_score(y_train, model_oof)
                    print(f"    {model_name} OOF AUC: {auc:.4f}")
                except:
                    pass
        
        # 训练元模型
        print(f"  训练元模型: {meta_model_type}")
        
        meta_model = self._create_meta_model(meta_model_type)
        meta_model.fit(oof_predictions, y_train)
        self.meta_model = meta_model
        
        # 评估
        meta_pred_train = meta_model.predict(oof_predictions)
        
        metrics = {}
        
        if self.task_type == "regression":
            from sklearn.metrics import mean_squared_error, r2_score
            metrics['train_mse'] = mean_squared_error(y_train, meta_pred_train)
            metrics['train_rmse'] = np.sqrt(metrics['train_mse'])
            metrics['train_r2'] = r2_score(y_train, meta_pred_train)
        else:
            metrics['train_accuracy'] = accuracy_score(y_train, meta_pred_train)
            try:
                meta_pred_proba = meta_model.predict_proba(oof_predictions)[:, 1]
                metrics['train_auc'] = roc_auc_score(y_train, meta_pred_proba)
            except:
                metrics['train_auc'] = 0.5
        
        # 验证集评估
        if X_val is not None and y_val is not None:
            test_meta_features = test_predictions
            meta_pred_val = meta_model.predict(test_meta_features)
            
            if self.task_type == "regression":
                metrics['val_mse'] = mean_squared_error(y_val, meta_pred_val)
                metrics['val_rmse'] = np.sqrt(metrics['val_mse'])
                metrics['val_r2'] = r2_score(y_val, meta_pred_val)
            else:
                metrics['val_accuracy'] = accuracy_score(y_val, meta_pred_val)
                try:
                    meta_pred_proba = meta_model.predict_proba(test_meta_features)[:, 1]
                    metrics['val_auc'] = roc_auc_score(y_val, meta_pred_proba)
                except:
                    metrics['val_auc'] = 0.5
        
        # 保存 OOF 预测
        if save_oof:
            self.oof_predictions = {
                'oof': oof_predictions,
                'test': test_predictions,
                'model_names': list(self.base_models.keys())
            }
        
        print(f"✅ Stacking 训练完成 - 训练集 AUC: {metrics.get('train_auc', 'N/A')}")
        
        return metrics
    
    def train_blending(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_holdout: pd.DataFrame,
        y_holdout: pd.Series,
        meta_model_type: str = "logistic_regression"
    ) -> Dict[str, float]:
        """
        Blending 集成训练（使用保留集训练元模型）
        
        Args:
            X_train: 训练特征（用于训练基模型）
            y_train: 训练标签
            X_holdout: 保留集特征（用于训练元模型）
            y_holdout: 保留集标签
            meta_model_type: 元模型类型
        
        Returns:
            评估指标
        """
        print(f"📚 开始 Blending 训练 - 基模型:{len(self.base_models)}")
        
        # 训练基模型
        train_predictions = np.zeros((len(X_train), len(self.base_models)))
        holdout_predictions = np.zeros((len(X_holdout), len(self.base_models)))
        
        for model_idx, (model_name, model_info) in enumerate(self.base_models.items()):
            print(f"  训练基模型 {model_idx + 1}/{len(self.base_models)}: {model_name}")
            
            model = model_info['model']
            model.fit(X_train, y_train)
            
            # 训练集预测
            if hasattr(model, 'predict_proba'):
                train_predictions[:, model_idx] = model.predict_proba(X_train)[:, 1]
                holdout_predictions[:, model_idx] = model.predict_proba(X_holdout)[:, 1]
            else:
                train_predictions[:, model_idx] = model.predict(X_train)
                holdout_predictions[:, model_idx] = model.predict(X_holdout)
            
            self.base_models[model_name]['oof'] = train_predictions[:, model_idx]
            self.base_models[model_name]['test_pred'] = holdout_predictions[:, model_idx]
        
        # 训练元模型
        print(f"  训练元模型: {meta_model_type}")
        
        meta_model = self._create_meta_model(meta_model_type)
        meta_model.fit(holdout_predictions, y_holdout)
        self.meta_model = meta_model
        
        # 评估
        meta_pred_train = meta_model.predict(train_predictions)
        meta_pred_holdout = meta_model.predict(holdout_predictions)
        
        metrics = {}
        
        if self.task_type == "regression":
            from sklearn.metrics import mean_squared_error, r2_score
            metrics['train_mse'] = mean_squared_error(y_train, meta_pred_train)
            metrics['train_r2'] = r2_score(y_train, meta_pred_train)
            metrics['val_mse'] = mean_squared_error(y_holdout, meta_pred_holdout)
            metrics['val_r2'] = r2_score(y_holdout, meta_pred_holdout)
        else:
            from sklearn.metrics import accuracy_score, roc_auc_score
            metrics['train_accuracy'] = accuracy_score(y_train, meta_pred_train)
            metrics['val_accuracy'] = accuracy_score(y_holdout, meta_pred_holdout)
            
            try:
                meta_pred_proba_train = meta_model.predict_proba(train_predictions)[:, 1]
                metrics['train_auc'] = roc_auc_score(y_train, meta_pred_proba_train)
            except:
                pass
            
            try:
                meta_pred_proba_holdout = meta_model.predict_proba(holdout_predictions)[:, 1]
                metrics['val_auc'] = roc_auc_score(y_holdout, meta_pred_proba_holdout)
            except:
                pass
        
        print(f"✅ Blending 训练完成 - 验证集 AUC: {metrics.get('val_auc', 'N/A')}")
        
        return metrics
    
    def train_voting(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        voting_type: str = "soft",
        weights: Dict[str, float] = None
    ) -> Dict[str, float]:
        """
        Voting 集成训练（加权投票）
        
        Args:
            X_train: 训练特征
            y_train: 训练标签
            voting_type: 投票类型 (soft/hard)
            weights: 模型权重
        
        Returns:
            评估指标
        """
        try:
            from sklearn.ensemble import VotingClassifier, VotingRegressor
            from sklearn.metrics import accuracy_score, roc_auc_score
        except ImportError:
            raise ImportError("Please install scikit-learn")
        
        print(f"🗳️  开始 Voting 训练 - 模型:{len(self.base_models)}, 类型:{voting_type}")
        
        # 准备模型列表
        estimators = []
        for model_name, model_info in self.base_models.items():
            estimators.append((model_name, model_info['model']))
        
        # 创建 Voting 模型
        if self.task_type == "regression":
            voting_model = VotingRegressor(estimators=estimators, weights=weights)
        else:
            voting_model = VotingClassifier(
                estimators=estimators,
                voting=voting_type,
                weights=weights
            )
        
        # 训练
        voting_model.fit(X_train, y_train)
        self.meta_model = voting_model
        
        # 评估
        y_pred = voting_model.predict(X_train)
        
        metrics = {}
        
        if self.task_type == "regression":
            from sklearn.metrics import mean_squared_error, r2_score
            metrics['train_mse'] = mean_squared_error(y_train, y_pred)
            metrics['train_rmse'] = np.sqrt(metrics['train_mse'])
            metrics['train_r2'] = r2_score(y_train, y_pred)
        else:
            metrics['train_accuracy'] = accuracy_score(y_train, y_pred)
            
            if voting_type == "soft" and hasattr(voting_model, 'predict_proba'):
                try:
                    y_proba = voting_model.predict_proba(X_train)[:, 1]
                    metrics['train_auc'] = roc_auc_score(y_train, y_proba)
                except:
                    pass
        
        print(f"✅ Voting 训练完成 - 训练集 AUC: {metrics.get('train_auc', 'N/A')}")
        
        return metrics
    
    def _create_meta_model(self, model_type: str) -> Any:
        """创建元模型"""
        try:
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
            from sklearn.linear_model import LogisticRegression, LinearRegression
            from sklearn.svm import SVC
            from sklearn.neural_network import MLPClassifier
        except ImportError:
            raise ImportError("Please install scikit-learn")
        
        model_map = {
            "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
            "linear_regression": LinearRegression(),
            "random_forest": RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42),
            "gradient_boosting": GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42),
            "svm": SVC(kernel='rbf', probability=True, random_state=42),
            "mlp": MLPClassifier(hidden_layer_sizes=(50,), max_iter=500, random_state=42),
        }
        
        if model_type not in model_map:
            print(f"⚠️  未知元模型类型 {model_type}，使用 LogisticRegression")
            return LogisticRegression(max_iter=1000, random_state=42)
        
        return model_map[model_type]
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用集成模型预测
        
        Args:
            X: 特征
        
        Returns:
            预测结果
        """
        if self.meta_model is None:
            raise ValueError("Model not trained")
        
        # 如果有基模型的测试预测，直接使用元模型
        if self.oof_predictions.get('test') is not None:
            return self.meta_model.predict(self.oof_predictions['test'])
        
        # 否则重新生成基模型预测
        n_samples = len(X)
        test_predictions = np.zeros((n_samples, len(self.base_models)))
        
        for model_idx, (model_name, model_info) in enumerate(self.base_models.items()):
            model = model_info['model']
            
            if hasattr(model, 'predict_proba'):
                test_predictions[:, model_idx] = model.predict_proba(X)[:, 1]
            else:
                test_predictions[:, model_idx] = model.predict(X)
        
        return self.meta_model.predict(test_predictions)
    
    def get_model_weights(self) -> Dict[str, float]:
        """获取模型权重（从元模型系数推导）"""
        if self.meta_model is None:
            return {}
        
        if hasattr(self.meta_model, 'coef_'):
            weights = self.meta_model.coef_.flatten()
            model_names = list(self.base_models.keys())
            
            weight_dict = {name: abs(w) for name, w in zip(model_names, weights)}
            
            # 归一化
            total = sum(weight_dict.values())
            if total > 0:
                weight_dict = {k: v / total for k, v in weight_dict.items()}
            
            return weight_dict
        
        return {}
    
    def save_ensemble(self, filepath: str):
        """保存集成模型"""
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump({
                'base_models': self.base_models,
                'meta_model': self.meta_model,
                'oof_predictions': self.oof_predictions,
                'task_type': self.task_type
            }, f)
    
    def load_ensemble(self, filepath: str):
        """加载集成模型"""
        import pickle
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.base_models = data['base_models']
            self.meta_model = data['meta_model']
            self.oof_predictions = data['oof_predictions']
            self.task_type = data['task_type']


class StackingClassifier:
    """简化的 Stacking 分类器（直接可用）"""
    
    def __init__(self, n_folds: int = 5):
        self.n_folds = n_folds
        self.ensemble = EnsembleTrainer(task_type="binary")
    
    def fit(self, X_train, y_train, X_val=None, y_val=None):
        """训练"""
        # 添加默认基模型
        try:
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
            from sklearn.linear_model import LogisticRegression
            from sklearn.svm import SVC
            from sklearn.naive_bayes import GaussianNB
        except ImportError:
            raise ImportError("Please install scikit-learn")
        
        self.ensemble.add_base_model("rf", RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42))
        self.ensemble.add_base_model("gb", GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42))
        self.ensemble.add_base_model("et", ExtraTreesClassifier(n_estimators=100, max_depth=5, random_state=42))
        self.ensemble.add_base_model("svm", SVC(kernel='rbf', probability=True, random_state=42))
        self.ensemble.add_base_model("nb", GaussianNB())
        
        return self.ensemble.train_stacking(X_train, y_train, X_val, y_val, n_folds=self.n_folds)
    
    def predict(self, X):
        """预测"""
        return self.ensemble.predict(X)
    
    def predict_proba(self, X):
        """预测概率"""
        if hasattr(self.ensemble.meta_model, 'predict_proba'):
            return self.ensemble.meta_model.predict_proba(X)
        return None
