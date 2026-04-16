"""
数据管理模块
"""
from src.data.data_manager import DataManager
from src.data.rqdata_adapter import RQDataAdapter
from src.data.tushare_adapter import TushareAdapter
from src.data.akshare_adapter import AkshareAdapter

__all__ = [
    'DataManager',
    'RQDataAdapter',
    'TushareAdapter',
    'AkshareAdapter',
]
