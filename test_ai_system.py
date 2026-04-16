"""
AI 量化系统 - 快速测试脚本
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("AI 量化系统 - 快速测试")
print("=" * 60)

# 测试 1: 数据获取
print("\n[测试 1] 数据获取...")
from src.data.data_fetcher import DataFetcher
fetcher = DataFetcher(source="akshare")
data = fetcher.fetch_stock_data("000001", "20230101", "20231231")
print(f"  数据量：{len(data)} 条")
print(f"  时间范围：{data['timestamp'].min()} ~ {data['timestamp'].max()}")

# 测试 2: AI 模型训练
print("\n[测试 2] AI 模型训练...")
from src.ai import AIModelTrainer

trainer = AIModelTrainer(task_type="binary")
X_train, y_train, X_test, y_test = trainer.prepare_data(data)

model_types = ['random_forest']
trainer.train_models(X_train, y_train, X_test, y_test, model_types)

print(f"  最佳模型：{trainer.best_model_type}")
print(f"  测试准确率：{trainer.metrics.get('test_accuracy', 0):.4f}")

# 特征重要性
importance = trainer.get_feature_importance(top_n=5)
print(f"  Top 特征：{importance.iloc[0]['feature']}")

# 保存模型
trainer.save_model("./models/ai_model_test.pkl")
print(f"  模型已保存")

# 测试 3: 策略创建
print("\n[测试 3] AI 策略创建...")
from src.ai import AIStrategy
from src.ml.ml_predictor import MLPredictor

ml_predictor = MLPredictor(
    model=trainer.model,
    feature_names=trainer.feature_names
)

strategy = AIStrategy(
    ml_predictor=ml_predictor,
    confidence_threshold=0.55
)

print(f"  AI 策略创建成功")

# 测试 4: 回测
print("\n[测试 4] 回测运行...")
from src.backtest_engine import BacktestEngine

engine = BacktestEngine(
    strategy=strategy,
    initial_cash=1000000,
    commission_rate=0.0003
)

result = engine.run(data, "000001")

print(f"  回测完成")
print(f"  总收益：{result.total_return:.2f}%")
print(f"  夏普比率：{result.sharpe_ratio:.2f}")
print(f"  最大回撤：{result.max_drawdown:.2f}%")

# 测试 5: 报告生成
print("\n[测试 5] 报告生成...")
from src.report_generator import ReportGenerator

report_gen = ReportGenerator(output_dir="./reports/test")
filepath = report_gen.save_report(result, "AI_Test", format="markdown")
print(f"  报告已保存：{filepath}")

print("\n" + "=" * 60)
print("所有测试完成!")
print("=" * 60)
print("\n系统状态:")
print("  [OK] 数据获取模块")
print("  [OK] AI 模型训练")
print("  [OK] AI 策略")
print("  [OK] 回测引擎")
print("  [OK] 报告生成")
print("\nAI 量化系统已就绪!")
