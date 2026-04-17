"""
高级 ML 工作流演示
从数据获取 → 特征工程 → 特征选择 → 模型训练 → IC 评估 → 策略信号

完整流程展示量化策略工厂的 ML/DL 深化能力
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def load_or_generate_data():
    """加载或生成测试数据"""
    print("\n" + "="*70)
    print("步骤 1: 数据准备")
    print("="*70)
    
    cache_file = 'data/cache/ml_workflow_test.csv'
    
    if os.path.exists(cache_file):
        print(f"加载缓存数据：{cache_file}")
        df = pd.read_csv(cache_file, parse_dates=['date'], index_col='date')
    else:
        print("生成模拟数据...")
        np.random.seed(42)
        n_days = 500
        
        # 生成日期
        dates = pd.date_range('2024-01-01', periods=n_days, freq='D')
        
        # 生成 OHLCV 数据
        base_price = 100
        returns = np.random.randn(n_days) * 0.02
        close = pd.Series(base_price * (1 + returns).cumprod())
        
        high = close * (1 + np.abs(np.random.randn(n_days)) * 0.01)
        low = close * (1 - np.abs(np.random.randn(n_days)) * 0.01)
        open_price = close.shift(1).fillna(base_price)
        volume = np.random.randint(10000, 100000, n_days)
        
        df = pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)
        df.index.name = 'date'
        
        # 保存缓存
        os.makedirs('data/cache', exist_ok=True)
        df.to_csv(cache_file)
        print(f"数据已缓存：{cache_file}")
    
    print(f"\n数据概览:")
    print(f"  日期范围：{df.index[0]} 至 {df.index[-1]}")
    print(f"  样本数：{len(df)}")
    print(f"  特征：OHLCV")
    
    return df


def calculate_features(df: pd.DataFrame) -> pd.DataFrame:
    """计算特征"""
    print("\n" + "="*70)
    print("步骤 2: 特征工程")
    print("="*70)
    
    from src.ml.feature_library import FeatureLibrary
    
    lib = FeatureLibrary()
    df_features = lib.calculate_all(df)
    
    feature_names = lib.get_feature_names()
    available_features = [f for f in feature_names if f in df_features.columns]
    
    print(f"\n特征统计:")
    print(f"  总特征数：{len(available_features)}")
    print(f"  可用特征：{len(available_features)}")
    print(f"  样本数：{len(df_features)}")
    
    # 显示部分特征
    print(f"\n部分特征示例:")
    sample_features = ['return_1d', 'rsi_12', 'macd', 'bb_position', 'volatility_10d']
    for f in sample_features:
        if f in df_features.columns:
            print(f"  {f}: mean={df_features[f].mean():.4f}, std={df_features[f].std():.4f}")
    
    return df_features, available_features


def select_features(df: pd.DataFrame, feature_names: list, target_col: str = 'target') -> tuple:
    """特征选择"""
    print("\n" + "="*70)
    print("步骤 3: 特征选择")
    print("="*70)
    
    from src.ml.auto_feature_selector import AutoFeatureSelector
    
    # 准备数据
    df_aligned = df[feature_names + ['close']].copy()
    df_aligned['target'] = (df_aligned['close'].shift(-1) > df_aligned['close']).astype(int)
    df_aligned = df_aligned.dropna()
    
    y = df_aligned['target']
    X = df_aligned[feature_names]
    
    # 简化特征选择：只用方差 + 相关性过滤
    selector = AutoFeatureSelector(target_col=target_col)
    selected_features = selector.sequential_selection(
        X, y,
        method='variance+correlation',
        variance_threshold=0.01,
        correlation_threshold=0.95
    )
    
    # 确保至少有 10 个特征
    if len(selected_features) < 10:
        print(f"警告：特征数过少，使用 Top 20 特征")
        selected_features = feature_names[:20]
    
    # 计算 IC
    print(f"\n计算特征 IC...")
    ic_df = selector.calc_ic(X[selected_features], y)
    
    print(f"\n最终保留特征数：{len(selected_features)}")
    print(f"特征筛选率：{len(selected_features)/len(feature_names)*100:.1f}%")
    
    return X, y, selected_features


def train_models(X: pd.DataFrame, y: pd.Series):
    """训练多个模型并对比"""
    print("\n" + "="*70)
    print("步骤 4: 模型训练与对比")
    print("="*70)
    
    from src.ml.advanced_models import AdvancedMLModels, compare_models
    from sklearn.model_selection import train_test_split
    
    # 划分训练测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=False
    )
    
    print(f"\n数据集划分:")
    print(f"  训练集：{len(X_train)} 样本")
    print(f"  测试集：{len(X_test)} 样本")
    
    # 简化模型对比（只训练 XGBoost）
    print(f"\n[1/1] 训练 XGBoost...")
    adv = AdvancedMLModels()
    adv.create_xgboost(n_estimators=50, max_depth=3, learning_rate=0.1)
    metrics = adv.train(X_train, y_train, X_test, y_test, verbose=False)
    
    df_results = pd.DataFrame([metrics])
    df_results['model'] = 'XGBoost'
    print(f"  验证集 AUC: {metrics.get('val_auc', 0):.4f}")
    
    return df_results, X_train, X_test, y_train, y_test


def evaluate_ic(y_pred, y_true, df_full: pd.DataFrame):
    """IC 评估"""
    print("\n" + "="*70)
    print("步骤 5: IC 评估")
    print("="*70)
    
    from src.ml.model_ic_evaluator import ModelICEvaluator
    
    evaluator = ModelICEvaluator()
    
    # 基础评估
    results = evaluator.evaluate(
        y_pred=y_pred,
        y_true=y_true,
        df_full=df_full,
        pred_col='pred',
        return_col='return'
    )
    
    # 生成报告
    print(evaluator.report())
    
    return evaluator, results


def generate_signals(df: pd.DataFrame, y_pred: np.ndarray, threshold: float = 0.55):
    """生成交易信号"""
    print("\n" + "="*70)
    print("步骤 6: 生成交易信号")
    print("="*70)
    
    # 创建信号
    signals = pd.DataFrame({
        'date': df.index[:len(y_pred)],
        'pred': y_pred,
        'signal': (y_pred > threshold).astype(int),
        'close': df['close'].iloc[:len(y_pred)].values
    })
    
    # 计算信号收益
    signals['next_return'] = signals['close'].shift(-1) / signals['close'] - 1
    signals['strategy_return'] = signals['signal'] * signals['next_return']
    
    # 统计
    total_days = len(signals)
    signal_days = signals['signal'].sum()
    signal_ratio = signal_days / total_days
    
    avg_signal_return = signals[signals['signal'] == 1]['next_return'].mean()
    avg_no_signal_return = signals[signals['signal'] == 0]['next_return'].mean()
    
    # 累计收益
    cumulative_signal = (1 + signals['strategy_return'].fillna(0)).cumprod() - 1
    cumulative_buy_hold = (1 + signals['next_return'].fillna(0)).cumprod() - 1
    
    print(f"\n信号统计:")
    print(f"  总天数：{total_days}")
    print(f"  信号天数：{signal_days} ({signal_ratio:.1%})")
    print(f"  信号日平均收益：{avg_signal_return:.4%}")
    print(f"  无信号日平均收益：{avg_no_signal_return:.4%}")
    print(f"  信号超额：{(avg_signal_return - avg_no_signal_return)*100:.2f}%")
    
    print(f"\n累计收益:")
    print(f"  策略累计：{cumulative_signal.iloc[-1]:.2%}")
    print(f"  买入持有：{cumulative_buy_hold.iloc[-1]:.2%}")
    print(f"  超额收益：{(cumulative_signal.iloc[-1] - cumulative_buy_hold.iloc[-1])*100:.2f}%")
    
    return signals


def main():
    """主流程"""
    print("\n" + "="*70)
    print("高级 ML 工作流演示")
    print("量化策略工厂 - ML/DL 深化能力展示")
    print("="*70)
    
    start_time = datetime.now()
    
    # 1. 数据准备
    df = load_or_generate_data()
    
    # 2. 特征工程
    df_features, feature_names = calculate_features(df)
    
    # 3. 特征选择
    X, y, selected_features = select_features(df_features, feature_names)
    
    # 4. 模型训练
    df_results, X_train, X_test, y_train, y_test = train_models(X, y)
    
    # 5. IC 评估
    from src.ml.advanced_models import AdvancedMLModels
    adv = AdvancedMLModels()
    adv.create_xgboost(n_estimators=100, max_depth=5)
    adv.train(X_train, y_train, X_test, y_test, verbose=False)
    
    y_pred = adv.predict(X_test)
    y_proba = adv.predict_proba(X_test)[:, 1]
    
    # 准备 IC 评估数据
    df_test = df_features.loc[X_test.index].copy()
    df_test['pred'] = y_proba
    df_test['true'] = y_test.values
    df_test['return'] = df_test['close'].shift(-1) / df_test['close'] - 1
    df_test = df_test.dropna()
    
    evaluator, ic_results = evaluate_ic(y_proba, y_test.values, df_test)
    
    # 6. 生成信号
    signals = generate_signals(df_features, y_proba)
    
    # 总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*70)
    print("流程完成总结")
    print("="*70)
    print(f"\n总耗时：{duration:.1f} 秒")
    print(f"\n关键指标:")
    print(f"  特征数：{len(feature_names)} → {len(selected_features)} (筛选后)")
    print(f"  最佳模型：{df_results.iloc[0]['model']}")
    print(f"  验证集 AUC: {df_results.iloc[0]['val_auc']:.4f}")
    print(f"  IC: {ic_results.get('ic', 0):.4f}")
    print(f"  Rank IC: {ic_results.get('rank_ic', 0):.4f}")
    print(f"  策略超额：{(signals['strategy_return'].mean() - signals['next_return'].mean())*100:.2f}%")
    
    print(f"\n{'='*70}")
    print("✅ ML/DL 深化功能验证完成")
    print(f"{'='*70}\n")
    
    return {
        'features': len(selected_features),
        'best_model': df_results.iloc[0]['model'],
        'auc': df_results.iloc[0]['val_auc'],
        'ic': ic_results.get('ic', 0),
        'excess_return': (signals['strategy_return'].mean() - signals['next_return'].mean())*100
    }


if __name__ == "__main__":
    results = main()
