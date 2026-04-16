"""
AI 量化完整示例 - 从数据到回测一站式
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("AI 量化自动交易系统 - 完整示例")
print("=" * 70)

# ==================== 步骤 1: 获取数据 ====================
print("\n【步骤 1】获取数据...")
from src.data.data_fetcher import DataFetcher

fetcher = DataFetcher(source="akshare")
data = fetcher.fetch_stock_data(
    symbol="000001",
    start_date="20230101",
    end_date="20231231"
)

if len(data) == 0:
    print("❌ 数据获取失败，使用模拟数据")
    # 生成模拟数据
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=252, freq='B')
    returns = np.random.normal(0.0005, 0.025, 252)
    price_series = 10 * np.cumprod(1 + returns)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'symbol': '000001',
        'open': price_series * (1 + np.random.uniform(-0.01, 0.01, 252)),
        'high': price_series * (1 + np.random.uniform(0, 0.03, 252)),
        'low': price_series * (1 - np.random.uniform(0, 0.03, 252)),
        'close': price_series,
        'volume': np.random.randint(10000, 1000000, 252)
    })

print(f"  [OK] 数据量：{len(data)} 条")
print(f"  时间范围：{data['timestamp'].min()} ~ {data['timestamp'].max()}")

# ==================== 步骤 2: 训练 AI 模型 ====================
print("\n【步骤 2】训练 AI 模型...")
from src.ai import AIModelTrainer

trainer = AIModelTrainer(task_type="binary", horizon=5)
X_train, y_train, X_test, y_test = trainer.prepare_data(data)

model_types = ['random_forest', 'xgboost', 'lightgbm']
trainer.train_models(X_train, y_train, X_test, y_test, model_types)

print(f"  [OK] 最佳模型：{trainer.best_model_type}")
print(f"     测试集准确率：{trainer.metrics.get('test_accuracy', 0):.4f}")

# 特征重要性
print("\n【特征重要性 Top 10】")
importance = trainer.get_feature_importance(top_n=10)
for idx, row in importance.iterrows():
    print(f"  {row['feature']:25s} {row['importance']:.4f}")

# 保存模型
trainer.save_model("./models/ai_model.pkl")

# ==================== 步骤 3: 创建 AI 策略 ====================
print("\n【步骤 3】创建 AI 策略...")
from src.ai import AIStrategy
from src.ml.ml_predictor import MLPredictor

ml_predictor = MLPredictor(
    model=trainer.model,
    feature_names=trainer.feature_names
)

strategy = AIStrategy(
    ml_predictor=ml_predictor,
    confidence_threshold=0.6,
    stop_loss_pct=0.03,
    take_profit_pct=0.05,
    max_holding_days=20
)

print(f"  ✅ AI 策略创建成功")
print(f"     置信度阈值：0.6")
print(f"     止损：3%")
print(f"     止盈：5%")
print(f"     最大持仓：20 天")

# ==================== 步骤 4: 运行回测 ====================
print("\n【步骤 4】运行回测...")
from src.backtest_engine import BacktestEngine

engine = BacktestEngine(
    strategy=strategy,
    initial_cash=1000000,
    commission_rate=0.0003,
    slippage=1.0
)

result = engine.run(data, "000001")

print(f"  ✅ 回测完成")

# ==================== 步骤 5: 查看结果 ====================
print("\n【步骤 5】回测结果")
print("=" * 70)

print(f"\n【基本信息】")
print(f"  策略名称：AI_{trainer.best_model_type}")
print(f"  回测品种：{result.symbol}")
print(f"  回测周期：{result.start_date[:10]} ~ {result.end_date[:10]}")
print(f"  初始资金：{result.initial_cash:,.0f}")
print(f"  最终资金：{result.final_cash:,.0f}")

print(f"\n【业绩指标】")
print(f"  总收益率：{result.total_return:.2f}%")
print(f"  年化收益：{result.annualized_return:.2f}%")
print(f"  夏普比率：{result.sharpe_ratio:.2f}")
print(f"  最大回撤：{result.max_drawdown:.2f}%")

if result.max_drawdown != 0:
    calmar = result.annualized_return / abs(result.max_drawdown)
    print(f"  卡玛比率：{calmar:.2f}")

print(f"\n【交易统计】")
print(f"  总交易次数：{result.total_trades}")
print(f"  胜率：{result.win_rate:.2f}%")
print(f"  盈亏比：{result.profit_loss_ratio:.2f}")
print(f"  平均每笔收益：{result.avg_trade_return:.2f}")
print(f"  最长连亏：{result.max_consecutive_losses} 次")

# ==================== 步骤 6: 生成报告 ====================
print("\n【步骤 6】生成报告...")
from src.report_generator import ReportGenerator

report_gen = ReportGenerator(output_dir="./reports")
filepath = report_gen.save_report(
    result=result,
    strategy_name=f"AI_{trainer.best_model_type}",
    format="markdown"
)

print(f"  ✅ 报告已保存：{filepath}")

print("\n" + "=" * 70)
print("AI 量化示例完成！")
print("=" * 70)

print("\n【下一步】")
print("1. 查看报告：打开 reports/ 目录")
print("2. 调整参数：修改策略参数重新回测")
print("3. 测试其他股票：修改 symbol 参数")
print("4. 自动化运行：运行 src/ai/automation.py")
print("\n【完整文档】")
print("查看 README_AI.md 获取详细使用指南")
print()
