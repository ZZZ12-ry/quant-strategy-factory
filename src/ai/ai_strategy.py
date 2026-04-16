"""
AI 增强策略 - 将 AI 预测集成到交易中
"""
import sys
sys.path.insert(0, '.')

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from src.strategies.base import BaseStrategy, Signal
from src.ml.ml_predictor import MLPredictor


class AIStrategy(BaseStrategy):
    """AI 增强策略 - 基于 ML 预测生成交易信号"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "confidence_threshold": 0.6,  # 置信度阈值
            "use_proba": True,            # 使用概率加权
            "stop_loss_pct": 0.03,        # 止损百分比
            "take_profit_pct": 0.05,      # 止盈百分比
            "max_holding_days": 20,       # 最大持仓天数
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            "confidence_threshold": (0.5, 0.8),
            "stop_loss_pct": (0.02, 0.05),
            "take_profit_pct": (0.03, 0.10),
            "max_holding_days": (10, 30),
        }
    
    def __init__(self, ml_predictor: MLPredictor, **params):
        """
        初始化 AI 策略
        
        Args:
            ml_predictor: ML 预测器
            **params: 策略参数
        """
        super().__init__(**params)
        self.ml = ml_predictor
        self.price_history = {}
        self.entry_prices = {}
        self.entry_times = {}
        self.holding_days = {}
    
    def _init_history(self, symbol: str):
        """初始化历史数据"""
        if symbol not in self.price_history:
            self.price_history[symbol] = {
                'close': [],
                'open': [],
                'high': [],
                'low': [],
                'volume': []
            }
            self.entry_prices[symbol] = None
            self.entry_times[symbol] = None
            self.holding_days[symbol] = 0
    
    def _update_history(self, bar: pd.Series):
        """更新历史数据"""
        symbol = bar['symbol']
        self._init_history(symbol)
        
        for key in ['close', 'open', 'high', 'low', 'volume']:
            self.price_history[symbol][key].append(bar[key])
            # 保持最近 100 条
            if len(self.price_history[symbol][key]) > 100:
                self.price_history[symbol][key] = self.price_history[symbol][key][-100:]
    
    def _get_ml_signal(self, bar: pd.Series) -> tuple:
        """
        获取 ML 信号
        
        Returns:
            (prediction, probas, confidence)
        """
        symbol = bar['symbol']
        
        # 获取预测
        probas = self.ml.predict_proba(bar, self.price_history[symbol])
        
        if probas is None:
            return None, None, 0.0
        
        # 获取主要预测
        if self.ml.task_type == "binary":
            # 二分类：1=涨，0=跌
            prob_up = probas.get('1', 0)
            prob_down = 1 - prob_up
            prediction = 1 if prob_up > 0.5 else 0
            confidence = max(prob_up, prob_down)
        
        elif self.ml.task_type == "multiclass":
            # 三分类：1=涨，0=震荡，-1=跌
            prob_up = probas.get('1', 0)
            prob_down = probas.get('-1', 0)
            prob_neutral = probas.get('0', 0)
            
            if prob_up > prob_down and prob_up > prob_neutral:
                prediction = 1
                confidence = prob_up
            elif prob_down > prob_up and prob_down > prob_neutral:
                prediction = -1
                confidence = prob_down
            else:
                prediction = 0
                confidence = prob_neutral
        
        else:
            # 回归
            prediction = self.ml.predict(bar, self.price_history[symbol])
            confidence = 0.5  # 回归没有置信度
        
        return prediction, probas, confidence
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        K 线数据回调
        
        Args:
            bar: K 线数据
        
        Returns:
            交易信号
        """
        symbol = bar['symbol']
        timestamp = bar['timestamp']
        close = bar['close']
        
        # 更新历史
        self._update_history(bar)
        
        # 更新持仓天数
        if self.entry_times.get(symbol) is not None:
            self.holding_days[symbol] += 1
        
        # 获取 ML 信号
        prediction, probas, confidence = self._get_ml_signal(bar)
        
        if prediction is None or confidence < 0.3:
            return None
        
        position = self.get_position(symbol)
        
        # === 没有持仓 ===
        if position is None:
            # 高置信度看涨 → 买入
            if prediction == 1 and confidence >= self.params["confidence_threshold"]:
                self.entry_prices[symbol] = close
                self.entry_times[symbol] = timestamp
                self.holding_days[symbol] = 0
                
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=confidence
                )
            
            # 高置信度看跌 → 做空
            elif prediction == -1 and confidence >= self.params["confidence_threshold"]:
                self.entry_prices[symbol] = close
                self.entry_times[symbol] = timestamp
                self.holding_days[symbol] = 0
                
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=confidence
                )
        
        # === 有持仓 ===
        else:
            entry_price = self.entry_prices.get(symbol, position.entry_price)
            
            if position.direction == "long":
                # 止损
                if close < entry_price * (1 - self.params["stop_loss_pct"]):
                    return self._close_position(symbol, bar, "止损")
                
                # 止盈
                if close > entry_price * (1 + self.params["take_profit_pct"]):
                    return self._close_position(symbol, bar, "止盈")
                
                # 持仓时间过长
                if self.holding_days[symbol] >= self.params["max_holding_days"]:
                    return self._close_position(symbol, bar, "时间平仓")
                
                # AI 预测反转
                if prediction == -1 and confidence >= self.params["confidence_threshold"]:
                    return self._close_position(symbol, bar, "AI 反转")
            
            elif position.direction == "short":
                # 止损
                if close > entry_price * (1 + self.params["stop_loss_pct"]):
                    return self._close_position(symbol, bar, "止损")
                
                # 止盈
                if close < entry_price * (1 - self.params["take_profit_pct"]):
                    return self._close_position(symbol, bar, "止盈")
                
                # 持仓时间过长
                if self.holding_days[symbol] >= self.params["max_holding_days"]:
                    return self._close_position(symbol, bar, "时间平仓")
                
                # AI 预测反转
                if prediction == 1 and confidence >= self.params["confidence_threshold"]:
                    return self._close_position(symbol, bar, "AI 反转")
        
        return None
    
    def _close_position(self, symbol: str, bar: pd.Series, reason: str) -> Signal:
        """平仓"""
        position = self.get_position(symbol)
        
        # 重置持仓信息
        self.entry_prices[symbol] = None
        self.entry_times[symbol] = None
        self.holding_days[symbol] = 0
        
        return self.generate_signal(
            symbol=symbol,
            timestamp=bar['timestamp'],
            direction="close",
            price=bar['close'],
            volume=position.volume,
            strength=1.0
        )
    
    def reset(self):
        """重置策略状态"""
        super().reset()
        self.price_history.clear()
        self.entry_prices.clear()
        self.entry_times.clear()
        self.holding_days.clear()


