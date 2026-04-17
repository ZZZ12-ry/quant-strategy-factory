"""
IC 分析页面 - 模型预测能力评估
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def generate_ic_data():
    """生成 IC 分析数据"""
    np.random.seed(42)
    n_days = 200
    
    # 日期
    dates = pd.date_range('2024-01-01', periods=n_days, freq='B')
    
    # 生成预测值和真实值
    pred = np.random.randn(n_days) * 0.5
    true = (pred * 0.3 + np.random.randn(n_days) * 0.7 > 0).astype(int)
    returns = pred * 0.02 + np.random.randn(n_days) * 0.01
    
    # 滚动 IC
    ic_series = []
    rank_ic_series = []
    window = 20
    
    for i in range(window, n_days):
        ic = np.corrcoef(pred[i-window:i], true[i-window:i])[0, 1]
        rank_ic = pd.Series(pred[i-window:i]).corr(pd.Series(true[i-window:i]).rank())
        ic_series.append(ic)
        rank_ic_series.append(rank_ic)
    
    ic_df = pd.DataFrame({
        'date': dates[window:],
        'ic': ic_series,
        'rank_ic': rank_ic_series
    }).set_index('date')
    
    # 分层回测数据
    stratified = pd.DataFrame({
        '组别': ['0 (最低)', '1', '2', '3', '4 (最高)', '多空收益'],
        '平均收益': ['-1.25%', '-0.55%', '-0.05%', '0.22%', '1.01%', '2.27%'],
        '样本数': [40, 40, 40, 40, 40, 200],
        '累计收益': ['-39.7%', '-20.1%', '-2.2%', '8.9%', '49.1%', '88.8%']
    })
    
    return ic_df, stratified, pred, true, returns


def plot_ic_time_series(ic_df):
    """绘制 IC 时间序列"""
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=ic_df.index,
        y=ic_df['ic'],
        name='IC',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.2)'
    ))
    
    fig.add_trace(go.Scatter(
        x=ic_df.index,
        y=ic_df['rank_ic'],
        name='Rank IC',
        line=dict(color='#2ca02c', width=2)
    ))
    
    # 零线
    fig.add_shape(
        type="line",
        x0=ic_df.index[0],
        y0=0,
        x1=ic_df.index[-1],
        y1=0,
        line=dict(color="gray", dash="dash")
    )
    
    fig.update_layout(
        title='IC 时间序列',
        xaxis_title='日期',
        yaxis_title='IC 值',
        height=400,
        showlegend=True,
        hovermode='x unified'
    )
    
    return fig


def plot_ic_histogram(ic_df):
    """绘制 IC 直方图"""
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=ic_df['ic'],
        name='IC 分布',
        nbinsx=20,
        marker_color='#1f77b4',
        opacity=0.7
    ))
    
    # 均值线
    mean_ic = ic_df['ic'].mean()
    fig.add_shape(
        type="line",
        x0=mean_ic,
        y0=0,
        x1=mean_ic,
        y1=0.15,
        line=dict(color="red", width=2)
    )
    
    fig.update_layout(
        title='IC 分布直方图',
        xaxis_title='IC 值',
        yaxis_title='频数',
        height=400,
        showlegend=False
    )
    
    return fig


def plot_stratified_returns(stratified):
    """绘制分层回测收益"""
    import plotly.graph_objects as go
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=stratified['组别'],
        y=[float(r.replace('%', '')) for r in stratified['平均收益']],
        marker_color=['#d62728', '#ff7f0e', '#7f7f7f', '#2ca02c', '#1f77b4', '#9467bd'],
        text=stratified['平均收益'],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='分层回测平均收益',
        xaxis_title='组别 (按预测值排序)',
        yaxis_title='平均收益 (%)',
        height=400,
        showlegend=False
    )
    
    return fig


def main():
    """主函数"""
    st.header("IC 分析")
    
    # 生成数据
    ic_df, stratified, pred, true, returns = generate_ic_data()
    
    # 关键指标
    st.subheader("关键指标")
    
    col1, col2, col3, col4 = st.columns(4)
    
    mean_ic = ic_df['ic'].mean()
    std_ic = ic_df['ic'].std()
    icir = mean_ic / std_ic if std_ic > 0 else 0
    mean_rank_ic = ic_df['rank_ic'].mean()
    
    with col1:
        delta_ic = mean_ic - 0.05
        st.metric("平均 IC", f"{mean_ic:.4f}", f"{delta_ic:.4f}")
    
    with col2:
        delta_rank = mean_rank_ic - 0.05
        st.metric("平均 Rank IC", f"{mean_rank_ic:.4f}", f"{delta_rank:.4f}")
    
    with col3:
        delta_icir = icir - 0.5
        st.metric("ICIR", f"{icir:.2f}", f"{delta_icir:.2f}")
    
    with col4:
        accuracy = (pred * true > 0).mean()
        delta_acc = accuracy - 0.55
        st.metric("方向准确率", f"{accuracy:.1%}", f"{delta_acc:.1%}")
    
    st.divider()
    
    # 图表区
    col1, col2 = st.columns(2)
    
    with col1:
        fig_ic_ts = plot_ic_time_series(ic_df)
        st.plotly_chart(fig_ic_ts, use_container_width=True)
    
    with col2:
        fig_ic_hist = plot_ic_histogram(ic_df)
        st.plotly_chart(fig_ic_hist, use_container_width=True)
    
    # 分层回测
    st.subheader("分层回测")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_stratified = plot_stratified_returns(stratified)
        st.plotly_chart(fig_stratified, use_container_width=True)
    
    with col2:
        st.markdown("#### 分层回测数据")
        st.dataframe(stratified, hide_index=True, use_container_width=True)
    
    # 评估结论
    st.divider()
    st.subheader("评估结论")
    
    if icir > 0.5:
        st.success(f"**优秀**: ICIR = {icir:.2f} > 0.5，模型具有强预测能力")
    elif icir > 0.2:
        st.info(f"**可用**: ICIR = {icir:.2f} > 0.2，模型具有一定预测能力")
    else:
        st.warning(f"**需改进**: ICIR = {icir:.2f} < 0.2，模型预测能力较弱")
    
    # 详细说明
    with st.expander("IC 指标说明"):
        st.markdown("""
        **IC (Information Coefficient)**
        
        - IC: 预测值与真实值的相关系数，衡量预测能力
        - Rank IC: 排序后的相关系数，更稳健抗异常值
        - ICIR: IC 除以 IC 标准差，衡量稳定性
        
        **评估标准**
        
        | 指标 | 优秀 | 可用 | 需改进 |
        |------|------|------|--------|
        | IC | > 0.1 | 0.05-0.1 | < 0.05 |
        | ICIR | > 0.5 | 0.2-0.5 | < 0.2 |
        
        **分层回测**
        
        按预测值从小到大分为 5 组，理论上：
        - 第 5 组 (预测最强) 收益应最高
        - 第 1 组 (预测最弱) 收益应最低
        - 多空收益 = 第 5 组 - 第 1 组
        """)


if __name__ == "__main__":
    main()
