"""
数据管理器 - 统一数据接口
"""
from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime


class DataManager:
    """数据管理器"""
    
    def __init__(self, data_source: str = "akshare", **kwargs):
        """
        初始化数据管理器
        
        Args:
            data_source: 数据源类型 (rqdata/tushare/akshare/local)
            **kwargs: 数据源配置参数
        """
        self.data_source = data_source
        self.adapter = self._create_adapter(data_source, **kwargs)
        self.cache: Dict[str, pd.DataFrame] = {}
    
    def _create_adapter(self, data_source: str, **kwargs) -> Any:
        """创建数据源适配器"""
        if data_source == "rqdata":
            from src.data.rqdata_adapter import RQDataAdapter
            return RQDataAdapter(**kwargs)
        elif data_source == "tushare":
            from src.data.tushare_adapter import TushareAdapter
            return TushareAdapter(**kwargs)
        elif data_source == "akshare":
            from src.data.akshare_adapter import AkshareAdapter
            return AkshareAdapter(**kwargs)
        elif data_source == "local":
            from src.data.local_adapter import LocalAdapter
            return LocalAdapter(**kwargs)
        else:
            raise ValueError(f"Unknown data source: {data_source}")
    
    def get_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        frequency: str = "1d",
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取 K 线数据
        
        Args:
            symbol: 品种代码 (如 RB.SHF, 000001.SZ)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            frequency: 频率 (1d/1h/1m)
            use_cache: 是否使用缓存
        
        Returns:
            DataFrame: 包含 timestamp/open/high/low/close/volume
        """
        cache_key = f"{symbol}_{start_date}_{end_date}_{frequency}"
        
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key].copy()
        
        # 获取数据
        df = self.adapter.get_bars(symbol, start_date, end_date, frequency)
        
        # 数据验证
        df = self._validate_data(df)
        
        # 缓存
        if use_cache:
            self.cache[cache_key] = df
        
        return df
    
    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证和清洗数据"""
        if df is None or len(df) == 0:
            raise ValueError("No data returned")
        
        # 必需列
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # 时间排序
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 去除重复
        df = df.drop_duplicates(subset=['timestamp'], keep='last')
        
        # 添加 symbol 列（如果没有）
        if 'symbol' not in df.columns:
            df['symbol'] = 'UNKNOWN'
        
        return df
    
    def get_symbols(self, market: str = "stock") -> List[str]:
        """获取品种列表"""
        return self.adapter.get_symbols(market)
    
    def clear_cache(self):
        """清除缓存"""
        self.cache.clear()
    
    def set_data_source(self, data_source: str, **kwargs):
        """切换数据源"""
        self.adapter = self._create_adapter(data_source, **kwargs)
