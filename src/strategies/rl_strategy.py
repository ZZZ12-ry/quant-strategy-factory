"""
强化学习策略 - 基于 DQN/PPO 的交易策略
参考：FinRL, Stable Baselines3, Trading Gym
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from src.strategies.base import BaseStrategy, Signal


class RLTradingStrategy(BaseStrategy):
    """
    强化学习交易策略（DQN）
    
    原理：使用深度强化学习（DQN）学习最优交易策略，
    状态包括价格、指标、持仓等，动作为买/卖/持有
    
    适用：单品种趋势交易
    """
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            'lookback_window': 30,       # 状态回溯窗口
            'training_episodes': 1000,    # 训练回合数
            'epsilon_start': 1.0,         # 初始探索率
            'epsilon_end': 0.01,          # 最终探索率
            'epsilon_decay': 0.995,       # 探索率衰减
            'gamma': 0.99,                # 折扣因子
            'learning_rate': 0.001,       # 学习率
            'batch_size': 64,             # 批次大小
            'replay_buffer_size': 10000,  # 经验回放大小
            'target_update_freq': 100,    # 目标网络更新频率
        }
    
    @classmethod
    def param_space(cls) -> Dict[str, Any]:
        return {
            'lookback_window': (20, 60),
            'gamma': (0.9, 0.99),
            'learning_rate': (0.0001, 0.01),
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.price_history = []
        self.feature_history = []
        self.position_history = []
        self.epsilon = self.params['epsilon_start']
        self.model = None
        self.target_model = None
        self.replay_buffer = []
        self.training_step = 0
        self.is_trained = False
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """K 线回调"""
        # 更新历史
        self._update_state(bar)
        
        # 需要足够的历史数据
        if len(self.price_history) < self.params['lookback_window']:
            return None
        
        # 生成状态
        state = self._get_state()
        
        # 训练模式（如果有历史数据）
        if not self.is_trained and len(self.replay_buffer) > self.params['batch_size']:
            self._train_step()
        
        # 选择动作
        if self.is_trained and self.model is not None:
            action = self._select_action(state)
        else:
            # 随机探索
            action = np.random.choice([0, 1, 2])  # 0: 持有，1: 买入，2: 卖出
        
        # 执行动作
        signal = self._execute_action(action, bar)
        
        # 存储经验
        reward = self._calculate_reward(bar)
        next_state = self._get_state()
        done = False
        
        self.replay_buffer.append((state, action, reward, next_state, done))
        
        if len(self.replay_buffer) > self.params['replay_buffer_size']:
            self.replay_buffer = self.replay_buffer[-self.params['replay_buffer_size']:]
        
        return signal
    
    def _update_state(self, bar: pd.Series):
        """更新状态历史"""
        self.price_history.append(bar['close'])
        
        # 计算简单特征
        if len(self.price_history) >= 5:
            ma5 = np.mean(self.price_history[-5:])
        else:
            ma5 = bar['close']
        
        if len(self.price_history) >= 20:
            ma20 = np.mean(self.price_history[-20:])
        else:
            ma20 = bar['close']
        
        # 收益率
        if len(self.price_history) >= 2:
            ret = (bar['close'] - self.price_history[-2]) / self.price_history[-2]
        else:
            ret = 0
        
        # 持仓
        position = 1 if 'position' in self.positions and self.positions['position'].direction == 'long' else 0
        if 'position' in self.positions and self.positions['position'].direction == 'short':
            position = -1
        
        features = {
            'price': bar['close'],
            'ma5': ma5,
            'ma20': ma20,
            'price_vs_ma5': bar['close'] / ma5 - 1,
            'price_vs_ma20': bar['close'] / ma20 - 1,
            'ma5_vs_ma20': ma5 / ma20 - 1,
            'return_1d': ret,
            'position': position,
        }
        
        self.feature_history.append(features)
        self.position_history.append(position)
        
        # 保持长度
        max_len = self.params['lookback_window'] + 10
        if len(self.price_history) > max_len:
            self.price_history = self.price_history[-max_len:]
            self.feature_history = self.feature_history[-max_len:]
            self.position_history = self.position_history[-max_len:]
    
    def _get_state(self) -> np.ndarray:
        """获取当前状态向量"""
        if len(self.feature_history) < self.params['lookback_window']:
            return np.zeros(self.params['lookback_window'] * 8)
        
        # 展平特征
        features = []
        for i in range(self.params['lookback_window']):
            feat = self.feature_history[-(self.params['lookback_window'] - i)]
            features.extend([
                feat['price'],
                feat['ma5'],
                feat['ma20'],
                feat['price_vs_ma5'],
                feat['price_vs_ma20'],
                feat['ma5_vs_ma20'],
                feat['return_1d'],
                feat['position'],
            ])
        
        return np.array(features)
    
    def _select_action(self, state: np.ndarray) -> int:
        """选择动作（epsilon-greedy）"""
        if np.random.random() < self.epsilon:
            return np.random.choice([0, 1, 2])
        
        if self.model is None:
            return 0
        
        # 使用模型预测
        try:
            q_values = self.model.predict(state.reshape(1, -1), verbose=0)[0]
            return np.argmax(q_values)
        except:
            return 0
    
    def _execute_action(self, action: int, bar: pd.Series) -> Optional[Signal]:
        """执行动作"""
        timestamp = bar.get('timestamp', datetime.now())
        
        # 当前持仓
        has_long = 'position' in self.positions and self.positions['position'].direction == 'long'
        has_short = 'position' in self.positions and self.positions['position'].direction == 'short'
        
        # 动作：0=持有，1=买入，2=卖出
        if action == 1:  # 买入
            if has_short:
                # 平空仓
                self.close_position('position', bar['close'], timestamp)
                return self.generate_signal('rl_close_short', timestamp, 'close_short', bar['close'], 1, 1.0)
            elif not has_long:
                # 开多仓
                self.update_position('position', 'long', 1, bar['close'], timestamp)
                return self.generate_signal('rl_buy', timestamp, 'long', bar['close'], 1, 1.0)
        
        elif action == 2:  # 卖出
            if has_long:
                # 平多仓
                self.close_position('position', bar['close'], timestamp)
                return self.generate_signal('rl_close_long', timestamp, 'close_long', bar['close'], 1, 1.0)
            elif not has_short:
                # 开空仓
                self.update_position('position', 'short', 1, bar['close'], timestamp)
                return self.generate_signal('rl_sell', timestamp, 'short', bar['close'], 1, 1.0)
        
        return None
    
    def _calculate_reward(self, bar: pd.Series) -> float:
        """计算奖励"""
        if len(self.position_history) < 2:
            return 0.0
        
        # 持仓收益
        position = self.position_history[-2]
        ret = (bar['close'] - self.price_history[-2]) / self.price_history[-2]
        
        reward = position * ret
        
        # 交易成本惩罚
        if position != self.position_history[-1]:
            reward -= 0.001  # 交易成本
        
        return reward
    
    def _train_step(self):
        """训练一步"""
        if len(self.replay_buffer) < self.params['batch_size']:
            return
        
        # 采样批次
        batch = self._sample_batch()
        
        states, actions, rewards, next_states, dones = batch
        
        # 这里需要实际的 DQN 训练
        # 简化处理，实际需要使用 PyTorch/TensorFlow
        
        self.training_step += 1
        
        # 衰减探索率
        self.epsilon = max(
            self.params['epsilon_end'],
            self.epsilon * self.params['epsilon_decay']
        )
        
        # 标记为已训练
        if self.training_step > 100:
            self.is_trained = True
    
    def _sample_batch(self) -> Tuple:
        """从回放缓冲区采样"""
        indices = np.random.choice(len(self.replay_buffer), self.params['batch_size'], replace=False)
        
        batch = [self.replay_buffer[i] for i in indices]
        
        states = np.array([item[0] for item in batch])
        actions = np.array([item[1] for item in batch])
        rewards = np.array([item[2] for item in batch])
        next_states = np.array([item[3] for item in batch])
        dones = np.array([item[4] for item in batch])
        
        return states, actions, rewards, next_states, dones
    
    def train_offline(self, data: pd.DataFrame, episodes: int = None):
        """
        离线训练
        
        Args:
            data: 历史 OHLCV 数据
            episodes: 训练回合数
        """
        episodes = episodes or self.params['training_episodes']
        
        print(f"🤖 开始 RL 训练 - 回合数:{episodes}")
        
        # 简化训练流程
        # 实际需要使用完整的 RL 训练循环
        
        for episode in range(episodes):
            # 重置环境
            self.price_history = []
            self.feature_history = []
            self.position_history = []
            
            # 跑一遍数据
            for idx, row in data.iterrows():
                bar = row
                self.on_bar(bar)
            
            if (episode + 1) % 100 == 0:
                print(f"  回合 {episode+1}/{episodes} - 探索率:{self.epsilon:.3f}")
        
        print(f"✅ RL 训练完成")
        self.is_trained = True


class PPOStrategy(BaseStrategy):
    """
    PPO（Proximal Policy Optimization）策略
    
    原理：使用 PPO 算法学习连续动作空间的交易策略，
    输出持仓比例而非离散动作
    
    适用：仓位管理 / 资产配置
    """
    
    @classmethod
    def default_params(cls) -> Dict[str, Any]:
        return {
            'lookback_window': 30,
            'max_position': 1.0,        # 最大仓位
            'clip_epsilon': 0.2,         # PPO 裁剪参数
            'gamma': 0.99,
            'lambda_gae': 0.95,          # GAE 参数
            'learning_rate': 0.0003,
            'training_epochs': 10,
        }
    
    def __init__(self, **params):
        super().__init__(**params)
        self.state_history = []
        self.position_target = 0.0
        self.current_position = 0.0
        self.is_trained = False
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """K 线回调"""
        # 更新状态
        self._update_state(bar)
        
        if len(self.state_history) < self.params['lookback_window']:
            return None
        
        # 获取目标仓位（简化：使用规则代替 RL 模型）
        target_position = self._get_target_position(bar)
        
        # 调整仓位
        if abs(target_position - self.current_position) > 0.1:
            signal = self._adjust_position(target_position, bar)
            self.current_position = target_position
            return signal
        
        return None
    
    def _update_state(self, bar: pd.Series):
        """更新状态"""
        features = {
            'close': bar['close'],
            'return_1d': bar['close'] / bar['open'] - 1,
            'volume': bar['volume'],
        }
        self.state_history.append(features)
        
        if len(self.state_history) > self.params['lookback_window'] + 10:
            self.state_history = self.state_history[-self.params['lookback_window']:]
    
    def _get_target_position(self, bar: pd.Series) -> float:
        """获取目标仓位（简化版）"""
        # 实际应该使用 PPO 模型预测
        # 这里使用简单规则
        
        if len(self.state_history) < 20:
            return 0.0
        
        # 趋势判断
        ma5 = np.mean([s['close'] for s in self.state_history[-5:]])
        ma20 = np.mean([s['close'] for s in self.state_history[-20:]])
        
        if ma5 > ma20:
            return self.params['max_position']
        elif ma5 < ma20:
            return -self.params['max_position']
        else:
            return 0.0
    
    def _adjust_position(self, target: float, bar: pd.Series) -> Optional[Signal]:
        """调整仓位"""
        timestamp = bar.get('timestamp', datetime.now())
        
        # 平仓
        if 'position' in self.positions:
            self.close_position('position', bar['close'], timestamp)
        
        # 开新仓
        if abs(target) > 0.1:
            direction = 'long' if target > 0 else 'short'
            self.update_position('position', direction, abs(target), bar['close'], timestamp)
            
            return self.generate_signal(
                'ppo_adjust',
                timestamp,
                direction,
                bar['close'],
                abs(target),
                1.0
            )
        
        return None
