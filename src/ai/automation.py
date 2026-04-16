"""
AI 量化自动化运行脚本 - 每日自动执行
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import schedule
import time
import os
import warnings
warnings.filterwarnings('ignore')

from src.data.data_fetcher import DataFetcher
from src.ai.ai_trainer import AIModelTrainer
from src.ai.ai_strategy import AIStrategy
from src.ml.ml_predictor import MLPredictor
from src.backtest_engine import BacktestEngine
from src.report_generator import ReportGenerator


class AIQuantAutomation:
    """AI 量化自动化系统"""
    
    def __init__(
        self,
        symbols: list = ["000001", "000002", "600000"],
        model_path: str = "./models/ai_model.pkl",
        report_dir: str = "./reports/auto"
    ):
        """
        初始化自动化系统
        
        Args:
            symbols: 股票池
            model_path: 模型路径
            report_dir: 报告目录
        """
        self.symbols = symbols
        self.model_path = model_path
        self.report_dir = report_dir
        
        self.trainer = None
        self.ml_predictor = None
        self.strategy = None
        
        # 创建目录
        os.makedirs(model_path.rsplit('/', 1)[0], exist_ok=True)
        os.makedirs(report_dir, exist_ok=True)
    
    def daily_job(self):
        """每日自动任务"""
        print(f"\n{'='*60}")
        print(f"[{datetime.now()}] 开始每日任务...")
        print(f"{'='*60}")
        
        # 1. 获取最新数据
        print("\n[1/5] 获取最新数据...")
        fetcher = DataFetcher(source="akshare")
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        all_data = []
        for symbol in self.symbols:
            print(f"  获取 {symbol} 数据...")
            data = fetcher.fetch_stock_data(symbol, start_date, end_date)
            if len(data) > 0:
                all_data.append(data)
        
        if not all_data:
            print("  ❌ 数据获取失败")
            return
        
        combined_data = pd.concat(all_data, ignore_index=True)
        print(f"  ✅ 获取数据：{len(combined_data)} 条")
        
        # 2. 检查模型是否需要重训
        print("\n[2/5] 检查模型状态...")
        should_retrain = self._should_retrain()
        
        if should_retrain:
            print("  模型需要重训...")
            self._retrain_model(combined_data)
        else:
            print("  模型状态良好，无需重训")
            self._load_model()
        
        # 3. 生成交易信号
        print("\n[3/5] 生成交易信号...")
        signals = self._generate_signals(combined_data)
        
        if signals:
            print(f"  ✅ 生成 {len(signals)} 个信号")
            for symbol, signal in signals.items():
                direction_map = {1: '买入', -1: '卖出', 0: '持有'}
                print(f"     {symbol}: {direction_map.get(signal, '未知')} (置信度：{signal})")
        else:
            print("  无交易信号")
        
        # 4. 保存信号
        print("\n[4/5] 保存信号...")
        self._save_signals(signals)
        
        # 5. 发送通知（可选）
        print("\n[5/5] 发送通知...")
        self._send_notification(signals)
        
        print(f"\n{'='*60}")
        print(f"[{datetime.now()}] 每日任务完成")
        print(f"{'='*60}")
    
    def _should_retrain(self) -> bool:
        """检查是否需要重训模型"""
        # 简单规则：如果模型超过 7 天未更新，则重训
        if not os.path.exists(self.model_path):
            return True
        
        model_time = datetime.fromtimestamp(os.path.getmtime(self.model_path))
        days_since_update = (datetime.now() - model_time).days
        
        return days_since_update > 7
    
    def _retrain_model(self, data: pd.DataFrame):
        """重训模型"""
        self.trainer = AIModelTrainer(task_type="binary")
        X_train, y_train, X_test, y_test = self.trainer.prepare_data(data)
        
        model_types = ['random_forest', 'xgboost', 'lightgbm']
        self.trainer.train_models(X_train, y_train, X_test, y_test, model_types)
        
        self.trainer.save_model(self.model_path)
        print(f"  ✅ 模型已保存：{self.model_path}")
        
        # 创建预测器
        self.ml_predictor = MLPredictor(
            model=self.trainer.model,
            feature_names=self.trainer.feature_names
        )
        
        # 创建策略
        self.strategy = AIStrategy(
            ml_predictor=self.ml_predictor,
            confidence_threshold=0.6
        )
    
    def _load_model(self):
        """加载模型"""
        if self.trainer is None:
            self.trainer = AIModelTrainer(task_type="binary")
            self.trainer.load_model(self.model_path)
        
        self.ml_predictor = MLPredictor(
            model=self.trainer.model,
            feature_names=self.trainer.feature_names
        )
        
        self.strategy = AIStrategy(
            ml_predictor=self.ml_predictor,
            confidence_threshold=0.6
        )
    
    def _generate_signals(self, data: pd.DataFrame) -> dict:
        """生成交易信号"""
        if self.ml_predictor is None:
            return {}
        
        signals = {}
        
        for symbol in self.symbols:
            symbol_data = data[data['symbol'] == symbol].iloc[-1:]
            
            if len(symbol_data) == 0:
                continue
            
            bar = symbol_data.iloc[-1]
            
            # 获取预测
            history = {
                'close': data[data['symbol'] == symbol]['close'].tolist()[-100:],
                'open': data[data['symbol'] == symbol]['open'].tolist()[-100:],
                'high': data[data['symbol'] == symbol]['high'].tolist()[-100:],
                'low': data[data['symbol'] == symbol]['low'].tolist()[-100:],
                'volume': data[data['symbol'] == symbol]['volume'].tolist()[-100:]
            }
            
            probas = self.ml_predictor.predict_proba(bar, history)
            
            if probas:
                prob_up = probas.get('1', 0)
                
                if prob_up > 0.6:
                    signals[symbol] = 1  # 买入
                elif prob_up < 0.4:
                    signals[symbol] = -1  # 卖出
                else:
                    signals[symbol] = 0  # 持有
        
        return signals
    
    def _save_signals(self, signals: dict):
        """保存信号"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"{self.report_dir}/signals_{timestamp}.csv"
        
        df = pd.DataFrame([
            {'symbol': symbol, 'signal': signal}
            for symbol, signal in signals.items()
        ])
        
        df.to_csv(filepath, index=False)
        print(f"  ✅ 信号已保存：{filepath}")
    
    def _send_notification(self, signals: dict):
        """发送通知（简化版）"""
        if not signals:
            return
        
        # 这里可以集成邮件、微信、钉钉等通知
        print("  通知内容:")
        for symbol, signal in signals.items():
            direction_map = {1: '买入', -1: '卖出', 0: '持有'}
            print(f"    {symbol}: {direction_map.get(signal, '未知')}")
    
    def start_scheduler(self):
        """启动定时任务"""
        print("启动 AI 量化自动化系统...")
        print(f"股票池：{self.symbols}")
        print(f"模型路径：{self.model_path}")
        
        # 每天 15:30 运行（A 股收盘后）
        schedule.every().day.at("15:30").do(self.daily_job)
        
        # 立即运行一次
        self.daily_job()
        
        print("\n定时任务已启动")
        print("每天 15:30 自动执行")
        print("按 Ctrl+C 停止")
        
        while True:
            schedule.run_pending()
            time.sleep(60)


def run_automation_demo():
    """运行自动化演示"""
    print("=" * 60)
    print("AI 量化自动化系统 - 演示")
    print("=" * 60)
    
    # 创建自动化系统
    auto = AIQuantAutomation(
        symbols=["000001", "000002", "600000"],
        model_path="./models/ai_model.pkl",
        report_dir="./reports/auto"
    )
    
    # 运行一次
    auto.daily_job()
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)
    print("\n如需启动定时任务，运行:")
    print("  auto.start_scheduler()")


if __name__ == "__main__":
    run_automation_demo()
