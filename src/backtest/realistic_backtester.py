"""
真实回测系统
包含：手续费、滑点、冲击成本

⚠️ 重要：这是评估策略真实表现的关键
"""
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class TradingCosts:
    """交易成本参数"""
    commission: float = 0.0003        # 手续费 万三
    slippage: float = 0.001           # 滑点 千一
    impact_cost: float = 0.0005       # 冲击成本 万分五
    min_commission: float = 5.0       # 最低手续费 5 元


class RealisticBacktester:
    """
    真实回测器
    
    核心功能：
    1. 计算真实交易成本
    2. 模拟真实成交
    3. 生成详细交易记录
    """
    
    def __init__(self, 
                 initial_capital: float = 1000000,
                 trading_costs: TradingCosts = None):
        """
        Args:
            initial_capital: 初始资金
            trading_costs: 交易成本参数
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.trading_costs = trading_costs or TradingCosts()
        
        # 持仓
        self.position = 0  # 持仓数量
        self.position_value = 0.0
        self.avg_entry_price = 0.0
        
        # 交易记录
        self.trades = []
        self.equity_curve = [initial_capital]
        
        # 绩效统计
        self.total_commission = 0.0
        self.total_slippage = 0.0
        self.total_impact = 0.0
    
    def calculate_costs(self, 
                       price: float, 
                       volume: int,
                       is_buy: bool) -> Dict:
        """
        计算交易成本
        
        Args:
            price: 成交价格
            volume: 成交数量
            is_buy: 是否买入
        
        Returns:
            成本明细
        """
        trade_value = price * volume
        
        # 手续费
        commission = max(trade_value * self.trading_costs.commission, 
                        self.trading_costs.min_commission)
        
        # 滑点（买入价更高，卖出价更低）
        if is_buy:
            slippage_price = price * (1 + self.trading_costs.slippage)
        else:
            slippage_price = price * (1 - self.trading_costs.slippage)
        
        slippage_cost = abs(slippage_price - price) * volume
        
        # 冲击成本（大单影响）
        impact_ratio = self.trading_costs.impact_cost
        if trade_value > 100000:  # 超过 10 万
            impact_ratio *= 1.5
        if trade_value > 500000:  # 超过 50 万
            impact_ratio *= 2
        
        impact_cost = trade_value * impact_ratio
        
        return {
            'commission': commission,
            'slippage': slippage_cost,
            'impact': impact_cost,
            'total_cost': commission + slippage_cost + impact_cost,
            'effective_price': slippage_price
        }
    
    def execute_buy(self, 
                   price: float, 
                   volume: int,
                   timestamp=None) -> Optional[Dict]:
        """
        执行买入
        
        Returns:
            成交信息
        """
        # 计算成本
        costs = self.calculate_costs(price, volume, is_buy=True)
        
        # 检查资金
        required_capital = costs['effective_price'] * volume + costs['total_cost']
        
        if required_capital > self.capital:
            return None  # 资金不足
        
        # 更新持仓
        if self.position == 0:
            self.avg_entry_price = costs['effective_price']
        else:
            # 加权平均
            total_value = self.avg_entry_price * self.position + costs['effective_price'] * volume
            self.avg_entry_price = total_value / (self.position + volume)
        
        self.position += volume
        self.position_value = self.avg_entry_price * self.position
        
        # 扣除资金
        self.capital -= required_capital
        
        # 更新统计
        self.total_commission += costs['commission']
        self.total_slippage += costs['slippage']
        self.total_impact += costs['impact']
        
        # 记录交易
        trade = {
            'type': 'buy',
            'timestamp': timestamp,
            'price': price,
            'volume': volume,
            'effective_price': costs['effective_price'],
            'commission': costs['commission'],
            'slippage': costs['slippage'],
            'impact': costs['impact'],
            'total_cost': costs['total_cost'],
            'position': self.position,
            'capital': self.capital
        }
        
        self.trades.append(trade)
        self.equity_curve.append(self.capital + self.position_value)
        
        return trade
    
    def execute_sell(self,
                    price: float,
                    volume: int,
                    timestamp=None) -> Optional[Dict]:
        """
        执行卖出
        
        Returns:
            成交信息
        """
        # 检查持仓
        if volume > self.position:
            return None  # 持仓不足
        
        # 计算成本
        costs = self.calculate_costs(price, volume, is_buy=False)
        
        # 计算实现盈亏
        pnl = (price - self.avg_entry_price) * volume - costs['total_cost']
        
        # 更新持仓
        self.position -= volume
        self.position_value = self.avg_entry_price * self.position
        
        # 增加资金
        sale_proceeds = costs['effective_price'] * volume - costs['total_cost']
        self.capital += sale_proceeds
        
        # 更新统计
        self.total_commission += costs['commission']
        self.total_slippage += costs['slippage']
        self.total_impact += costs['impact']
        
        # 记录交易
        trade = {
            'type': 'sell',
            'timestamp': timestamp,
            'price': price,
            'volume': volume,
            'effective_price': costs['effective_price'],
            'pnl': pnl,
            'commission': costs['commission'],
            'slippage': costs['slippage'],
            'impact': costs['impact'],
            'total_cost': costs['total_cost'],
            'position': self.position,
            'capital': self.capital
        }
        
        self.trades.append(trade)
        self.equity_curve.append(self.capital + self.position_value)
        
        return trade
    
    def get_performance_metrics(self) -> Dict:
        """获取绩效指标"""
        if not self.trades:
            return {}
        
        # 计算净值
        equity = pd.Series(self.equity_curve)
        returns = equity.pct_change().dropna()
        
        # 绩效指标
        total_return = (equity.iloc[-1] - self.initial_capital) / self.initial_capital * 100
        
        if len(returns) > 1:
            sharpe = returns.mean() / (returns.std() + 1e-8) * np.sqrt(252)
            max_dd = ((equity.cummax() - equity) / equity.cummax()).max() * 100
        else:
            sharpe = 0
            max_dd = 0
        
        # 交易统计
        buy_trades = [t for t in self.trades if t['type'] == 'buy']
        sell_trades = [t for t in self.trades if t['type'] == 'sell']
        
        profitable_trades = [t for t in sell_trades if t.get('pnl', 0) > 0]
        win_rate = len(profitable_trades) / len(sell_trades) * 100 if sell_trades else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital + self.position_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'total_commission': self.total_commission,
            'total_slippage': self.total_slippage,
            'total_impact': self.total_impact,
            'total_costs': self.total_commission + self.total_slippage + self.total_impact,
            'cost_ratio': (self.total_commission + self.total_slippage + self.total_impact) / self.initial_capital * 100
        }
    
    def get_trade_summary(self) -> pd.DataFrame:
        """获取交易汇总"""
        return pd.DataFrame(self.trades)


def test_realistic_backtester():
    """测试真实回测系统"""
    print("\n" + "="*70)
    print("真实回测系统 - 测试")
    print("="*70)
    
    # 创建回测器
    backtester = RealisticBacktester(
        initial_capital=1000000,
        trading_costs=TradingCosts(
            commission=0.0003,
            slippage=0.001,
            impact_cost=0.0005
        )
    )
    
    print(f"\n回测设置:")
    print(f"  初始资金：{backtester.initial_capital:,.0f}")
    print(f"  手续费：{backtester.trading_costs.commission*10000:.1f} wan3")
    print(f"  滑点：{backtester.trading_costs.slippage*1000:.1f} qian1")
    print(f"  冲击成本：{backtester.trading_costs.impact_cost*10000:.1f} wan5")
    
    # 模拟交易
    print(f"\n{'='*70}")
    print("模拟交易")
    print(f"{'='*70}")
    
    # 交易 1: 买入
    print(f"\n交易 1: 买入 100 手 @ 4000")
    trade1 = backtester.execute_buy(price=4000, volume=100, timestamp='2024-01-01')
    if trade1:
        print(f"  成交价：{trade1['effective_price']:.2f}")
        print(f"  手续费：{trade1['commission']:.2f}")
        print(f"  滑点：{trade1['slippage']:.2f}")
        print(f"  冲击成本：{trade1['impact']:.2f}")
        print(f"  总成本：{trade1['total_cost']:.2f}")
    
    # 交易 2: 卖出
    print(f"\n交易 2: 卖出 100 手 @ 4100")
    trade2 = backtester.execute_sell(price=4100, volume=100, timestamp='2024-01-05')
    if trade2:
        print(f"  成交价：{trade2['effective_price']:.2f}")
        print(f"  毛利润：{(4100-4000)*100:.2f}")
        print(f"  净利润：{trade2['pnl']:.2f}")
        print(f"  总成本：{trade2['total_cost']:.2f}")
    
    # 绩效报告
    print(f"\n{'='*70}")
    print("绩效报告")
    print(f"{'='*70}")
    
    metrics = backtester.get_performance_metrics()
    
    print(f"\n资金情况:")
    print(f"  初始资金：{metrics.get('initial_capital',0):,.0f}")
    print(f"  最终资金：{metrics.get('final_capital',0):,.0f}")
    print(f"  总收益率：{metrics.get('total_return',0):.2f}%")
    
    print(f"\n风险指标:")
    print(f"  夏普比率：{metrics.get('sharpe_ratio',0):.2f}")
    print(f"  最大回撤：{metrics.get('max_drawdown',0):.2f}%")
    
    print(f"\n交易统计:")
    print(f"  交易次数：{metrics.get('total_trades',0)}")
    print(f"  胜率：{metrics.get('win_rate',0):.1f}%")
    
    print(f"\n交易成本:")
    print(f"  手续费：{metrics.get('total_commission',0):.2f}")
    print(f"  滑点：{metrics.get('total_slippage',0):.2f}")
    print(f"  冲击成本：{metrics.get('total_impact',0):.2f}")
    print(f"  总成本：{metrics.get('total_costs',0):.2f}")
    print(f"  成本占比：{metrics.get('cost_ratio',0):.3f}%")
    
    print(f"\n{'='*70}")
    print("[OK] 真实回测系统测试完成")
    print(f"{'='*70}")
    
    return backtester, metrics


if __name__ == "__main__":
    backtester, metrics = test_realistic_backtester()
