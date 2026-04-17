"""
特征工程页面 - 特征选择与分析
"""
import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def generate_feature_data():
    """生成特征数据"""
    np.random.seed(42)
    n_samples = 500
    n_features = 30
    
    feature_names = [f'feature_{i}' for i in range(n_features)]
    X = pd.DataFrame(np.random.randn(n_samples, n_features), columns=feature_names)
    
    # 添加冗余特征
    for i in range(5):
        X[f'redundant_{i}'] = X[f'feature_{i}'] + np.random.randn(n_samples) * 0.1
    
    # 生成目标
    y = (X['feature_0'] * 2 + X['feature_1'] * 1.5 + np.random.randn(n_samples) * 0.5 > 0).astype(int)
    
    return X, y, feature_names


def plot_correlation_heatmap(X):
    """绘制相关性热力图"""
    import plotly.graph_objects as go
    
    corr_matrix = X.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu',
        zmid=0
    ))
    
    fig.update_layout(
        title='特征相关性矩阵',
        height=600,
        xaxis=dict(tickangle=-45),
        yaxis=dict(tickangle=0)
    )
    
    return fig


def plot_feature_importance(importance_df):
    """绘制特征重要性"""
    import plotly.graph_objects as go
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=importance_df['importance'],
        y=importance_df['feature'],
        orientation='h',
        marker_color='#1f77b4'
    ))
    
    fig.update_layout(
        title='特征重要性排名',
        xaxis_title='重要性',
        yaxis_title='特征',
        height=500
    )
    
    return fig


def main():
    """主函数"""
    st.header("特征工程")
    
    # 生成数据
    X, y, feature_names = generate_feature_data()
    
    # 参数配置
    with st.expander("特征选择参数", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            method = st.selectbox(
                "选择方法",
                ["方差过滤", "相关性过滤", "互信息过滤", "树模型重要性", "顺序选择 (推荐)"]
            )
        
        with col2:
            threshold = st.slider("阈值", 0.0, 1.0, 0.5, 0.05)
        
        with col3:
            max_features = st.slider("最大特征数", 5, 50, 20)
    
    # 运行按钮
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"当前特征数：**{len(feature_names)}**")
    with col2:
        run_button = st.button("运行特征选择", type="primary", use_container_width=True)
    
    if run_button:
        with st.spinner("正在运行特征选择..."):
            # 调用特征选择器
            from src.ml.auto_feature_selector import AutoFeatureSelector
            
            selector = AutoFeatureSelector()
            
            if method == "方差过滤":
                selected = selector.filter_variance(X, threshold=threshold)
            elif method == "相关性过滤":
                selected = selector.filter_correlation(X, threshold=threshold)
            elif method == "树模型重要性":
                selected = selector.embedded_tree_importance(X, y, threshold=threshold)
            else:
                selected = selector.sequential_selection(
                    X, y,
                    method='variance+correlation+tree',
                    variance_threshold=0.5,
                    correlation_threshold=threshold,
                    tree_threshold=0.01
                )
            
            # 显示结果
            st.success(f"特征选择完成！保留 **{len(selected)}** 个特征")
            
            # 特征列表
            st.subheader("保留的特征")
            st.write(", ".join(selected))
            
            # 相关性热力图
            st.subheader("相关性热力图")
            fig_corr = plot_correlation_heatmap(X[selected])
            st.plotly_chart(fig_corr, use_container_width=True)
            
            # 特征重要性
            if len(selected) > 0:
                st.subheader("特征重要性")
                ic_df = selector.calc_ic(X[selected], y)
                
                fig_imp = plot_feature_importance(ic_df.head(15))
                st.plotly_chart(fig_imp, use_container_width=True)
    
    # 特征统计
    st.subheader("特征统计信息")
    st.dataframe(X.describe(), use_container_width=True)


if __name__ == "__main__":
    main()
