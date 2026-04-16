"""
AI 量化完整回测流程 - 从数据到回测一站式
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from src.data.data_fetcher import DataFetcher
from src.ai.ai_trainer import AIModelTrainer
from src.ai.ai_strategy import AIStrategy
from src.ml.ml_predictor import MLPredictor
from src.backtest_engine import BacktestEngine
from src.report_generator import ReportGenerator
from src.portfolio_analyzer import PortfolioAnalyzer


class AIQuantBacktest:
    """AI 量化回测系统 - 端到端流程"""
    
    def __init__(
        self,
        symbol: str = "000001",
        start_date: str = "20230101",
        end_date: str = "20231231",
        task_type: str = "binary",
        initial_cash: float = 1000000
    ):
        """
        初始化 AI 量化回测系统
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            task_type: 任务类型 (binary/multiclass)
            initial_cash: 初始资金
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.task_type = task_type
        self.initial_cash = initial_cash
        
        self.data = None
        self.trainer = None
        self.strategy = None
        self.result = None
    
    def run(self, verbose: bool = True):
        """
        运行完整回测流程
        
        Args:
            verbose: 是否打印详细信息
        
        Returns:
            回测结果
        """
        if verbose:
            print("=" * 70)
            print("AI 量化自动回测系统")
            print("=" * 70)
            print(f"股票代码：{self.symbol}")
            print(f"回测周期：{self.start_date} ~ {self.end_date}")
            print(f"任务类型：{self.task_type}")
            print(f"初始资金：{self.initial_cash:,.0f}")
            print("=" * 70)
        
        # 步骤 1: 获取数据
        if verbose:
            print("\n【步骤 1/5】获取数据...")
        
        fetcher = DataFetcher(source="akshare")
        self.data = fetcher.fetch_stock_data(
            self.symbol,
            self.start_date,
            self.end_date
        )
        
        if len(self.data) == 0:
            print("❌ 数据获取失败")
            return None
        
        if verbose:
            print(f"  ✅ 获取数据：{len(self.data)} 条")
            print(f"     时间范围：{self.data['timestamp'].min()} ~ {self.data['timestamp'].max()}")
        
        # 步骤 2: 训练 AI 模型
        if verbose:
            print("\n【步骤 2/5】训练 AI 模型...")
        
        self.trainer = AIModelTrainer(task_type=self.task_type)
        X_train, y_train, X_test, y_test = self.trainer.prepare_data(self.data)
        
        model_types = ['random_forest', 'xgboost', 'lightgbm']
        self.trainer.train_models(X_train, y_train, X_test, y_test, model_types)
        
        if verbose:
            print(f"  ✅ 最佳模型：{self.trainer.best_model_type}")
            if self.task_type == "binary":
                print(f"     测试集准确率：{self.trainer.metrics.get('test_accuracy', 0):.4f}")
            else:
                print(f"     测试集 R²: {self.trainer.metrics.get('test_r2', 0):.4f}")
        
        # 步骤 3: 创建 AI 策略
        if verbose:
            print("\n【步骤 3/5】创建 AI 策略...")
        
        ml_predictor = MLPredictor(
            model=self.trainer.model,
            feature_names=self.trainer.feature_names
        )
        
        self.strategy = AIStrategy(
            ml_predictor=ml_predictor,
            confidence_threshold=0.6,
            stop_loss_pct=0.03,
            take_profit_pct=0.05
        )
        
        if verbose:
            print(f"  ✅ AI 策略创建成功")
            print(f"     置信度阈值：0.6")
            print(f"     止损：3%")
            print(f"     止盈：5%")
        
        # 步骤 4: 运行回测
        if verbose:
            print("\n【步骤 4/5】运行回测...")
        
        engine = BacktestEngine(
            strategy=self.strategy,
            initial_cash=self.initial_cash,
            commission_rate=0.0003,
            slippage=1.0
        )
        
        self.result = engine.run(self.data, self.symbol)
        
        if verbose:
            print(f"  ✅ 回测完成")
        
        # 步骤 5: 生成报告
        if verbose:
            print("\n【步骤 5/5】生成报告...")
        
        report_gen = ReportGenerator(output_dir="./reports")
        filepath = report_gen.save_report(
            result=self.result,
            strategy_name=f"AI_{self.trainer.best_model_type}",
            format="markdown"
        )
        
        if verbose:
            print(f"  ✅ 报告已保存：{filepath}")
        
        # 打印回测结果
        if verbose:
            self._print_results()
        
        return self.result
    
    def _print_results(self):
        """打印回测结果"""
        print("\n" + "=" * 70)
        print("回测结果")
        print("=" * 70)
        
        print(f"\n【基本信息】")
        print(f"  策略名称：AI_{self.trainer.best_model_type}")
        print(f"  回测品种：{self.result.symbol}")
        print(f"  回测周期：{self.result.start_date[:10]} ~ {self.result.end_date[:10]}")
        print(f"  初始资金：{self.result.initial_cash:,.0f}")
        print(f"  最终资金：{self.result.final_cash:,.0f}")
        
        print(f"\n【业绩指标】")
        print(f"  总收益率：{self.result.total_return:.2f}%")
        print(f"  年化收益：{self.result.annualized_return:.2f}%")
        print(f"  夏普比率：{self.result.sharpe_ratio:.2f}")
        print(f"  最大回撤：{self.result.max_drawdown:.2f}%")
        
        if self.result.max_drawdown != 0:
            calmar = self.result.annualized_return / abs(self.result.max_drawdown)
            print(f"  卡玛比率：{calmar:.2f}")
        
        print(f"\n【交易统计】")
        print(f"  总交易次数：{self.result.total_trades}")
        print(f"  胜率：{self.result.win_rate:.2f}%")
        print(f"  盈亏比：{self.result.profit_loss_ratio:.2f}")
        print(f"  平均每笔收益：{self.result.avg_trade_return:.2f}")
        print(f"  最长连亏：{self.result.max_consecutive_losses} 次")
        
        print("\n" + "=" * 70)


def run_ai_backtest(
    symbol: str = "000001",
    start_date: str = "20230101",
    end_date: str = "20231231",
    task_type: str = "binary"
):
    """
    一键运行 AI 量化回测
    
    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        task_type: 任务类型
    
    Returns:
        回测结果
    """
    backtest = AIQuantBacktest(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        task_type=task_type
    )
    
    result = backtest.run(verbose=True)
    
    return result


if __name__ == "__main__":
    # 运行示例
    print("开始 AI 量化回测示例...")
    print("股票：平安银行 (000001)")
    print("周期：2023 年全年")
    print()
    
    result = run_ai_backtest(
        symbol="000001",
        start_date="20230101",
        end_date="20231231",
        task_type="binary"
    )
