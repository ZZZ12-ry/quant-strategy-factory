"""
本地数据适配器 - CSV/Parquet 文件
"""
from typing import Optional, List
import pandas as pd
import os


class LocalAdapter:
    """本地数据适配器"""
    
    def __init__(self, data_dir: str = "./data"):
        """
        初始化本地数据适配器
        
        Args:
            data_dir: 数据文件目录
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def get_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        frequency: str = "1d"
    ) -> pd.DataFrame:
        """
        从本地文件读取 K 线数据
        
        Args:
            symbol: 品种代码
            start_date: 开始日期
            end_date: 结束日期
            frequency: 频率
        
        Returns:
            DataFrame with OHLCV data
        """
        # 文件路径
        file_path = os.path.join(self.data_dir, f"{symbol}_{frequency}.csv")
        
        if not os.path.exists(file_path):
            # 尝试 parquet 格式
            file_path = os.path.join(self.data_dir, f"{symbol}_{frequency}.parquet")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        # 读取数据
        if file_path.endswith('.parquet'):
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path)
        
        # 时间过滤
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        return df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
    
    def save_bars(self, df: pd.DataFrame, symbol: str, frequency: str = "1d"):
        """保存数据到本地"""
        file_path = os.path.join(self.data_dir, f"{symbol}_{frequency}.csv")
        df.to_csv(file_path, index=False)
    
    def get_symbols(self, market: str = "stock") -> List[str]:
        """获取本地数据中的品种列表"""
        symbols = set()
        for file in os.listdir(self.data_dir):
            if file.endswith('.csv') or file.endswith('.parquet'):
                parts = file.replace('.csv', '').replace('.parquet', '').split('_')
                if len(parts) > 0:
                    symbols.add(parts[0])
        return list(symbols)
