"""
RQData 数据适配器 - 米筐数据
"""
from typing import Optional, List
import pandas as pd


class RQDataAdapter:
    """RQData 适配器"""
    
    def __init__(self, username: str = None, password: str = None):
        """
        初始化 RQData 适配器
        
        Args:
            username: RQData 用户名
            password: RQData 密码
        """
        self.username = username
        self.password = password
        self.initialized = False
    
    def _init_client(self):
        """初始化 RQData 客户端"""
        if not self.initialized:
            try:
                import rqdatac
                if self.username and self.password:
                    rqdatac.init(self.username, self.password)
                else:
                    rqdatac.init()
                self.initialized = True
            except ImportError:
                raise ImportError("Please install rqdatac: pip install rqdatac")
    
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
            frequency: 频率 (1d/1h/1m)
        
        Returns:
            DataFrame with OHLCV data
        """
        self._init_client()
        import rqdatac
        
        # 频率映射
        freq_map = {
            "1d": "1d",
            "1h": "1h",
            "30m": "30m",
            "1m": "1m"
        }
        freq = freq_map.get(frequency, "1d")
        
        # 获取数据
        df = rqdatac.get_price(
            symbol,
            start_date=start_date,
            end_date=end_date,
            frequency=freq,
            adjust='none'
        )
        
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        # 格式转换
        df = df.reset_index()
        df = df.rename(columns={
            'time': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })
        
        df['symbol'] = symbol
        
        return df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
    
    def get_symbols(self, market: str = "stock") -> List[str]:
        """获取品种列表"""
        self._init_client()
        import rqdatac
        
        if market == "stock":
            stocks = rqdatac.all_instruments(type='CS', market='cn')
            return stocks['order_book_id'].tolist()
        elif market == "future":
            futures = rqdatac.all_instruments(type='Future', market='cn')
            return futures['order_book_id'].tolist()
        else:
            return []
