# 量化策略工厂 - 重大升级总结

## 🎉 完成日期：2026-04-16

本次升级完成了**两大方向**的深化扩展：

---

## ✅ 升级方向 1：深化 ML 能力

### 1.1 因子自动挖掘 ⭐⭐⭐

**文件**: `src/ml/auto_feature_miner.py`

**功能**:
- ✅ **遗传算法因子挖掘** - 通过进化算法自动生成有效因子
- ✅ **Alpha158 风格因子** - 158 个经典 Alpha 因子生成器
- ✅ **IC 评估系统** - Rank IC 自动评估因子有效性
- ✅ **因子表达式生成** - 支持嵌套表达式和算子组合

**核心类**:
```python
AutoFeatureMiner:
  - evolve()              # 进化算法挖掘因子
  - evaluate_feature()    # 评估因子 IC
  - generate_random_feature()  # 随机生成因子表达式

AlphaGenerator:
  - generate_all()        # 生成 Alpha158 因子
  - get_alpha_names()     # 获取因子列表
```

**使用示例**:
```python
from src.ml.auto_feature_miner import AutoFeatureMiner, AlphaGenerator

# 方法 1: Alpha158 因子生成
alpha_gen = AlphaGenerator()
df_with_alphas = alpha_gen.generate_all(data)  # 生成 158 个因子

# 方法 2: 遗传算法挖掘
miner = AutoFeatureMiner()
best_features = miner.evolve(
    data=data,
    population_size=50,
    generations=20,
    mutation_rate=0.2
)
# 输出 Top 20 有效因子
```

---

### 1.2 集成学习 ⭐⭐⭐

**文件**: `src/ml/ensemble_trainer.py`

**功能**:
- ✅ **Stacking 集成** - K 折交叉验证 + 元模型
- ✅ **Blending 集成** - 保留集训练元模型
- ✅ **Voting 集成** - 加权投票/平均投票
- ✅ **模型权重分析** - 自动推导各基模型贡献度

**核心类**:
```python
EnsembleTrainer:
  - add_base_model()      # 添加基模型
  - train_stacking()      # Stacking 训练
  - train_blending()      # Blending 训练
  - train_voting()        # Voting 训练
  - get_model_weights()   # 获取模型权重

StackingClassifier:       # 简化的一键式 Stacking
  - fit()                 # 一键训练
  - predict()             # 预测
```

**支持模型**:
- Random Forest
- Gradient Boosting
- Extra Trees
- SVM
- Logistic Regression
- MLP (神经网络)
- Naive Bayes

**使用示例**:
```python
from src.ml.ensemble_trainer import EnsembleTrainer

ensemble = EnsembleTrainer(task_type="binary")

# 添加基模型
ensemble.add_base_model("rf", RandomForestClassifier(n_estimators=100))
ensemble.add_base_model("gb", GradientBoostingClassifier(n_estimators=100))
ensemble.add_base_model("et", ExtraTreesClassifier(n_estimators=100))

# 训练 Stacking
metrics = ensemble.train_stacking(
    X_train, y_train,
    X_val, y_val,
    n_folds=5,
    meta_model_type="logistic_regression"
)

# 获取模型权重
weights = ensemble.get_model_weights()
# 输出：{'rf': 0.35, 'gb': 0.40, 'et': 0.25}
```

---

### 1.3 深度学习 ⭐⭐⭐

**文件**: `src/ml/deep_learning.py`

**功能**:
- ✅ **LSTM 模型** - 长短期记忆网络
- ✅ **GRU 模型** - 门控循环单元（更快）
- ✅ **Transformer 编码器** - 自注意力机制
- ✅ **双框架支持** - PyTorch 和 TensorFlow
- ✅ **时序数据准备** - 自动创建序列数据

**核心类**:
```python
DeepLearningModel:
  - build_lstm()          # 构建 LSTM
  - build_gru()           # 构建 GRU
  - build_transformer()   # 构建 Transformer
  - prepare_sequences()   # 准备时序数据
  - train()               # 训练模型
  - predict()             # 预测

DeepLearningPredictor:    # 在线预测器
  - update_buffer()       # 更新特征缓冲
  - predict()             # 实时预测
```

**便捷函数**:
```python
create_lstm_model(input_shape, lstm_units=[64, 32], ...)
create_gru_model(input_shape, gru_units=[64, 32], ...)
create_transformer_model(input_shape, d_model=64, n_heads=4, ...)
```

**使用示例**:
```python
from src.ml.deep_learning import create_lstm_model

# 构建 LSTM
model = create_lstm_model(
    input_shape=(60, 10),  # 60 时间步，10 特征
    lstm_units=[64, 32],
    dropout_rate=0.2,
    dense_units=[32]
)

# 准备数据
X_train, y_train, X_test, y_test = model.prepare_sequences(
    data=df,
    target_col='close',
    feature_cols=['ma_5', 'ma_20', 'rsi', ...],
    lookback=60,
    horizon=5
)

# 训练
history = model.train(
    X_train, y_train,
    X_test, y_test,
    epochs=50,
    batch_size=32,
    early_stopping_patience=10
)

# 预测
predictions = model.predict(X_test)
```

