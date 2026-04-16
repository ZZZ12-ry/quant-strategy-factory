"""
成交量策略 v3 - 优化版
包含：最佳参数 + 交易成本 + 多品种测试
"""
from src.strategies.volume_night_day import VolumeNightDayStrategyV2
import pandas as pd
import numpy as np
from datetime import datetime


def backtest_with_cost(strategy, df, commission=0.0003):
    """带交易成本的回测"""
    strategy.reset()
    trades = []
    current_trade = None
    equity_curve = [1.0]  # 净值曲线
    
    for idx, row in df.iterrows():
        signal = strategy.on_bar(row)
        if signal:
            if signal.direction in ['long', 'short']:
                current_trade = {
                    'entry_time': signal.timestamp,
                    'entry_price': signal.price,
                    'direction': signal.direction,
                    'strength': signal.strength
                }
            elif current_trade:
                pnl_pct = (signal.price - current_trade['entry_price']) / current_trade['entry_price']
                if current_trade['direction'] == 'short':
                    pnl_pct = -pnl_pct
                # 扣除双边手续费
                pnl_pct -= commission * 2
                
                current_trade['exit_time'] = signal.timestamp
                current_trade['exit_price'] = signal.price
                current_trade['exit_type'] = signal.symbol.replace('volume_', '')
                current_trade['pnl_pct'] = pnl_pct
                trades.append(current_trade)
                
                equity_curve.append(equity_curve[-1] * (1 + pnl_pct))
                current_trade = None
    
    return trades, equity_curve


def calc_metrics(trades, equity_curve):
    """计算完整绩效指标"""
    if not trades:
        return {}
    
    returns = [t['pnl_pct'] for t in trades]
    winning = [r for r in returns if r > 0]
    losing = [r for r in returns if r <= 0]
    
    # 最大回撤
    equity = np.array(equity_curve)
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / peak
    max_dd = np.max(drawdown) * 100
    
    # 年化收益（假设每笔交易约 5 天）
    total_days = len(equity_curve) * 5
    annual_factor = 252 / max(total_days, 1)
    total_return = (equity_curve[-1] / equity_curve[0] - 1) * 100
    annual_return = ((equity_curve[-1] / equity_curve[0]) ** annual_factor - 1) * 100
    
    metrics = {
        'total_return': total_return,
        'annual_return': annual_return,
        'sharpe': np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252),
        'calmar': annual_return / (max_dd + 1e-8),
        'win_rate': len(winning) / len(returns) * 100,
        'avg_win': np.mean(winning) * 100 if winning else 0,
        'avg_loss': np.mean(losing) * 100 if losing else 0,
        'profit_factor': abs(sum(winning) / (sum(losing) + 1e-8)),
        'max_drawdown': max_dd,
        'total_trades': len(trades),
        'final_equity': equity_curve[-1],
    }
    
    return metrics


def print_metrics(metrics, title=""):
    """打印绩效指标"""
    if title:
        print(f"\n  {title}")
        print(f"  " + "-"*50)
    
    print(f"  总收益率：{metrics.get('total_return', 0):.2f}%")
    print(f"  夏普比率：{metrics.get('sharpe', 0):.2f}")
    print(f"  胜    率：{metrics.get('win_rate', 0):.1f}%")
    print(f"  盈 亏 比：{abs(metrics.get('avg_win', 0) / (metrics.get('avg_loss', 1))):.2f}")
    print(f"  最大回撤：{metrics.get('max_drawdown', 0):.2f}%")
    print(f"  交易次数：{metrics.get('total_trades', 0)}")
    print(f"  最终净值：{metrics.get('final_equity', 1):.4f}")


