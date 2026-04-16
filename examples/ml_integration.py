"""
ML 深度集成示例 - 端到端 ML 策略
参考：Qlib RD-Agent 自动化流程
"""
import sys
sys.path.insert(0, '..')

import pandas as pd
import numpy as np
from datetime import datetime

from src.ml.feature_library import FeatureLibrary
from src.ml.model_trainer import ModelTrainer
from src.ml.ml_predictor import MLPredictor, MLStrategyMixin
from src.strategy_factory import StrategyFactory
from src.backtest_engine import BacktestEngine


def generate_sample_data(days: int = 500) -> pd.DataFrame:
    """生成模拟数据"""
    np.random.seed(42)
    
    dates = pd.date_range(start="2024-01-01", periods=days, freq='D')
    
    # 几何布朗运动
    initial_price = 4000
    returns = np.random.normal(0.0005, 0.02, days)
    price_series = initial_price * np.cumprod(1 + returns)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'symbol': 'RB.SHF',
        'open': price_series * (1 + np.random.uniform(-0.005, 0.005, days)),
        'high': price_series * (1 + np.random.uniform(0, 0.02, days)),
        'low': price_series * (1 - np.random.uniform(0, 0.02, days)),
        'close': price_series,
        'volume': np.random.randint(1000, 10000, days)
    })
    
    return df


def create_labels(data: pd.DataFrame, horizon: int = 5) -> pd.Series:
    """创建标签：未来 N 天涨跌"""
    future_return = data['close'].shift(-horizon) / data['close'] - 1
    labels = (future_return > 0.02).astype(int)  # 涨超 2% 为 1
    return labels


def main():
    print("=" * 60)
    print("ML 深度集成示例 - 端到端流程")
    print("=" * 60)
    
    # ==================== 1. 数据准备 ====================
    print("\n[1/5] 准备数据...")
    data = generate_sample_data(500)
    print(f"数据量：{len(data)} 条")
    
    # ==================== 2. 因子计算 ====================
    print("\n[2/5] 计算因子 (100+)...")
    feature_lib = FeatureLibrary()
    df_with_features = feature_lib.calculate_all(data)
    
    feature_names = feature_lib.get_feature_names()
    print(f"因子数量：{len(feature_names)}")
    print(f"可用因子：{', '.join(feature_names[:10])}...")
    
    # ==================== 3. 标签创建 ====================
    print("\n[3/5] 创建标签...")
    labels = create_labels(df_with_features, horizon=5)
    
    # 对齐
    common_idx = df_with_features.index.intersection(labels.dropna().index)
    X = df_with_features.loc[common_idx, feature_names]
    y = labels.loc[common_idx]
    
    print(f"样本数量：{len(X)}")
    print(f"正样本比例：{y.mean():.2%}")
    
    # ==================== 4. 模型训练 ====================
    print("\n[4/5] 训练模型...")
    
    # 划分训练集测试集（时间序列）
    train_size = int(len(X) * 0.7)
    X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]
    
    print(f"训练集：{len(X_train)}, 测试集：{len(X_test)}")
    
    # 创建训练器
    trainer = ModelTrainer(task_type="binary")
    
    # 训练随机森林
    print("\n训练随机森林...")
    metrics = trainer.train(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        model_type="random_forest",
        n_estimators=100,
        max_depth=5
    )
    
    print("\n模型表现:")
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")
    
    # 因子重要性
    print("\nTop 10 重要因子:")
    importance = trainer.get_feature_importance(top_n=10)
    for idx, row in importance.iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")
    
    # ==================== 5. ML 策略集成 ====================
    print("\n[5/5] ML 策略回测...")
    
    # 创建预测器
    predictor = MLPredictor(model=trainer.model, feature_names=feature_names)
    
    # 使用 ML 信号增强的简单策略
    class MLEnhancedStrategy:
        """ML 增强策略"""
        
        def __init__(self, predictor: MLPredictor, threshold: float = 0.6):
            self.predictor = predictor
            self.threshold = threshold
            self.history = {'close': [], 'open': [], 'high': [], 'low': [], 'volume': []}
            self.position = None
        
        def on_bar(self, bar: pd.Series):
            # 更新历史
            for key in ['close', 'open', 'high', 'low', 'volume']:
                self.history[key].append(bar[key])
                if len(self.history[key]) > 100:
                    self.history[key] = self.history[key][-100:]
            
            # 获取 ML 预测
            prediction = self.predictor.predict(bar, self.history)
            
            if prediction is None:
                return None
            
            # 根据预测生成信号
            if prediction > self.threshold and self.position is None:
                self.position = 'long'
                return {'action': 'buy', 'price': bar['close']}
            elif prediction < (1 - self.threshold) and self.position == 'long':
                self.position = None
                return {'action': 'sell', 'price': bar['close']}
            
            return None
    
    # 简化回测
    ml_strategy = MLEnhancedStrategy(predictor, threshold=0.55)
    
    # 模拟交易
    trades = []
    cash = 1000000
    position = 0
    
    for idx, bar in df_with_features.iterrows():
        signal = ml_strategy.on_bar(bar)
        
        if signal:
            if signal['action'] == 'buy' and cash > 0:
                position = cash / bar['close']
                cash = 0
                trades.append({'type': 'buy', 'price': bar['close'], 'time': bar['timestamp']})
            
            elif signal['action'] == 'sell' and position > 0:
                cash = position * bar['close']
                trades.append({'type': 'sell', 'price': bar['close'], 'time': bar['timestamp']})
    
    # 计算收益
    if len(trades) >= 2:
        total_return = (cash / 1000000 - 1) * 100
        print(f"\nML 策略回测结果:")
        print(f"  交易次数：{len(trades)}")
        print(f"  总收益：{total_return:.2f}%")
        print(f"  买入次数：{len([t for t in trades if t['type'] == 'buy'])}")
        print(f"  卖出次数：{len([t for t in trades if t['type'] == 'sell'])}")
    
    print("\n" + "=" * 60)
    print("ML 集成完成！")
    print("=" * 60)
    
    # ==================== 6. 保存模型 ====================
    print("\n[可选] 保存模型...")
    trainer.save_model("./ml_model.pkl")
    print("模型已保存到：./ml_model.pkl")


if __name__ == "__main__":
    main()
