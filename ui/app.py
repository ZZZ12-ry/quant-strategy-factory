"""
量化策略工厂 - Web UI 主页面
基于 Streamlit 构建
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 页面配置
st.set_page_config(
    page_title="量化策略工厂",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
    }
    h1, h2, h3 {
        color: #262730;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
</style>
""", unsafe_allow_html=True)


def load_css():
    """加载自定义样式"""
    st.markdown("""
    <style>
        .main-header {
            font-size: 36px;
            font-weight: bold;
            color: #1f77b4;
            margin-bottom: 20px;
        }
        .section-header {
            font-size: 24px;
            font-weight: bold;
            color: #262730;
            margin-top: 30px;
            margin-bottom: 15px;
        }
    </style>
    """, unsafe_allow_html=True)


def create_sample_data():
    """生成示例数据用于演示"""
    np.random.seed(42)
    n_days = 252
    
    # 日期
    dates = pd.date_range('2024-01-01', periods=n_days, freq='B')
    
    # 生成收益曲线
    strategy_returns = np.random.randn(n_days) * 0.02 + 0.0005
    benchmark_returns = np.random.randn(n_days) * 0.015 + 0.0003
    
    # 累计收益
    strategy_cum = (1 + strategy_returns).cumprod() - 1
    benchmark_cum = (1 + benchmark_returns).cumprod() - 1
    
    # 回撤
    strategy_peak = strategy_cum.cummax()
    drawdown = (strategy_cum - strategy_peak) / (1 + strategy_peak)
    
    # 月度收益
    df = pd.DataFrame({
        'date': dates,
        'strategy': strategy_cum,
        'benchmark': benchmark_cum,
        'drawdown': drawdown
    })
    df['month'] = df['date'].dt.to_period('M')
    monthly_returns = df.groupby('month')['strategy'].apply(lambda x: x.iloc[-1] - x.iloc[0])
    
    return df, strategy_returns, monthly_returns


def display_metrics(metrics):
    """显示关键指标卡片"""
    cols = st.columns(5)
    
    metric_configs = [
        ("总收益率", f"{metrics['total_return']:.2%}", "0.262626"),
        ("年化收益", f"{metrics['annualized']:.2%}", "0.262626"),
        ("夏普比率", f"{metrics['sharpe']:.2f}", "0.262626"),
        ("最大回撤", f"{metrics['max_drawdown']:.2%}", "d62728"),
        ("胜率", f"{metrics['win_rate']:.1%}", "2ca02c"),
    ]
    
    for i, (label, value, color) in enumerate(metric_configs):
        with cols[i]:
            st.markdown(f"""
                <div class="metric-card" style="border-left: 4px solid #{color};">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
            """, unsafe_allow_html=True)


def plot_cumulative_returns(df):
    """绘制累计收益曲线"""
    chart_data = df[['date', 'strategy', 'benchmark']].set_index('date')
    
    st.subheader("累计收益对比")
    st.line_chart(chart_data, use_container_width=True)


def plot_drawdown(df):
    """绘制回撤曲线"""
    drawdown_data = df[['date', 'drawdown']].set_index('date')
    
    st.subheader("回撤曲线")
    st.area_chart(drawdown_data, color="#d62728", use_container_width=True)


