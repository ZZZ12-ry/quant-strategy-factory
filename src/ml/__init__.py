"""
机器学习模块 - 因子挖掘、集成学习、深度学习
参考：Qlib RD-Agent, Kaggle Ensembling, Time Series Transformers
"""
from src.ml.feature_library import FeatureLibrary
from src.ml.model_trainer import ModelTrainer
from src.ml.ml_predictor import MLPredictor
from src.ml.auto_feature_miner import AutoFeatureMiner, AlphaGenerator
from src.ml.ensemble_trainer import EnsembleTrainer, StackingClassifier
from src.ml.deep_learning import DeepLearningModel, DeepLearningPredictor
from src.ml.deep_learning import create_lstm_model, create_gru_model, create_transformer_model

__all__ = [
    # 基础 ML
    'FeatureLibrary',
    'ModelTrainer',
    'MLPredictor',
    
    # 因子自动挖掘
    'AutoFeatureMiner',
    'AlphaGenerator',
    
    # 集成学习
    'EnsembleTrainer',
    'StackingClassifier',
    
    # 深度学习
    'DeepLearningModel',
    'DeepLearningPredictor',
    'create_lstm_model',
    'create_gru_model',
    'create_transformer_model',
]
