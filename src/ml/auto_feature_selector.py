"""
自动特征选择器
- 过滤法 (Filter): 方差/相关性/互信息
- 包裹法 (Wrapper): RFE/递归特征消除
- 嵌入法 (Embedded): L1 正则化/树模型重要性
- 遗传算法特征挖掘
"""
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime


class AutoFeatureSelector:
    """自动特征选择器"""
    
    def __init__(self, target_col: str = 'target'):
        self.target_col = target_col
        self.selected_features = []
        self.feature_scores = {}
        self.selection_method = None
    
    def filter_variance(self, X: pd.DataFrame, threshold: float = 0.01) -> List[str]:
        """
        过滤法：低方差特征过滤
        
        Args:
            X: 特征矩阵
            threshold: 方差阈值
        
        Returns:
            保留的特征列表
        """
        variances = X.var()
        keep_features = variances[variances > threshold].index.tolist()
        
        print(f"[方差过滤] 原始特征：{len(X.columns)}, 保留：{len(keep_features)}, 移除：{len(X.columns) - len(keep_features)}")
        
        return keep_features
    
    def filter_correlation(self, X: pd.DataFrame, threshold: float = 0.95) -> List[str]:
        """
        过滤法：高相关特征过滤
        
        Args:
            X: 特征矩阵
            threshold: 相关系数阈值
        
        Returns:
            保留的特征列表
        """
        corr_matrix = X.corr().abs()
        
        # 找出高相关特征对
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        to_drop = [column for column in upper.columns if any(upper[column] > threshold)]
        
        keep_features = [f for f in X.columns if f not in to_drop]
        
        print(f"[相关性过滤] 原始特征：{len(X.columns)}, 保留：{len(keep_features)}, 移除：{len(to_drop)}")
        
        return keep_features
    
    def filter_mutual_info(self, X: pd.DataFrame, y: pd.Series, 
                          threshold: float = 0.01, n_bins: int = 10) -> List[str]:
        """
        过滤法：互信息特征选择
        
        Args:
            X: 特征矩阵
            y: 目标变量
            threshold: 互信息阈值
            n_bins: 离散化分箱数
        
        Returns:
            保留的特征列表
        """
        try:
            from sklearn.feature_selection import mutual_info_classif
        except ImportError:
            raise ImportError("请安装 scikit-learn: pip install scikit-learn")
        
        # 离散化连续特征
        X_discrete = X.copy()
        for col in X.columns:
            if X[col].dtype == 'float64':
                X_discrete[col] = pd.qcut(X[col], q=n_bins, labels=False, duplicates='drop')
        
        # 计算互信息
        mi_scores = mutual_info_classif(X_discrete, y, discrete_features=True, random_state=42)
        
        # 筛选特征
        mi_df = pd.DataFrame({
            'feature': X.columns,
            'mutual_info': mi_scores
        }).sort_values('mutual_info', ascending=False)
        
        keep_features = mi_df[mi_df['mutual_info'] > threshold]['feature'].tolist()
        
        print(f"[互信息过滤] 原始特征：{len(X.columns)}, 保留：{len(keep_features)}, 移除：{len(X.columns) - len(keep_features)}")
        
        return keep_features
    
    def wrapper_rfe(self, X: pd.DataFrame, y: pd.Series, 
                   model: Any, n_features: int = 20) -> List[str]:
        """
        包裹法：递归特征消除 (RFE)
        
        Args:
            X: 特征矩阵
            y: 目标变量
            model: 基础模型（如 RandomForest）
            n_features: 保留的特征数
        
        Returns:
            保留的特征列表
        """
        try:
            from sklearn.feature_selection import RFE
        except ImportError:
            raise ImportError("请安装 scikit-learn: pip install scikit-learn")
        
        rfe = RFE(estimator=model, n_features_to_select=n_features, step=1)
        rfe.fit(X, y)
        
        keep_features = X.columns[rfe.support_].tolist()
        
        print(f"[RFE 包裹法] 原始特征：{len(X.columns)}, 保留：{len(keep_features)}")
        
        return keep_features
    
    def embedded_l1(self, X: pd.DataFrame, y: pd.Series, 
                   C: float = 1.0) -> List[str]:
        """
        嵌入法：L1 正则化特征选择
        
        Args:
            X: 特征矩阵
            y: 目标变量
            C: 正则化强度（越小越强）
        
        Returns:
            保留的特征列表
        """
        try:
            from sklearn.linear_model import LogisticRegression
        except ImportError:
            raise ImportError("请安装 scikit-learn: pip install scikit-learn")
        
        # L1 正则化
        lr = LogisticRegression(penalty='l1', solver='liblinear', C=C, random_state=42)
        lr.fit(X, y)
        
        # 提取非零系数特征
        keep_features = X.columns[lr.coef_[0] != 0].tolist()
        
        print(f"[L1 嵌入法] 原始特征：{len(X.columns)}, 保留：{len(keep_features)}")
        
        return keep_features
    
    def embedded_tree_importance(self, X: pd.DataFrame, y: pd.Series,
                                 model_type: str = 'xgboost',
                                 threshold: float = 0.01) -> List[str]:
        """
        嵌入法：树模型特征重要性
        
        Args:
            X: 特征矩阵
            y: 目标变量
            model_type: 模型类型（xgboost/lightgbm/randomforest）
            threshold: 重要性阈值
        
        Returns:
            保留的特征列表
        """
        if model_type == 'xgboost':
            try:
                import xgboost as xgb
                model = xgb.XGBClassifier(n_estimators=100, max_depth=5, random_state=42)
            except ImportError:
                raise ImportError("请安装 XGBoost")
        elif model_type == 'lightgbm':
            try:
                import lightgbm as lgb
                model = lgb.LGBMClassifier(n_estimators=100, max_depth=-1, random_state=42)
            except ImportError:
                raise ImportError("请安装 LightGBM")
        else:  # randomforest
            try:
                from sklearn.ensemble import RandomForestClassifier
                model = RandomForestClassifier(n_estimators=100, random_state=42)
            except ImportError:
                raise ImportError("请安装 scikit-learn")
        
        model.fit(X, y)
        
        # 特征重要性
        importance_df = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        keep_features = importance_df[importance_df['importance'] > threshold]['feature'].tolist()
        
        print(f"[树模型重要性] 原始特征：{len(X.columns)}, 保留：{len(keep_features)}")
        
        return keep_features
    
    def sequential_selection(self, X: pd.DataFrame, y: pd.Series,
                            method: str = 'variance+correlation+tree',
                            **kwargs) -> List[str]:
        """
        顺序特征选择：多步骤组合
        
        Args:
            X: 特征矩阵
            y: 目标变量
            method: 选择方法组合（如 'variance+correlation+tree'）
            **kwargs: 各方法参数
        
        Returns:
            最终保留的特征列表
        """
        methods = method.split('+')
        current_features = X.columns.tolist()
        
        print(f"\n{'='*60}")
        print(f"顺序特征选择：{method}")
        print(f"{'='*60}")
        
        for i, m in enumerate(methods, 1):
            print(f"\n步骤 {i}/{len(methods)}: {m}")
            print(f"{'-'*40}")
            
            X_subset = X[current_features]
            
            if m == 'variance':
                current_features = self.filter_variance(
                    X_subset, 
                    threshold=kwargs.get('variance_threshold', 0.01)
                )
            elif m == 'correlation':
                current_features = self.filter_correlation(
                    X_subset,
                    threshold=kwargs.get('correlation_threshold', 0.95)
                )
            elif m == 'mutual_info':
                current_features = self.filter_mutual_info(
                    X_subset, y,
                    threshold=kwargs.get('mi_threshold', 0.01)
                )
            elif m == 'tree':
                current_features = self.embedded_tree_importance(
                    X_subset, y,
                    model_type=kwargs.get('model_type', 'xgboost'),
                    threshold=kwargs.get('tree_threshold', 0.01)
                )
            elif m == 'rfe':
                from sklearn.ensemble import RandomForestClassifier
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                current_features = self.wrapper_rfe(
                    X_subset, y, model,
                    n_features=kwargs.get('n_features', 20)
                )
            elif m == 'l1':
                current_features = self.embedded_l1(
                    X_subset, y,
                    C=kwargs.get('C', 1.0)
                )
        
        self.selected_features = current_features
        self.selection_method = method
        
        print(f"\n{'='*60}")
        print(f"最终保留特征数：{len(current_features)}/{len(X.columns)}")
        print(f"{'='*60}\n")
        
        return current_features
    
    def genetic_feature_selection(self, X: pd.DataFrame, y: pd.Series,
                                 n_generations: int = 10,
                                 population_size: int = 20,
                                 crossover_rate: float = 0.8,
                                 mutation_rate: float = 0.1) -> List[str]:
        """
        遗传算法特征选择
        
        Args:
            X: 特征矩阵
            y: 目标变量
            n_generations: 迭代代数
            population_size: 种群大小
            crossover_rate: 交叉率
            mutation_rate: 变异率
        
        Returns:
            最优特征子集
        """
        try:
            import xgboost as xgb
            from sklearn.model_selection import cross_val_score
        except ImportError:
            raise ImportError("请安装 XGBoost 和 scikit-learn")
        
        n_features = X.shape[1]
        feature_names = X.columns.tolist()
        
        # 初始化种群
        population = []
        for _ in range(population_size):
            # 随机生成特征掩码
            mask = np.random.rand(n_features) > 0.5
            if mask.sum() == 0:
                mask[np.random.randint(n_features)] = True
            population.append(mask)
        
        def fitness(mask):
            """适应度函数：交叉验证 AUC"""
            selected = [feature_names[i] for i in range(n_features) if mask[i]]
            if len(selected) == 0:
                return 0
            
            X_selected = X[selected]
            model = xgb.XGBClassifier(n_estimators=50, max_depth=3, random_state=42)
            
            try:
                scores = cross_val_score(model, X_selected, y, cv=3, scoring='roc_auc')
                return scores.mean()
            except:
                return 0
        
        print(f"\n{'='*60}")
        print(f"遗传算法特征选择")
        print(f"{'='*60}")
        print(f"种群大小：{population_size}, 代数：{n_generations}")
        print(f"{'='*60}\n")
        
        best_fitness = 0
        best_mask = None
        
        for gen in range(n_generations):
            # 计算适应度
            fitness_scores = [fitness(mask) for mask in population]
            
            # 更新最优
            gen_best = max(fitness_scores)
            if gen_best > best_fitness:
                best_fitness = gen_best
                best_mask = population[fitness_scores.index(gen_best)]
            
            print(f"Generation {gen+1}/{n_generations}: Best AUC = {gen_best:.4f}")
            
            # 选择（锦标赛选择）
            new_population = []
            for _ in range(population_size):
                contestants = np.random.choice(population, size=3, replace=False)
                winner = contestants[np.argmax([fitness_scores[population.index(c)] for c in contestants])]
                new_population.append(winner.copy())
            
            # 交叉
            for i in range(0, population_size, 2):
                if np.random.rand() < crossover_rate:
                    point = np.random.randint(1, n_features)
                    new_population[i][point:], new_population[i+1][point:] = \
                        new_population[i+1][point:].copy(), new_population[i][point:].copy()
            
            # 变异
            for i in range(population_size):
                if np.random.rand() < mutation_rate:
                    idx = np.random.randint(n_features)
                    new_population[i][idx] = not new_population[i][idx]
            
            population = new_population
        
        # 返回最优特征
        selected_features = [feature_names[i] for i in range(n_features) if best_mask[i]]
        
        print(f"\n{'='*60}")
        print(f"遗传算法完成")
        print(f"最优 AUC: {best_fitness:.4f}")
        print(f"保留特征：{len(selected_features)}/{n_features}")
        print(f"{'='*60}\n")
        
        self.selected_features = selected_features
        self.selection_method = 'genetic_algorithm'
        
        return selected_features
    
    def calc_ic(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """
        计算每个特征的 IC 值（信息系数）
        
        IC = 特征值与下期收益率的相关系数
        
        Args:
            X: 特征矩阵
            y: 目标变量（下期收益率）
        
        Returns:
            IC 统计 DataFrame
        """
        ic_results = []
        
        for col in X.columns:
            # 计算 IC
            ic = X[col].corr(y)
            
            # 计算 Rank IC
            ic_rank = X[col].rank().corr(y.rank())
            
            ic_results.append({
                'feature': col,
                'ic': ic if not np.isnan(ic) else 0,
                'rank_ic': ic_rank if not np.isnan(ic_rank) else 0,
            })
        
        ic_df = pd.DataFrame(ic_results).sort_values('ic', key=abs, ascending=False)
        
        # 统计信息
        mean_ic = ic_df['ic'].abs().mean()
        mean_rank_ic = ic_df['rank_ic'].abs().mean()
        
        print(f"\n{'='*60}")
        print(f"特征 IC 分析")
        print(f"{'='*60}")
        print(f"特征总数：{len(ic_df)}")
        print(f"平均 |IC|: {mean_ic:.4f}")
        print(f"平均 |Rank IC|: {mean_rank_ic:.4f}")
        print(f"\nTop 10 特征:")
        print(ic_df.head(10)[['feature', 'ic', 'rank_ic']].to_string(index=False))
        print(f"{'='*60}\n")
        
        return ic_df


def test_feature_selector():
    """测试特征选择器"""
    print("\n" + "="*70)
    print("自动特征选择器测试")
    print("="*70)
    
    # 生成测试数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 50
    
    # 生成特征
    feature_names = [f'feature_{i}' for i in range(n_features)]
    X = pd.DataFrame(np.random.randn(n_samples, n_features), columns=feature_names)
    
    # 添加一些冗余特征（高相关）
    for i in range(10):
        X[f'redundant_{i}'] = X[f'feature_{i}'] + np.random.randn(n_samples) * 0.1
    
    # 生成目标变量（与部分特征相关）
    y = (X['feature_0'] * 2 + X['feature_1'] * 1.5 + X['feature_2'] + 
         np.random.randn(n_samples) * 0.5 > 0).astype(int)
    
    print(f"\n数据集:")
    print(f"  样本数：{n_samples}")
    print(f"  特征数：{X.shape[1]}")
    print(f"  正样本比例：{y.mean()*100:.1f}%")
    
    # 测试顺序选择
    selector = AutoFeatureSelector()
    selected = selector.sequential_selection(
        X, y,
        method='variance+correlation+tree',
        variance_threshold=0.01,
        correlation_threshold=0.95,
        tree_threshold=0.01
    )
    
    # 计算 IC
    selector.calc_ic(X[selected], y)
    
    print(f"\n[OK] 测试完成")
    
    return selector, selected


if __name__ == "__main__":
    selector, selected = test_feature_selector()
