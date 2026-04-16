# AI 自动量化交易系统 - 完整使用指南

---

## 🎯 系统目标

**实现 AI 自动量化交易** - 从数据获取、模型训练、策略生成到自动交易的完整流程

---

## 📁 项目结构

```
quant-strategy-factory/
├── src/
│   ├── data/                    # 数据模块
│   │   ├── data_fetcher.py      # 数据获取 ⭐ 新增
│   │   └── ...
│   │
│   ├── ai/                      # AI 核心模块 ⭐ 新增
│   │   ├── __init__.py
│   │   ├── ai_trainer.py        # AI 模型训练
│   │   ├── ai_strategy.py       # AI 增强策略
│   │   ├── ai_backtest.py       # AI 回测流程
│   │   └── automation.py        # 自动化运行
│   │
│   ├── ml/                      # ML 基础模块
│   │   ├── feature_library.py   # 67+ 因子库
│   │   ├── model_trainer.py     # 模型训练器
│   │   └── ml_predictor.py      # 预测器
│   │
│   ├── strategies/              # 策略模板 (16 个)
│   ├── backtest_engine.py       # 回测引擎
│   └── ...
│
├── examples/                    # 示例代码
├── models/                      # 模型存储 (自动生成)
├── reports/                     # 报告输出 (自动生成)
└── README_AI.md                 # 本文档
```

---

## 🚀 快速开始

### 方式 1: 一键回测（推荐新手）

```python
from src.ai import run_ai_backtest

# 运行 AI 量化回测
result = run_ai_backtest(
    symbol="000001",        # 平安银行
    start_date="20230101",  # 开始日期
    end_date="20231231",    # 结束日期
    task_type="binary"      # 二分类（涨/跌）
)
```

**输出：**
```
======================================================================
AI 量化自动回测系统
======================================================================
股票代码：000001
回测周期：20230101 ~ 20231231
任务类型：binary
初始资金：1,000,000
======================================================================

【步骤 1/5】获取数据...
  ✅ 获取数据：242 条
     时间范围：2023-01-03 ~ 2023-12-29

【步骤 2/5】训练 AI 模型...
  ✅ 最佳模型：random_forest
     测试集准确率：0.62

【步骤 3/5】创建 AI 策略...
  ✅ AI 策略创建成功

【步骤 4/5】运行回测...
  ✅ 回测完成

【步骤 5/5】生成报告...
  ✅ 报告已保存：./reports/AI_random_forest_20260409.md

======================================================================
回测结果
======================================================================

【基本信息】
  策略名称：AI_random_forest
  回测品种：000001
  回测周期：2023-01-03 ~ 2023-12-29
  初始资金：1,000,000
  最终资金：1,052,340

【业绩指标】
  总收益率：5.23%
  年化收益：5.31%
  夏普比率：0.85
  最大回撤：-3.42%
  卡玛比率：1.55

【交易统计】
  总交易次数：28
  胜率：57.14%
  盈亏比：1.82
  ...
```

---

### 方式 2: 分步执行（推荐进阶）

#### 步骤 1: 获取数据

```python
from src.data.data_fetcher import DataFetcher

fetcher = DataFetcher(source="akshare")
data = fetcher.fetch_stock_data(
    symbol="000001",
    start_date="20230101",
    end_date="20231231"
)

print(f"获取数据：{len(data)} 条")
```

---

#### 步骤 2: 训练 AI 模型

```python
from src.ai import AIModelTrainer

# 创建训练器
trainer = AIModelTrainer(task_type="binary")  # 预测涨跌

# 准备数据
X_train, y_train, X_test, y_test = trainer.prepare_data(data)

# 训练多个模型
model_types = ['random_forest', 'xgboost', 'lightgbm']
trainer.train_models(X_train, y_train, X_test, y_test, model_types)

print(f"最佳模型：{trainer.best_model_type}")
print(f"测试集准确率：{trainer.metrics['test_accuracy']:.4f}")

# 查看特征重要性
importance = trainer.get_feature_importance(top_n=15)
print("\nTop 15 重要特征:")
for idx, row in importance.iterrows():
    print(f"  {row['feature']:25s} {row['importance']:.4f}")

# 保存模型
trainer.save_model("./models/ai_model.pkl")
```

---

#### 步骤 3: 创建 AI 策略

```python
from src.ai import AIStrategy
from src.ml.ml_predictor import MLPredictor

# 创建预测器
ml_predictor = MLPredictor(
    model=trainer.model,
    feature_names=trainer.feature_names
)

# 创建 AI 策略
strategy = AIStrategy(
    ml_predictor=ml_predictor,
    confidence_threshold=0.6,  # 置信度阈值
    stop_loss_pct=0.03,        # 止损 3%
    take_profit_pct=0.05       # 止盈 5%
)
```

---

#### 步骤 4: 运行回测

