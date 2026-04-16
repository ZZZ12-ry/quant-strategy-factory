"""
Barra 风格因子库
参考：MSCI Barra 风格因子模型

实现 10 大风格因子：
1. Beta - 市场敏感度
2. Momentum - 价格动量
3. Size - 市值规模
4. Value - 价值因子
5. Quality - 质量因子
6. Volatility - 波动率
7. Liquidity - 流动性
8. Growth - 成长性
9. Leverage - 杠杆率
10. Reversal - 短期反转
"""
import pandas as pd
import numpy as np
from typing import Dict, List


class BarraFactors:
    """Barra 风格因子库"""
    
    def __init__(self):
        self.factor_names = []
    
    def calculate_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有 Barra 风格因子
        
        Args:
            data: OHLCV 数据，需要包含 open/high/low/close/volume
        
        Returns:
            包含所有因子的 DataFrame
        """
        df = data.copy()
        
        df = self._calc_momentum_factors(df)
        df = self._calc_volatility_factors(df)
        df = self._calc_liquidity_factors(df)
        df = self._calc_reversal_factors(df)
        df = self._calc_value_factors(df)
        df = self._calc_quality_factors(df)
        df = self._calc_size_factors(df)
        df = self._calc_beta_factors(df)
        df = self._calc_growth_factors(df)
        df = self._calc_leverage_factors(df)
        
        # 去除 NaN
        df = df.dropna()
        
        return df
    
    def _calc_momentum_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """动量因子"""
        # 1-20 日动量
        for period in [1, 3, 5, 10, 20, 60]:
            df[f'mom_{period}d'] = df['close'].pct_change(period)
        
        # 加权动量（近期权重更大）
        df['mom_weighted'] = (
            0.5 * df['close'].pct_change(5) +
            0.3 * df['close'].pct_change(10) +
            0.2 * df['close'].pct_change(20)
        )
        
        # 去除最近 1 天的动量（避免短期反转效应）
        df['mom_12_1'] = df['close'].pct_change(12) - df['close'].pct_change(1)
        
        # 价格加速度
        df['mom_acceleration'] = df['mom_5d'] - df['mom_5d'].shift(5)
        
        # 成交量加权动量
        if 'volume' in df.columns:
            df['mom_volume_weighted'] = (
                df['close'].pct_change(5) * 
                df['volume'] / df['volume'].rolling(20).mean()
            )
        
        self.factor_names.extend([
            'mom_1d', 'mom_3d', 'mom_5d', 'mom_10d', 'mom_20d', 'mom_60d',
            'mom_weighted', 'mom_12_1', 'mom_acceleration', 'mom_volume_weighted'
        ])
        
        return df
    
    def _calc_volatility_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """波动率因子"""
        returns = df['close'].pct_change()
        
        # 历史波动率
        for period in [5, 10, 20, 60]:
            df[f'vol_{period}d'] = returns.rolling(period).std()
        
        # 相对波动率
        df['vol_ratio'] = df['vol_5d'] / (df['vol_20d'] + 1e-8)
        
        # 波动率偏度
        df['vol_skew'] = returns.rolling(20).skew()
        
        # 波动率峰度
        df['vol_kurtosis'] = returns.rolling(20).kurt()
        
        # Parkinson 波动率（用 high/low 估计）
        df['vol_parkinson'] = np.sqrt(
            (np.log(df['high'] / df['low'])) ** 2 / (4 * np.log(2))
        ).rolling(20).mean()
        
        # Garman-Klass 波动率
        df['vol_garman_klass'] = np.sqrt(
            0.5 * (np.log(df['high'] / df['low'])) ** 2 -
            (2 * np.log(2) - 1) * (np.log(df['close'] / df['open'])) ** 2
        ).rolling(20).mean()
        
        # 下行波动率
        negative_returns = returns.copy()
        negative_returns[negative_returns > 0] = 0
        df['vol_downside'] = negative_returns.rolling(20).std()
        
        self.factor_names.extend([
            'vol_5d', 'vol_10d', 'vol_20d', 'vol_60d',
            'vol_ratio', 'vol_skew', 'vol_kurtosis',
            'vol_parkinson', 'vol_garman_klass', 'vol_downside'
        ])
        
        return df
    
    def _calc_liquidity_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """流动性因子"""
        if 'volume' not in df.columns:
            return df
        
        # 成交量均线
        for period in [5, 10, 20, 60]:
            df[f'liq_vol_ma_{period}'] = df['volume'].rolling(period).mean()
        
        # 成交量变化率
        df['liq_vol_change'] = df['volume'].pct_change(5)
        
        # 成交量标准差
        df['liq_vol_std'] = df['volume'].rolling(20).std()
        
        # 换手率代理（成交量 / 价格）
        df['liq_turnover'] = df['volume'] / df['close']
        
        # Amihud 非流动性（收益率绝对值 / 成交量）
        returns = df['close'].pct_change().abs()
        df['liq_amihud'] = returns / (df['volume'] + 1e-8)
        df['liq_amihud_20d'] = df['liq_amihud'].rolling(20).mean()
        
        # 成交量集中度
        df['liq_vol_concentration'] = df['volume'] / (df['liq_vol_ma_20'] + 1e-8)
        
        self.factor_names.extend([
            'liq_vol_ma_5', 'liq_vol_ma_10', 'liq_vol_ma_20', 'liq_vol_ma_60',
            'liq_vol_change', 'liq_vol_std', 'liq_turnover',
            'liq_amihud', 'liq_amihud_20d', 'liq_vol_concentration'
        ])
        
        return df
    
    def _calc_reversal_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """短期反转因子"""
        returns = df['close'].pct_change()
        
        # 短期反转
        df['rev_1d'] = -returns
        df['rev_3d'] = -df['close'].pct_change(3)
        df['rev_5d'] = -df['close'].pct_change(5)
        
        # 相对于 MA 的偏离
        df['rev_vs_ma5'] = -(df['close'] / df['close'].rolling(5).mean() - 1)
        df['rev_vs_ma10'] = -(df['close'] / df['close'].rolling(10).mean() - 1)
        df['rev_vs_ma20'] = -(df['close'] / df['close'].rolling(20).mean() - 1)
        
        # 价格位置（20 日内）
        df['rev_price_position'] = (
            (df['close'] - df['low'].rolling(20).min()) /
            (df['high'].rolling(20).max() - df['low'].rolling(20).min() + 1e-8)
        )
        
        self.factor_names.extend([
            'rev_1d', 'rev_3d', 'rev_5d',
            'rev_vs_ma5', 'rev_vs_ma10', 'rev_vs_ma20',
            'rev_price_position'
        ])
        
        return df
    
    def _calc_value_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """价值因子（用技术指标代替基本面）"""
        # Z-Score（均值回归）
        for period in [10, 20, 60]:
            ma = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()
            df[f'val_zscore_{period}'] = (df['close'] - ma) / (std + 1e-8)
        
        # 布林带位置
        ma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        df['val_bb_position'] = (df['close'] - (ma20 - 2 * std20)) / (4 * std20 + 1e-8)
        
        # 相对强弱（RSI）
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['val_rsi'] = 100 - 100 / (1 + gain / (loss + 1e-8))
        
        self.factor_names.extend([
            'val_zscore_10', 'val_zscore_20', 'val_zscore_60',
            'val_bb_position', 'val_rsi'
        ])
        
        return df
    
    def _calc_quality_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """质量因子（趋势质量）"""
        # 趋势强度（R-squared）
        for period in [10, 20]:
            x = np.arange(period)
            df[f'qual_r2_{period}'] = df['close'].rolling(period).apply(
                lambda y: np.corrcoef(x, y)[0, 1] ** 2 if len(y) == period else 0
            )
        
        # 均线排列质量
        ma5 = df['close'].rolling(5).mean()
        ma10 = df['close'].rolling(10).mean()
        ma20 = df['close'].rolling(20).mean()
        
        df['qual_ma_alignment'] = (
            (ma5 > ma10).astype(int) + 
            (ma10 > ma20).astype(int) +
            (ma5 > ma20).astype(int)
        ) / 3.0
        
        # 价格一致性
        df['qual_consistency'] = df['close'].pct_change().rolling(20).apply(
            lambda x: (x > 0).sum() / len(x)
        )
        
        # 收益稳定性
        returns = df['close'].pct_change()
        df['qual_stability'] = returns.rolling(20).mean() / (returns.rolling(20).std() + 1e-8)
        
        self.factor_names.extend([
            'qual_r2_10', 'qual_r2_20',
            'qual_ma_alignment', 'qual_consistency', 'qual_stability'
        ])
        
        return df
    
    def _calc_size_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """规模因子"""
        if 'volume' in df.columns:
            # 成交金额（代理市值）
            df['size_amount'] = df['close'] * df['volume']
            df['size_amount_log'] = np.log(df['size_amount'] + 1)
            df['size_amount_ma20'] = df['size_amount'].rolling(20).mean()
            
            # 成交量规模
            df['size_volume_log'] = np.log(df['volume'] + 1)
        
        # 价格水平
        df['size_price_level'] = np.log(df['close'])
        
        self.factor_names.extend([
            'size_amount', 'size_amount_log', 'size_amount_ma20',
            'size_volume_log', 'size_price_level'
        ])
        
        return df
    
    def _calc_beta_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """Beta 因子（用自身波动率代替市场 Beta）"""
        returns = df['close'].pct_change()
        
        # 滚动 Beta（相对于自身均值的敏感度）
        df['beta_20d'] = returns.rolling(20).std() / (returns.std() + 1e-8)
        df['beta_60d'] = returns.rolling(60).std() / (returns.std() + 1e-8)
        
        # 上行/下行 Beta
        positive_returns = returns.copy()
        positive_returns[positive_returns < 0] = 0
        negative_returns = returns.copy()
        negative_returns[negative_returns > 0] = 0
        
        df['beta_upside'] = positive_returns.rolling(20).std() / (returns.rolling(20).std() + 1e-8)
        df['beta_downside'] = negative_returns.rolling(20).std() / (returns.rolling(20).std() + 1e-8)
        
        self.factor_names.extend([
            'beta_20d', 'beta_60d', 'beta_upside', 'beta_downside'
        ])
        
        return df
    
    def _calc_growth_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """成长因子"""
        # 价格成长率
        for period in [20, 60]:
            df[f'growth_{period}d'] = df['close'].pct_change(period)
        
        # 成交量成长率
        if 'volume' in df.columns:
            df['growth_volume_20d'] = df['volume'].rolling(20).mean() / (df['volume'].rolling(60).mean() + 1e-8)
        
        # 波动率成长
        returns = df['close'].pct_change()
        df['growth_vol'] = returns.rolling(10).std() / (returns.rolling(30).std() + 1e-8)
        
        self.factor_names.extend([
            'growth_20d', 'growth_60d', 'growth_volume_20d', 'growth_vol'
        ])
        
        return df
    
    def _calc_leverage_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """杠杆因子（用波动率/价格范围代替）"""
        # 日内波动幅度
        df['lev_intraday_range'] = (df['high'] - df['low']) / df['close']
        df['lev_intraday_range_ma'] = df['lev_intraday_range'].rolling(20).mean()
        
        # ATR / 价格（标准化波动）
        tr = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['lev_atr_ratio'] = tr.rolling(14).mean() / df['close']
        
        self.factor_names.extend([
            'lev_intraday_range', 'lev_intraday_range_ma', 'lev_atr_ratio'
        ])
        
        return df
    
    def get_factor_names(self) -> List[str]:
        """获取所有因子名称"""
        return list(set(self.factor_names))
    
    def get_factor_categories(self) -> Dict[str, List[str]]:
        """获取因子分类"""
        return {
            'Momentum': [f for f in self.factor_names if f.startswith('mom_')],
            'Volatility': [f for f in self.factor_names if f.startswith('vol_')],
            'Liquidity': [f for f in self.factor_names if f.startswith('liq_')],
            'Reversal': [f for f in self.factor_names if f.startswith('rev_')],
            'Value': [f for f in self.factor_names if f.startswith('val_')],
            'Quality': [f for f in self.factor_names if f.startswith('qual_')],
            'Size': [f for f in self.factor_names if f.startswith('size_')],
            'Beta': [f for f in self.factor_names if f.startswith('beta_')],
            'Growth': [f for f in self.factor_names if f.startswith('growth_')],
            'Leverage': [f for f in self.factor_names if f.startswith('lev_')],
        }


def test_barra_factors():
    """测试 Barra 因子"""
    print("\n" + "="*70)
    print("Barra 风格因子库 - 测试")
    print("="*70)
    
    # 获取真实数据
    try:
        import akshare as ak
        df = ak.futures_zh_daily_sina(symbol="RB2405")
        df = df.rename(columns={
            'open': 'open', 'high': 'high', 'low': 'low',
            'close': 'close', 'volume': 'volume'
        })
        df['timestamp'] = pd.to_datetime(df['date'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"\n[OK] 获取螺纹钢数据：{len(df)} 条")
    except:
        np.random.seed(42)
        n = 300
        close = 100 * np.exp(np.cumsum(np.random.randn(n) * 0.02))
        df = pd.DataFrame({
            'open': close * (1 + np.random.randn(n) * 0.005),
            'high': close * (1 + np.abs(np.random.randn(n) * 0.01)),
            'low': close * (1 - np.abs(np.random.randn(n) * 0.01)),
            'close': close,
            'volume': np.random.randint(10000, 50000, n),
            'timestamp': pd.date_range('2024-01-01', periods=n)
        })
        print(f"\n[SIM] 使用模拟数据：{len(df)} 条")
    
    # 计算因子
    barra = BarraFactors()
    df_with_factors = barra.calculate_all(df)
    
    # 统计
    factor_names = barra.get_factor_names()
    categories = barra.get_factor_categories()
    
    print(f"\n因子总数：{len(factor_names)}")
    print(f"有效数据行：{len(df_with_factors)}")
    
    print(f"\n因子分类:")
    for cat, factors in categories.items():
        print(f"  {cat}: {len(factors)} 个")
    
    # 因子有效性检验
    print(f"\n{'='*70}")
    print("因子有效性检验（IC 分析）")
    print(f"{'='*70}")
    
    # 计算未来 5 日收益
    df_with_factors['future_return_5d'] = df_with_factors['close'].shift(-5) / df_with_factors['close'] - 1
    df_valid = df_with_factors.dropna()
    
    from src.ml.factor_analyzer import FactorAnalyzer
    analyzer = FactorAnalyzer()
    
    # 选取部分因子分析
    factor_cols = [f for f in factor_names if f in df_valid.columns][:20]
    
    results = analyzer.batch_analyze(
        df_valid[factor_cols],
        df_valid['future_return_5d']
    )
    
    print(f"\nTop 10 有效因子:")
    print(f"{'因子':<25} {'IC':<10} {'多空收益%':<12}")
    print(f"{'-'*50}")
    
    for _, row in results.head(10).iterrows():
        print(f"{row['factor_name']:<25} {row['ic']:>8.4f} {row['long_short_return']*100:>10.2f}")
    
    print(f"\n{'='*70}")
    print(f"[OK] Barra 因子库测试完成")
    print(f"[OK] 共 {len(factor_names)} 个因子，{len(categories)} 个分类")
    print(f"{'='*70}")
    
    return barra, df_with_factors, results


if __name__ == "__main__":
    barra, data, results = test_barra_factors()
