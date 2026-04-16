# 量化策略工厂 - 依赖安装指南

## 核心依赖（必需）

```bash
# 基础库
pip install numpy pandas scipy matplotlib

# 数据源
pip install akshare tushare

# 回测引擎
pip install tqdm jinja2 pyyaml
```

---

## 机器学习增强（推荐）

```bash
# scikit-learn（已有）
pip install scikit-learn>=1.0.0

# XGBoost - 梯度提升树
pip install xgboost>=1.5.0

# LightGBM - 轻量级梯度提升机
pip install lightgbm>=3.3.0

# CatBoost - 类别特征处理
pip install catboost>=1.0.0
```

**安装后功能**:
- ✅ 高级梯度提升模型
- ✅ 更好的特征重要性分析
- ✅ 更快的训练速度

---

## 深度学习（可选）

```bash
# PyTorch
pip install torch torchvision

# 或 TensorFlow
pip install tensorflow>=2.8.0

# 优化库
pip install optuna>=3.0.0
```

**安装后功能**:
- ✅ LSTM/GRU/Transformer 模型
- ✅ 自动超参数优化
- ✅ 因子自动挖掘

---

## 技术分析（可选）

```bash
# TA-Lib - 技术指标库
pip install TA-Lib

# 或纯 Python 实现
pip install ta-lib-binary
```

**安装后功能**:
- ✅ 150+ 技术指标
- ✅ 更丰富的因子库

---

## 一键安装所有依赖

```bash
# Windows
pip install numpy pandas scipy matplotlib scikit-learn xgboost lightgbm catboost optuna ta-lib-binary

# Linux/Mac
pip install numpy pandas scipy matplotlib scikit-learn xgboost lightgbm catboost optuna TA-Lib
```

---

## 验证安装

```python
# 测试 XGBoost
import xgboost as xgb
print(f"XGBoost 版本：{xgb.__version__}")

# 测试 LightGBM
import lightgbm as lgb
print(f"LightGBM 版本：{lgb.__version__}")

# 测试 CatBoost
import catboost as cb
print(f"CatBoost 版本：{cb.__version__}")

# 测试 TA-Lib
import talib
print(f"TA-Lib 版本：{talib.__version__}")
```

---

## 当前状态

| 模块 | 状态 | 说明 |
|------|------|------|
| scikit-learn | ✅ 已安装 | 基础 ML 模型 |
| XGBoost | ⚠️ 需安装 | 高级梯度提升 |
| LightGBM | ⚠️ 需安装 | 轻量级梯度提升 |
| CatBoost | ⚠️ 需安装 | 类别特征处理 |
| PyTorch/TensorFlow | ⚠️ 需安装 | 深度学习 |
| TA-Lib | ⚠️ 需安装 | 技术指标 |

---

*更新时间：2026-04-16*
