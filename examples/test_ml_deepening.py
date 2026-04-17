"""
简化版 ML 工作流测试
验证 ML/DL 深化功能
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def test_feature_selector():
    """测试特征选择器"""
    print("\n" + "="*70)
    print("测试 1: 自动特征选择器")
    print("="*70)
    
    from src.ml.auto_feature_selector import AutoFeatureSelector
    
    # 生成测试数据
    np.random.seed(42)
    n_samples = 500
    n_features = 30
    
    feature_names = [f'feature_{i}' for i in range(n_features)]
    X = pd.DataFrame(np.random.randn(n_samples, n_features), columns=feature_names)
    
    # 添加一些冗余特征
    for i in range(5):
        X[f'redundant_{i}'] = X[f'feature_{i}'] + np.random.randn(n_samples) * 0.1
    
    # 生成目标变量
    y = (X['feature_0'] * 2 + X['feature_1'] * 1.5 + np.random.randn(n_samples) * 0.5 > 0).astype(int)
    
    print(f"\n数据集:")
    print(f"  样本数：{n_samples}")
    print(f"  特征数：{X.shape[1]}")
    
    # 特征选择
    selector = AutoFeatureSelector()
    selected = selector.sequential_selection(
        X, y,
        method='variance+correlation+tree',
        variance_threshold=0.5,  # 提高阈值确保有筛选
        correlation_threshold=0.9,
        tree_threshold=0.01
    )
    
    # 计算 IC
    if len(selected) > 0:
        ic_df = selector.calc_ic(X[selected], y)
    
    print(f"\n[PASS] 特征选择器测试通过")
    print(f"   保留特征：{len(selected)}/{X.shape[1]}")
    
    return True


def test_ic_evaluator():
    """测试 IC 评估器"""
    print("\n" + "="*70)
    print("测试 2: 模型 IC 评估器")
    print("="*70)
    
    from src.ml.model_ic_evaluator import ModelICEvaluator
    
    # 生成测试数据
    np.random.seed(42)
    n_samples = 200
    
    # 生成有一定预测能力的预测值
    y_pred = np.random.randn(n_samples) * 0.5
    y_true = (y_pred * 0.3 + np.random.randn(n_samples) * 0.7 > 0).astype(int)
    returns = y_pred * 0.02 + np.random.randn(n_samples) * 0.01
    
    # 创建 DataFrame
    dates = pd.date_range('2024-01-01', periods=n_samples, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'pred': y_pred,
        'true': y_true,
        'return': returns
    }).set_index('date')
    
    print(f"\n数据集:")
    print(f"  样本数：{n_samples}")
    print(f"  日期范围：{dates[0]} 至 {dates[-1]}")
    
    # IC 评估
    evaluator = ModelICEvaluator()
    results = evaluator.evaluate(
        y_pred=y_pred,
        y_true=y_true,
        df_full=df,
        pred_col='pred',
        return_col='return'
    )
    
    # 滚动 IC
    ic_ts = evaluator.calc_ic_time_series(df['pred'], df['true'], periods=20)
    
    print(f"\n[PASS] IC 评估器测试通过")
    print(f"   IC: {results['ic']:.4f}")
    print(f"   Rank IC: {results['rank_ic']:.4f}")
    print(f"   方向准确率：{results['direction_accuracy']:.1%}")
    
    return True


def test_advanced_models():
    """测试高级模型"""
    print("\n" + "="*70)
    print("测试 3: 高级 ML 模型 (XGBoost)")
    print("="*70)
    
    from src.ml.advanced_models import AdvancedMLModels
    from sklearn.model_selection import train_test_split
    
    # 生成测试数据
    np.random.seed(42)
    n_samples = 500
    n_features = 20
    
    X = pd.DataFrame(np.random.randn(n_samples, n_features),
                     columns=[f'feature_{i}' for i in range(n_features)])
    y = (X['feature_0'] + X['feature_1'] * 2 + np.random.randn(n_samples) * 0.5 > 0).astype(int)
    
    # 划分数据集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print(f"\n数据集:")
    print(f"  训练集：{len(X_train)} 样本")
    print(f"  测试集：{len(X_test)} 样本")
    print(f"  特征数：{n_features}")
    
    # 训练模型
    adv = AdvancedMLModels()
    adv.create_xgboost(n_estimators=50, max_depth=3, learning_rate=0.1)
    metrics = adv.train(X_train, y_train, X_test, y_test, verbose=False)
    
    # 特征重要性
    importance = adv.get_feature_importance(top_n=5)
    
    print(f"\n模型表现:")
    print(f"  训练集 AUC: {metrics.get('train_auc', 0):.4f}")
    print(f"  验证集 AUC: {metrics.get('val_auc', 0):.4f}")
    print(f"  训练集准确率：{metrics.get('train_accuracy', 0):.1%}")
    print(f"  验证集准确率：{metrics.get('val_accuracy', 0):.1%}")
    
    print(f"\nTop 5 特征重要性:")
    for _, row in importance.iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")
    
    print(f"\n[PASS] 高级模型测试通过")
    
    return True


def main():
    """主测试流程"""
    print("\n" + "="*70)
    print("ML/DL 深化功能验证测试")
    print("量化策略工厂 v1.1")
    print("="*70)
    
    start_time = datetime.now()
    results = {}
    
    try:
        # 测试 1: 特征选择器
        results['feature_selector'] = test_feature_selector()
        
        # 测试 2: IC 评估器
        results['ic_evaluator'] = test_ic_evaluator()
        
        # 测试 3: 高级模型
        results['advanced_models'] = test_advanced_models()
        
    except Exception as e:
        print(f"\n[FAILED] 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    print(f"\n总耗时：{duration:.1f} 秒")
    print(f"\n测试结果:")
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\n{'='*70}")
    if all_passed:
        print("[SUCCESS] 所有测试通过！ML/DL 深化功能验证完成")
    else:
        print("[FAILED] 部分测试失败，请检查错误信息")
    print(f"{'='*70}\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
