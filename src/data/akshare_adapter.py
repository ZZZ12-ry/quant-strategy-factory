"""
Akshare 数据适配器 - 开源财经数据
"""
from typing import Optional, List
import pandas as pd
import numpy as np


class AkshareAdapter:
    """Akshare 适配器"""
    
    def __init__(self):
        """初始化 Akshare 适配器"""
        pass
    
    def get_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        frequency: str = "1d"
    ) -> pd.DataFrame:
        """
        获取 K 线数据
        
        Args:
            symbol: 品种代码
            start_date: 开始日期
            end_date: 结束日期
            frequency: 频率
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            import akshare as ak
        except ImportError:
            raise ImportError("Please install akshare: pip install akshare")
        
        # 解析品种类型
        if '.' in symbol:
            code, exchange = symbol.split('.')
            
            if exchange in ['SHF', 'DCE', 'CZCE']:
                # 期货
                return self._get_futures_bars(code, start_date, end_date)
            elif exchange in ['SZ', 'SH']:
                # A 股
                return self._get_stock_bars(symbol, start_date, end_date)
        else:
            # 默认按股票处理
            return self._get_stock_bars(symbol, start_date, end_date)
    
    def _get_stock_bars(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取股票日线数据"""
        import akshare as ak
        
        try:
            # 获取历史行情
            df = ak.stock_zh_a_hist(
                symbol=symbol.replace('.', ''),
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # 前复权
            )
            
            if df is None or len(df) == 0:
                return pd.DataFrame()
            
            # 格式转换
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
            print(f"Error fetching stock data: {e}")
            return pd.DataFrame()
    
    def _get_futures_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取期货日线数据"""
        import akshare as ak
        
        try:
            # 获取期货历史行情
            df = ak.futures_zh_daily_sina(symbol=code)
            
            if df is None or len(df) == 0:
                return pd.DataFrame()
            
            # 格式转换
            df = df.rename(columns={
                'date': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['symbol'] = code
            
            # 时间过滤
            df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
            
            return df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
        
        except Exception as e:
            print(f"Error fetching futures data: {e}")
            return pd.DataFrame()
    
    def get_symbols(self, market: str = "stock") -> List[str]:
        """获取品种列表"""
        import akshare as ak
        
        if market == "stock":
            try:
                df = ak.stock_info_a_code_name()
                return df['code'].tolist()
            except:
                return []
        elif market == "future":
            # 返回常见期货品种
            return [
                'RB', 'HC', 'I', 'J', 'JM',  # 黑色系
                'CU', 'AL', 'ZN', 'PB', 'NI',  # 有色金属
                'M', 'Y', 'P', 'CF', 'SR',  # 农产品
                'AU', 'AG',  # 贵金属
                'SC', 'BU',  # 能源化工
            ]
        else:
            return []
