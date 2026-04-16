# 量化策略工厂 (Quant Strategy Factory)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Strategies](https://img.shields.io/badge/strategies-24-green.svg)](docs/STRATEGY_LIST.md)
[![Factors](https://img.shields.io/badge/factors-130+-orange.svg)](docs/USER_GUIDE.md)

> **从策略创意到回测验证，只需 10 分钟**  
> 一个完整的量化策略研发基础设施

---

## 📖 项目简介

**量化策略工厂**是一个专业的量化交易策略研发平台，帮助量化研究员和交易者：

- ✅ **快速验证策略创意** - 从代码到回测结果，10 分钟内完成
- ✅ **复用成熟策略模板** - 24 个经典策略，开箱即用
- ✅ **AI 增强** - 机器学习 + 深度学习 + 因子自动挖掘
- ✅ **专业风控** - 多层次止损 + 仓位管理 + 风险预警
- ✅ **真实回测** - 手续费 + 滑点 + 冲击成本
- ✅ **模拟交易** - 期货仿真账户 + 实时信号验证

**你不是在重复造轮子，而是在组装轮子。**

---

## 🎯 核心特性

### 1. 策略库 (24 个策略模板)

| 类别 | 策略数 | 代表策略 |
|------|--------|---------|
| **趋势跟踪** | 6 | 双均线、海龟交易、通道突破 |
| **均值回归** | 3 | 布林带回归、RSI 回归 |
| **震荡策略** | 3 | KDJ 震荡、Awesome 震荡 |
| **突破策略** | 2 | Dual Thrust、波动率突破 |
| **套利策略** | 3 | 期现套利、跨期套利、配对交易 |
| **多因子策略** | 2 | Barra 多因子、因子择时 |
| **ML/DL 策略** | 3 | XGBoost、LSTM、强化学习 |
| **成交量策略** | 2 | 成交量昼夜效应 |

### 2. 因子库 (130+ 因子)

```python
# Barra 风格因子 (63 个)
- Momentum (动量) - 10 个因子
- Volatility (波动率) - 10 个因子
- Liquidity (流动性) - 10 个因子
- Value (价值) - 5 个因子
- Quality (质量) - 5 个因子
- Size (规模) - 5 个因子
- ... (共 10 大类别)

# 技术指标因子 (67 个)
- MA/EMA 均线系统
- MACD/RSI/KDJ指标
- 布林带/ATR波动率
- 成交量相关指标
```

### 3. AI 增强

- ✅ **机器学习** - XGBoost/LightGBM/CatBoost
- ✅ **深度学习** - LSTM/GRU/Transformer
- ✅ **集成学习** - Stacking/Blending/Voting
- ✅ **因子挖掘** - 遗传算法自动发现因子
- ✅ **自动调参** - 贝叶斯优化

### 4. 风控系统

```python
# 仓位管理
max_single_position = 30%    # 单策略最大仓位
max_total_position = 80%     # 总仓位上限
min_cash_ratio = 20%         # 最小现金比例

# 止损限制
max_daily_loss = 5%          # 单日最大亏损
max_drawdown = 20%           # 最大回撤
stop_loss_per_trade = 3%     # 单笔止损

# 风险等级
LOW → MEDIUM → HIGH → EXTREME (强制平仓)
```

### 5. 真实回测

- ✅ 手续费（万三）
- ✅ 滑点（千一）
- ✅ 冲击成本（大单加倍）
- ✅ 真实成交模拟
- ✅ 详细交易记录

### 6. 样本外验证

- ✅ 训练集/验证集/测试集分割
- ✅ 滚动回测（Walk Forward）
- ✅ 参数稳定性检验
- ✅ 过拟合检测

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆仓库
git clone https://github.com/ZZZ12-ry/quant-strategy-factory.git
cd quant-strategy-factory

# 安装核心依赖
pip install -r requirements.txt

# 安装机器学习（可选）
pip install xgboost lightgbm catboost

# 安装深度学习（可选）
pip install torch torchvision
```

### 2. 一键演示

```bash
# 运行完整演示流程
python run_full_demo.py
```

**演示内容包括**:
1. 获取历史数据（带缓存）
2. 批量回测（多品种）
3. 样本外验证
4. 模拟盘测试
5. 生成报告

### 3. 查看报告

```bash
# 回测报告
open reports/backtest_report.html

# 模拟盘报告
open reports/simulated_trading_report.json
```

---

## 💻 使用示例

### 示例 1: 简单回测

```python
from src.strategy_factory import StrategyFactory
from src.backtest.realistic_backtester import RealisticBacktester, TradingCosts

# 创建策略
factory = StrategyFactory()
strategy = factory.create("DualMA", fast_ma=10, slow_ma=30)

# 创建回测器
backtester = RealisticBacktester(
    initial_capital=1000000,
    trading_costs=TradingCosts(
        commission=0.0003,  # 万三
        slippage=0.001,     # 千一
        impact_cost=0.0005  # 万分五
    )
)

# 获取数据
import akshare as ak
df = ak.futures_zh_daily_sina(symbol="RB2405")

# 运行回测
for idx, row in df.iterrows():
    signal = strategy.on_bar(row)
    if signal:
        if signal.direction in ['long', 'short']:
            backtester.execute_buy(signal.price, signal.volume)
        else:
            backtester.execute_sell(signal.price, signal.volume)

# 查看绩效
metrics = backtester.get_performance_metrics()
print(f"总收益：{metrics['total_return']:.2f}%")
print(f"夏普比率：{metrics['sharpe']:.2f}")
print(f"最大回撤：{metrics['max_drawdown']:.2f}%")
```

### 示例 2: 多因子策略

```python
from src.strategies.multifactor_strategy_v2 import MultiFactorStrategyV2

# 创建策略
strategy = MultiFactorStrategyV2(
    factor_weights={
        'Momentum': 0.15,
        'Volatility': 0.10,
        'Liquidity': 0.15,
        'Quality': 0.15,
        'Value': 0.10,
    },
    rebalance_period=5  # 5 日调仓
)

# 运行策略
for idx, row in df.iterrows():
    signal = strategy.on_bar(row)
    if signal:
        print(f"{signal.timestamp}: {signal.direction} @ {signal.price}")
```

### 示例 3: 风控管理

```python
from src.risk.risk_manager import RiskManager, PositionLimits, LossLimits

# 创建风控管理器
risk_mgr = RiskManager(
    initial_capital=1000000,
    position_limits=PositionLimits(
        max_single_position=0.30,
        max_total_position=0.80
    ),
    loss_limits=LossLimits(
        max_daily_loss=0.05,
        max_drawdown=0.20
    )
)

# 下单前检查
if risk_mgr.check_position_limit(200000):
    # 允许开仓
    position = risk_mgr.get_allowed_position(signal_strength=0.8)
    print(f"允许仓位：{position:,.0f}")

# 检查是否强平
if risk_mgr.should_close_all():
    print("风控警告：强制平仓")
```

### 示例 4: 模拟交易

```python
from src.trading.simulated_account import SimulatedTradingAccount, OrderType, OrderSide

# 创建模拟账户
account = SimulatedTradingAccount(initial_capital=1000000)

# 买入开仓
order = account.submit_order(
    symbol='RB2405',
    side=OrderSide.BUY,
    volume=10,
    order_type=OrderType.MARKET
)
account.execute_order(order, market_price=4000)

# 更新行情
account.update_market_price('RB2405', 4100)

# 平多仓
order2 = account.submit_order(
    symbol='RB2405',
    side=OrderSide.CLOSE_LONG,
    volume=10
)
account.execute_order(order2, market_price=4100)

# 查看账户
summary = account.get_account_summary()
print(f"权益：{summary['equity']:,.0f}")
print(f"收益：{summary['total_return']:.2f}%")
```

---

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| [使用指南](docs/USER_GUIDE.md) | 完整使用教程 |
| [策略列表](docs/STRATEGY_LIST.md) | 24 个策略详解 |
| [安装指南](docs/INSTALL_GUIDE.md) | 依赖安装说明 |
| [因子库文档](docs/ML_MULTIFACTOR_PROGRESS.md) | 130+ 因子说明 |
| [风控系统](docs/RISK_BACKTEST_SUMMARY.md) | 风控规则详解 |
| [模拟盘指南](docs/DATA_SIMULATION_SUMMARY.md) | 模拟交易教程 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────┐
│              数据层                          │
│  - 历史数据获取 (AKShare/Tushare)           │
│  - 数据缓存 (避免重复获取)                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              策略层                          │
│  - 24 个策略模板                              │
│  - 多因子策略 (Barra)                        │
│  - ML/DL策略 (XGBoost/LSTM)                 │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              风控层                          │
│  - 仓位管理                                 │
│  - 止损监控                                 │
│  - 风险预警 (4 级)                           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              交易层                          │
│  - 模拟账户                                 │
│  - 订单管理                                 │
│  - 持仓管理                                 │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              验证层                          │
│  - 真实回测 (含成本)                         │
│  - 样本外验证 (滚动回测)                     │
│  - 过拟合检测                               │
└─────────────────────────────────────────────┘
```

---

## 📊 代码统计

| 指标 | 数量 |
|------|------|
| **文件数** | 113 |
| **代码行数** | 26,000+ |
| **策略数** | 24 |
| **因子数** | 130+ |
| **文档数** | 15+ |
| **示例数** | 10+ |

---

## ⚠️ 重要声明

### 学习用途

**本项目仅供学习和研究使用**

- ✅ 学习量化策略开发方法
- ✅ 理解因子/ML/套利逻辑
- ✅ 模拟盘验证策略
- ❌ **不建议直接实盘交易**

### 风险提示

1. **回测≠实盘**
   - 回测收益≠实盘收益
   - 成本估算是理想的
   - 实盘有心理因素

2. **需要验证流程**
   ```
   回测 → 样本外验证 → 模拟盘 (3-6 月) → 小资金实盘 (1-5 万)
   ```

3. **做好亏损准备**
   - 量化交易有风险
   - 可能亏光本金
   - 持续学习是关键

---

## 🎯 开发路线图

### 已完成 (v1.0)

- ✅ 24 个策略模板
- ✅ 130+ 因子库
- ✅ ML/DL集成
- ✅ 风控系统
- ✅ 真实回测
- ✅ 样本外验证
- ✅ 模拟账户

### 计划中 (v2.0)

- ⏳ 更多历史数据 (3-5 年)
- ⏳ 实时行情接入
- ⏳ 实盘接口（谨慎）
- ⏳ Web 界面
- ⏳ 策略优化器

---

## 🤝 贡献指南

欢迎贡献代码、报告问题、提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 📞 联系方式

- **GitHub**: [@ZZZ12-ry](https://github.com/ZZZ12-ry)
- **Issues**: [问题反馈](https://github.com/ZZZ12-ry/quant-strategy-factory/issues)
- **Discussions**: [讨论区](https://github.com/ZZZ12-ry/quant-strategy-factory/discussions)

---

## 🙏 致谢

感谢以下开源项目：

- [AKShare](https://akshare.akfamily.xyz) - 财经数据接口
- [Tushare](https://tushare.pro) - 财经数据
- [Scikit-learn](https://scikit-learn.org) - 机器学习
- [XGBoost](https://xgboost.ai) - 梯度提升树
- [PyTorch](https://pytorch.org) - 深度学习

---

## 📈 项目统计

![Stars](https://img.shields.io/github/stars/ZZZ12-ry/quant-strategy-factory?style=social)
![Forks](https://img.shields.io/github/forks/ZZZ12-ry/quant-strategy-factory?style=social)
![Issues](https://img.shields.io/github/issues/ZZZ12-ry/quant-strategy-factory)
![Last Commit](https://img.shields.io/github/last-commit/ZZZ12-ry/quant-strategy-factory)

---

**最后更新**: 2026-04-16  
**版本**: v1.0  
**状态**: 框架完整，可以开始学习使用

---

> **量化是终身事业，持续学习，谨慎交易！** 📚
