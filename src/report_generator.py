"""
报告生成器 - 生成策略回测报告
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from jinja2 import Template
import os


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = "./reports"):
        """
        初始化报告生成器
        
        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(
        self,
        result,
        strategy_name: str = None,
        format: str = "text"
    ) -> str:
        """
        生成回测报告
        
        Args:
            result: 回测结果
            strategy_name: 策略名称
            format: 输出格式 (text/html/markdown)
        
        Returns:
            报告内容
        """
        if format == "text":
            return self._generate_text_report(result, strategy_name)
        elif format == "html":
            return self._generate_html_report(result, strategy_name)
        elif format == "markdown":
            return self._generate_markdown_report(result, strategy_name)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _generate_text_report(self, result, strategy_name: str = None) -> str:
        """生成文本报告"""
        name = strategy_name or result.strategy_name
        
        report = f"""
═══════════════════════════════════════════════════
策略回测报告 - {name}
═══════════════════════════════════════════════════

基本信息
───────────────────────────────────────────────────
策略名称：{name}
回测品种：{result.symbol}
回测周期：{result.start_date} ~ {result.end_date}
初始资金：{result.initial_cash:,.0f}
最终资金：{result.final_cash:,.0f}

业绩指标
───────────────────────────────────────────────────
总收益率：{result.total_return:.2f}%
年化收益：{result.annualized_return:.2f}%
夏普比率：{result.sharpe_ratio:.2f}
最大回撤：{result.max_drawdown:.2f}%
卡玛比率：{result.annualized_return / abs(result.max_drawdown) if result.max_drawdown != 0 else 0:.2f}

交易统计
───────────────────────────────────────────────────
总交易次数：{result.total_trades}
胜率：{result.win_rate:.2f}%
盈亏比：{result.profit_loss_ratio:.2f}
平均每笔收益：{result.avg_trade_return:.2f}
最长连亏：{result.max_consecutive_losses} 次

风险指标
───────────────────────────────────────────────────
初始资金：{result.initial_cash:,.0f}
最终资金：{result.final_cash:,.0f}
绝对收益：{result.final_cash - result.initial_cash:,.0f}

═══════════════════════════════════════════════════
报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
═══════════════════════════════════════════════════
"""
        return report
    
    def _generate_markdown_report(self, result, strategy_name: str = None) -> str:
        """生成 Markdown 报告"""
        name = strategy_name or result.strategy_name
        
        report = f"""# 策略回测报告 - {name}

## 基本信息

| 项目 | 值 |
|------|-----|
| 策略名称 | {name} |
| 回测品种 | {result.symbol} |
| 回测周期 | {result.start_date} ~ {result.end_date} |
| 初始资金 | {result.initial_cash:,.0f} |
| 最终资金 | {result.final_cash:,.0f} |

## 业绩指标

| 指标 | 值 |
|------|-----|
| 总收益率 | {result.total_return:.2f}% |
| 年化收益 | {result.annualized_return:.2f}% |
| 夏普比率 | {result.sharpe_ratio:.2f} |
| 最大回撤 | {result.max_drawdown:.2f}% |
| 卡玛比率 | {result.annualized_return / abs(result.max_drawdown) if result.max_drawdown != 0 else 0:.2f} |

## 交易统计

| 指标 | 值 |
|------|-----|
| 总交易次数 | {result.total_trades} |
| 胜率 | {result.win_rate:.2f}% |
| 盈亏比 | {result.profit_loss_ratio:.2f} |
| 平均每笔收益 | {result.avg_trade_return:.2f} |
| 最长连亏 | {result.max_consecutive_losses} 次 |

## 权益曲线

（此处可插入权益曲线图表）

---
*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        return report
    
    def _generate_html_report(self, result, strategy_name: str = None) -> str:
        """生成 HTML 报告"""
        name = strategy_name or result.strategy_name
        
        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <title>策略回测报告 - {{ name }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .metric { font-size: 1.2em; }
        .positive { color: green; }
        .negative { color: red; }
    </style>
</head>
<body>
    <h1>策略回测报告 - {{ name }}</h1>
    
    <h2>基本信息</h2>
    <table>
        <tr><th>策略名称</th><td>{{ name }}</td></tr>
        <tr><th>回测品种</th><td>{{ result.symbol }}</td></tr>
        <tr><th>回测周期</th><td>{{ result.start_date }} ~ {{ result.end_date }}</td></tr>
        <tr><th>初始资金</th><td>{{ "%.0f"|format(result.initial_cash) }}</td></tr>
        <tr><th>最终资金</th><td>{{ "%.0f"|format(result.final_cash) }}</td></tr>
    </table>
    
    <h2>业绩指标</h2>
    <table>
        <tr><th>总收益率</th><td class="{{ 'positive' if result.total_return > 0 else 'negative' }}">{{ "%.2f"|format(result.total_return) }}%</td></tr>
        <tr><th>年化收益</th><td class="{{ 'positive' if result.annualized_return > 0 else 'negative' }}">{{ "%.2f"|format(result.annualized_return) }}%</td></tr>
        <tr><th>夏普比率</th><td>{{ "%.2f"|format(result.sharpe_ratio) }}</td></tr>
        <tr><th>最大回撤</th><td class="negative">{{ "%.2f"|format(result.max_drawdown) }}%</td></tr>
    </table>
    
    <h2>交易统计</h2>
    <table>
        <tr><th>总交易次数</th><td>{{ result.total_trades }}</td></tr>
        <tr><th>胜率</th><td>{{ "%.2f"|format(result.win_rate) }}%</td></tr>
        <tr><th>盈亏比</th><td>{{ "%.2f"|format(result.profit_loss_ratio) }}</td></tr>
        <tr><th>平均每笔收益</th><td>{{ "%.2f"|format(result.avg_trade_return) }}</td></tr>
        <tr><th>最长连亏</th><td>{{ result.max_consecutive_losses }} 次</td></tr>
    </table>
    
    <p><em>报告生成时间：{{ timestamp }}</em></p>
</body>
</html>
""")
        
        html = template.render(
            name=name,
            result=result,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        return html
    
    def save_report(
        self,
        result,
        strategy_name: str = None,
        format: str = "text",
        filename: str = None
    ) -> str:
        """
        保存报告到文件
        
        Args:
            result: 回测结果
            strategy_name: 策略名称
            format: 输出格式
            filename: 文件名
        
        Returns:
            文件路径
        """
        content = self.generate_report(result, strategy_name, format)
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{strategy_name or result.strategy_name}_{timestamp}"
        
        ext_map = {"text": "txt", "html": "html", "markdown": "md"}
        ext = ext_map.get(format, "txt")
        
        filepath = os.path.join(self.output_dir, f"{filename}.{ext}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Report saved to: {filepath}")
        return filepath
    
    def generate_comparison_report(
        self,
        results: Dict[str, Any],
        format: str = "markdown"
    ) -> str:
        """
        生成多策略对比报告
        
        Args:
            results: 策略结果字典 {strategy_name: result}
            format: 输出格式
        
        Returns:
            报告内容
        """
        if format == "markdown":
            report = "# 多策略对比报告\n\n"
            report += "## 业绩指标对比\n\n"
            report += "| 策略 | 总收益 | 年化 | 夏普 | 最大回撤 | 胜率 |\n"
            report += "|------|--------|------|------|----------|------|\n"
            
            for name, result in results.items():
                report += f"| {name} | {result.total_return:.1f}% | {result.annualized_return:.1f}% | {result.sharpe_ratio:.2f} | {result.max_drawdown:.1f}% | {result.win_rate:.1f}% |\n"
            
            return report
        else:
            raise NotImplementedError("Only markdown format supported for comparison report")
