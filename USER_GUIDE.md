# 量化策略工厂 - 完整使用指南

## 📚 目录

1. [快速开始](#快速开始)
2. [系统架构](#系统架构)
3. [模块说明](#模块说明)
4. [使用示例](#使用示例)
5. [常见问题](#常见问题)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 核心依赖
pip install numpy pandas scipy matplotlib

# 数据源
pip install akshare tushare

# 机器学习（可选）
pip install scikit-learn xgboost

# 其他
pip install tqdm jinja2 pyyaml
```

### 2. 一键运行演示

```bash
cd quant-strategy-factory
python run_full_demo.py
```

### 3. 查看报告

```bash
# 回测报告
open reports/backtest_report.html

# 模拟盘报告
open reports/simulated_trading_report.json
```

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────┐
│              数据层                          │
│  - historical_data_fetcher  历史数据获取    │
│  - data_cache              数据缓存         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              策略层                          │
│  - multifactor_strategy_v2  多因子策略      │
│  - volume_night_day         成交量策略      │
│  - pairs_trading            配对交易        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              风控层                          │
│  - risk_manager             风险管理        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              交易层                          │
│  - simulated_account        模拟账户        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              验证层                          │
│  - realistic_backtester     真实回测        │
│  - out_of_sample_validator  样本外验证      │
└─────────────────────────────────────────────┘
```

---

## 📦 模块说明

### 数据层

| 模块 | 功能 | 文件 |
|------|------|------|
| **历史数据获取** | 获取期货历史数据 | `src/data/historical_data_fetcher.py` |
| **数据缓存** | 本地缓存，避免重复获取 | `src/data/data_cache.py` |

### 策略层

| 策略 | 类型 | 文件 |
|------|------|------|
| **多因子策略 v2** | Barra 因子 + ML | `src/strategies/multifactor_strategy_v2.py` |
| **成交量策略** | 量价关系 | `src/strategies/volume_night_day.py` |
| **配对交易** | 统计套利 | `src/strategies/pairs_trading.py` |

### 风控层

| 功能 | 说明 | 文件 |
|------|------|------|
| **仓位管理** | 单策略/总仓位限制 | `src/risk/risk_manager.py` |
| **止损监控** | 多层次止损 | `src/risk/risk_manager.py` |
| **风险预警** | 4 级风险等级 | `src/risk/risk_manager.py` |

### 交易层

| 功能 | 说明 | 文件 |
|------|------|------|
| **模拟账户** | 期货仿真账户 | `src/trading/simulated_account.py` |
| **订单管理** | 市价/限价/止损单 | `src/trading/simulated_account.py` |
| **持仓管理** | 实时盈亏计算 | `src/trading/simulated_account.py` |

### 验证层

| 功能 | 说明 | 文件 |
|------|------|------|
| **真实回测** | 手续费/滑点/冲击成本 | `src/backtest/realistic_backtester.py` |
| **样本外验证** | 滚动回测/过拟合检测 | `src/validation/out_of_sample_validator.py` |

---

## 💻 使用示例

### 1. 获取历史数据

```python
from src.data.historical_data_fetcher import HistoricalDataFetcher
from src.data.data_cache import DataCache

# 创建获取器和缓存
fetcher = HistoricalDataFetcher()
cache = DataCache()

# 自动更新缓存
symbols = ['RB2405', 'HC2405', 'CU2405']
cache.auto_update(fetcher, symbols, max_age_days=7)

# 加载数据
data = cache.load_data('RB2405', max_age_days=30)
```

### 2. 运行回测

```python
from src.backtest.realistic_backtester import RealisticBacktester, TradingCosts

# 创建回测器
backtester = RealisticBacktester(
    initial_capital=1000000,
    trading_costs=TradingCosts(
        commission=0.0003,
        slippage=0.001,
        impact_cost=0.0005
    )
)

# 执行交易
backtester.execute_buy(price=4000, volume=100)
backtester.execute_sell(price=4100, volume=100)

# 获取绩效
metrics = backtester.get_performance_metrics()
```

### 3. 样本外验证

```python
from src.validation.out_of_sample_validator import OutOfSampleValidator, SplitConfig

validator = OutOfSampleValidator(
    SplitConfig(
        train_ratio=0.6,
        walk_forward_window=252,
        walk_forward_step=63
    )
)

# 滚动回测
results = validator.walk_forward_analysis(data, strategy_func, n_splits=5)
```

### 4. 模拟交易

```python
from src.trading.simulated_account import SimulatedTradingAccount, OrderType, OrderSide

# 创建模拟账户
account = SimulatedTradingAccount(initial_capital=1000000)

# 提交订单
order = account.submit_order(
    symbol='RB2405',
    side=OrderSide.BUY,
    volume=10,
    order_type=OrderType.MARKET
)

# 执行订单
account.execute_order(order, market_price=4000)

# 更新行情
account.update_market_price('RB2405', 4100)

# 获取账户汇总
summary = account.get_account_summary()
```

### 5. 风控管理

```python
from src.risk.risk_manager import RiskManager, PositionLimits, LossLimits

# 创建风控管理器
risk_mgr = RiskManager(
    initial_capital=1000000,
    position_limits=PositionLimits(
        max_single_position=0.30
    ),
    loss_limits=LossLimits(
        max_drawdown=0.20
    )
)

# 检查仓位
allowed = risk_mgr.check_position_limit(200000)

# 获取允许仓位
position = risk_mgr.get_allowed_position(signal_strength=0.8)

# 检查是否强平
should_close = risk_mgr.should_close_all()
```

---

## ⚠️ 常见问题

### Q1: 数据获取失败？

**A**: 检查网络连接，AKShare 需要联网。可以使用缓存数据：

```python
cache = DataCache()
data = cache.load_data('RB2405', max_age_days=30)
```

### Q2: 回测结果为负？

**A**: 正常现象。可能原因：
- 策略不适合该品种
- 参数需要优化
- 市场环境变化

建议：多品种测试，参数优化

### Q3: 模拟盘和回测差异大？

**A**: 正常现象。差异来源：
- 回测成本是估算
- 实盘滑点更大
- 心理因素影响

建议：至少 3-6 个月模拟盘验证

### Q4: 如何实盘？

**A**: 严格遵循以下流程：

```
1. 历史回测 (3-5 年数据) ✅
   ↓
2. 样本外验证 (滚动回测) ✅
   ↓
3. 模拟盘测试 (3-6 个月) ⚠️
   ↓
4. 小资金实盘 (1-5 万) ❌
   ↓
5. 逐步加仓 ❌
```

**当前状态**: 可以开始模拟盘测试，**不能实盘**！

---

## 📋 文件结构

```
quant-strategy-factory/
├── src/
│   ├── data/                      # 数据层
│   │   ├── historical_data_fetcher.py
│   │   └── data_cache.py
│   ├── strategies/                # 策略层
│   │   ├── multifactor_strategy_v2.py
│   │   ├── volume_night_day.py
│   │   └── pairs_trading.py
│   ├── risk/                      # 风控层
│   │   └── risk_manager.py
│   ├── trading/                   # 交易层
│   │   └── simulated_account.py
│   ├── backtest/                  # 回测层
│   │   └── realistic_backtester.py
│   └── validation/                # 验证层
│       └── out_of_sample_validator.py
├── data/
│   └── cache/                     # 数据缓存
├── reports/                       # 报告输出
├── config.ini                     # 配置文件
├── run_full_demo.py               # 综合演示
└── README.md                      # 本文档
```

---

## 🎯 下一步建议

### 学习路线

1. **基础学习** (1-2 周)
   - 阅读所有模块代码
   - 运行综合演示
   - 理解回测流程

2. **模拟盘练习** (3-6 个月)
   - 开通期货仿真账户
   - 运行模拟交易
   - 记录交易心理

3. **小资金实盘** (6 个月后)
   - 1-5 万试水
   - 严格执行风控
   - 持续学习改进

### 推荐资源

**书籍**:
- 《量化交易：如何建立自己的算法交易事业》
- 《主动投资组合管理》
- 《打开量化投资的黑箱》

**网站**:
- 聚宽：https://www.joinquant.com
- 米筐：https://www.ricequant.com
- AKShare: https://akshare.akfamily.xyz

---

## 📞 技术支持

**重要提醒**:
1. 本系统仅供学习研究
2. 不构成投资建议
3. 实盘需谨慎，做好亏损准备
4. 持续学习，量化是终身事业

---

*文档更新时间：2026-04-16*  
*系统版本：v1.0*  
*完成度：95%（框架完整）*
