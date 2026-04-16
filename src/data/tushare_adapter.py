"""
Tushare 数据适配器 - Tushare Pro
"""
from typing import Optional, List
import pandas as pd


class TushareAdapter:
    """Tushare 适配器"""
    
    def __init__(self, token: str = None):
        """
        初始化 Tushare 适配器
        
        Args:
            token: Tushare Pro token
        """
        self.token = token
        self.pro = None
    
    def _init_client(self):
        """初始化 Tushare 客户端"""
        if self.pro is None:
            try:
                import tushare as ts
                if self.token:
                    ts.set_token(self.token)
                self.pro = ts.pro_api()
            except ImportError:
                raise ImportError("Please install tushare: pip install tushare")
    
    def get_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        frequency: str = "1d"
    ) -> pd.DataFrame:
        """
        获取 K 线数据（日线）
        
        Args:
            symbol: 品种代码 (如 000001.SZ)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            frequency: 频率 (仅支持 1d)
        
        Returns:
            DataFrame with OHLCV data
        """
        self._init_client()
        
        # 日期格式转换
        start = start_date.replace('-', '')
        end = end_date.replace('-', '')
        
        # 解析代码
        ts_code = symbol.replace('.', '')
        
        # 获取日线数据
        df = self.pro.daily(
            ts_code=ts_code,
            start_date=start,
            end_date=end
        )
        
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        # 格式转换
        df = df.rename(columns={
            'trade_date': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'vol': 'volume'
        })
        
        # 时间转换
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['symbol'] = symbol
        
        return df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
    
    def get_symbols(self, market: str = "stock") -> List[str]:
        """获取品种列表"""
        self._init_client()
        
        if market == "stock":
            df = self.pro.stock_basic(exchange='', list_status='L')
            return (df['ts_code'] + '.' + df['exchange']).tolist()
        else:
            return []