def run_full_optimization():
    """完整优化流程"""
    print("\n" + "="*70)
    print("成交量策略完整优化流程")
    print("="*70)
    
    # ========== 第一步：获取多品种数据 ==========
    print("\n[Step 1] 获取多品种数据...")
    
    datasets = {}
    symbols = {
        'RB2405': '螺纹钢',
        'HC2405': '热卷',
        'CU2405': '沪铜',
        'AL2405': '沪铝',
        'AU2412': '黄金',
    }
    
    try:
        import akshare as ak
        for symbol, name in symbols.items():
            try:
                df = ak.futures_zh_daily_sina(symbol=symbol)
                df = df.rename(columns={
                    'open': 'open', 'high': 'high', 'low': 'low',
                    'close': 'close', 'volume': 'volume'
                })
                df['timestamp'] = pd.to_datetime(df['date'])
                df = df.sort_values('timestamp').reset_index(drop=True)
                if len(df) > 50:
                    datasets[symbol] = {'name': name, 'data': df}
                    print(f"  [OK] {name}({symbol}): {len(df)} 条")
            except Exception as e:
                print(f"  [FAIL] {name}({symbol}): {e}")
    except ImportError:
        print("  [WARN] Akshare 未安装，使用模拟数据")
    
    # 如果没有真实数据，生成模拟数据
    if not datasets:
        print("  使用模拟数据...")
        np.random.seed(42)
        for i, (symbol, name) in enumerate(symbols.items()):
            np.random.seed(42 + i)
            n = 300
            returns = np.random.randn(n) * 0.02 + 0.0002
            close = 100 * np.exp(np.cumsum(returns))
            volume = (np.random.randint(10000, 50000, n) + np.abs(returns) * 100000).astype(int)
            df = pd.DataFrame({
                'open': close * (1 + np.random.randn(n) * 0.005),
                'high': close * (1 + np.abs(np.random.randn(n) * 0.01)),
                'low': close * (1 - np.abs(np.random.randn(n) * 0.01)),
                'close': close, 'volume': volume,
                'timestamp': pd.date_range('2024-01-01', periods=n)
            })
            datasets[symbol] = {'name': name, 'data': df}
            print(f"  [SIM] {name}({symbol}): {len(df)} 条")
    
    # ========== 第二步：用优化后参数回测 ==========
    print(f"\n[Step 2] 使用优化后参数回测...")
    
    # 优化后的最佳参数
    best_params = {
        'volume_ma_period': 20,
        'volume_zscore_threshold': 1.5,
        'price_ma_period': 25,
        'momentum_period': 5,
        'stop_loss_pct': 0.025,
        'take_profit_pct': 0.04,
        'trailing_stop_pct': 0.015,
    }
    
    print(f"\n  最优参数（夏普比率最大化）:")
    for key, value in best_params.items():
        print(f"    {key}: {value}")
    
    # 默认参数对比
    default_params = {
        'volume_ma_period': 20,
        'volume_zscore_threshold': 1.5,
        'price_ma_period': 20,
        'momentum_period': 5,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.04,
        'trailing_stop_pct': 0.015,
    }
    
    # ========== 第三步：多品种回测 ==========
    print(f"\n[Step 3] 多品种回测（含交易成本）...")
    print(f"  交易成本：双边 0.06%（手续费 0.03%/边）")
    
    all_results = {}
    
    for symbol, info in datasets.items():
        name = info['name']
        data = info['data']
        
        # 优化后参数
        strategy_opt = VolumeNightDayStrategyV2(**best_params)
        trades_opt, equity_opt = backtest_with_cost(strategy_opt, data)
        metrics_opt = calc_metrics(trades_opt, equity_opt)
        
        # 默认参数
        strategy_def = VolumeNightDayStrategyV2(**default_params)
        trades_def, equity_def = backtest_with_cost(strategy_def, data)
        metrics_def = calc_metrics(trades_def, equity_def)
        
        all_results[symbol] = {
            'name': name,
            'optimized': metrics_opt,
            'default': metrics_def,
            'trades_opt': trades_opt,
            'equity_opt': equity_opt,
        }
    
    # ========== 第四步：输出结果 ==========
    print(f"\n[Step 4] 回测结果对比")
    print(f"\n{'='*70}")
    print(f"{'品种':<10} {'参数':<8} {'收益%':<10} {'夏普':<8} {'胜率%':<8} {'回撤%':<10} {'交易数':<8}")
    print(f"{'-'*70}")
    
    for symbol, result in all_results.items():
        name = result['name']
        
        opt = result['optimized']
        if opt:
            print(f"{name:<10} {'优化':<8} {opt.get('total_return',0):>8.2f} {opt.get('sharpe',0):>6.2f} {opt.get('win_rate',0):>6.1f} {opt.get('max_drawdown',0):>8.2f} {opt.get('total_trades',0):>6}")
        
        default = result['default']
        if default:
            print(f"{'':>10} {'默认':<8} {default.get('total_return',0):>8.2f} {default.get('sharpe',0):>6.2f} {default.get('win_rate',0):>6.1f} {default.get('max_drawdown',0):>8.2f} {default.get('total_trades',0):>6}")
        
        print(f"{'-'*70}")
    
    # ========== 第五步：详细交易记录（最佳品种） ==========
    best_symbol = max(all_results.keys(), key=lambda s: all_results[s]['optimized'].get('total_return', 0))
    best_result = all_results[best_symbol]
    
    print(f"\n[Step 5] 最佳品种详细记录：{best_result['name']}({best_symbol})")
    print_metrics(best_result['optimized'], "优化后绩效")
    
    trades = best_result['trades_opt']
    if trades:
        print(f"\n  交易明细（前 15 笔）:")
        for i, t in enumerate(trades[:15], 1):
            direction = "LONG " if t['direction'] == 'long' else "SHORT"
            pnl_str = f"+{t['pnl_pct']*100:.2f}%" if t['pnl_pct'] > 0 else f"{t['pnl_pct']*100:.2f}%"
            print(f"    {i:>2}. {direction} | {t['entry_price']:.2f} -> {t['exit_price']:.2f} | {pnl_str:>8} | {t.get('exit_type','')}")
    
    # ========== 第六步：总结 ==========
    print(f"\n{'='*70}")
    print("优化总结")
    print(f"{'='*70}")
    
    # 统计所有品种的平均表现
    opt_returns = [r['optimized'].get('total_return', 0) for r in all_results.values() if r['optimized']]
    def_returns = [r['default'].get('total_return', 0) for r in all_results.values() if r['default']]
    
    print(f"\n  优化后参数 vs 默认参数（平均）:")
    print(f"    优化后平均收益：{np.mean(opt_returns):.2f}%")
    print(f"    默认参数平均收益：{np.mean(def_returns):.2f}%")
    print(f"    提升：{np.mean(opt_returns) - np.mean(def_returns):.2f}%")
    
    print(f"\n  最佳参数组合:")
    for key, value in best_params.items():
        print(f"    {key}: {value}")
    
    profitable = sum(1 for r in opt_returns if r > 0)
    print(f"\n  品种胜率：{profitable}/{len(opt_returns)} ({profitable/len(opt_returns)*100:.0f}%)")
    
    print(f"\n{'='*70}")
    print("[OK] 优化完成")
    print(f"{'='*70}")
    
    return all_results, best_params


if __name__ == "__main__":
    results, best_params = run_full_optimization()
