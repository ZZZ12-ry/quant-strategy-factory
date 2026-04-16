"""
因子自动挖掘 - 参考 Qlib RD-Agent
自动化发现有效因子，通过遗传算法/进化策略生成新因子
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import random


class AutoFeatureMiner:
    """因子自动挖掘器 - 通过遗传算法自动生成有效因子"""
    
    def __init__(self, base_features: List[str] = None):
        """
        初始化因子挖掘器
        
        Args:
            base_features: 基础因子列表
        """
        self.base_features = base_features or self._default_base_features()
        self.operators = self._init_operators()
        self.population = []
        self.generation = 0
        self.best_features = []
        self.feature_history = []
    
    def _default_base_features(self) -> List[str]:
        """默认基础因子"""
        return [
            'close', 'open', 'high', 'low', 'volume',
            'return_1d', 'return_5d', 'return_10d',
            'ma_5', 'ma_10', 'ma_20',
            'volume_ratio', 'volatility_10d',
            'rsi_12', 'macd', 'bb_position'
        ]
    
    def _init_operators(self) -> Dict[str, callable]:
        """初始化因子操作符"""
        operators = {
            # 算术操作
            'add': lambda x, y: x + y,
            'sub': lambda x, y: x - y,
            'mul': lambda x, y: x * y,
            'div': lambda x, y: x / (y + 1e-8),
            
            # 数学变换
            'log': lambda x: np.log(np.abs(x) + 1e-8),
            'sqrt': lambda x: np.sqrt(np.abs(x)),
            'square': lambda x: x ** 2,
            'inverse': lambda x: 1 / (x + 1e-8),
            
            # 时序操作
            'delay_1': lambda x: x.shift(1),
            'delay_3': lambda x: x.shift(3),
            'delay_5': lambda x: x.shift(5),
            'delta_1': lambda x: x.diff(1),
            'delta_5': lambda x: x.diff(5),
            
            # 统计操作
            'ts_mean_5': lambda x: x.rolling(5).mean(),
            'ts_mean_10': lambda x: x.rolling(10).mean(),
            'ts_std_5': lambda x: x.rolling(5).std(),
            'ts_std_10': lambda x: x.rolling(10).std(),
            'ts_rank_10': lambda x: x.rolling(10).apply(lambda arr: (arr[-1] - arr.min()) / (arr.max() - arr.min() + 1e-8)),
            
            # 截面标准化
            'rank': lambda x: x.rank(pct=True),
            'zscore': lambda x: (x - x.mean()) / (x.std() + 1e-8),
        }
        return operators
    
    def generate_random_feature(self, max_depth: int = 3) -> str:
        """
        随机生成一个因子表达式
        
        Args:
            max_depth: 最大嵌套深度
        
        Returns:
            因子表达式字符串
        """
        def build_expression(depth: int) -> str:
            if depth >= max_depth or random.random() < 0.3:
                return random.choice(self.base_features)
            
            operator = random.choice(list(self.operators.keys()))
            arity = 2 if operator in ['add', 'sub', 'mul', 'div'] else 1
            
            if arity == 1:
                expr = f"{operator}({build_expression(depth + 1)})"
            else:
                expr = f"{operator}({build_expression(depth + 1)}, {build_expression(depth + 1)})"
            
            return expr
        
        return build_expression(0)
    
    def evaluate_feature(
        self,
        feature_expr: str,
        data: pd.DataFrame,
        label: str = 'future_return_5d',
        horizon: int = 5
    ) -> Tuple[float, Optional[pd.Series]]:
        """
        评估因子 IC 值
        
        Args:
            feature_expr: 因子表达式
            data: OHLCV 数据
            label: 标签列名
            horizon: 预测周期
        
        Returns:
            (IC 值，因子值序列)
        """
        try:
            # 创建因子值
            df = data.copy()
            
            # 执行因子表达式
            feature_values = self._execute_expression(feature_expr, df)
            
            if feature_values is None or len(feature_values) == 0:
                return 0.0, None
            
            # 创建标签（未来收益率）
            if label not in df.columns:
                df[label] = df['close'].shift(-horizon) / df['close'] - 1
            
            # 对齐数据
            valid_mask = ~(feature_values.isna() | df[label].isna())
            if valid_mask.sum() < 30:
                return 0.0, None
            
            feature_aligned = feature_values[valid_mask]
            label_aligned = df[label][valid_mask]
            
            # 计算 IC（Rank IC）
            ic = self._calculate_rank_ic(feature_aligned, label_aligned)
            
            return ic, feature_values
            
        except Exception as e:
            return 0.0, None
    
    def _execute_expression(self, expr: str, df: pd.DataFrame) -> Optional[pd.Series]:
        """执行因子表达式"""
        try:
            # 创建安全命名空间
            namespace = {
                col: df[col] for col in df.columns
            }
            namespace.update(self.operators)
            namespace['np'] = np
            namespace['pd'] = pd
            
            # 执行表达式
            result = eval(expr, {"__builtins__": {}}, namespace)
            
            if isinstance(result, pd.Series):
                return result
            else:
                return None
                
        except Exception as e:
            return None
    
    def _calculate_rank_ic(self, factor: pd.Series, label: pd.Series) -> float:
        """计算 Rank IC"""
        try:
            factor_rank = factor.rank()
            label_rank = label.rank()
            
            corr = factor_rank.corr(label_rank, method='spearman')
            
            if np.isnan(corr):
                return 0.0
            
            return corr
            
        except:
            return 0.0
    
    def evolve(
        self,
        data: pd.DataFrame,
        population_size: int = 50,
        generations: int = 20,
        mutation_rate: float = 0.2,
        crossover_rate: float = 0.7,
        elite_ratio: float = 0.1,
        horizon: int = 5
    ) -> List[Dict[str, Any]]:
        """
        进化算法挖掘因子
        
        Args:
            data: OHLCV 数据
            population_size: 种群大小
            generations: 进化代数
            mutation_rate: 变异率
            crossover_rate: 交叉率
            elite_ratio: 精英比例
            horizon: 预测周期
        
        Returns:
            最佳因子列表
        """
        print(f"🧬 开始因子挖掘 - 种群:{population_size}, 代数:{generations}")
        
        # 初始化种群
        population = [self.generate_random_feature() for _ in range(population_size)]
        
        best_features = []
        best_ics = []
        
        for gen in range(generations):
            self.generation = gen
            
            # 评估种群
            fitness_scores = []
            feature_values_cache = {}
            
            for feature_expr in population:
                ic, feature_values = self.evaluate_feature(feature_expr, data, horizon=horizon)
                fitness_scores.append(ic)
                feature_values_cache[feature_expr] = (ic, feature_values)
            
            # 记录最佳
            sorted_indices = np.argsort(fitness_scores)[::-1]
            elite_count = int(population_size * elite_ratio)
            
            for idx in sorted_indices[:elite_count]:
                feature_expr = population[idx]
                ic = fitness_scores[idx]
                best_features.append({
                    'generation': gen,
                    'expression': feature_expr,
                    'ic': ic,
                    'feature_values': feature_values_cache[feature_expr][1]
                })
            
            if gen % 5 == 0:
                print(f"  代数 {gen}: 最佳 IC = {max(fitness_scores):.4f}")
            
            # 选择（锦标赛选择）
            new_population = []
            
            # 保留精英
            for idx in sorted_indices[:elite_count]:
                new_population.append(population[idx])
            
            # 生成新个体
            while len(new_population) < population_size:
                # 选择父代
                parent1 = self._tournament_select(population, fitness_scores)
                parent2 = self._tournament_select(population, fitness_scores)
                
                # 交叉
                if random.random() < crossover_rate:
                    child1, child2 = self._crossover(parent1, parent2)
                else:
                    child1, child2 = parent1, parent2
                
                # 变异
                if random.random() < mutation_rate:
                    child1 = self._mutate(child1)
                if random.random() < mutation_rate:
                    child2 = self._mutate(child2)
                
                new_population.extend([child1, child2])
            
            population = new_population[:population_size]
        
        # 整理结果
        best_features.sort(key=lambda x: x['ic'], reverse=True)
        self.best_features = best_features[:20]
        
        print(f"✅ 挖掘完成 - 最佳 IC: {best_features[0]['ic']:.4f}" if best_features else "❌ 无有效因子")
        
        return self.best_features
    
    def _tournament_select(self, population: List[str], fitness_scores: List[float], k: int = 5) -> str:
        """锦标赛选择"""
        indices = random.sample(range(len(population)), min(k, len(population)))
        best_idx = max(indices, key=lambda i: fitness_scores[i])
        return population[best_idx]
    
    def _crossover(self, parent1: str, parent2: str) -> Tuple[str, str]:
        """交叉操作"""
        # 找到子表达式
        parts1 = self._extract_subexpressions(parent1)
        parts2 = self._extract_subexpressions(parent2)
        
        if len(parts1) > 1 and len(parts2) > 1:
            # 随机选择子表达式交换
            idx1 = random.randint(0, len(parts1) - 1)
            idx2 = random.randint(0, len(parts2) - 1)
            
            child1 = parent1.replace(parts1[idx1], parts2[idx2], 1)
            child2 = parent2.replace(parts2[idx2], parts1[idx1], 1)
            
            return child1, child2
        
        return parent1, parent2
    
    def _mutate(self, expr: str) -> str:
        """变异操作"""
        mutation_type = random.choice(['replace', 'add_operator', 'remove_operator'])
        
        if mutation_type == 'replace':
            # 替换一个基础因子
            for feature in self.base_features:
                if feature in expr:
                    new_feature = random.choice(self.base_features)
                    return expr.replace(feature, new_feature, 1)
        
        elif mutation_type == 'add_operator':
            # 添加一个操作符
            operator = random.choice(['log', 'sqrt', 'delay_1', 'ts_mean_5'])
            return f"{operator}({expr})"
        
        elif mutation_type == 'remove_operator':
            # 移除一个操作符（简化）
            for op in self.operators.keys():
                if f"{op}(" in expr:
                    return expr.replace(f"{op}(", "").replace(")", "", 1)
        
        return expr
    
    def _extract_subexpressions(self, expr: str) -> List[str]:
        """提取子表达式"""
        subexprs = []
        depth = 0
        start = 0
        
        for i, char in enumerate(expr):
            if char == '(':
                if depth == 0:
                    start = i
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    subexprs.append(expr[start:i+1])
        
        if not subexprs:
            subexprs.append(expr)
        
        return subexprs
    
    def get_top_features(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """获取 Top N 因子"""
        return self.best_features[:top_n]
    
    def save_features(self, filepath: str):
        """保存挖掘的因子"""
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump({
                'best_features': self.best_features,
                'generation': self.generation,
                'base_features': self.base_features
            }, f)
    
    def load_features(self, filepath: str):
        """加载因子"""
        import pickle
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.best_features = data['best_features']
            self.generation = data['generation']
            self.base_features = data['base_features']


class AlphaGenerator:
    """Alpha158 风格因子生成器"""
    
    def __init__(self):
        self.alpha_functions = self._init_alpha_functions()
    
    def _init_alpha_functions(self) -> Dict[str, callable]:
        """初始化 Alpha158 风格因子"""
        alphas = {}
        
        # Alpha#001: -1 * CORR(RANK(DELAY(close, 1)), RANK(VOLUME), 10)
        alphas['alpha_001'] = lambda df: -1 * df['close'].shift(1).rolling(10).corr(df['volume'].rank())
        
        # Alpha#002: -1 * DELTA(DELTA(DELAY(close, 1), 1), 1)
        alphas['alpha_002'] = lambda df: -1 * df['close'].shift(1).diff().diff()
        
        # Alpha#003: SUM(OPEN, 5) * SUM(RET, 5) - DELAY(SUM(OPEN, 5) * SUM(RET, 5), 10)
        alphas['alpha_003'] = lambda df: (df['open'].rolling(5).sum() * df['close'].pct_change().rolling(5).sum()) - \
                                         (df['open'].rolling(5).sum() * df['close'].pct_change().rolling(5).sum()).shift(10)
        
        # Alpha#004: -1 * TS_RANK(RANK(HIGH), 9)
        alphas['alpha_004'] = lambda df: -1 * df['high'].rolling(9).apply(lambda x: (x[-1] - x.min()) / (x.max() - x.min() + 1e-8))
        
        # Alpha#005: RANK(OPEN - (SUM(VWAP, 10) / 10)) * -1 * ABS(RANK(CLOSE - VWAP))
        alphas['alpha_005'] = lambda df: (df['open'] - (df['close'].rolling(10).mean() / 10)).rank() * \
                                         -1 * abs((df['close'] - df['close'].rolling(10).mean()).rank())
        
        # Alpha#006: -1 * CORR(OPEN, VOLUME, 10)
        alphas['alpha_006'] = lambda df: -1 * df['open'].rolling(10).corr(df['volume'])
        
        # Alpha#007: ADV15 < VOLUME ? -1 * TS_RANK(ABS(RET), 20) : 0
        alphas['alpha_007'] = lambda df: np.where(
            df['volume'].rolling(15).mean() < df['volume'],
            -1 * df['close'].pct_change().abs().rolling(20).apply(lambda x: (x[-1] - x.min()) / (x.max() - x.min() + 1e-8)),
            0
        )
        
        # Alpha#010: RET * VOLUME
        alphas['alpha_010'] = lambda df: df['close'].pct_change() * df['volume']
        
        # Alpha#014: -1 * CORR(RANK(OPEN), RANK(VOLUME), 15)
        alphas['alpha_014'] = lambda df: -1 * df['open'].rank().rolling(15).corr(df['volume'].rank())
        
        # Alpha#027: CMN_CLOSE / CMN_OPEN
        alphas['alpha_027'] = lambda df: df['close'].rolling(3).mean() / df['open'].rolling(3).mean()
        
        # Alpha#038: -1 * TS_RANK(RET, 10)
        alphas['alpha_038'] = lambda df: -1 * df['close'].pct_change().rolling(10).apply(lambda x: (x[-1] - x.min()) / (x.max() - x.min() + 1e-8))
        
        # Alpha#045: -1 * CORR(OPEN, CLOSE, 10)
        alphas['alpha_045'] = lambda df: -1 * df['open'].rolling(10).corr(df['close'])
        
        # Alpha#055: -1 * CORR(RANK(OPEN), RANK(CLOSE), 10)
        alphas['alpha_055'] = lambda df: -1 * df['open'].rank().rolling(10).corr(df['close'].rank())
        
        # Alpha#066: -1 * CORR(OPEN, VOLUME, 10)
        alphas['alpha_066'] = lambda df: -1 * df['open'].rolling(10).corr(df['volume'])
        
        # Alpha#101: (CLOSE - OPEN) / (HIGH - LOW + 0.001)
        alphas['alpha_101'] = lambda df: (df['close'] - df['open']) / (df['high'] - df['low'] + 0.001)
        
        # Alpha#120: -1 * CORR(VWAP, VOLUME, 20)
        alphas['alpha_120'] = lambda df: -1 * df['close'].rolling(20).corr(df['volume'])
        
        # Alpha#158: -1 * CORR(RANK(RET), RANK(VOLUME), 20)
        alphas['alpha_158'] = lambda df: -1 * df['close'].pct_change().rank().rolling(20).corr(df['volume'].rank())
        
        return alphas
    
    def generate_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成所有 Alpha158 风格因子
        
        Args:
            data: OHLCV 数据
        
        Returns:
            包含所有因子的 DataFrame
        """
        df = data.copy()
        
        print(f"📊 生成 Alpha158 风格因子 - 共{len(self.alpha_functions)}个")
        
        for name, func in self.alpha_functions.items():
            try:
                df[name] = func(df)
            except Exception as e:
                df[name] = np.nan
        
        # 去除 NaN
        df = df.dropna()
        
        print(f"✅ 因子生成完成 - 有效数据:{len(df)}行")
        
        return df
    
    def get_alpha_names(self) -> List[str]:
        """获取所有 Alpha 因子名称"""
        return list(self.alpha_functions.keys())
