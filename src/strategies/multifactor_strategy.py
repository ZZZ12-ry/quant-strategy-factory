"""
多因子策略 - 基于多因子模型的量化策略
参考：Barra 多因子模型，Qlib Alpha158
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from src.strategies.base import BaseStrategy, Signal
from src.ml.feature_library import FeatureLibrary


class MultiFactorStrategy(BaseStrategy):
    """
    多因子策略
    
    原理：结合多个因子（价值、动量、质量、波动率等）生成综合评分，
    根据评分做多高分品种，做空低分品种
    
    适用：多品种组合 / 股票池
    """
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            'factor_weights': {
                'momentum': 0.3,
                'value': 0.2,
                'quality': 0.2,
                'volatility': 0.15,
                'size': 0.15,
            },
            'lookback_period': 60,      # 因子计算窗口
            'rebalance_period': 5,       # 调仓周期
            'top_percentile': 0.2,       # 做多前 20%
            'bottom_percentile': 0.2,    # 做空前 20%
            'zscore_clip': 3.0,          # Z-Score 截断
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            'lookback_period': (30, 120),
            'rebalance_period': (3, 10),
            'top_percentile': (0.1, 0.3),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.feature_lib = FeatureLibrary()
        self.price_history = {}
        self.factor_scores = {}
        self.days_since_rebalance = 0
        self.current_positions = []
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        K 线回调
        
        Args:
            bar: 包含 symbol 和 OHLCV 的 K 线
        """
        symbol = bar.get('symbol', 'UNKNOWN')
        
        # 更新价格历史
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append({
            'open': bar['open'],
            'high': bar['high'],
            'low': bar['low'],
            'close': bar['close'],
            'volume': bar['volume'],
            'timestamp': bar.get('timestamp', datetime.now())
        })
        
        # 保持历史长度
        max_len = self.params['lookback_period'] + 10
        if len(self.price_history[symbol]) > max_len:
            self.price_history[symbol] = self.price_history[symbol][-max_len:]
        
        # 调仓日
        self.days_since_rebalance += 1
        if self.days_since_rebalance < self.params['rebalance_period']:
            return None
        
        self.days_since_rebalance = 0
        
        # 计算所有品种的因子得分
        self._calculate_factor_scores()
        
        # 需要足够的品种
        if len(self.factor_scores) < 10:
            return None
        
        # 排序
        sorted_symbols = sorted(self.factor_scores.items(), key=lambda x: x[1], reverse=True)
        
        n_top = max(1, int(len(sorted_symbols) * self.params['top_percentile']))
        n_bottom = max(1, int(len(sorted_symbols) * self.params['bottom_percentile']))
        
        new_longs = [s[0] for s in sorted_symbols[:n_top]]
        new_shorts = [s[0] for s in sorted_symbols[-n_bottom:]]
        
        # 调仓
        signals = []
        
        # 平掉不再持有的
        for sym in self.current_positions:
            if sym not in new_longs and sym not in new_shorts:
                if sym in self.positions:
                    pos = self.positions[sym]
                    self.close_position(
                        symbol=sym,
                        exit_price=bar['close'],
                        exit_time=bar.get('timestamp', datetime.now())
                    )
        
        # 开新多头
        for sym in new_longs:
            if sym not in self.current_positions:
                self.update_position(
                    symbol=sym,
                    direction='long',
                    volume=1,
                    entry_price=bar['close'],
                    entry_time=bar.get('timestamp', datetime.now())
                )
        
        # 开新空头
        for sym in new_shorts:
            if sym not in self.current_positions:
                self.update_position(
                    symbol=sym,
                    direction='short',
                    volume=1,
                    entry_price=bar['close'],
                    entry_time=bar.get('timestamp', datetime.now())
                )
        
        self.current_positions = new_longs + new_shorts
        
        return self.generate_signal(
            symbol='multifactor_rebalance',
            timestamp=bar.get('timestamp', datetime.now()),
            direction='rebalance',
            price=bar['close'],
            volume=len(new_longs) + len(new_shorts),
            strength=1.0
        )
    
    def _calculate_factor_scores(self):
        """计算所有品种的综合因子得分"""
        self.factor_scores = {}
        
        for symbol, history in self.price_history.items():
            if len(history) < self.params['lookback_period']:
                continue
            
            # 转换为 DataFrame
            df = pd.DataFrame(history)
            
            # 计算因子
            try:
                df_with_factors = self.feature_lib.calculate_all(df)
                
                # 提取因子值（最新一期）
                latest = df_with_factors.iloc[-1]
                
                # 计算各类因子得分
                momentum_score = self._calc_momentum_score(latest)
                value_score = self._calc_value_score(latest)
                quality_score = self._calc_quality_score(latest)
                volatility_score = self._calc_volatility_score(latest)
                size_score = self._calc_size_score(latest, symbol)
                
                # 综合得分
                weights = self.params['factor_weights']
                total_score = (
                    momentum_score * weights['momentum'] +
                    value_score * weights['value'] +
                    quality_score * weights['quality'] +
                    volatility_score * weights['volatility'] +
                    size_score * weights['size']
                )
                
                self.factor_scores[symbol] = total_score
                
            except Exception as e:
                continue
    
    def _calc_momentum_score(self, latest: pd.Series) -> float:
        """动量因子得分"""
        score = 0.0
        
        # 价格动量
        if 'return_20d' in latest:
            score += latest['return_20d']
        if 'momentum_10' in latest:
            score += latest['momentum_10']
        if 'rsi_12' in latest:
            # RSI 标准化
            score += (latest['rsi_12'] - 50) / 50
        
        return score
    
    def _calc_value_score(self, latest: pd.Series) -> float:
        """价值因子得分（均值回归）"""
        score = 0.0
        
        # 价格相对位置
        if 'bb_position' in latest:
            # 布林带下轨得分高
            score += (1 - latest['bb_position'])
        if 'zscore_20' in latest:
            # Z-Score 负值得分高
            score -= latest['zscore_20']
        
        return score
    
    def _calc_quality_score(self, latest: pd.Series) -> float:
        """质量因子得分"""
        score = 0.0
        
        # 趋势质量
        if 'price_vs_ma20' in latest:
            score += latest['price_vs_ma20']
        if 'ma5_vs_ma20' in latest:
            score += latest['ma5_vs_ma20']
        
        return score
    
    def _calc_volatility_score(self, latest: pd.Series) -> float:
        """波动率因子得分（低波得分高）"""
        score = 0.0
        
        if 'volatility_20d' in latest:
            # 波动率越低得分越高（负相关）
            score -= latest['volatility_20d']
        if 'atr_norm' in latest:
            score -= latest['atr_norm']
        
        return score
    
    def _calc_size_score(self, latest: pd.Series, symbol: str) -> float:
        """规模因子得分"""
        # 简化：使用成交量作为规模代理
        if 'volume_ratio' in latest:
            return np.log(latest['volume_ratio'] + 1)
        return 0.0


