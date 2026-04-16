"""
数据缓存模块
避免重复获取数据，提高效率

⚠️ 重要：减少 API 调用，加快回测速度
"""
import pandas as pd
import os
import json
from datetime import datetime
from typing import Dict, Optional


class DataCache:
    """
    数据缓存管理器
    
    功能：
    - 本地存储历史数据
    - 自动更新机制
    - 数据版本管理
    """
    
    def __init__(self, cache_dir: str = 'data/cache'):
        """
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # 缓存元数据
        self.metadata_file = os.path.join(cache_dir, 'metadata.json')
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """加载元数据"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        """保存元数据"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def save_data(self, symbol: str, data: pd.DataFrame, source: str = 'akshare'):
        """
        保存数据到缓存
        
        Args:
            symbol: 合约代码
            data: DataFrame
            source: 数据源
        """
        # 保存数据
        filepath = os.path.join(self.cache_dir, f'{symbol}.csv')
        data.to_csv(filepath, index=False)
        
        # 更新元数据
        self.metadata[symbol] = {
            'source': source,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'rows': len(data),
            'start_date': str(data['date'].min()) if 'date' in data.columns else 'N/A',
            'end_date': str(data['date'].max()) if 'date' in data.columns else 'N/A'
        }
        
        self._save_metadata()
        
        print(f"  [缓存] 保存 {symbol}: {len(data)} 条")
    
    def load_data(self, symbol: str, max_age_days: int = 7) -> Optional[pd.DataFrame]:
        """
        从缓存加载数据
        
        Args:
            symbol: 合约代码
            max_age_days: 最大缓存天数
        
        Returns:
            DataFrame 或 None
        """
        filepath = os.path.join(self.cache_dir, f'{symbol}.csv')
        
        if not os.path.exists(filepath):
            print(f"  [缓存] {symbol}: 无缓存")
            return None
        
        # 检查缓存时间
        if symbol in self.metadata:
            last_update = datetime.strptime(
                self.metadata[symbol]['last_update'],
                '%Y-%m-%d %H:%M:%S'
            )
            age_days = (datetime.now() - last_update).days
            
            if age_days > max_age_days:
                print(f"  [缓存] {symbol}: 缓存过期 ({age_days} 天)")
                return None
        
        # 加载数据
        try:
            df = pd.read_csv(filepath, parse_dates=['date'])
            print(f"  [缓存] 加载 {symbol}: {len(df)} 条")
            return df
        except Exception as e:
            print(f"  [缓存] {symbol}: 加载失败 {e}")
            return None
    
    def get_cache_status(self) -> pd.DataFrame:
        """获取缓存状态"""
        if not self.metadata:
            return pd.DataFrame()
        
        df = pd.DataFrame.from_dict(self.metadata, orient='index')
        return df
    
    def clear_cache(self, symbol: str = None):
        """
        清除缓存
        
        Args:
            symbol: 合约代码，None 表示清除所有
        """
        import glob
        
        if symbol:
            # 清除单个
            filepath = os.path.join(self.cache_dir, f'{symbol}.csv')
            if os.path.exists(filepath):
                os.remove(filepath)
                if symbol in self.metadata:
                    del self.metadata[symbol]
                    self._save_metadata()
                print(f"  [缓存] 清除 {symbol}")
        else:
            # 清除所有
            for filepath in glob.glob(os.path.join(self.cache_dir, '*.csv')):
                os.remove(filepath)
            self.metadata = {}
            self._save_metadata()
            print(f"  [缓存] 清除所有缓存")
    
    def auto_update(self, fetcher, symbols: list, max_age_days: int = 7):
        """
        自动更新缓存
        
        Args:
            fetcher: 数据获取器
            symbols: 合约列表
            max_age_days: 最大缓存天数
        """
        print(f"\n自动更新缓存...")
        print(f"  品种数：{len(symbols)}")
        
        for symbol in symbols:
            # 尝试加载缓存
            data = self.load_data(symbol, max_age_days)
            
            if data is None:
                # 缓存无效，重新获取
                print(f"\n获取 {symbol}...")
                data = fetcher.fetch_futures_daily(symbol)
                
                if data is not None:
                    self.save_data(symbol, data)
            else:
                print(f"✓ {symbol}: 使用缓存 ({len(data)} 条)")


def test_cache():
    """测试缓存功能"""
    print("\n" + "="*60)
    print("数据缓存测试")
    print("="*60)
    
    cache = DataCache()
    
    # 查看缓存状态
    print(f"\n当前缓存:")
    status = cache.get_cache_status()
    if not status.empty:
        print(status.to_string())
    else:
        print("  无缓存")
    
    # 测试保存
    print(f"\n测试保存...")
    import numpy as np
    test_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100),
        'open': 4000 + np.random.randn(100) * 50,
        'high': 4000 + np.random.randn(100) * 50,
        'low': 4000 + np.random.randn(100) * 50,
        'close': 4000 + np.random.randn(100) * 50,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    cache.save_data('TEST001', test_data)
    
    # 测试加载
    print(f"\n测试加载...")
    loaded = cache.load_data('TEST001')
    if loaded is not None:
        print(f"  加载成功：{len(loaded)} 条")
    
    # 清除测试数据
    cache.clear_cache('TEST001')
    
    print(f"\n[OK] 缓存测试完成")
    
    return cache


if __name__ == "__main__":
    cache = test_cache()
