# ML/DL 深化功能文档

## 概述

量化策略工厂 ML/DL 深化方向已完成，新增三大核心功能：

1. **自动特征选择器** - 7 种特征选择方法
2. **模型 IC 评估器** - 专业量化模型评估
3. **完整 ML 工作流** - 从数据到交易信号

---

## 新增文件

| 文件 | 说明 | 行数 |
|------|------|------|
| `src/ml/auto_feature_selector.py` | 自动特征选择器 | ~450 行 |
| `src/ml/model_ic_evaluator.py` | IC 评估器 | ~250 行 |
| `examples/advanced_ml_workflow.py` | 完整工作流演示 | ~260 行 |
| `docs/ML_DL_DEEPENING.md` | 本文档 | - |

---

## 功能 1: 自动特征选择器

### 支持方法

#### 过滤法 (Filter Methods)
- **方差过滤** - 移除低方差特征
- **相关性过滤** - 移除高相关特征（多重共线性）
- **互信息过滤** - 基于信息论的特征选择

#### 包裹法 (Wrapper Methods)
- **RFE 递归特征消除** - 迭代移除最不重要特征

#### 嵌入法 (Embedded Methods)
- **L1 正则化** - 基于 Logistic Regression 的稀疏特征选择
- **树模型重要性** - XGBoost/LightGBM/RandomForest 特征重要性

#### 高级方法
- **遗传算法** - 进化优化特征子集

### 使用示例

```python
from src.ml.auto_feature_selector import AutoFeatureSelector

# 创建选择器
selector = AutoFeatureSelector(target_col='target')

# 方法 1: 单一方法
selected = selector.filter_variance(X, threshold=0.01)
selected = selector.filter_correlation(X, threshold=0.95)
selected = selector.embedded_tree_importance(X, y, model_type='xgboost')

# 方法 2: 顺序组合（推荐）
selected = selector.sequential_selection(
    X, y,
    method='variance+correlation+tree',  # 方差→相关性→树模型
    variance_threshold=0.01,
    correlation_threshold=0.95,
    tree_threshold=0.02
)

# 方法 3: 遗传算法（计算密集）
selected = selector.genetic_feature_selection(
    X, y,
    n_generations=10,
    population_size=20
)

# 计算特征 IC
ic_df = selector.calc_ic(X[selected], y)
```

### 输出示例

```
============================================================
顺序特征选择：variance+correlation+tree
============================================================

步骤 1/3: variance
----------------------------------------
[方差过滤] 原始特征：67, 保留：65, 移除：2

步骤 2/3: correlation
----------------------------------------
[相关性过滤] 原始特征：65, 保留：52, 移除：13

步骤 3/3: tree
----------------------------------------
[树模型重要性] 原始特征：52, 保留：28, 移除：24

============================================================
最终保留特征数：28/67
============================================================
```

---

## 功能 2: 模型 IC 评估器

### IC 指标说明

| 指标 | 说明 | 评估标准 |
|------|------|---------|
| **IC** | Pearson 相关系数 | > 0.1 强，> 0.05 中，< 0.05 弱 |
| **Rank IC** | Spearman 秩相关 | 更稳健，抗异常值 |
| **ICIR** | IC / IC 标准差 | > 0.5 优秀，> 0.2 可用 |
| **方向准确率** | 预测方向正确率 | > 55% 可用 |

### 分层回测

按预测值分位数分组（如 5 组），测试：
- 每组平均收益
- 多空收益（做多前 20%，做空后 20%）
- 累计收益曲线

### 使用示例

```python
from src.ml.model_ic_evaluator import ModelICEvaluator

# 创建评估器
evaluator = ModelICEvaluator()

# 基础 IC 评估
results = evaluator.evaluate(
    y_pred=y_proba,      # 预测概率
    y_true=y_true,       # 真实标签
    df_full=df,          # 完整 DataFrame
    pred_col='pred',
    return_col='return'
)

# 滚动 IC 时间序列
ic_ts = evaluator.calc_ic_time_series(
    df['pred'], df['return'],
    periods=20  # 20 日滚动
)

# 分层回测
stratified = evaluator.stratified_backtest(
    df,
    pred_col='pred',
    return_col='return',
    n_groups=5
)

# 生成报告
print(evaluator.report())
```

### 报告示例

```
============================================================
模型 IC 评估报告
============================================================

IC 统计:
  平均 IC: 0.0823
  IC 标准差：0.0312
  ICIR: 2.64
  
Rank IC 统计:
  平均 Rank IC: 0.0756
  Rank IC 标准差：0.0298
  Rank ICIR: 2.54

T 统计量：3.87

评估标准:
  ICIR > 0.5: ✅ 优秀
  ICIR > 0.2: ⚠️ 可用
  ICIR < 0.2: ❌ 需改进

============================================================
```

---

## 功能 3: 完整 ML 工作流

### 流程步骤

```
1. 数据准备 → 2. 特征工程 → 3. 特征选择 → 
4. 模型训练 → 5. IC 评估 → 6. 生成信号
```

### 运行演示

```bash
cd quant-strategy-factory
python examples/advanced_ml_workflow.py
```

### 输出内容

1. **数据概览** - 样本数、日期范围
2. **特征统计** - 特征数量、示例
3. **特征选择** - 筛选过程、IC 分析
4. **模型对比** - XGBoost/LightGBM/CatBoost AUC 对比
5. **IC 评估** - IC/Rank IC/ICIR/分层回测
6. **交易信号** - 信号统计、累计收益

