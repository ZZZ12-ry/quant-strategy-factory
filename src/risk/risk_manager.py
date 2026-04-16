"""
风险管理系统
包含：仓位管理、止损止盈、风险限额

⚠️ 重要：这是保护本金的核心模块，必须严格执行
"""
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"           # 低风险
    MEDIUM = "medium"     # 中等风险
    HIGH = "high"         # 高风险
    EXTREME = "extreme"   # 极高风险


@dataclass
class PositionLimits:
    """仓位限制"""
    max_single_position: float = 0.30    # 单策略最大仓位 30%
    max_total_position: float = 0.80     # 总仓位上限 80%
    min_cash_ratio: float = 0.20         # 最小现金比例 20%


@dataclass
class LossLimits:
    """止损限制"""
    max_daily_loss: float = 0.05         # 单日最大亏损 5%
    max_weekly_loss: float = 0.10        # 单周最大亏损 10%
    max_monthly_loss: float = 0.15       # 单月最大亏损 15%
    max_drawdown: float = 0.20           # 最大回撤 20%
    stop_loss_per_trade: float = 0.03    # 单笔交易止损 3%


class RiskManager:
    """
    风险管理器
    
    核心功能：
    1. 仓位控制
    2. 止损监控
    3. 风险预警
    4. 强制平仓
    """
    
    def __init__(self, 
                 initial_capital: float = 1000000,
                 position_limits: PositionLimits = None,
                 loss_limits: LossLimits = None):
        """
        Args:
            initial_capital: 初始资金
            position_limits: 仓位限制
            loss_limits: 止损限制
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        
        self.position_limits = position_limits or PositionLimits()
        self.loss_limits = loss_limits or LossLimits()
        
        # 持仓记录
        self.positions = {}
        self.position_value = 0.0
        
        # 收益记录
        self.daily_returns = []
        self.equity_curve = [initial_capital]
        
        # 风险预警
        self.warnings = []
    
    def update_capital(self, current_value: float):
        """更新资金情况"""
        self.current_capital = current_value
        self.peak_capital = max(self.peak_capital, current_value)
        self.equity_curve.append(current_value)
    
    def check_position_limit(self, new_position_value: float) -> bool:
        """
        检查仓位限制
        
        Returns:
            是否允许开仓
        """
        total_value = self.position_value + new_position_value
        position_ratio = total_value / self.current_capital
        
        # 检查单策略仓位
        if new_position_value / self.current_capital > self.position_limits.max_single_position:
            self.warnings.append("⚠️ 单策略仓位超限")
            return False
        
        # 检查总仓位
        if position_ratio > self.position_limits.max_total_position:
            self.warnings.append("⚠️ 总仓位超限")
            return False
        
        # 检查现金比例
        cash_ratio = (self.current_capital - total_value) / self.current_capital
        if cash_ratio < self.position_limits.min_cash_ratio:
            self.warnings.append("⚠️ 现金比例不足")
            return False
        
        return True
    
    def check_daily_loss(self, today_pnl: float) -> bool:
        """检查单日亏损"""
        daily_return = today_pnl / self.current_capital
        
        if daily_return < -self.loss_limits.max_daily_loss:
            self.warnings.append(f"🔴 单日亏损超限：{daily_return*100:.2f}%")
            return False
        
        return True
    
    def check_drawdown(self) -> bool:
        """检查回撤"""
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        
        if current_drawdown > self.loss_limits.max_drawdown:
            self.warnings.append(f"🔴 回撤超限：{current_drawdown*100:.2f}%")
            return False
        
        return True
    
    def check_risk_level(self) -> RiskLevel:
        """评估当前风险等级"""
        # 计算回撤
        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        
        # 计算波动率
        if len(self.equity_curve) > 10:
            returns = pd.Series(self.equity_curve).pct_change()
            volatility = returns.std()
        else:
            volatility = 0
        
        # 风险评分
        risk_score = 0
        
        # 回撤评分
        if drawdown > 0.15:
            risk_score += 3
        elif drawdown > 0.10:
            risk_score += 2
        elif drawdown > 0.05:
            risk_score += 1
        
        # 波动率评分
        if volatility > 0.03:
            risk_score += 2
        elif volatility > 0.02:
            risk_score += 1
        
        # 确定风险等级
        if risk_score >= 4:
            return RiskLevel.EXTREME
        elif risk_score >= 3:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def get_allowed_position(self, signal_strength: float = 1.0) -> float:
        """
        计算允许的仓位
        
        Args:
            signal_strength: 信号强度 (0-1)
        
        Returns:
            允许的仓位金额
        """
        # 基础仓位
        base_position = self.current_capital * self.position_limits.max_single_position
        
        # 根据风险等级调整
        risk_level = self.check_risk_level()
        
        if risk_level == RiskLevel.EXTREME:
            risk_factor = 0.0  # 禁止开仓
        elif risk_level == RiskLevel.HIGH:
            risk_factor = 0.3
        elif risk_level == RiskLevel.MEDIUM:
            risk_factor = 0.6
        else:
            risk_factor = 1.0
        
        # 根据信号强度调整
        allowed_position = base_position * risk_factor * signal_strength
        
        return allowed_position
    
    def should_close_all(self) -> bool:
        """是否应该全部平仓"""
        # 检查是否触发强制平仓条件
        if not self.check_drawdown():
            return True
        
        if self.check_risk_level() == RiskLevel.EXTREME:
            return True
        
        return False
    
    def get_risk_report(self) -> Dict:
        """生成风险报告"""
        return {
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'total_return': (self.current_capital - self.initial_capital) / self.initial_capital * 100,
            'max_drawdown': (self.peak_capital - min(self.equity_curve)) / self.peak_capital * 100,
            'current_drawdown': (self.peak_capital - self.current_capital) / self.peak_capital * 100,
            'risk_level': self.check_risk_level().value,
            'position_ratio': self.position_value / self.current_capital * 100,
            'warnings': self.warnings[-10:],  # 最近 10 条预警
        }


def test_risk_manager():
    """测试风控系统"""
    print("\n" + "="*70)
    print("风险管理系统 - 测试")
    print("="*70)
    
    # 创建风控管理器
    risk_mgr = RiskManager(
        initial_capital=1000000,
        position_limits=PositionLimits(
            max_single_position=0.30,
            max_total_position=0.80,
            min_cash_ratio=0.20
        ),
        loss_limits=LossLimits(
            max_daily_loss=0.05,
            max_drawdown=0.20,
            stop_loss_per_trade=0.03
        )
    )
    
    print(f"\n初始设置:")
    print(f"  初始资金：{risk_mgr.initial_capital:,.0f}")
    print(f"  单策略最大仓位：{risk_mgr.position_limits.max_single_position*100:.0f}%")
    print(f"  最大回撤限制：{risk_mgr.loss_limits.max_drawdown*100:.0f}%")
    
    # 模拟交易场景
    print(f"\n{'='*70}")
    print("模拟交易场景测试")
    print(f"{'='*70}")
    
    # 场景 1: 正常开仓
    print(f"\n场景 1: 正常开仓")
    allowed = risk_mgr.get_allowed_position(signal_strength=0.8)
    print(f"  允许仓位：{allowed:,.0f}")
    print(f"  风险等级：{risk_mgr.check_risk_level().value}")
    
    # 场景 2: 亏损后
    print(f"\n场景 2: 亏损 10% 后")
    risk_mgr.update_capital(900000)
    allowed = risk_mgr.get_allowed_position(signal_strength=0.8)
    print(f"  当前资金：{risk_mgr.current_capital:,.0f}")
    print(f"  允许仓位：{allowed:,.0f}")
    print(f"  风险等级：{risk_mgr.check_risk_level().value}")
    
    # 场景 3: 大幅亏损
    print(f"\n场景 3: 亏损 20% 后")
    risk_mgr.update_capital(800000)
    should_close = risk_mgr.should_close_all()
    print(f"  当前资金：{risk_mgr.current_capital:,.0f}")
    print(f"  是否强制平仓：{should_close}")
    print(f"  风险等级：{risk_mgr.check_risk_level().value}")
    
    # 风险报告
    print(f"\n{'='*70}")
    print("风险报告")
    print(f"{'='*70}")
    
    report = risk_mgr.get_risk_report()
    for key, value in report.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    print(f"\n{'='*70}")
    print("[OK] 风控系统测试完成")
    print(f"{'='*70}")
    
    return risk_mgr


if __name__ == "__main__":
    risk_mgr = test_risk_manager()