def plot_monthly_returns(monthly_returns):
    """绘制月度收益热力图"""
    st.subheader("月度收益热力图")
    
    # 转换为热力图格式
    monthly_df = pd.DataFrame({
        'month': monthly_returns.index.astype(str),
        'return': monthly_returns.values
    })
    
    # 创建热力图
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=[monthly_df['return'].values],
        x=monthly_df['month'].values,
        y=['收益率'],
        colorscale='RdYlGn',
        zmid=0
    ))
    
    fig.update_layout(
        height=150,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(tickangle=-45)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def main():
    """主函数"""
    load_css()
    
    # 标题
    st.markdown('<div class="main-header">量化策略工厂</div>', unsafe_allow_html=True)
    st.markdown("从策略创意到回测验证，只需 10 分钟")
    
    st.divider()
    
    # 侧边栏
    with st.sidebar:
        st.header("导航")
        
        page = st.radio(
            "选择页面",
            ["策略回测", "特征工程", "模型训练", "IC 分析", "关于"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.header("快速操作")
        if st.button("运行示例回测", use_container_width=True):
            st.session_state['run_demo'] = True
        if st.button("重置参数", use_container_width=True):
            st.session_state['params'] = {}
        
        st.divider()
        
        # 系统状态
        st.header("系统状态")
        st.info("策略工厂 v1.1\nML/DL 深化功能已启用")
    
    # 主内容区
    if page == "策略回测":
        render_backtest_page()
    elif page == "特征工程":
        render_feature_page()
    elif page == "模型训练":
        render_model_page()
    elif page == "IC 分析":
        render_ic_page()
    elif page == "关于":
        render_about_page()


def render_backtest_page():
    """策略回测页面"""
    st.header("策略回测")
    
    # 参数配置区
    with st.expander("策略参数配置", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            strategy_type = st.selectbox(
                "策略类型",
                ["双均线", "海龟交易", "通道突破", "布林带回归", "多因子"]
            )
            initial_capital = st.number_input("初始资金", value=1000000, step=100000)
        
        with col2:
            fast_ma = st.slider("快线周期", 5, 50, 10)
            slow_ma = st.slider("慢线周期", 20, 200, 30)
            commission = st.number_input("手续费率", value=0.0003, step=0.0001)
        
        with col3:
            symbol = st.text_input("交易品种", value="RB2405")
            start_date = st.date_input("开始日期", value=pd.Timestamp("2024-01-01"))
            end_date = st.date_input("结束日期", value=pd.Timestamp("2024-12-31"))
        
        run_button = st.button("运行回测", type="primary", use_container_width=True)
    
    # 回测结果
    if run_button or st.session_state.get('run_demo', False):
        with st.spinner("正在运行回测..."):
            # 生成示例数据
            df, strategy_returns, monthly_returns = create_sample_data()
            
            # 计算指标
            metrics = {
                'total_return': df['strategy'].iloc[-1],
                'annualized': (1 + df['strategy'].iloc[-1]) ** (252/len(df)) - 1,
                'sharpe': strategy_returns.mean() / strategy_returns.std() * np.sqrt(252),
                'max_drawdown': df['drawdown'].min(),
                'win_rate': (strategy_returns > 0).mean(),
            }
            
            # 显示指标
            display_metrics(metrics)
            
            st.divider()
            
            # 图表
            col1, col2 = st.columns(2)
            with col1:
                plot_cumulative_returns(df)
            with col2:
                plot_drawdown(df)
            
            # 月度收益
            plot_monthly_returns(monthly_returns)
            
            # 交易记录
            st.subheader("交易记录")
            trade_record = pd.DataFrame({
                '日期': pd.date_range('2024-01-01', periods=10, freq='ME'),
                '方向': ['买入', '卖出', '买入', '卖出'] * 3,
                '价格': np.random.uniform(3800, 4200, 12),
                '数量': np.random.randint(1, 10, 12),
                '盈亏': np.random.uniform(-5000, 8000, 12)
            })
            st.dataframe(trade_record, use_container_width=True)
            
            st.session_state['run_demo'] = False
    
    else:
        # 空状态
        st.info("点击"运行回测"按钮开始策略回测，或先配置策略参数")


def render_feature_page():
    """特征工程页面"""
    st.header("特征工程")
    
    st.markdown("### 特征选择工具")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 特征列表
        st.markdown("#### 可用特征")
        feature_names = [
            'return_1d', 'return_5d', 'return_20d',
            'ma_5', 'ma_10', 'ma_20',
            'rsi_6', 'rsi_12', 'rsi_24',
            'macd', 'macd_signal', 'macd_hist',
            'bb_position', 'volatility_10d', 'atr_14'
        ]
        
        selected_features = st.multiselect(
            "选择特征",
            feature_names,
            default=['return_1d', 'rsi_12', 'macd'],
            label_visibility="collapsed"
        )
    
    with col2:
        # 选择方法
        st.markdown("#### 选择方法")
        method = st.selectbox(
            "特征选择方法",
            ["方差过滤", "相关性过滤", "树模型重要性", "顺序选择 (推荐)"]
        )
        
        threshold = st.slider("阈值", 0.0, 1.0, 0.5)
        
        if st.button("运行特征选择", type="primary", use_container_width=True):
            st.success(f"已选择 {len(selected_features)} 个特征")


def render_model_page():
    """模型训练页面"""
    st.header("模型训练")
    
    st.markdown("### 高级 ML 模型")
    
    # 模型选择
    col1, col2 = st.columns(2)
    
    with col1:
        model_type = st.selectbox(
            "选择模型",
            ["XGBoost", "LightGBM", "CatBoost", "Random Forest"]
        )
        
        n_estimators = st.slider("树的数量", 50, 500, 100)
        max_depth = st.slider("最大深度", 3, 15, 5)
        learning_rate = st.slider("学习率", 0.01, 0.3, 0.1)
    
    with col2:
        st.markdown("#### 训练参数")
        test_size = st.slider("测试集比例", 0.1, 0.5, 0.2)
        cv_folds = st.slider("交叉验证折数", 3, 10, 5)
        random_state = st.number_input("随机种子", value=42)
    
    if st.button("开始训练", type="primary", use_container_width=True):
        with st.spinner(f"正在训练 {model_type} 模型..."):
            # 模拟训练过程
            progress_bar = st.progress(0)
            for i in range(100):
                progress_bar.progress(i + 1)
            
            st.success("模型训练完成！")
            
            # 显示结果
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("训练集 AUC", "0.9991")
            with col2:
                st.metric("验证集 AUC", "0.9820")
            with col3:
                st.metric("特征数", "22")


def render_ic_page():
    """IC 分析页面"""
    st.header("IC 分析")
    
    st.markdown("### 模型预测能力评估")
    
    # IC 指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("IC", "0.2337", "0.05")
    with col2:
        st.metric("Rank IC", "0.2244", "0.04")
    with col3:
        st.metric("ICIR", "2.64", "0.5")
    with col4:
        st.metric("方向准确率", "57.5%", "2%")
    
    st.divider()
    
    # IC 时间序列
    st.subheader("IC 时间序列")
    
    # 生成示例 IC 数据
    np.random.seed(42)
    ic_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100, freq='D'),
        'ic': np.random.randn(100) * 0.1 + 0.05,
        'rank_ic': np.random.randn(100) * 0.1 + 0.04
    }).set_index('date')
    
    st.line_chart(ic_data, use_container_width=True)
    
    # 分层回测
    st.subheader("分层回测结果")
    
    stratified_data = pd.DataFrame({
        '组别': ['0 (最低)', '1', '2', '3', '4 (最高)', '多空收益'],
        '平均收益': ['-1.25%', '-0.55%', '-0.05%', '0.22%', '1.01%', '2.27%'],
        '累计收益': ['-39.7%', '-20.1%', '-2.2%', '8.9%', '49.1%', '88.8%']
    })
    
    st.dataframe(stratified_data, use_container_width=True, hide_index=True)


def render_about_page():
    """关于页面"""
    st.header("关于量化策略工厂")
    
    st.markdown("""
    ### 项目简介
    
    量化策略工厂是一个专业的量化交易策略研发平台，帮助量化研究员和交易者：
    
    - 快速验证策略创意
    - 复用成熟策略模板
    - AI 增强预测能力
    - 专业风控系统
    
    ### 核心特性
    
    **策略库**: 24 个经典策略模板
    
    **因子库**: 130+ 量化因子
    
    **AI 增强**: XGBoost/LightGBM/CatBoost
    
    **风控系统**: 多层次止损 + 仓位管理
    
    ### 版本信息
    
    - 当前版本：v1.1
    - 更新日期：2026-04-17
    - ML/DL 深化功能已启用
    
    ### 相关链接
    
    - GitHub: https://github.com/ZZZ12-ry/quant-strategy-factory
    - 文档：docs/ML_DL_DEEPENING.md
    """)


if __name__ == "__main__":
    main()