### 关键指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 特征筛选率 | 30-50% | 保留核心特征 |
| 验证集 AUC | > 0.55 | 模型预测能力 |
| IC | > 0.05 | 预测与真实相关性 |
| ICIR | > 0.5 | 稳定性 |
| 策略超额 | > 0.02% | 信号日超额收益 |

---

## 集成到策略

### 多因子策略增强

```python
from src.ml.auto_feature_selector import AutoFeatureSelector
from src.ml.model_ic_evaluator import ModelICEvaluator
from src.strategies.multifactor_strategy_v2 import MultiFactorStrategyV2

# 1. 特征选择
selector = AutoFeatureSelector()
selected_factors = selector.sequential_selection(X, y, method='variance+correlation+tree')

# 2. 训练模型
from src.ml.advanced_models import AdvancedMLModels
adv = AdvancedMLModels()
adv.create_xgboost(n_estimators=100, max_depth=5)
adv.train(X[selected_factors], y, X_val, y_val)

# 3. IC 验证
evaluator = ModelICEvaluator()
y_pred = adv.predict_proba(X_test)[:, 1]
evaluator.evaluate(y_pred, y_test, df_test)

# 4. 整合到多因子策略
strategy = MultiFactorStrategyV2(
    factor_weights={f: 1.0/len(selected_factors) for f in selected_factors}
)
```

### ML 策略信号

```python
# 使用 ML 模型生成交易信号
signal_strength = y_proba[0]  # 预测概率

if signal_strength > 0.6:
    # 强做多信号
    action = 'long'
elif signal_strength < 0.4:
    # 强做空信号
    action = 'short'
else:
    # 观望
    action = 'hold'
```

---

## 性能基准

### 测试环境
- CPU: Intel i7 / AMD Ryzen 7
- 内存：16GB
- 数据：500 交易日，67 特征

### 运行时间

| 步骤 | 耗时 |
|------|------|
| 特征工程 | ~2 秒 |
| 特征选择（顺序法） | ~5 秒 |
| 特征选择（遗传算法） | ~30 秒 |
| 模型训练（XGBoost） | ~3 秒 |
| IC 评估 | ~1 秒 |
| **总计** | **~10-40 秒** |

### 内存占用
- 峰值：~500MB
- 平均：~200MB

---

## 最佳实践

### 1. 特征选择建议

**推荐流程**:
```
方差过滤 (0.01) → 相关性过滤 (0.95) → 树模型重要性 (0.02)
```

**理由**:
- 方差过滤快速移除无效特征
- 相关性过滤避免多重共线性
- 树模型重要性捕捉非线性关系

### 2. IC 评估标准

| 指标 | 优秀 | 可用 | 需改进 |
|------|------|------|--------|
| IC | > 0.1 | 0.05-0.1 | < 0.05 |
| Rank IC | > 0.1 | 0.05-0.1 | < 0.05 |
| ICIR | > 0.5 | 0.2-0.5 | < 0.2 |
| 方向准确率 | > 60% | 55-60% | < 55% |

### 3. 避免过拟合

- 使用样本外验证
- 检查 IC 稳定性（滚动 IC）
- 特征数 < 样本数/10
- 使用交叉验证

---

## 下一步深化方向

### 已完成 ✅
- [x] 自动特征选择器（7 种方法）
- [x] 模型 IC 评估器
- [x] 完整 ML 工作流
- [x] XGBoost/LightGBM/CatBoost 集成

### 计划中 🔄
- [ ] TA-Lib 集成（技术指标库）
- [ ] 图神经网络（GNN）- 品种关联
- [ ] Attention 机制 - 时序重要性
- [ ] 元学习 - 快速适应新市场
- [ ] AutoML - 全自动特征 + 模型选择

---

## API 参考

### AutoFeatureSelector

```python
class AutoFeatureSelector:
    def filter_variance(X, threshold=0.01) -> List[str]
    def filter_correlation(X, threshold=0.95) -> List[str]
    def filter_mutual_info(X, y, threshold=0.01) -> List[str]
    def wrapper_rfe(X, y, model, n_features=20) -> List[str]
    def embedded_l1(X, y, C=1.0) -> List[str]
    def embedded_tree_importance(X, y, model_type='xgboost') -> List[str]
    def sequential_selection(X, y, method='variance+correlation+tree') -> List[str]
    def genetic_feature_selection(X, y, n_generations=10) -> List[str]
    def calc_ic(X, y) -> pd.DataFrame
```

### ModelICEvaluator

```python
class ModelICEvaluator:
    def calc_ic(y_pred, y_true) -> Dict[str, float]
    def calc_ic_time_series(pred, true, periods=20) -> pd.DataFrame
    def stratified_backtest(df, pred_col, return_col, n_groups=5) -> pd.DataFrame
    def evaluate(y_pred, y_true, df_full) -> Dict
    def report() -> str
```

---

## 常见问题

### Q1: 特征选择后 IC 反而下降？
**A**: 可能原因：
- 移除了重要但高相关的特征
- 树模型阈值设置过高
- 建议尝试不同方法组合

### Q2: IC 很高但实盘亏损？
**A**: 可能原因：
- 过拟合训练数据
- 未考虑交易成本
- 样本外验证不足
- 建议增加滚动回测和成本模拟

### Q3: 遗传算法太慢？
**A**: 优化建议：
- 减少种群大小（20→10）
- 减少迭代代数（10→5）
- 使用更简单的模型（depth=3）
- 改用顺序选择法

---

*最后更新：2026-04-17*  
*版本：v1.1 (ML/DL 深化完成)*  
*状态：功能完整，可投入使用*
