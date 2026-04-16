"""
数据获取模块 - 支持多种数据源
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List


class DataFetcher:
    """数据获取器"""
    
    def __init__(self, source: str = "akshare"):
        """
        初始化数据获取器
        
        Args:
            source: 数据源 (akshare/rqdata/tushare/local)
        """
        self.source = source
    
    def fetch_stock_data(
        self,
        symbol: str = "000001",
        start_date: str = "20230101",
        end_date: str = "20231231",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取 A 股日线数据
        
        Args:
            symbol: 股票代码 (如 000001)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            adjust: 复权类型 (qfq/hfq/None)
        
        Returns:
            DataFrame with OHLCV
        """
        if self.source == "akshare":
            return self._fetch_akshare(symbol, start_date, end_date, adjust)
        elif self.source == "local":
            return self._fetch_local(symbol, start_date, end_date)
        else:
            return self._generate_sample(symbol, start_date, end_date)
    
    def _fetch_akshare(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str
    ) -> pd.DataFrame:
        """从 Akshare 获取数据"""
        try:
            import akshare as ak
        except ImportError:
            print("❌ 请安装 akshare: pip install akshare")
            return self._generate_sample(symbol, start_date, end_date)
        
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            # 格式转换
            df = df.rename(columns={
                '日期': 'timestamp',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['symbol'] = symbol
            
            # 选择必需列
            required_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
            available_cols = [col for col in required_cols if col in df.columns]
            
            return df[available_cols]
        
        except Exception as e:
            print(f"⚠️ Akshare 获取数据失败：{e}")
            print("   使用模拟数据代替")
            return self._generate_sample(symbol, start_date, end_date)
    
    def _fetch_local(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """从本地文件获取数据"""
        import os
        file_path = f"./data/{symbol}.csv"
        
        if not os.path.exists(file_path):
            print(f"⚠️ 本地文件不存在：{file_path}")
            return self._generate_sample(symbol, start_date, end_date)
        
        df = pd.read_csv(file_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 时间过滤
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        return df
    
    def _generate_sample(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """生成模拟数据（用于测试）"""
        np.random.seed(42)
        
        dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日
        n_days = len(dates)
        
        # 几何布朗运动
        initial_price = 10.0
        returns = np.random.normal(0.0005, 0.025, n_days)
        price_series = initial_price * np.cumprod(1 + returns)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'symbol': symbol,
            'open': price_series * (1 + np.random.uniform(-0.01, 0.01, n_days)),
            'high': price_series * (1 + np.random.uniform(0, 0.03, n_days)),
            'low': price_series * (1 - np.random.uniform(0, 0.03, n_days)),
            'close': price_series,
            'volume': np.random.randint(10000, 1000000, n_days)
        })
        
        return df
    
    def fetch_index_data(
        self,
        symbol: str = "000001",  # 上证指数
        start_date: str = "20230101",
        end_date: str = "20231231"
    ) -> pd.DataFrame:
        """获取指数数据"""
        if self.source == "akshare":
            try:
                import akshare as ak
                df = ak.stock_zh_index_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date
                )
                
                df = df.rename(columns={
                    '日期': 'timestamp',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume'
                })
                
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['symbol'] = symbol
                
                return df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
            
            except Exception as e:
                print(f"⚠️ 指数数据获取失败：{e}")
        
        return self._generate_sample(symbol, start_date, end_date)
    
    def fetch_multiple_stocks(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """获取多只股票数据"""
        all_data = []
        
        for symbol in symbols:
            print(f"  获取 {symbol} 数据...")
            df = self.fetch_stock_data(symbol, start_date, end_date)
            if len(df) > 0:
                all_data.append(df)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def save_to_csv(self, df: pd.DataFrame, symbol: str):
        """保存数据到本地"""
        import os
        os.makedirs("./data", exist_ok=True)
        
        file_path = f"./data/{symbol}.csv"
        df.to_csv(file_path, index=False)
        print(f"✅ 数据已保存：{file_path}")


def test_data_fetch():
    """测试数据获取"""
    print("=" * 60)
    print("测试数据获取模块")
    print("=" * 60)
    
    fetcher = DataFetcher(source="akshare")
    
    # 测试获取单只股票
    print("\n[测试 1] 获取平安银行数据...")
    data = fetcher.fetch_stock_data("000001", "20230101", "20231231")
    
    if len(data) > 0:
        print(f"✅ 成功获取数据：{len(data)} 条")
        print(f"   时间范围：{data['timestamp'].min()} ~ {data['timestamp'].max()}")
        print(f"   数据列：{data.columns.tolist()}")
        print(f"\n   前 5 行:")
        print(data.head())
        
        # 保存
        fetcher.save_to_csv(data, "000001")
    else:
        print("❌ 数据获取失败")
    
    # 测试获取多只股票
    print("\n[测试 2] 获取多只股票数据...")
    symbols = ["000001", "000002", "600000", "601318"]
    multi_data = fetcher.fetch_multiple_stocks(symbols, "20230101", "20230630")
    
    if len(multi_data) > 0:
        print(f"✅ 成功获取 {len(symbols)} 只股票数据")
        print(f"   总数据量：{len(multi_data)} 条")
        print(f"   股票列表：{multi_data['symbol'].unique().tolist()}")
    
    print("\n" + "=" * 60)
    print("数据获取测试完成")
    print("=" * 60)
    
    return data


if __name__ == "__main__":
    test_data_fetch()
