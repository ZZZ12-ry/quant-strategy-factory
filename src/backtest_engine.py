"""
回测引擎 - 执行策略回测
"""
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime

from src.strategies.base import BaseStrategy, Signal


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    initial_cash: float
    final_cash: float
    total_return: float  # 总收益率
    annualized_return: float  # 年化收益
    sharpe_ratio: float  # 夏普比率
    max_drawdown: float  # 最大回撤
    total_trades: int  # 总交易次数
    win_rate: float  # 胜率
    profit_loss_ratio: float  # 盈亏比
    avg_trade_return: float  # 平均每笔收益
    max_consecutive_losses: int  # 最长连亏
    trades: List[Dict]  # 交易记录
    equity_curve: List[float]  # 资金曲线


class BacktestEngine:
    """回测引擎"""
    
    def __init__(
        self,
        strategy: BaseStrategy,
        initial_cash: float = 1000000,
        commission_rate: float = 0.0003,
        slippage: float = 1.0,
        contract_multiplier: float = 1.0
    ):
        self.strategy = strategy
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.contract_multiplier = contract_multiplier
        
        self.cash = initial_cash
        self.positions: Dict[str, int] = {}  # symbol -> volume
        self.trades: List[Dict] = []
        self.equity_curve: List[float] = []
    
    def run(
        self,
        data: pd.DataFrame,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> BacktestResult:
        """
        运行回测
        
        Args:
            data: K 线数据，包含 timestamp/open/high/low/close/volume
            symbol: 品种代码
            start_date: 开始日期
            end_date: 结束日期
        """
        # 重置策略状态
        self.strategy.reset()
        self.cash = self.initial_cash
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
        # 数据预处理
        if start_date:
            data = data[data['timestamp'] >= start_date]
        if end_date:
            data = data[data['timestamp'] <= end_date]
        
        # 逐 K 线回测
        for idx, bar in data.iterrows():
            # 调用策略
            signal = self.strategy.on_bar(bar)
            
            # 执行信号
            if signal:
                self._execute_signal(signal, bar)
            
            # 更新资金曲线
            equity = self._calculate_equity(bar)
            self.equity_curve.append(equity)
        
        # 计算回测结果
        return self._calculate_results(symbol, data)
    
    def _execute_signal(self, signal: Signal, bar: pd.Series):
        """执行交易信号"""
        price = bar['close']
        
        # 应用滑点
        if signal.direction == "long":
            exec_price = price + self.slippage
        elif signal.direction == "short":
            exec_price = price - self.slippage
        else:  # close
            exec_price = price
        
        # 计算手续费
        commission = exec_price * self.contract_multiplier * self.commission_rate
        
        if signal.direction == "long":
            # 开多
            volume = signal.volume
            cost = exec_price * volume * self.contract_multiplier + commission
            if cost <= self.cash:
                self.cash -= cost
                self.positions[signal.symbol] = self.positions.get(signal.symbol, 0) + volume
                self.trades.append({
                    "timestamp": signal.timestamp,
                    "symbol": signal.symbol,
                    "action": "buy",
                    "price": exec_price,
                    "volume": volume,
                    "commission": commission
                })
        
        elif signal.direction == "short":
            # 开空（简化处理，假设可以无限制做空）
            volume = signal.volume
            self.cash += exec_price * volume * self.contract_multiplier - commission
            self.positions[signal.symbol] = self.positions.get(signal.symbol, 0) - volume
            self.trades.append({
                "timestamp": signal.timestamp,
                "symbol": signal.symbol,
                "action": "sell",
                "price": exec_price,
                "volume": volume,
                "commission": commission
            })
        
        elif signal.direction == "close":
            # 平仓
            if signal.symbol in self.positions:
                position = self.positions[signal.symbol]
                abs_position = abs(position)
                
                if position > 0:
                    # 平多
                    self.cash += exec_price * abs_position * self.contract_multiplier - commission
                    self.trades.append({
                        "timestamp": signal.timestamp,
                        "symbol": signal.symbol,
                        "action": "close_long",
                        "price": exec_price,
                        "volume": abs_position,
                        "commission": commission
                    })
                else:
                    # 平空
                    self.cash -= exec_price * abs_position * self.contract_multiplier + commission
                    self.trades.append({
                        "timestamp": signal.timestamp,
                        "symbol": signal.symbol,
                        "action": "close_short",
                        "price": exec_price,
                        "volume": abs_position,
                        "commission": commission
                    })
                
                del self.positions[signal.symbol]
    
    def _calculate_equity(self, bar: pd.Series) -> float:
        """计算当前总权益"""
        equity = self.cash
        
        # 加上持仓市值（简化处理，用当前价格计算）
        for symbol, volume in self.positions.items():
            if volume > 0:
                equity += bar['close'] * volume * self.contract_multiplier
            elif volume < 0:
                equity -= bar['close'] * abs(volume) * self.contract_multiplier
        
        return equity
    
    def _calculate_results(self, symbol: str, data: pd.DataFrame) -> BacktestResult:
        """计算回测结果指标"""
        if len(self.equity_curve) == 0:
            return BacktestResult(
                strategy_name=self.strategy.__class__.__name__,
                symbol=symbol,
                start_date=str(data['timestamp'].min()),
                end_date=str(data['timestamp'].max()),
                initial_cash=self.initial_cash,
                final_cash=self.initial_cash,
                total_return=0.0,
                annualized_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                total_trades=0,
                win_rate=0.0,
                profit_loss_ratio=0.0,
                avg_trade_return=0.0,
                max_consecutive_losses=0,
                trades=[],
                equity_curve=[]
            )
        
        # 基础指标
        final_cash = self.equity_curve[-1]
        total_return = (final_cash - self.initial_cash) / self.initial_cash * 100
        
        # 年化收益
        days = (data['timestamp'].max() - data['timestamp'].min()).days
        if days > 0:
            annualized_return = ((final_cash / self.initial_cash) ** (365 / days) - 1) * 100
        else:
            annualized_return = 0.0
        
        # 夏普比率
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        if len(returns) > 0 and returns.std() != 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0
        
        # 最大回撤
        equity_series = pd.Series(self.equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()
        
        # 交易统计
        total_trades = len([t for t in self.trades if t['action'] in ['close_long', 'close_short']])
        
        # 计算盈亏
        trade_pnls = []
        for i, trade in enumerate(self.trades):
            if trade['action'] in ['close_long', 'close_short']:
                # 找到对应的开仓交易
                for prev_trade in reversed(self.trades[:i]):
                    if prev_trade['symbol'] == trade['symbol']:
                        if trade['action'] == 'close_long' and prev_trade['action'] == 'buy':
                            pnl = (trade['price'] - prev_trade['price']) * prev_trade['volume']
                            pnl -= (trade['commission'] + prev_trade['commission'])
                            trade_pnls.append(pnl)
                            break
                        elif trade['action'] == 'close_short' and prev_trade['action'] == 'sell':
                            pnl = (prev_trade['price'] - trade['price']) * prev_trade['volume']
                            pnl -= (trade['commission'] + prev_trade['commission'])
                            trade_pnls.append(pnl)
                            break
        
        # 胜率
        winning_trades = len([p for p in trade_pnls if p > 0])
        win_rate = (winning_trades / len(trade_pnls) * 100) if trade_pnls else 0.0
        
        # 盈亏比
        avg_win = np.mean([p for p in trade_pnls if p > 0]) if any(p > 0 for p in trade_pnls) else 0
        avg_loss = abs(np.mean([p for p in trade_pnls if p < 0])) if any(p < 0 for p in trade_pnls) else 1
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
        
        # 平均每笔收益
        avg_trade_return = np.mean(trade_pnls) if trade_pnls else 0.0
        
        # 最长连亏
        max_consecutive_losses = 0
        current_losses = 0
        for pnl in trade_pnls:
            if pnl < 0:
                current_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_losses = 0
        
        return BacktestResult(
            strategy_name=self.strategy.__class__.__name__,
            symbol=symbol,
            start_date=str(data['timestamp'].min()),
            end_date=str(data['timestamp'].max()),
            initial_cash=self.initial_cash,
            final_cash=final_cash,
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            total_trades=total_trades,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            avg_trade_return=avg_trade_return,
            max_consecutive_losses=max_consecutive_losses,
            trades=self.trades,
            equity_curve=self.equity_curve
        )
