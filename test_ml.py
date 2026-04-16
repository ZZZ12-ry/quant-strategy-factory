"""
测试 ML 模块
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from src.ml.feature_library import FeatureLibrary
from src.ml.model_trainer import ModelTrainer

print("=" * 60)
print("Testing ML Module")
print("=" * 60)

# 生成数据
np.random.seed(42)
dates = pd.date_range(start="2024-01-01", periods=500, freq='D')
returns = np.random.normal(0.0005, 0.02, 500)
price_series = 4000 * np.cumprod(1 + returns)

data = pd.DataFrame({
    'timestamp': dates,
    'symbol': 'RB.SHF',
    'open': price_series,
    'high': price_series * 1.02,
    'low': price_series * 0.98,
    'close': price_series,
    'volume': np.random.randint(1000, 10000, 500)
})

print("\n[1/3] Feature Calculation...")
feature_lib = FeatureLibrary()
df_features = feature_lib.calculate_all(data)
feature_names = feature_lib.get_feature_names()
print(f"  Features calculated: {len(feature_names)}")
print(f"  Sample features: {feature_names[:5]}")

print("\n[2/3] Creating Labels...")
future_return = df_features['close'].shift(-5) / df_features['close'] - 1
labels = (future_return > 0.02).astype(int)
common_idx = df_features.index.intersection(labels.dropna().index)
X = df_features.loc[common_idx, feature_names]
y = labels.loc[common_idx]
print(f"  Samples: {len(X)}")
print(f"  Positive rate: {y.mean():.2%}")

print("\n[3/3] Training Model...")
train_size = int(len(X) * 0.7)
X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

trainer = ModelTrainer(task_type="binary")
metrics = trainer.train(
    X_train=X_train, y_train=y_train,
    X_test=X_test, y_test=y_test,
    model_type="random_forest",
    n_estimators=100, max_depth=5
)

print(f"  Train Accuracy: {metrics.get('train_accuracy', 0):.4f}")
print(f"  Test Accuracy: {metrics.get('test_accuracy', 0):.4f}")

print("\n  Top 5 Feature Importance:")
importance = trainer.get_feature_importance(top_n=5)
for idx, row in importance.iterrows():
    print(f"    {row['feature']}: {row['importance']:.4f}")

print("\n" + "=" * 60)
print("ML Module Test PASSED!")
print("=" * 60)
