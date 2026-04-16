"""
深度学习与强化学习示例
演示如何使用 LSTM/Transformer 和 RL 策略
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def demo_lstm_prediction():
    """演示 LSTM 价格预测"""
    print("\n" + "="*60)
    print("🧠 LSTM 价格预测示例")
    print("="*60)
    
    from src.ml.deep_learning import create_lstm_model, DeepLearningModel
    
    # 生成模拟数据
    np.random.seed(42)
    n_samples = 1000
    
    # 生成带趋势的价格序列
    trend = np.linspace(100, 150, n_samples)
    noise = np.random.randn(n_samples) * 2
    prices = trend + noise
    
    # 创建特征
    df = pd.DataFrame({
        'close': prices,
        'open': prices * (1 + np.random.randn(n_samples) * 0.01),
        'high': prices * (1 + np.abs(np.random.randn(n_samples) * 0.02)),
        'low': prices * (1 - np.abs(np.random.randn(n_samples) * 0.02)),
        'volume': np.random.randint(1000, 10000, n_samples)
    })
    
    # 添加技术指标
    df['ma_5'] = df['close'].rolling(5).mean()
    df['ma_20'] = df['close'].rolling(20).mean()
    df['return_1d'] = df['close'].pct_change()
    df['volatility_10d'] = df['return_1d'].rolling(10).std()
    
    df = df.dropna()
    
    # 准备特征
    feature_cols = ['close', 'ma_5', 'ma_20', 'return_1d', 'volatility_10d']
    target_col = 'close'
    
    # 创建序列数据
    lookback = 20
    horizon = 5
    
    X, y = [], []
    for i in range(lookback, len(df) - horizon):
        X.append(df[feature_cols].iloc[i-lookback:i].values)
        y.append(df[target_col].iloc[i])
    
    X = np.array(X)
    y = np.array(y)
    
    # 划分训练测试集
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"\n📊 数据准备完成")
    print(f"  训练集：{len(X_train)} 样本")
    print(f"  测试集：{len(X_test)} 样本")
    print(f"  序列长度：{lookback}")
    print(f"  特征数：{len(feature_cols)}")
    
    # 构建 LSTM 模型
    print(f"\n🏗️  构建 LSTM 模型...")
    
    try:
        model = create_lstm_model(
            input_shape=(lookback, len(feature_cols)),
            lstm_units=[64, 32],
            dropout_rate=0.2,
            dense_units=[32],
            output_units=1
        )
        
        print(f"✅ LSTM 模型构建成功")
        print(f"  输入形状：{X_train.shape[1:]}")
        print(f"  LSTM 层：[64, 32]")
        print(f"  全连接层：[32]")
        
        # 训练（简化演示，实际训练需要更多 epoch）
        print(f"\n📈 开始训练...")
        
        history = model.train(
            X_train, y_train,
            X_test, y_test,
            epochs=10,
            batch_size=32,
            learning_rate=0.001,
            early_stopping_patience=5
        )
        
        print(f"\n✅ 训练完成")
        print(f"  最终训练损失：{history['loss'][-1]:.6f}")
        if 'val_loss' in history:
            print(f"  最终验证损失：{history['val_loss'][-1]:.6f}")
        
        # 预测
        predictions = model.predict(X_test)
        
        # 评估
        mse = np.mean((predictions - y_test) ** 2)
        mae = np.mean(np.abs(predictions - y_test))
        
        print(f"\n📊 测试集评估")
        print(f"  MSE: {mse:.6f}")
        print(f"  MAE: {mae:.6f}")
        print(f"  MAPE: {np.mean(np.abs((y_test - predictions) / y_test)) * 100:.2f}%")
        
    except ImportError as e:
        print(f"⚠️  需要安装深度学习框架:")
        print(f"  pip install torch  # 或")
        print(f"  pip install tensorflow")
        print(f"\n{e}")


def demo_auto_feature_mining():
    """演示因子自动挖掘"""
    print("\n" + "="*60)
    print("⛏️  因子自动挖掘示例")
    print("="*60)
    
    from src.ml.auto_feature_miner import AutoFeatureMiner, AlphaGenerator
    
    # 生成模拟数据
    np.random.seed(42)
    n_samples = 500
    
    df = pd.DataFrame({
        'close': 100 + np.cumsum(np.random.randn(n_samples)),
        'open': 100 + np.cumsum(np.random.randn(n_samples)),
        'high': 100 + np.cumsum(np.random.randn(n_samples)) + np.abs(np.random.randn(n_samples)) * 2,
        'low': 100 + np.cumsum(np.random.randn(n_samples)) - np.abs(np.random.randn(n_samples)) * 2,
        'volume': np.random.randint(1000, 10000, n_samples)
    })
    
    df['close'] = df['close'].clip(lower=50)
    
    print(f"\n📊 数据：{len(df)} 行")
    
    # 方法 1: Alpha158 风格因子生成
    print(f"\n🔧 生成 Alpha158 风格因子...")
    
    alpha_gen = AlphaGenerator()
    df_with_alphas = alpha_gen.generate_all(df)
    
    print(f"✅ 生成 {len(alpha_gen.get_alpha_names())} 个 Alpha 因子")
    print(f"   样本：{alpha_gen.get_alpha_names()[:5]}...")
    
    # 方法 2: 遗传算法因子挖掘
    print(f"\n🧬 使用遗传算法挖掘因子...")
    
    miner = AutoFeatureMiner()
    
    best_features = miner.evolve(
        data=df,
        population_size=30,
        generations=10,
        mutation_rate=0.2,
        crossover_rate=0.7,
        horizon=5
    )
    
    if best_features:
        print(f"\n✅ 挖掘到 {len(best_features)} 个有效因子")
        print(f"\n🏆 Top 5 因子:")
        for i, feat in enumerate(best_features[:5], 1):
            print(f"  {i}. IC={feat['ic']:.4f} - {feat['expression'][:80]}...")
    
    print(f"\n💡 提示：可以使用这些因子构建多因子策略")


def demo_ensemble_learning():
    """演示集成学习"""
    print("\n" + "="*60)
    print("📚 集成学习示例 (Stacking/Blending/Voting)")
    print("="*60)
    
    from src.ml.ensemble_trainer import EnsembleTrainer, StackingClassifier
    
    # 生成模拟数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 20
    
    X = pd.DataFrame(np.random.randn(n_samples, n_features),
                     columns=[f'feature_{i}' for i in range(n_features)])
    
    # 创建标签（未来收益率）
    y = pd.Series((np.random.randn(n_samples) > 0).astype(int))
    
    # 划分训练测试集
    split_idx = int(n_samples * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"\n📊 数据：{n_samples} 样本，{n_features} 特征")
    
    # 方法 1: Stacking
    print(f"\n📚 Stacking 集成...")
    
    try:
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
        from sklearn.linear_model import LogisticRegression
        
        ensemble = EnsembleTrainer(task_type="binary")
        
        # 添加基模型
        ensemble.add_base_model("rf", RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42))
        ensemble.add_base_model("gb", GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42))
        ensemble.add_base_model("et", ExtraTreesClassifier(n_estimators=100, max_depth=5, random_state=42))
        
        # 训练 Stacking
        metrics = ensemble.train_stacking(
            X_train, y_train,
            X_test, y_test,
            n_folds=5,
            meta_model_type="logistic_regression"
        )
        
        print(f"\n✅ Stacking 训练完成")
        print(f"  训练集 AUC: {metrics.get('train_auc', 'N/A'):.4f}" if metrics.get('train_auc') else "  训练集 Accuracy: {:.4f}".format(metrics.get('train_accuracy', 0)))
        print(f"  验证集 AUC: {metrics.get('val_auc', 'N/A'):.4f}" if metrics.get('val_auc') else "  验证集 Accuracy: {:.4f}".format(metrics.get('val_accuracy', 0)))
        
        # 模型权重
        weights = ensemble.get_model_weights()
        if weights:
            print(f"\n⚖️  模型权重:")
            for name, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
                print(f"  {name}: {weight:.3f}")
        
    except ImportError as e:
        print(f"⚠️  需要安装 scikit-learn: pip install scikit-learn")
    
    # 方法 2: 简化的 Stacking 分类器
    print(f"\n🚀 使用 StackingClassifier (一键式)...")
    
    try:
        clf = StackingClassifier(n_folds=5)
        metrics = clf.fit(X_train, y_train, X_test, y_test)
        
        print(f"✅ 训练完成")
        
    except Exception as e:
        print(f"⚠️  {e}")


def demo_rl_strategy():
    """演示强化学习策略"""
    print("\n" + "="*60)
    print("🤖 强化学习交易策略示例")
    print("="*60)
    
    from src.strategies.rl_strategy import RLTradingStrategy
    
    # 生成模拟价格
    np.random.seed(42)
    n_days = 500
    
    df = pd.DataFrame({
        'close': 100 + np.cumsum(np.random.randn(n_days)),
        'open': 100 + np.cumsum(np.random.randn(n_days)),
        'high': 100 + np.cumsum(np.random.randn(n_days)) + np.abs(np.random.randn(n_days)) * 2,
        'low': 100 + np.cumsum(np.random.randn(n_days)) - np.abs(np.random.randn(n_days)) * 2,
        'volume': np.random.randint(1000, 10000, n_days),
        'timestamp': pd.date_range('2024-01-01', periods=n_days)
    })
    
    df['close'] = df['close'].clip(lower=50)
    
    print(f"\n📊 数据：{len(df)} 天")
    
    # 创建 RL 策略
    strategy = RLTradingStrategy(
        lookback_window=20,
        training_episodes=100,
        epsilon_start=1.0,
        epsilon_end=0.1,
        epsilon_decay=0.99
    )
    
    print(f"\n🏗️  RL 策略配置:")
    print(f"  回溯窗口：{strategy.params['lookback_window']}")
    print(f"  训练回合：{strategy.params['training_episodes']}")
    print(f"  探索率：{strategy.params['epsilon_start']} -> {strategy.params['epsilon_end']}")
    
    # 运行策略（模拟训练）
    print(f"\n📈 运行策略...")
    
    signals = []
    for idx, row in df.iterrows():
        signal = strategy.on_bar(row)
        if signal:
            signals.append(signal)
    
    print(f"\n✅ 生成 {len(signals)} 个交易信号")
    
    # 统计
    if signals:
        buy_signals = [s for s in signals if s.direction == 'long']
        sell_signals = [s for s in signals if s.direction == 'short']
        close_signals = [s for s in signals if 'close' in s.direction]
        
        print(f"\n📊 信号统计:")
        print(f"  买入：{len(buy_signals)}")
        print(f"  卖出：{len(sell_signals)}")
        print(f"  平仓：{len(close_signals)}")


def demo_arbitrage_strategy():
    """演示套利策略"""
    print("\n" + "="*60)
    print("💹 套利策略示例")
    print("="*60)
    
    from src.strategies.arbitrage_strategies import SpotFuturesArbitrage, CalendarSpreadArbitrage
    
    # 生成模拟数据（期货和现货）
    np.random.seed(42)
    n_days = 300
    
    # 期货价格
    futures_price = 100 + np.cumsum(np.random.randn(n_days))
    
    # 现货价格（与期货有价差关系）
    spread_mean = 2
    spread_std = 1
    spreads = spread_mean + np.random.randn(n_days) * spread_std
    spot_price = futures_price - spreads
    
    df = pd.DataFrame({
        'close': futures_price,
        'open': futures_price * (1 + np.random.randn(n_days) * 0.01),
        'high': futures_price * (1 + np.abs(np.random.randn(n_days) * 0.02)),
        'low': futures_price * (1 - np.abs(np.random.randn(n_days) * 0.02)),
        'volume': np.random.randint(1000, 10000, n_days),
        'spot_price': spot_price,
        'timestamp': pd.date_range('2024-01-01', periods=n_days)
    })
    
    print(f"\n📊 数据：{len(df)} 天")
    print(f"  期货均价：{df['close'].mean():.2f}")
    print(f"  现货均价：{df['spot_price'].mean():.2f}")
    print(f"  平均价差：{(df['close'] - df['spot_price']).mean():.2f}")
    
    # 期现套利策略
    strategy = SpotFuturesArbitrage(
        zscore_entry=2.0,
        zscore_exit=0.5,
        lookback_window=60
    )
    
    print(f"\n🏗️  策略配置:")
    print(f"  开仓阈值：Z-Score > {strategy.params['zscore_entry']}")
    print(f"  平仓阈值：Z-Score < {strategy.params['zscore_exit']}")
    print(f"  历史窗口：{strategy.params['lookback_window']} 天")
    
    # 运行策略
    print(f"\n📈 运行策略...")
    
    signals = []
    for idx, row in df.iterrows():
        signal = strategy.on_bar(row)
        if signal:
            signals.append(signal)
    
    print(f"\n✅ 生成 {len(signals)} 个交易信号")
    
    # 统计
    if signals:
        long_signals = [s for s in signals if 'long' in s.direction]
        short_signals = [s for s in signals if 'short' in s.direction]
        close_signals = [s for s in signals if 'close' in s.direction]
        
        print(f"\n📊 信号统计:")
        print(f"  开多：{len(long_signals)}")
        print(f"  开空：{len(short_signals)}")
        print(f"  平仓：{len(close_signals)}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 量化策略工厂 - 深度学习与强化学习演示")
    print("="*60)
    
    # 选择演示
    demos = {
        '1': ('LSTM 价格预测', demo_lstm_prediction),
        '2': ('因子自动挖掘', demo_auto_feature_mining),
        '3': ('集成学习', demo_ensemble_learning),
        '4': ('RL 交易策略', demo_rl_strategy),
        '5': ('套利策略', demo_arbitrage_strategy),
    }
    
    print("\n请选择演示:")
    for key, (name, _) in demos.items():
        print(f"  {key}. {name}")
    print(f"  a. 全部运行")
    
    choice = input("\n输入选项 (1-5 或 a): ").strip().lower()
    
    if choice == 'a':
        for _, (_, func) in demos.items():
            try:
                func()
            except Exception as e:
                print(f"\n❌ 错误：{e}")
    elif choice in demos:
        try:
            demos[choice][1]()
        except Exception as e:
            print(f"\n❌ 错误：{e}")
    else:
        print("无效选项")
    
    print("\n" + "="*60)
    print("✅ 演示完成")
    print("="*60)