---

## ✅ 升级方向 2：扩展策略库

### 2.1 套利策略 ⭐⭐⭐

**文件**: `src/strategies/arbitrage_strategies.py`

**新增策略 (3 个)**:

#### 1. SpotFuturesArbitrage - 期现套利
- **原理**: 期货与现货价差回归
- **参数**: zscore_entry, zscore_exit, lookback_window
- **适用**: 黄金、白银、铜、螺纹钢等有现货的期货

#### 2. CalendarSpreadArbitrage - 跨期套利
- **原理**: 近月与远月合约价差回归
- **参数**: near_month, far_month, zscore_entry
- **适用**: 期货近远月合约

#### 3. CrossSectionalMomentum - 横截面动量
- **原理**: 做多强势品种，做空弱势品种
- **参数**: momentum_period, top_n, bottom_n
- **适用**: 多品种组合轮动

**使用示例**:
```python
from src.strategy_factory import StrategyFactory

factory = StrategyFactory()

# 期现套利
strategy = factory.create("SpotFuturesArbitrage", 
                         zscore_entry=2.0,
                         zscore_exit=0.5)

# 跨期套利
strategy = factory.create("CalendarSpreadArbitrage",
                         near_month=1,
                         far_month=2)

# 横截面动量
strategy = factory.create("CrossSectionalMomentum",
                         momentum_period=20,
                         top_n=3,
                         bottom_n=3)
```

---

### 2.2 多因子策略 ⭐⭐

**文件**: `src/strategies/multifactor_strategy.py`

**新增策略 (2 个)**:

#### 1. MultiFactorStrategy - 多因子策略
- **原理**: 综合价值、动量、质量、波动率、规模因子
- **因子类型**:
  - Momentum: 价格动量、RSI
  - Value: 布林带位置、Z-Score
  - Quality: 均线关系、趋势强度
  - Volatility: ATR、波动率
  - Size: 成交量规模
- **适用**: 多品种组合 / 股票池

#### 2. FactorTimingStrategy - 因子择时
- **原理**: 动态调整因子权重
- **机制**: 根据因子历史表现调整权重
- **适用**: 多因子策略增强

**使用示例**:
```python
# 多因子策略
strategy = factory.create("MultiFactor",
                         factor_weights={
                             'momentum': 0.3,
                             'value': 0.2,
                             'quality': 0.2,
                             'volatility': 0.15,
                             'size': 0.15
                         },
                         rebalance_period=5)

# 因子择时
strategy = factory.create("FactorTiming",
                         base_weights={
                             'momentum': 0.25,
                             'value': 0.25,
                             'quality': 0.25,
                             'volatility': 0.25
                         })
```

---

### 2.3 强化学习策略 ⭐⭐⭐

**文件**: `src/strategies/rl_strategy.py`

**新增策略 (2 个)**:

#### 1. RLTradingStrategy - DQN 交易策略
- **原理**: 深度 Q 网络学习最优交易策略
- **状态**: 价格、指标、持仓
- **动作**: 买入/卖出/持有
- **算法**: DQN + 经验回放 + 目标网络
- **适用**: 单品种趋势交易

#### 2. PPOStrategy - PPO 仓位管理
- **原理**: 近端策略优化学习连续仓位
- **输出**: 持仓比例（-1 到 1）
- **适用**: 仓位管理 / 资产配置

**使用示例**:
```python
# DQN 策略
strategy = factory.create("RLTrading",
                         lookback_window=30,
                         training_episodes=1000,
                         gamma=0.99,
                         learning_rate=0.001)

# 离线训练
strategy.train_offline(data, episodes=1000)

# PPO 策略
strategy = factory.create("PPO",
                         max_position=1.0,
                         clip_epsilon=0.2,
                         learning_rate=0.0003)
```

---

## 📊 策略库总览

### 策略分类（23 个）

| 类别 | 数量 | 策略名称 |
|------|------|---------|
| **趋势跟踪** | 6 | DualMA, TurtleTrader, ChannelBreakout, MACDTrend, AroonTrend, ADXTrend |
| **均值回归** | 3 | BollingerMR, RSIMR, MeanReversion |
| **震荡策略** | 3 | KDJ, AwesomeOsc, Stochastic |
| **突破策略** | 2 | DualThrust, VolatilityBreakout |
| **动量策略** | 1 | MomentumRank |
| **形态识别** | 1 | PatternRecognition |
| **套利策略** ⭐ | 3 | SpotFuturesArbitrage, CalendarSpreadArbitrage, CrossSectionalMomentum |
| **多因子策略** ⭐ | 2 | MultiFactor, FactorTiming |
| **强化学习** ⭐ | 2 | RLTrading, PPO |
| **总计** | **23** | - |

---

## 📁 新增文件清单

### ML 模块（深化）
```
src/ml/
├── auto_feature_miner.py    ⭐ 新增 - 因子自动挖掘
├── ensemble_trainer.py       ⭐ 新增 - 集成学习
├── deep_learning.py          ⭐ 新增 - 深度学习
├── __init__.py               更新 - 导出新增模块
```

