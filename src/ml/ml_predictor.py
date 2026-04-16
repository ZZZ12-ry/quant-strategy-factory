"""
ML 预测器 - 策略中的 ML 预测
参考：Qlib 在线预测
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


class MLPredictor:
    """ML 预测器 - 用于策略中"""
    
    def __init__(self, model=None, feature_names: list = None):
        """
        初始化预测器
        
        Args:
            model: 训练好的模型
            feature_names: 特征名称列表
        """
        self.model = model
        self.feature_names = feature_names or []
        self.feature_buffer = {}
    
    def set_model(self, model, feature_names: list):
        """设置模型"""
        self.model = model
        self.feature_names = feature_names
    
    def calculate_features(self, bar: pd.Series, history: Dict[str, list]) -> pd.DataFrame:
        """
        计算单条特征
        
        Args:
            bar: 当前 K 线
            history: 历史数据
        
        Returns:
            特征 DataFrame
        """
        # 简化特征计算示例
        features = {}
        
        # 需要足够历史数据
        min_history = 20
        for key in history:
            if len(history[key]) < min_history:
                return None
        
        # 收益率
        close_prices = history['close']
        features['return_1d'] = (close_prices[-1] - close_prices[-2]) / close_prices[-2] if len(close_prices) > 1 else 0
        features['return_5d'] = (close_prices[-1] - close_prices[-6]) / close_prices[-6] if len(close_prices) > 5 else 0
        features['return_10d'] = (close_prices[-1] - close_prices[-11]) / close_prices[-11] if len(close_prices) > 10 else 0
        
        # 均线
        features['ma_5'] = np.mean(close_prices[-5:])
        features['ma_10'] = np.mean(close_prices[-10:])
        features['ma_20'] = np.mean(close_prices[-20:])
        
        # 价格相对位置
        features['price_vs_ma5'] = close_prices[-1] / features['ma_5'] - 1
        features['price_vs_ma10'] = close_prices[-1] / features['ma_10'] - 1
        features['price_vs_ma20'] = close_prices[-1] / features['ma_20'] - 1
        
        # 均线关系
        features['ma5_vs_ma10'] = features['ma_5'] / features['ma_10'] - 1
        features['ma5_vs_ma20'] = features['ma_5'] / features['ma_20'] - 1
        
        # 波动率
        returns = np.diff(close_prices[-21:]) / close_prices[-21:-1]
        features['volatility_20d'] = np.std(returns) if len(returns) > 0 else 0
        
        # 成交量
        volumes = history.get('volume', [])
        if len(volumes) > 5:
            features['volume_ratio'] = volumes[-1] / np.mean(volumes[-5:])
        else:
            features['volume_ratio'] = 1
        
        # 动量
        features['momentum_10'] = features['return_10d']
        
        # 布林带位置
        ma20 = features['ma_20']
        std20 = np.std(close_prices[-20:])
        bb_lower = ma20 - 2 * std20
        bb_upper = ma20 + 2 * std20
        features['bb_position'] = (close_prices[-1] - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        
        # Z-Score
        features['zscore_20'] = (close_prices[-1] - ma20) / std20 if std20 > 0 else 0
        
        # 创建 DataFrame
        feature_df = pd.DataFrame([features])
        
        # 只保留需要的特征
        if self.feature_names:
            available_cols = [col for col in self.feature_names if col in feature_df.columns]
            feature_df = feature_df[available_cols]
        
        return feature_df
    
    def predict(self, bar: pd.Series, history: Dict[str, list]) -> Optional[float]:
        """
        预测
        
        Args:
            bar: 当前 K 线
            history: 历史数据
        
        Returns:
            预测值
        """
        if self.model is None:
            return None
        
        # 计算特征
        features = self.calculate_features(bar, history)
        if features is None:
            return None
        
        # 预测
        prediction = self.model.predict(features)[0]
        
        return prediction
    
    def predict_proba(self, bar: pd.Series, history: Dict[str, list]) -> Optional[Dict[str, float]]:
        """
        预测概率（分类任务）
        
        Args:
            bar: 当前 K 线
            history: 历史数据
        
        Returns:
            各类别概率
        """
        if self.model is None:
            return None
        
        if not hasattr(self.model, 'predict_proba'):
            return None
        
        # 计算特征
        features = self.calculate_features(bar, history)
        if features is None:
            return None
        
        # 预测概率
        probas = self.model.predict_proba(features)[0]
        
        # 返回字典
        if hasattr(self.model, 'classes_'):
            classes = self.model.classes_
            return {str(cls): prob for cls, prob in zip(classes, probas)}
        else:
            return {'class_0': probas[0], 'class_1': probas[1]} if len(probas) == 2 else None


class MLStrategyMixin:
    """ML 策略混合类 - 将 ML 预测集成到策略中"""
    
    def __init__(self, ml_predictor: MLPredictor = None):
        """初始化 ML 混合类"""
        self.ml_predictor = ml_predictor
        self.price_history = {'close': [], 'open': [], 'high': [], 'low': [], 'volume': []}
    
    def update_history(self, bar: pd.Series):
        """更新历史数据"""
        self.price_history['close'].append(bar['close'])
        self.price_history['open'].append(bar['open'])
        self.price_history['high'].append(bar['high'])
        self.price_history['low'].append(bar['low'])
        self.price_history['volume'].append(bar['volume'])
        
        # 保持历史数据长度
        max_len = 100
        for key in self.price_history:
            if len(self.price_history[key]) > max_len:
                self.price_history[key] = self.price_history[key][-max_len:]
    
    def get_ml_signal(self, bar: pd.Series, threshold: float = 0.6) -> Optional[str]:
        """
        获取 ML 信号
        
        Args:
            bar: 当前 K 线
            threshold: 置信度阈值
        
        Returns:
            信号方向 (long/short/none)
        """
        if self.ml_predictor is None:
            return None
        
        # 更新历史
        self.update_history(bar)
        
        # 获取预测概率
        probas = self.ml_predictor.predict_proba(bar, self.price_history)
        
        if probas is None:
            return None
        
        # 根据概率生成信号
        if '1' in probas and probas['1'] > threshold:
            return 'long'
        elif '0' in probas and probas['0'] > threshold:
            return 'short'
        else:
            return 'none'
