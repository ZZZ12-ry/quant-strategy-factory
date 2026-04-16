"""
模拟盘接口框架
连接期货仿真账户，进行实时信号验证

⚠️ 重要：这是从回测到实盘的必经之路
"""
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"      # 市价单
    LIMIT = "limit"        # 限价单
    STOP = "stop"          # 止损单


class OrderSide(Enum):
    """买卖方向"""
    BUY = "buy"            # 买入开仓
    SELL = "sell"          # 卖出开仓
    CLOSE_LONG = "close_long"   # 平多
    CLOSE_SHORT = "close_short" # 平空


@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    price: float
    volume: int
    timestamp: datetime
    status: str = "pending"  # pending/filled/cancelled
    filled_price: float = 0.0
    filled_volume: int = 0


@dataclass
class Position:
    """持仓"""
    symbol: str
    direction: str  # long/short
    volume: int
    avg_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


class SimulatedTradingAccount:
    """
    模拟交易账户
    
    功能：
    - 模拟期货账户
    - 实时行情接收
    - 订单执行
    - 持仓管理
    - 绩效统计
    """
    
    def __init__(self,
                 initial_capital: float = 1000000,
                 commission_rate: float = 0.0003,
                 slippage: float = 0.001):
        """
        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率
            slippage: 滑点
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        
        # 持仓
        self.positions: Dict[str, Position] = {}
        
        # 订单
        self.orders: List[Order] = []
        self.order_counter = 0
        
        # 成交记录
        self.trades = []
        
        # 账户统计
        self.equity_curve = [initial_capital]
        self.daily_returns = []
        
        # 风控
        self.max_drawdown = 0.0
        self.total_commission = 0.0
    
    def submit_order(self,
                    symbol: str,
                    side: OrderSide,
                    volume: int,
                    price: float = 0.0,
                    order_type: OrderType = OrderType.MARKET) -> Optional[Order]:
        """
        提交订单
        
        Args:
            symbol: 合约代码
            side: 买卖方向
            volume: 手数
            price: 价格（市价单可为 0）
            order_type: 订单类型
        
        Returns:
            订单对象
        """
        # 生成订单 ID
        self.order_counter += 1
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.order_counter}"
        
        # 创建订单
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=price,
            volume=volume,
            timestamp=datetime.now()
        )
        
        self.orders.append(order)
        
        print(f"[订单] {order_id}: {side.value} {symbol} {volume}手 @ {price}")
        
        return order
    
    def execute_order(self,
                     order: Order,
                     market_price: float) -> bool:
        """
        执行订单
        
        Args:
            order: 订单对象
            market_price: 市场价格
        
        Returns:
            是否成功执行
        """
        # 检查订单状态
        if order.status != "pending":
            return False
        
        # 计算执行价格（含滑点）
        if order.side in [OrderSide.BUY, OrderSide.CLOSE_SHORT]:
            exec_price = market_price * (1 + self.slippage)
        else:
            exec_price = market_price * (1 - self.slippage)
        
        # 检查资金
        trade_value = exec_price * order.volume * 10  # 期货合约乘数 10
        commission = trade_value * self.commission_rate
        
        if order.side in [OrderSide.BUY, OrderSide.SELL]:
            # 开仓需要保证金（假设 10%）
            margin = trade_value * 0.10
            required_capital = margin + commission
            
            if required_capital > self.capital:
                print(f"  [失败] 资金不足：需要 {required_capital:.2f}, 可用 {self.capital:.2f}")
                order.status = "cancelled"
                return False
        
        # 执行订单
        order.status = "filled"
        order.filled_price = exec_price
        order.filled_volume = order.volume
        
        # 更新持仓
        self._update_position(order, exec_price)
        
        # 扣除手续费
        self.capital -= commission
        self.total_commission += commission
        
        # 记录成交
        trade = {
            'order_id': order.order_id,
            'symbol': order.symbol,
            'side': order.side.value,
            'price': exec_price,
            'volume': order.volume,
            'commission': commission,
            'timestamp': order.timestamp
        }
        self.trades.append(trade)
        
        print(f"  [成交] {order.volume}手 @ {exec_price:.2f}, 手续费 {commission:.2f}")
        
        return True
    
    def _update_position(self, order: Order, exec_price: float):
        """更新持仓"""
        symbol = order.symbol
        
        if order.side == OrderSide.BUY:
            # 买入开仓
            if symbol in self.positions and self.positions[symbol].direction == 'long':
                # 加仓
                pos = self.positions[symbol]
                total_value = pos.avg_price * pos.volume + exec_price * order.volume
                pos.volume += order.volume
                pos.avg_price = total_value / pos.volume
            else:
                # 新建多仓
                self.positions[symbol] = Position(
                    symbol=symbol,
                    direction='long',
                    volume=order.volume,
                    avg_price=exec_price
                )
        
        elif order.side == OrderSide.SELL:
            # 卖出开仓
            if symbol in self.positions and self.positions[symbol].direction == 'short':
                # 加仓
                pos = self.positions[symbol]
                total_value = pos.avg_price * pos.volume + exec_price * order.volume
                pos.volume += order.volume
                pos.avg_price = total_value / pos.volume
            else:
                # 新建空仓
                self.positions[symbol] = Position(
                    symbol=symbol,
                    direction='short',
                    volume=order.volume,
                    avg_price=exec_price
                )
        
        elif order.side == OrderSide.CLOSE_LONG:
            # 平多仓
            if symbol in self.positions and self.positions[symbol].direction == 'long':
                pos = self.positions[symbol]
                pnl = (exec_price - pos.avg_price) * order.volume * 10
                pos.realized_pnl += pnl
                
                pos.volume -= order.volume
                if pos.volume <= 0:
                    del self.positions[symbol]
                
                self.capital += pnl
        
        elif order.side == OrderSide.CLOSE_SHORT:
            # 平空仓
            if symbol in self.positions and self.positions[symbol].direction == 'short':
                pos = self.positions[symbol]
                pnl = (pos.avg_price - exec_price) * order.volume * 10
                pos.realized_pnl += pnl
                
                pos.volume -= order.volume
                if pos.volume <= 0:
                    del self.positions[symbol]
                
                self.capital += pnl
    
    def update_market_price(self, symbol: str, price: float):
        """更新市场价格（模拟行情推送）"""
        # 更新持仓盈亏
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.direction == 'long':
                pos.unrealized_pnl = (price - pos.avg_price) * pos.volume * 10
            else:
                pos.unrealized_pnl = (pos.avg_price - price) * pos.volume * 10
        
        # 更新账户权益
        total_unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        equity = self.capital + total_unrealized
        
        self.equity_curve.append(equity)
        
        # 计算回撤
        peak = max(self.equity_curve)
        drawdown = (peak - equity) / peak
        self.max_drawdown = max(self.max_drawdown, drawdown)
    
    def get_account_summary(self) -> Dict:
        """获取账户汇总"""
        total_unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        total_realized = sum(p.realized_pnl for p in self.positions.values())
        equity = self.capital + total_unrealized
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.capital,
            'equity': equity,
            'unrealized_pnl': total_unrealized,
            'realized_pnl': total_realized,
            'total_return': (equity - self.initial_capital) / self.initial_capital * 100,
            'max_drawdown': self.max_drawdown * 100,
            'total_commission': self.total_commission,
            'position_count': len(self.positions),
            'order_count': len(self.orders),
            'trade_count': len(self.trades)
        }
    
    def get_positions(self) -> List[Dict]:
        """获取持仓列表"""
        return [
            {
                'symbol': pos.symbol,
                'direction': pos.direction,
                'volume': pos.volume,
                'avg_price': pos.avg_price,
                'unrealized_pnl': pos.unrealized_pnl,
                'realized_pnl': pos.realized_pnl
            }
            for pos in self.positions.values()
        ]
    
    def get_trades(self) -> pd.DataFrame:
        """获取成交记录"""
        return pd.DataFrame(self.trades)
    
    def export_report(self, filename: str = 'simulated_trading_report.json'):
        """导出报告"""
        report = {
            'account_summary': self.get_account_summary(),
            'positions': self.get_positions(),
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] 报告已保存：{filename}")


def test_simulated_trading():
    """测试模拟交易"""
    print("\n" + "="*60)
    print("模拟交易账户测试")
    print("="*60)
    
    # 创建模拟账户
    account = SimulatedTradingAccount(
        initial_capital=1000000,
        commission_rate=0.0003,
        slippage=0.001
    )
    
    print(f"\n初始设置:")
    print(f"  初始资金：{account.initial_capital:,.0f}")
    print(f"  手续费率：{account.commission_rate*10000:.1f}wan4")
    print(f"  滑点：{account.slippage*1000:.1f}qian1")
    
    # 模拟交易场景
    print(f"\n{'='*60}")
    print("模拟交易场景")
    print(f"{'='*60}")
    
    # 场景 1: 买入开仓
    print(f"\n[场景 1] 买入开仓 RB2405 10 手 @ 4000")
    order1 = account.submit_order(
        symbol='RB2405',
        side=OrderSide.BUY,
        volume=10,
        price=4000
    )
    account.execute_order(order1, market_price=4000)
    
    # 场景 2: 更新行情
    print(f"\n[场景 2] 更新行情 RB2405 -> 4100")
    account.update_market_price('RB2405', 4100)
    
    # 场景 3: 平多仓
    print(f"\n[场景 3] 平多仓 RB2405 10 手 @ 4100")
    order2 = account.submit_order(
        symbol='RB2405',
        side=OrderSide.CLOSE_LONG,
        volume=10,
        price=4100
    )
    account.execute_order(order2, market_price=4100)
    
    # 账户汇总
    print(f"\n{'='*60}")
    print("账户汇总")
    print(f"{'='*60}")
    
    summary = account.get_account_summary()
    
    print(f"\n资金情况:")
    print(f"  初始资金：{summary['initial_capital']:,.0f}")
    print(f"  当前权益：{summary['equity']:,.0f}")
    print(f"  总收益率：{summary['total_return']:.2f}%")
    
    print(f"\n风险指标:")
    print(f"  最大回撤：{summary['max_drawdown']:.2f}%")
    
    print(f"\n交易统计:")
    print(f"  订单数：{summary['order_count']}")
    print(f"  成交数：{summary['trade_count']}")
    print(f"  总手续费：{summary['total_commission']:.2f}")
    
    print(f"\n持仓:")
    positions = account.get_positions()
    if positions:
        for pos in positions:
            print(f"  {pos['symbol']} {pos['direction']} {pos['volume']}手 "
                  f"盈亏：{pos['unrealized_pnl']:.2f}")
    else:
        print(f"  无持仓")
    
    # 导出报告
    account.export_report('simulated_trading_report.json')
    
    print(f"\n{'='*60}")
    print("[OK] 模拟交易测试完成")
    print(f"{'='*60}")
    
    return account


if __name__ == "__main__":
    account = test_simulated_trading()