### 策略模块（扩展）
```
src/strategies/
├── arbitrage_strategies.py   ⭐ 新增 - 套利策略 (3 个)
├── multifactor_strategy.py   ⭐ 新增 - 多因子策略 (2 个)
├── rl_strategy.py            ⭐ 新增 - 强化学习策略 (2 个)
├── __init__.py               更新 - 导出新增策略
```

### 示例代码
```
examples/
├── advanced_ml_demo.py       ⭐ 新增 - 深度学习与 RL 演示
```

### 配置文件
```
requirements.txt              更新 - 添加深度学习依赖
src/strategy_factory.py       更新 - 注册 7 个新策略
```

---

## 🚀 快速开始

### 安装依赖

```bash
cd quant-strategy-factory

# 核心依赖
pip install -r requirements.txt

# 深度学习（可选）
pip install torch  # 或
pip install tensorflow

# 集成学习增强（可选）
pip install xgboost lightgbm
```

### 运行示例

```bash
# 深度学习与强化学习演示
python examples/advanced_ml_demo.py

# 因子自动挖掘演示
python examples/ml_factor_mining.py

# 集成学习演示
python examples/ml_integration.py
```

### Python API

```python
from src.strategy_factory import StrategyFactory
from src.ml.auto_feature_miner import AutoFeatureMiner
from src.ml.deep_learning import create_lstm_model
from src.ml.ensemble_trainer import StackingClassifier

# 1. 因子挖掘
miner = AutoFeatureMiner()
best_features = miner.evolve(data, generations=20)

# 2. 深度学习
model = create_lstm_model(input_shape=(60, 10))
model.train(X_train, y_train, X_test, y_test)

# 3. 集成学习
clf = StackingClassifier()
clf.fit(X_train, y_train, X_test, y_test)

# 4. 新策略
factory = StrategyFactory()
strategy = factory.create("RLTrading")
strategy = factory.create("MultiFactor")
strategy = factory.create("SpotFuturesArbitrage")
```

---

## 📈 功能对比

| 功能模块 | 升级前 | 升级后 | 提升 |
|---------|--------|--------|------|
| **策略模板** | 16 个 | **23 个** | +44% |
| **ML 因子** | 67 个 | **225+ 个** | +236% |
| **ML 模型** | 基础 ML | **深度学习 + 集成学习** | 质的飞跃 |
| **策略类型** | 传统技术指标 | **套利/多因子/RL** | 全面扩展 |

---

## 🎯 核心价值

### 1. 因子自动挖掘
- **传统方式**: 手动设计因子，耗时耗力
- **现在**: 遗传算法自动挖掘，发现人类想不到的因子组合

### 2. 集成学习
- **传统方式**: 单一模型，容易过拟合
- **现在**: Stacking/Blending/Voting，多模型融合，稳健性提升

### 3. 深度学习
- **传统方式**: 线性模型，无法捕捉复杂模式
- **现在**: LSTM/Transformer，捕捉时序依赖和非线性关系

### 4. 强化学习
- **传统方式**: 固定规则，无法适应市场变化
- **现在**: RL 自主学习，动态优化交易策略

### 5. 套利策略
- **传统方式**: 单向投机，风险较高
- **现在**: 市场中性套利，低风险稳定收益

---

## ⏭️ 后续可选方向

### 1. Web Dashboard
- FastAPI 后端 + Vue3 前端
- 交互式回测界面
- 实时训练进度可视化

### 2. 实盘对接
- 期货公司 API 对接
- 实盘风控系统
- 订单管理

### 3. 更多策略
- 增加到 30-50 个策略
- 套利策略扩展（跨市场/跨资产）
- 深度学习策略（Transformer 直接交易）

### 4. 因子库扩展
- Alpha360 完整实现
- 另类数据因子（舆情/新闻）
- 基本面因子（财务数据）

---

## 💡 使用建议

### 新手入门
1. 从经典策略开始（DualMA, TurtleTrader）
2. 使用 Akshare 免费数据回测
3. 参数优化 + Monte Carlo 测试

### 进阶使用
1. 因子自动挖掘发现新因子
2. 集成学习提升预测稳健性
3. 多因子策略构建组合

### 高级应用
1. 深度学习捕捉非线性模式
2. 强化学习动态优化策略
3. 套利策略降低风险

---

## 📝 注意事项

1. **深度学习需要 GPU** - 建议安装 CUDA 版本 PyTorch/TensorFlow
2. **RL 训练时间长** - 建议离线训练，在线推理
3. **套利策略需要真实价差数据** - 模拟数据效果有限
4. **过拟合风险** - 所有策略都需要 Monte Carlo 测试

---

*升级完成日期：2026-04-16*  
*策略数量：23 个*  
*ML 因子：225+ 个*  
*深度学习：LSTM/GRU/Transformer*  
*强化学习：DQN/PPO*  
*集成学习：Stacking/Blending/Voting*