class EnsembleAIStrategy(BaseStrategy):
    """集成 AI 策略 - 多个模型投票"""
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            "confidence_threshold": 0.6,
            "min_agreement": 0.6,  # 最小一致比例
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.05,
        }
    
    def __init__(self, ml_predictors: List[MLPredictor], **params):
        """
        初始化集成 AI 策略
        
        Args:
            ml_predictors: 多个 ML 预测器列表
            **params: 策略参数
        """
        super().__init__(**params)
        self.ml_predictors = ml_predictors
        self.price_history = {}
        self.entry_prices = {}
    
    def _get_ensemble_signal(self, bar: pd.Series) -> tuple:
        """获取集成信号（投票）"""
        symbol = bar['symbol']
        predictions = []
        confidences = []
        
        for ml in self.ml_predictors:
            probas = ml.predict_proba(bar, self.price_history.get(symbol, {}))
            if probas:
                prob_up = probas.get('1', 0)
                predictions.append(1 if prob_up > 0.5 else 0)
                confidences.append(max(prob_up, 1 - prob_up))
        
        if not predictions:
            return None, 0.0
        
        # 投票
        agreement = sum(predictions) / len(predictions)
        
        if agreement >= self.params["min_agreement"]:
            final_prediction = 1
            confidence = np.mean(confidences)
        elif agreement <= (1 - self.params["min_agreement"]):
            final_prediction = -1
            confidence = np.mean(confidences)
        else:
            final_prediction = 0
            confidence = 0.0
        
        return final_prediction, confidence
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """K 线回调"""
        symbol = bar['symbol']
        timestamp = bar['timestamp']
        close = bar['close']
        
        # 更新历史（简化）
        if symbol not in self.price_history:
            self.price_history[symbol] = {'close': [], 'open': [], 'high': [], 'low': [], 'volume': []}
        for key in self.price_history[symbol]:
            self.price_history[symbol][key].append(bar[key])
            if len(self.price_history[symbol][key]) > 100:
                self.price_history[symbol][key] = self.price_history[symbol][key][-100:]
        
        # 获取集成信号
        prediction, confidence = self._get_ensemble_signal(bar)
        
        if prediction is None or confidence < self.params["confidence_threshold"]:
            return None
        
        position = self.get_position(symbol)
        
        if position is None:
            if prediction == 1:
                self.entry_prices[symbol] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="long",
                    price=close,
                    volume=1,
                    strength=confidence
                )
            elif prediction == -1:
                self.entry_prices[symbol] = close
                return self.generate_signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction="short",
                    price=close,
                    volume=1,
                    strength=confidence
                )
        else:
            entry_price = self.entry_prices.get(symbol, position.entry_price)
            
            if position.direction == "long":
                if close < entry_price * (1 - self.params["stop_loss_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                if close > entry_price * (1 + self.params["take_profit_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
            
            elif position.direction == "short":
                if close > entry_price * (1 + self.params["stop_loss_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
                if close < entry_price * (1 - self.params["take_profit_pct"]):
                    return self.generate_signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        direction="close",
                        price=close,
                        volume=position.volume,
                        strength=1.0
                    )
        
        return None
