"""
机器学习因子挖掘示例 - 使用 scikit-learn
"""
import sys
sys.path.insert(0, '..')

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


def generate_features(data: pd.DataFrame) -> pd.DataFrame:
    """生成技术因子"""
    df = data.copy()
    
    # 动量因子
    df['return_1d'] = df['close'].pct_change(1)
    df['return_5d'] = df['close'].pct_change(5)
    df['return_10d'] = df['close'].pct_change(10)
    
    # 均线因子
    df['ma_5'] = df['close'].rolling(5).mean()
    df['ma_10'] = df['close'].rolling(10).mean()
    df['ma_20'] = df['close'].rolling(20).mean()
    df['price_vs_ma5'] = df['close'] / df['ma_5'] - 1
    df['price_vs_ma10'] = df['close'] / df['ma_10'] - 1
    df['ma5_vs_ma10'] = df['ma_5'] / df['ma_10'] - 1
    
    # 波动率因子
    df['volatility_5d'] = df['return_1d'].rolling(5).std()
    df['volatility_10d'] = df['return_1d'].rolling(10).std()
    
    # 成交量因子
    df['volume_ma5'] = df['volume'].rolling(5).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma5']
    
    # 高低位因子
    df['high_low_range'] = (df['high'] - df['low']) / df['close']
    df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
    
    return df


def create_labels(data: pd.DataFrame, horizon: int = 5) -> pd.Series:
    """
    创建预测标签
    
    Args:
        data: 数据
        horizon: 预测周期
    
    Returns:
        标签（1=上涨，0=下跌）
    """
    future_return = data['close'].shift(-horizon) / data['close'] - 1
    labels = (future_return > 0).astype(int)
    return labels


def main():
    print("=" * 60)
    print("机器学习因子挖掘示例")
    print("=" * 60)
    
    # 1. 生成模拟数据
    print("\n[1/4] 生成数据...")
    np.random.seed(42)
    
    n_days = 1000
    dates = pd.date_range(start="2022-01-01", periods=n_days, freq='D')
    
    returns = np.random.normal(0.0005, 0.02, n_days)
    price_series = 4000 * np.cumprod(1 + returns)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'symbol': 'RB.SHF',
        'open': price_series,
        'high': price_series * 1.02,
        'low': price_series * 0.98,
        'close': price_series,
        'volume': np.random.randint(1000, 10000, n_days)
    })
    
    print(f"数据量：{len(data)} 条")
    
    # 2. 生成因子
    print("\n[2/4] 生成技术因子...")
    df = generate_features(data)
    df = df.dropna()  # 去除 NaN
    
    feature_cols = [
        'return_1d', 'return_5d', 'return_10d',
        'price_vs_ma5', 'price_vs_ma10', 'ma5_vs_ma10',
        'volatility_5d', 'volatility_10d',
        'volume_ratio', 'high_low_range', 'close_position'
    ]
    
    X = df[feature_cols]
    y = create_labels(df, horizon=5)
    
    # 对齐
    common_idx = X.index.intersection(y.dropna().index)
    X = X.loc[common_idx]
    y = y.loc[common_idx]
    
    print(f"因子数量：{len(feature_cols)}")
    print(f"样本数量：{len(X)}")
    
    # 3. 训练模型
    print("\n[3/4] 训练随机森林模型...")
    
    # 划分训练集测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, shuffle=False
    )
    
    # 训练模型
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # 预测
    y_pred = model.predict(X_test)
    
    print("\n模型表现:")
    print(classification_report(y_test, y_pred))
    
    # 4. 因子重要性
    print("\n[4/4] 因子重要性分析:")
    
    importance_df = pd.DataFrame({
        'factor': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(importance_df.to_string(index=False))
    
    # 5. 因子组合策略
    print("\n[因子组合策略回测]")
    
    # 使用模型预测生成交易信号
    df['prediction'] = model.predict(X)
    df['position'] = df['prediction'].shift(1)  # 前一天预测，当天持仓
    
    # 计算策略收益
    df['strategy_return'] = df['position'] * df['return_1d']
    
    # 累计收益
    cumulative_return = (1 + df['strategy_return']).cumprod()
    
    print(f"策略累计收益：{(cumulative_return.iloc[-1] - 1) * 100:.2f}%")
    print(f"基准累计收益：{(df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100:.2f}%")
    
    print("\n" + "=" * 60)
    print("因子挖掘完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