```python
from src.backtest_engine import BacktestEngine
from src.report_generator import ReportGenerator

# 创建回测引擎
engine = BacktestEngine(
    strategy=strategy,
    initial_cash=1000000,
    commission_rate=0.0003,
    slippage=1.0
)

# 运行回测
result = engine.run(data, "000001")

# 查看结果
print(f"总收益率：{result.total_return:.2f}%")
print(f"夏普比率：{result.sharpe_ratio:.2f}")
print(f"最大回撤：{result.max_drawdown:.2f}%")

# 生成报告
report_gen = ReportGenerator(output_dir="./reports")
report_gen.save_report(result, strategy_name="AI_Strategy", format="markdown")
```

---

### 方式 3: 自动化运行（实盘准备）

```python
from src.ai.automation import AIQuantAutomation

# 创建自动化系统
auto = AIQuantAutomation(
    symbols=["000001", "000002", "600000", "601318"],  # 股票池
    model_path="./models/ai_model.pkl",
    report_dir="./reports/auto"
)

# 运行一次
auto.daily_job()

# 或启动定时任务（每天 15:30 自动执行）
# auto.start_scheduler()
```

---

## 📋 完整示例代码

### 示例 1: 单只股票回测

```python
"""
AI 量化回测示例 - 单只股票
"""
from src.ai import run_ai_backtest

# 运行回测
result = run_ai_backtest(
    symbol="000001",
    start_date="20230101",
    end_date="20231231",
    task_type="binary"
)

# 查看结果
print(f"总收益：{result.total_return:.2f}%")
print(f"夏普比率：{result.sharpe_ratio:.2f}")
```

**运行：**
```bash
python examples/ai_backtest_single.py
```

---

### 示例 2: 多股票对比

```python
"""
AI 量化回测示例 - 多股票对比
"""
from src.ai import AIQuantBacktest

symbols = ["000001", "000002", "600000", "601318"]
results = []

for symbol in symbols:
    print(f"\n回测 {symbol}...")
    
    backtest = AIQuantBacktest(
        symbol=symbol,
        start_date="20230101",
        end_date="20231231",
        task_type="binary"
    )
    
    result = backtest.run(verbose=False)
    
    if result:
        results.append({
            'symbol': symbol,
            'return': result.total_return,
            'sharpe': result.sharpe_ratio,
            'max_dd': result.max_drawdown
        })

# 对比结果
import pandas as pd
df = pd.DataFrame(results)
print("\n" + "="*60)
print("回测结果对比")
print("="*60)
print(df.sort_values('sharpe', ascending=False))
```

**运行：**
```bash
python examples/ai_backtest_multi.py
```

---

### 示例 3: 模型对比分析

```python
"""
AI 模型对比分析
"""
from src.data.data_fetcher import DataFetcher
from src.ai import AIModelTrainer

# 获取数据
fetcher = DataFetcher(source="akshare")
data = fetcher.fetch_stock_data("000001", "20230101", "20231231")

# 训练器
trainer = AIModelTrainer(task_type="binary")
X_train, y_train, X_test, y_test = trainer.prepare_data(data)

# 训练更多模型
model_types = [
    'random_forest',
    'xgboost',
    'lightgbm',
    'gradient_boosting',
    'decision_tree'
]

results = trainer.train_models(X_train, y_train, X_test, y_test, model_types)

# 对比
print("\n模型对比:")
print("-" * 60)
for r in results['all_results']:
    model = r['model_type']
    acc = r['metrics'].get('test_accuracy', 0)
    print(f"{model:20s} 准确率：{acc:.4f}")
```

**运行：**
```bash
python examples/ai_model_comparison.py
```

---

## 🔧 参数调优

### AI 模型参数

```python
# 调整任务类型
trainer = AIModelTrainer(
    task_type="binary",      # binary/multiclass/regression
    horizon=5,               # 预测未来 5 天
    threshold=0.02           # 涨跌幅 2% 阈值
)

# 调整数据划分
X_train, y_train, X_test, y_test = trainer.prepare_data(
    data,
    train_ratio=0.7,  # 训练集 70%
    val_ratio=0.15    # 验证集 15%
)
```

---

### AI 策略参数

```python
strategy = AIStrategy(
    ml_predictor=ml_predictor,
    
    # 核心参数
    confidence_threshold=0.6,   # 置信度阈值 (0.5-0.8)
    use_proba=True,             # 使用概率加权
    
    # 风控参数
    stop_loss_pct=0.03,         # 止损 3%
    take_profit_pct=0.05,       # 止盈 5%
    max_holding_days=20         # 最大持仓 20 天
)
```

---

### 参数优化

```python
from src.optimizer import Optimizer

# 优化 AI 策略参数
optimizer = Optimizer(
    strategy_class=AIStrategy,
    metric="sharpe_ratio"
)

best_params, best_result = optimizer.bayesian_optimize(
    param_bounds={
        "confidence_threshold": (0.5, 0.8),
        "stop_loss_pct": (0.02, 0.05),
        "take_profit_pct": (0.03, 0.10),
        "max_holding_days": (10, 30)
    },
    data=data,
    symbol="000001",
    n_iterations=50
)

print(f"最优参数：{best_params}")
```

---

## 📊 输出说明

### 1. 控制台输出

