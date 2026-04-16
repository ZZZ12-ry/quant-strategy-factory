# 量化策略工厂 - 完整策略列表 (15 个)

## 📊 策略分类总览

| 类别 | 策略数量 | 策略名称 |
|------|---------|---------|
| **趋势跟踪** | 6 | DualMA, TurtleTrader, ChannelBreakout, MACDTrend, AroonTrend, ADXTrend |
| **均值回归** | 3 | BollingerMR, RSIMR, MeanReversion |
| **震荡策略** | 3 | KDJ, AwesomeOsc, Stochastic |
| **突破策略** | 2 | DualThrust, VolatilityBreakout |
| **动量策略** | 1 | MomentumRank |
| **形态识别** | 1 | PatternRecognition |
| **总计** | **15** | - |

---

## 📈 趋势跟踪策略 (6 个)

### 1. DualMA - 双均线交叉
- **原理:** 快慢均线金叉死叉
- **参数:** fast_ma, slow_ma, use_ema, stop_loss_pct, take_profit_pct
- **适用:** 期货/股票趋势行情
- **优点:** 简单经典，参数少
- **缺点:** 震荡市频繁止损

### 2. TurtleTrader - 海龟交易
- **原理:** 唐奇安通道突破
- **参数:** entry_period, exit_period, atr_multiplier
- **适用:** 期货强趋势品种
- **优点:** 趋势捕捉能力强
- **缺点:** 回撤较大

### 3. ChannelBreakout - 通道突破
- **原理:** 价格突破 N 日高低点
- **参数:** lookback_days, k1, k2
- **适用:** 期货日内/日线
- **优点:** 捕捉突破行情
- **缺点:** 假突破多

### 4. MACDTrend - MACD 趋势
- **原理:** MACD 金叉死叉 + 柱状图
- **参数:** fast_period, slow_period, signal_period, histogram_threshold
- **适用:** 期货/股票
- **优点:** 动量确认
- **缺点:** 滞后性

### 5. AroonTrend - Aroon 趋势强度
- **原理:** Aroon Up/Down 判断趋势强弱
- **参数:** aroon_period, aroon_up_threshold, aroon_down_threshold
- **适用:** 股票/期货趋势识别
- **优点:** 量化趋势强度
- **缺点:** 参数敏感

### 6. ADXTrend - ADX 趋向指数
- **原理:** ADX>+DI/-DI 组合
- **参数:** adx_period, adx_threshold, di_period
- **适用:** 强趋势品种
- **优点:** 过滤震荡
- **缺点:** ADX 滞后

---

## 📉 均值回归策略 (3 个)

### 7. BollingerMR - 布林带回归
- **原理:** 价格触及布林带上下轨回归
- **参数:** ma_period, std_dev, exit_ma, stop_loss_pct
- **适用:** 震荡行情
- **优点:** 逻辑清晰
- **缺点:** 趋势市亏损

### 8. RSIMR - RSI 超买超卖
- **原理:** RSI 极端值反转
- **参数:** rsi_period, oversold, overbought, exit_rsi
- **适用:** 震荡市
- **优点:** 反应快
- **缺点:** 钝化风险

### 9. MeanReversion - Z-Score 回归
- **原理:** 价格偏离均线 N 个标准差回归
- **参数:** ma_period, entry_std, exit_std
- **适用:** 统计套利
- **优点:** 统计学基础
- **缺点:** 假设正态分布

---

## 🔄 震荡策略 (3 个)

### 10. KDJ - KDJ 震荡
- **原理:** KDJ 超买超卖 + 金叉死叉
- **参数:** n_period, k_period, d_period, oversold, overbought
- **适用:** 短线震荡
- **优点:** 灵敏
- **缺点:** 假信号多

### 11. AwesomeOsc - 动量震荡
- **原理:** Awesome Oscillator 零线穿越 + 碟形
- **参数:** fast_period, slow_period, saucer_confirm
- **适用:** 期货/股票
- **优点:** 多重确认
- **缺点:** 参数多

### 12. Stochastic - 随机指标
- **原理:** %K/%D 超买超卖
- **参数:** k_period, d_period, oversold, overbought
- **适用:** 震荡市
- **优点:** 经典指标
- **缺点:** 趋势市失效

---

## 🚀 突破策略 (2 个)

### 13. DualThrust - 双 thrust 突破
- **原理:** Range 突破 + 时间平仓
- **参数:** lookback_days, k1, k2, exit_hour
- **适用:** 日内期货
- **优点:** 专为日内设计
- **缺点:** 需要分钟数据

### 14. VolatilityBreakout - 波动率突破
- **原理:** ATR 通道突破 + 跟踪止损
- **参数:** atr_period, entry_multiplier, exit_multiplier
- **适用:** 高波动品种
- **优点:** 自适应波动
- **缺点:** ATR 滞后

---

## 📊 其他策略 (2 个)

### 15. MomentumRank - 动量排名轮动
- **原理:** 多品种动量排名 + 定期调仓
- **参数:** momentum_period, top_n, rebalance_period
- **适用:** 多品种组合
- **优点:** 分散风险
- **缺点:** 需要多品种数据

### 16. PatternRecognition - K 线形态识别
- **原理:** 锤子线/吞没/晨星等形态
- **参数:** min_body_ratio, min_shadow_ratio, confirmation
- **适用:** 短线交易
- **优点:** 直观
- **缺点:** 主观性强

---

## 🎯 策略选择指南

### 按市场环境选择

| 市场环境 | 推荐策略 |
|---------|---------|
| **强趋势** | TurtleTrader, ADXTrend, AroonTrend |
| **震荡市** | BollingerMR, RSIMR, KDJ, MeanReversion |
| **突破行情** | DualThrust, ChannelBreakout, VolatilityBreakout |
| **动量行情** | MACDTrend, MomentumRank, AwesomeOsc |

### 按资产类别选择

| 资产类别 | 推荐策略 |
|---------|---------|
| **商品期货** | TurtleTrader, DualThrust, VolatilityBreakout |
| **股票** | DualMA, MACDTrend, RSIMR |
| **股指期货** | MACDTrend, ADXTrend, BollingerMR |
| **多品种组合** | MomentumRank |

### 按交易频率选择

| 交易频率 | 推荐策略 |
|---------|---------|
| **日内** | DualThrust, PatternRecognition |
| **短线 (1-5 天)** | KDJ, RSIMR, Stochastic |
| **中线 (5-20 天)** | DualMA, MACDTrend, BollingerMR |
| **长线 (20 天+)** | TurtleTrader, AroonTrend, MomentumRank |

---

## 🔧 策略开发建议

### 1. 从经典开始
先测试 DualMA、TurtleTrader 等经典策略，理解框架

### 2. 参数优化
对每个策略进行参数优化，找到最优参数

### 3. 组合配置
选择 3-5 个低相关策略构建组合

### 4. 压力测试
用 Monte Carlo 检验策略稳健性

### 5. 实盘验证
小资金实盘验证后再加大投入

---

*策略数量：15 个 | 最后更新：2026-04-09*