class FactorTimingStrategy(BaseStrategy):
    """
    因子择时策略
    
    原理：根据不同因子的历史表现，动态调整因子权重，
    在因子有效时增加权重，失效时降低权重
    
    适用：多因子策略的增强版本
    """
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            'base_weights': {
                'momentum': 0.25,
                'value': 0.25,
                'quality': 0.25,
                'volatility': 0.25,
            },
            'lookback_period': 60,
            'performance_window': 20,   # 因子表现评估窗口
            'weight_adjustment': 0.5,    # 权重调整幅度
            'rebalance_period': 5,
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.factor_performance = {
            'momentum': [],
            'value': [],
            'quality': [],
            'volatility': [],
        }
        self.dynamic_weights = self.params['base_weights'].copy()
        self.last_factor_returns = {}
        self.days_since_rebalance = 0
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """K 线回调"""
        # 更新因子表现历史
        self._update_factor_performance(bar)
        
        # 调仓日
        self.days_since_rebalance += 1
        if self.days_since_rebalance < self.params['rebalance_period']:
            return None
        
        self.days_since_rebalance = 0
        
        # 动态调整权重
        self._adjust_weights()
        
        return self.generate_signal(
            symbol='factor_timing',
            timestamp=bar.get('timestamp', datetime.now()),
            direction='rebalance',
            price=bar['close'],
            volume=1,
            strength=1.0
        )
    
    def _update_factor_performance(self, bar: pd.Series):
        """更新因子表现"""
        # 简化：假设已经计算了各因子的收益
        # 实际需要回测各因子的历史表现
        
        for factor in self.factor_performance.keys():
            # 这里需要实际计算因子收益
            # 简化处理
            self.factor_performance[factor].append(np.random.randn() * 0.01)
            
            if len(self.factor_performance[factor]) > self.params['performance_window']:
                self.factor_performance[factor] = self.factor_performance[factor][-self.params['performance_window']:]
    
    def _adjust_weights(self):
        """根据历史表现调整因子权重"""
        new_weights = {}
        
        for factor, perf_history in self.factor_performance.items():
            if len(perf_history) < 10:
                new_weights[factor] = self.params['base_weights'][factor]
                continue
            
            # 计算因子 IC 均值
            mean_ic = np.mean(perf_history)
            
            # 调整权重（IC 越高权重越大）
            adjustment = 1 + self.params['weight_adjustment'] * np.tanh(mean_ic * 10)
            new_weights[factor] = self.params['base_weights'][factor] * adjustment
        
        # 归一化
        total = sum(new_weights.values())
        self.dynamic_weights = {k: v / total for k, v in new_weights.items()}
