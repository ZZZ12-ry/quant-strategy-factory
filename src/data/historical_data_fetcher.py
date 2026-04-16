"""
历史数据获取与批量回测
获取 3-5 年期货数据，进行多品种回测

⚠️ 重要：这是验证策略稳定性的关键
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import time


class HistoricalDataFetcher:
    """
    历史数据获取器
    
    支持：
    - 国内商品期货（AKShare）
    - 多品种批量获取
    - 数据清洗和存储
    """
    
    def __init__(self, data_source='akshare'):
        self.data_source = data_source
        self.cache = {}
    
    def fetch_futures_daily(self, 
                           symbol: str,
                           start_date: str = '20200101',
                           end_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取期货日线数据
        
        Args:
            symbol: 合约代码（如 RB2405）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
        
        Returns:
            DataFrame with OHLCV
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        try:
            import akshare as ak
            
            print(f"  获取 {symbol} 数据...")
            df = ak.futures_zh_daily_sina(symbol=symbol)
            
            if df.empty:
                print(f"  [WARN] {symbol} 无数据")
                return None
            
            # 数据清洗
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'date': 'date'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            df = df.sort_values('date').reset_index(drop=True)
            
            # 添加合约信息
            df['symbol'] = symbol
            
            print(f"  [OK] {symbol}: {len(df)} 条")
            
            return df
            
        except Exception as e:
            print(f"  [FAIL] {symbol}: {e}")
            return None
    
    def fetch_multiple_contracts(self,
                                symbols: List[str],
                                start_date: str = '20200101',
                                end_date: str = None) -> Dict[str, pd.DataFrame]:
        """
        批量获取多个合约数据
        
        Args:
            symbols: 合约列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            {symbol: DataFrame}
        """
        print(f"\n批量获取数据...")
        print(f"  合约数：{len(symbols)}")
        print(f"  时间范围：{start_date} - {end_date}")
        
        results = {}
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] {symbol}")
            df = self.fetch_futures_daily(symbol, start_date, end_date)
            
            if df is not None:
                results[symbol] = df
            
            # 避免请求过快
            time.sleep(0.5)
        
        print(f"\n{'='*60}")
        print(f"获取完成：{len(results)}/{len(symbols)} 个合约")
        
        return results
    
    def get_continuous_contract(self,
                               variety: str,
                               start_date: str = '20200101',
                               end_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取连续合约（主力合约拼接）
        
        Args:
            variety: 品种代码（如 RB, CU, AU）
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            连续合约数据
        """
        # 主力合约列表（需要根据实际月份调整）
        # 这里简化处理，实际需要更复杂的逻辑
        print(f"\n获取 {variety} 连续合约...")
        
        # 尝试获取主力合约
        try:
            import akshare as ak
            
            # 获取主力合约连续数据
            df = ak.futures_zh_continuous_sina(symbol=variety)
            
            if df.empty:
                return None
            
            df = df.rename(columns={
                'open': 'open', 'high': 'high', 'low': 'low',
                'close': 'close', 'volume': 'volume', 'date': 'date'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df['symbol'] = f'{variety}_continuous'
            
            print(f"  [OK] {variety}: {len(df)} 条")
            
            return df
            
        except Exception as e:
            print(f"  [FAIL] {variety}: {e}")
            return None
    
    def save_to_csv(self, data_dict: Dict[str, pd.DataFrame], output_dir: str):
        """保存数据到 CSV"""
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        for symbol, df in data_dict.items():
            filepath = os.path.join(output_dir, f'{symbol}.csv')
            df.to_csv(filepath, index=False)
            print(f"  保存：{filepath}")
    
    def load_from_csv(self, input_dir: str) -> Dict[str, pd.DataFrame]:
        """从 CSV 加载数据"""
        import os
        import glob
        
        results = {}
        
        for filepath in glob.glob(os.path.join(input_dir, '*.csv')):
            symbol = os.path.basename(filepath).replace('.csv', '')
            df = pd.read_csv(filepath, parse_dates=['date'])
            results[symbol] = df
            print(f"  加载：{symbol} ({len(df)} 条)")
        
        return results


class BatchBacktester:
    """
    批量回测器
    
    功能：
    - 多品种批量回测
    - 绩效统计对比
    - 生成回测报告
    """
    
    def __init__(self, strategy_func, initial_capital=1000000):
        self.strategy_func = strategy_func
        self.initial_capital = initial_capital
        self.results = {}
    
    def backtest_single(self,
                       data: pd.DataFrame,
                       symbol: str) -> Dict:
        """
        单个品种回测
        
        Returns:
            绩效指标
        """
        try:
            # 运行策略
            metrics = self.strategy_func(data)
            metrics['symbol'] = symbol
            metrics['data_length'] = len(data)
            
            return metrics
            
        except Exception as e:
            print(f"  [FAIL] {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e)
            }
    
    def backtest_multiple(self,
                         data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        多品种批量回测
        
        Args:
            data_dict: {symbol: DataFrame}
        
        Returns:
            回测结果汇总
        """
        print(f"\n{'='*60}")
        print(f"批量回测")
        print(f"{'='*60}")
        print(f"品种数：{len(data_dict)}")
        
        results = []
        
        for i, (symbol, data) in enumerate(data_dict.items(), 1):
            print(f"\n[{i}/{len(data_dict)}] {symbol}")
            
            metrics = self.backtest_single(data, symbol)
            results.append(metrics)
        
        # 转换为 DataFrame
        df_results = pd.DataFrame(results)
        
        # 排序
        if 'total_return' in df_results.columns:
            df_results = df_results.sort_values('total_return', ascending=False)
        
        # 打印汇总
        print(f"\n{'='*60}")
        print(f"回测汇总")
        print(f"{'='*60}")
        
        print(f"\n{df_results[['symbol', 'total_return', 'sharpe', 'max_drawdown']].to_string()}")
        
        # 统计
        profitable = (df_results['total_return'] > 0).sum() if 'total_return' in df_results.columns else 0
        print(f"\n盈利品种：{profitable}/{len(data_dict)}")
        
        self.results = df_results
        
        return df_results
    
    def generate_report(self, output_file: str = 'backtest_report.html'):
        """生成回测报告"""
        if self.results.empty:
            print("[WARN] 无回测结果")
            return
        
        # 生成 HTML 报告
        html = f"""
        <html>
        <head>
            <title>批量回测报告</title>
            <style>
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>批量回测报告</h1>
            <p>生成时间：{datetime.now()}</p>
            <p>品种数：{len(self.results)}</p>
            {self.results.to_html(index=False)}
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n[OK] 报告已保存：{output_file}")


def test_historical_data():
    """测试历史数据获取"""
    print("\n" + "="*60)
    print("历史数据获取测试")
    print("="*60)
    
    fetcher = HistoricalDataFetcher()
    
    # 测试品种列表
    test_symbols = [
        'RB2405',  # 螺纹钢
        'HC2405',  # 热卷
        'CU2405',  # 沪铜
        'AL2405',  # 沪铝
        'AU2412',  # 黄金
    ]
    
    # 获取数据
    data = fetcher.fetch_multiple_contracts(
        test_symbols,
        start_date='20230101',
        end_date='20241231'
    )
    
    # 保存数据
    if data:
        fetcher.save_to_csv(data, 'data/historical_futures')
    
    return fetcher, data


def test_batch_backtest(data_dict: Dict[str, pd.DataFrame]):
    """测试批量回测"""
    print("\n" + "="*60)
    print("批量回测测试")
    print("="*60)
    
    # 定义简单策略
    def simple_strategy(data):
        """简单双均线策略"""
        if len(data) < 50:
            return {'total_return': 0, 'sharpe': 0, 'max_drawdown': 0}
        
        # 计算均线
        ma5 = data['close'].rolling(5).mean()
        ma20 = data['close'].rolling(20).mean()
        
        # 生成信号
        signals = np.where(ma5 > ma20, 1, -1)
        
        # 计算收益
        returns = data['close'].pct_change()
        strategy_returns = signals.shift(1) * returns
        
        # 绩效指标
        total_return = (1 + strategy_returns).prod() - 1
        sharpe = strategy_returns.mean() / (strategy_returns.std() + 1e-8) * np.sqrt(252)
        max_dd = ((1 + strategy_returns).cummax() - (1 + strategy_returns).cumsum()).max()
        
        return {
            'total_return': total_return * 100,
            'sharpe': sharpe,
            'max_drawdown': max_dd * 100
        }
    
    # 创建回测器
    backtester = BatchBacktester(simple_strategy, initial_capital=1000000)
    
    # 批量回测
    results = backtester.backtest_multiple(data_dict)
    
    # 生成报告
    backtester.generate_report('backtest_report.html')
    
    return backtester, results


if __name__ == "__main__":
    # 测试 1: 获取历史数据
    fetcher, data = test_historical_data()
    
    # 测试 2: 批量回测
    if data:
        backtester, results = test_batch_backtest(data)
