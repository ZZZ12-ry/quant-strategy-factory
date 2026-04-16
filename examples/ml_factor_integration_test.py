"""
ML 模型 + 因子组合 整合测试
使用 XGBoost/LightGBM 预测因子组合收益
"""
import pandas as pd
import numpy as np
from src.ml.barra_factors import BarraFactors
from src.ml.factor_analyzer import FactorAnalyzer


def prepare_ml_data(df, lookback=60):
    """准备 ML 训练数据"""
    print("\n准备 ML 数据...")
    
    # 计算因子
    barra = BarraFactors()
    df_factors = barra.calculate_all(df)
    
    # 计算未来收益
    for period in [1, 5, 10]:
        df_factors[f'return_{period}d'] = df_factors['close'].shift(-period) / df_factors['close'] - 1
    
    # 去除 NaN
    df_factors = df_factors.dropna()
    
    # 获取因子名称
    factor_names = barra.get_factor_names()
    X_cols = [f for f in factor_names if f in df_factors.columns]
    
    print(f"  样本数：{len(df_factors)}")
    print(f"  因子数：{len(X_cols)}")
    
    return df_factors, X_cols


def train_ml_models(df_factors, X_cols, target_col='return_5d'):
    """训练多个 ML 模型"""
    print("\n训练 ML 模型...")
    
    # 准备数据
    X = df_factors[X_cols].values
    y = (df_factors[target_col] > 0).astype(int)  # 分类：涨跌
    
    # 划分训练测试集
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"  训练集：{len(X_train)} 样本")
    print(f"  测试集：{len(X_test)} 样本")
    
    results = []
    
    # 1. XGBoost
    try:
        import xgboost as xgb
        print("\n[1/3] 训练 XGBoost...")
        
        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            eval_metric='logloss'
        )
        
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
        
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        
        from sklearn.metrics import accuracy_score, roc_auc_score
        acc = accuracy_score(y_test, y_pred)
        try:
            auc = roc_auc_score(y_test, y_proba)
        except:
            auc = 0.5
        
        # 特征重要性
        importance = pd.DataFrame({
            'feature': X_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        results.append({
            'model': 'XGBoost',
            'accuracy': acc,
            'auc': auc,
            'importance': importance
        })
        
        print(f"  测试集准确率：{acc:.4f}")
        print(f"  测试集 AUC: {auc:.4f}")
        
    except ImportError:
        print("  [SKIP] XGBoost 未安装")
    
    # 2. LightGBM (跳过，有兼容性问题)
    print("\n[2/3] 跳过 LightGBM（pandas 兼容性）")
    
    # 3. CatBoost
    try:
        import catboost as cb
        print("\n[3/3] 训练 CatBoost...")
        
        model = cb.CatBoostClassifier(
            iterations=100,
            depth=6,
            learning_rate=0.1,
            random_state=42,
            verbose=0
        )
        
        model.fit(X_train, y_train, eval_set=(X_test, y_test))
        
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        
        from sklearn.metrics import accuracy_score, roc_auc_score
        acc = accuracy_score(y_test, y_pred)
        try:
            auc = roc_auc_score(y_test, y_proba)
        except:
            auc = 0.5
        
        importance = pd.DataFrame({
            'feature': X_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        results.append({
            'model': 'CatBoost',
            'accuracy': acc,
            'auc': auc,
            'importance': importance
        })
        
        print(f"  测试集准确率：{acc:.4f}")
        print(f"  测试集 AUC: {auc:.4f}")
        
    except ImportError:
        print("  [SKIP] CatBoost 未安装")
    
    return results


def analyze_feature_importance(results):
    """分析特征重要性"""
    print("\n" + "="*70)
    print("特征重要性分析")
    print("="*70)
    
    for result in results:
        print(f"\n{result['model']} Top 10 因子:")
        print(f"{'因子':<35} {'重要性':<10}")
        print(f"{'-'*50}")
        
        importance = result['importance'].head(10)
        for _, row in importance.iterrows():
            print(f"{row['feature']:<35} {row['importance']:.4f}")


def test_ml_factor_integration():
    """测试 ML + 因子整合"""
    print("\n" + "="*70)
    print("ML 模型 + 因子组合 整合测试")
    print("="*70)
    
    # 获取数据
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
    except Exception as e:
        print(f"\n[WARN] 获取数据失败：{e}")
        print("使用模拟数据...")
        np.random.seed(42)
        n = 500
        close = 100 * np.exp(np.cumsum(np.random.randn(n) * 0.02))
        df = pd.DataFrame({
            'open': close * (1 + np.random.randn(n) * 0.005),
            'high': close * (1 + np.abs(np.random.randn(n) * 0.01)),
            'low': close * (1 - np.abs(np.random.randn(n) * 0.01)),
            'close': close,
            'volume': np.random.randint(10000, 50000, n),
            'timestamp': pd.date_range('2024-01-01', periods=n)
        })
    
    # 准备数据
    df_factors, X_cols = prepare_ml_data(df)
    
    # 训练模型
    results = train_ml_models(df_factors, X_cols)
    
    # 分析特征重要性
    if results:
        analyze_feature_importance(results)
        
        # 模型对比
        print("\n" + "="*70)
        print("模型对比")
        print("="*70)
        print(f"\n{'模型':<15} {'准确率':<12} {'AUC':<12}")
        print(f"{'-'*45}")
        
        for result in results:
            print(f"{result['model']:<15} {result['accuracy']:>10.4f} {result['auc']:>10.4f}")
        
        # 最佳模型
        best = max(results, key=lambda x: x['auc'])
        print(f"\n最佳模型：{best['model']} (AUC = {best['auc']:.4f})")
    
    print("\n" + "="*70)
    print("[OK] ML + 因子整合测试完成")
    print("="*70)
    
    return results


if __name__ == "__main__":
    results = test_ml_factor_integration()