```
======================================================================
回测结果
======================================================================

【基本信息】
  策略名称：AI_random_forest
  回测品种：000001
  回测周期：2023-01-03 ~ 2023-12-29
  初始资金：1,000,000
  最终资金：1,052,340

【业绩指标】
  总收益率：5.23%
  年化收益：5.31%
  夏普比率：0.85
  最大回撤：-3.42%
  卡玛比率：1.55

【交易统计】
  总交易次数：28
  胜率：57.14%
  盈亏比：1.82
  平均每笔收益：1,869.29
  最长连亏：3 次
```

---

### 2. Markdown 报告

保存在 `./reports/AI_random_forest_YYYYMMDD.md`

```markdown
# 策略回测报告 - AI_random_forest

## 基本信息
| 项目 | 值 |
|------|-----|
| 策略名称 | AI_random_forest |
| 回测品种 | 000001 |
| 回测周期 | 2023-01-03 ~ 2023-12-29 |
| 初始资金 | 1,000,000 |
| 最终资金 | 1,052,340 |

## 业绩指标
| 指标 | 值 |
|------|-----|
| 总收益率 | 5.23% |
| 年化收益 | 5.31% |
| 夏普比率 | 0.85 |
| 最大回撤 | -3.42% |
| 卡玛比率 | 1.55 |

## 交易统计
| 指标 | 值 |
|------|-----|
| 总交易次数 | 28 |
| 胜率 | 57.14% |
| 盈亏比 | 1.82 |
...
```

---

### 3. 特征重要性

```
Top 15 重要特征:
  volatility_10d            0.0595
  volatility_20d            0.0508
  bb_upper                  0.0363
  ma_20                     0.0331
  macd_hist                 0.0303
  rsi_12                    0.0287
  momentum_10               0.0265
  price_vs_ma20             0.0251
  ...
```

---

## ⚠️ 注意事项

### 1. 数据质量

- ✅ 使用前复权数据（qfq）
- ✅ 至少 1 年历史数据
- ✅ 确保数据完整性

### 2. 防止过拟合

- ✅ 使用样本外测试
- ✅ Monte Carlo 压力测试
- ✅ 多只股票验证

### 3. 模型更新

- ✅ 每周重训一次
- ✅ 检测模型漂移
- ✅ 及时淘汰失效模型

### 4. 风险管理

- ✅ 设置止损止盈
- ✅ 控制仓位
- ✅ 分散投资

---

## 🎯 实盘准备

### 步骤 1: 充分回测

```python
# 多股票回测
symbols = ["000001", "000002", "600000", "601318", "000063"]
for symbol in symbols:
    run_ai_backtest(symbol, "20220101", "20231231")
```

---

### 步骤 2: 参数优化

```python
# 优化策略参数
best_params, _ = optimizer.bayesian_optimize(...)
```

---

### 步骤 3: 模拟盘测试

```python
# 自动化运行（模拟）
auto = AIQuantAutomation(symbols=[...])
auto.daily_job()  # 每日生成信号，不实际交易
```

---

### 步骤 4: 小资金实盘

```python
# 小资金测试
backtest = AIQuantBacktest(
    symbol="000001",
    initial_cash=10000  # 1 万元测试
)
```

---

### 步骤 5: 实盘对接（未来）

```python
# 对接券商 API（待实现）
from src.trading.broker_api import BrokerAPI

broker = BrokerAPI(broker="your_broker")
broker.place_order(symbol, direction, volume, price)
```

---

## 📚 常见问题

### Q1: 模型准确率低怎么办？

**A:** 
1. 增加训练数据量
2. 尝试不同模型
3. 调整特征工程
4. 修改预测周期（horizon）

---

### Q2: 回测很好，实盘亏钱？

**A:** 
1. 检查过拟合（Monte Carlo 测试）
2. 考虑交易成本（手续费 + 滑点）
3. 市场风格变化
4. 模型需要重新训练

---

### Q3: 应该选择什么模型？

**A:**
- **Random Forest**: 稳定，不易过拟合，推荐首选
- **XGBoost**: 性能好，需要调参
- **LightGBM**: 速度快，适合大数据
- **LSTM/深度学习**: 需要大量数据，不推荐初期使用

---

### Q4: 多久重训一次模型？

**A:**
- **初期**: 每周一次
- **稳定后**: 每两周或每月
- **市场大幅波动时**: 立即重训

---

## 🚀 下一步

### 阶段 1: 熟悉系统（1 周）
- ✅ 运行示例代码
- ✅ 理解每个模块
- ✅ 调整参数测试

### 阶段 2: 深度优化（2-4 周）
- 扩展因子库
- 尝试更多模型
- 参数优化

### 阶段 3: 模拟盘（1-2 月）
- 每日自动生成信号
- 记录信号表现
- 对比回测 vs 模拟

### 阶段 4: 实盘（3 月+）
- 小资金测试
- 逐步增加资金
- 持续监控优化

---

## 📞 技术支持

如有问题，请查看：
1. 本文档
2. 代码注释
3. 示例代码

---

*最后更新：2026-04-09*  
*版本：AI Quant System v1.0*
