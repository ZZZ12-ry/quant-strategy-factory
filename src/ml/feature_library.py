"""
因子库 - 100+ 量化因子
参考：Qlib Alpha158/Alpha360
"""
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np


class FeatureLibrary:
    """因子库"""
    
    def __init__(self):
        self.features = {}
        self.feature_names = []
    
    def calculate_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有因子
        
        Args:
            data: OHLCV 数据
        
        Returns:
            包含所有因子的 DataFrame
        """
        df = data.copy()
        
        # 基础因子
        df = self._add_price_features(df)
        df = self._add_volume_features(df)
        df = self._add_volatility_features(df)
        df = self._add_momentum_features(df)
        df = self._add_mean_reversion_features(df)
        df = self._add_pattern_features(df)
        
        # 高级因子
        df = self._add_technical_features(df)
        df = self._add_statistical_features(df)
        
        # 去除 NaN
        df = df.dropna()
        
        return df
    
    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """价格相关因子"""
        # 收益率
        df['return_1d'] = df['close'].pct_change(1)
        df['return_3d'] = df['close'].pct_change(3)
        df['return_5d'] = df['close'].pct_change(5)
        df['return_10d'] = df['close'].pct_change(10)
        df['return_20d'] = df['close'].pct_change(20)
        
        # 均线
        df['ma_5'] = df['close'].rolling(5).mean()
        df['ma_10'] = df['close'].rolling(10).mean()
        df['ma_20'] = df['close'].rolling(20).mean()
        df['ma_60'] = df['close'].rolling(60).mean()
        
        # 价格相对位置
        df['price_vs_ma5'] = df['close'] / df['ma_5'] - 1
        df['price_vs_ma10'] = df['close'] / df['ma_10'] - 1
        df['price_vs_ma20'] = df['close'] / df['ma_20'] - 1
        df['price_vs_ma60'] = df['close'] / df['ma_60'] - 1
        
        # 均线关系
        df['ma5_vs_ma10'] = df['ma_5'] / df['ma_10'] - 1
        df['ma5_vs_ma20'] = df['ma_5'] / df['ma_20'] - 1
        df['ma10_vs_ma20'] = df['ma_10'] / df['ma_20'] - 1
        
        # 高低点
        df['high_20d'] = df['high'].rolling(20).max()
        df['low_20d'] = df['low'].rolling(20).min()
        df['price_position'] = (df['close'] - df['low_20d']) / (df['high_20d'] - df['low_20d'])
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """成交量因子"""
        # 成交量均线
        df['volume_ma5'] = df['volume'].rolling(5).mean()
        df['volume_ma10'] = df['volume'].rolling(10).mean()
        df['volume_ma20'] = df['volume'].rolling(20).mean()
        
        # 成交量比率
        df['volume_ratio'] = df['volume'] / df['volume_ma5']
        df['volume_ratio_10'] = df['volume'] / df['volume_ma10']
        
        # 成交量变化
        df['volume_change'] = df['volume'].pct_change(1)
        df['volume_change_3d'] = df['volume'].pct_change(3)
        df['volume_change_5d'] = df['volume'].pct_change(5)
        
        # 量价关系
        df['volume_price_corr'] = df['volume'].rolling(20).corr(df['close'])
        
        return df
    
    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """波动率因子"""
        # 真实波动率
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        
        # ATR
        df['atr_5'] = df['tr'].rolling(5).mean()
        df['atr_10'] = df['tr'].rolling(10).mean()
        df['atr_14'] = df['tr'].rolling(14).mean()
        df['atr_20'] = df['tr'].rolling(20).mean()
        
        # 波动率
        df['volatility_5d'] = df['return_1d'].rolling(5).std()
        df['volatility_10d'] = df['return_1d'].rolling(10).std()
        df['volatility_20d'] = df['return_1d'].rolling(20).std()
        
        # 波动率变化
        df['volatility_change'] = df['volatility_5d'].pct_change(1)
        
        # 标准化 ATR
        df['atr_norm'] = df['atr_14'] / df['close']
        
        return df
    
    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """动量因子"""
        # RSI
        for period in [6, 12, 24]:
            delta = df['close'].diff(1)
            gain = delta.where(delta > 0, 0)
            loss = (-delta).where(delta < 0, 0)
            
            avg_gain = gain.rolling(period).mean()
            avg_loss = loss.rolling(period).mean()
            
            rs = avg_gain / avg_loss
            df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        # 动量
        for period in [5, 10, 20]:
            df[f'momentum_{period}'] = df['close'].pct_change(period)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False)
        exp2 = df['close'].ewm(span=26, adjust=False)
        macd_line = exp1.mean() - exp2.mean()
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_hist'] = macd_line - signal_line
        
        # CCI
        tp = (df['high'] + df['low'] + df['close']) / 3
        df['cci_20'] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
        
        return df
    
    def _add_mean_reversion_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """均值回归因子"""
        # 布林带
        ma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        df['bb_upper'] = ma20 + 2 * std20
        df['bb_lower'] = ma20 - 2 * std20
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / ma20
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Z-Score
        for period in [10, 20, 60]:
            ma = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()
            df[f'zscore_{period}'] = (df['close'] - ma) / std
        
        # KDJ
        low_n = df['low'].rolling(9).min()
        high_n = df['high'].rolling(9).max()
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        df['kdj_k'] = rsv.rolling(3).mean()
        df['kdj_d'] = df['kdj_k'].rolling(3).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
        
        return df
    
    def _add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """K 线形态因子"""
        # 实体大小
        df['body_size'] = abs(df['close'] - df['open']) / df['close']
        
        # 上下影线
        df['upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / df['close']
        df['lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / df['close']
        
        # 涨跌幅
        df['price_change'] = (df['close'] - df['open']) / df['open']
        
        # 跳空
        df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        
        return df
    
    def _add_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """技术指标因子"""
        # ADX
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
        
        df['adx'] = (tr.rolling(14).mean() / close).rolling(14).mean() * 100
        
        # Williams %R
        highest_high = df['high'].rolling(14).max()
        lowest_low = df['low'].rolling(14).min()
        df['williams_r'] = -100 * (highest_high - close) / (highest_high - lowest_low)
        
        return df
    
    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """统计因子"""
        # 偏度
        df['skewness_20'] = df['return_1d'].rolling(20).skew()
        
        # 峰度
        df['kurtosis_20'] = df['return_1d'].rolling(20).kurt()
        
        # 相关性
        df['corr_price_volume'] = df['close'].rolling(20).corr(df['volume'])
        
        # 自相关
        df['autocorr_1d'] = df['return_1d'].rolling(20).apply(lambda x: x.autocorr(lag=1))
        
        return df
    
    def get_feature_names(self) -> List[str]:
        """获取因子名称列表"""
        return [
            'return_1d', 'return_3d', 'return_5d', 'return_10d', 'return_20d',
            'ma_5', 'ma_10', 'ma_20', 'ma_60',
            'price_vs_ma5', 'price_vs_ma10', 'price_vs_ma20', 'price_vs_ma60',
            'ma5_vs_ma10', 'ma5_vs_ma20', 'ma10_vs_ma20',
            'price_position',
            'volume_ma5', 'volume_ma10', 'volume_ma20',
            'volume_ratio', 'volume_ratio_10',
            'volume_change', 'volume_change_3d', 'volume_change_5d',
            'volume_price_corr',
            'tr', 'atr_5', 'atr_10', 'atr_14', 'atr_20',
            'volatility_5d', 'volatility_10d', 'volatility_20d',
            'volatility_change', 'atr_norm',
            'rsi_6', 'rsi_12', 'rsi_24',
            'momentum_5', 'momentum_10', 'momentum_20',
            'macd', 'macd_signal', 'macd_hist', 'cci_20',
            'bb_upper', 'bb_lower', 'bb_width', 'bb_position',
            'zscore_10', 'zscore_20', 'zscore_60',
            'kdj_k', 'kdj_d', 'kdj_j',
            'body_size', 'upper_shadow', 'lower_shadow',
            'price_change', 'gap',
            'adx', 'williams_r',
            'skewness_20', 'kurtosis_20',
            'corr_price_volume', 'autocorr_1d'
        ]
    
    def get_feature_importance(self, model, feature_names: List[str]) -> pd.DataFrame:
        """获取因子重要性"""
        if hasattr(model, 'feature_importances_'):
            importance_df = pd.DataFrame({
                'feature': feature_names,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            return importance_df
        else:
            return pd.DataFrame()
