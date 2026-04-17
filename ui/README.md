# 量化策略工厂 - Web UI

基于 Streamlit 构建的可视化界面，无需前端知识即可使用。

---

## 快速开始

### 方法 1: 一键启动 (推荐)

```bash
run_ui.bat
```

### 方法 2: 手动启动

```bash
# 1. 安装依赖
pip install streamlit plotly

# 2. 启动 UI
cd ui
streamlit run app.py
```

启动后会自动打开浏览器，访问 http://localhost:8501

---

## 功能模块

### 主页面 (app.py)

**策略回测**
- 参数配置（策略类型、周期、品种）
- 一键运行回测
- 结果可视化（收益曲线、回撤、月度收益）
- 交易记录查看

**特征工程**
- 特征选择（7 种方法）
- 相关性热力图
- 特征重要性排名

**模型训练**
- 模型选择（XGBoost/LightGBM/CatBoost）
- 参数配置
- 训练进度展示
- 模型表现指标

**IC 分析**
- IC 时间序列
- IC 分布直方图
- 分层回测结果
- 评估结论

---

## 页面导航

```
量化策略工厂 (主页)
├── 策略回测
├── 特征工程 (pages/02_feature_engineering.py)
└── IC 分析 (pages/03_ic_analysis.py)
```

---

## 截图预览

### 策略回测页面
- 累计收益曲线
- 回撤曲线
- 月度收益热力图
- 关键指标卡片

### 特征工程页面
- 特征相关性热力图
- 特征重要性排序
- 特征统计信息

### IC 分析页面
- IC 时间序列
- IC 分布直方图
- 分层回测柱状图

---

## 自定义配置

### 修改主题

编辑 `ui/app.py`，在 `st.set_page_config` 后添加：

```python
st.markdown("""
<style>
    .main-header {
        color: #1f77b4;  /* 修改主色调 */
    }
</style>
""", unsafe_allow_html=True)
```

### 添加新页面

在 `ui/pages/` 目录下创建文件：

```python
# ui/pages/04_new_feature.py
import streamlit as st

def main():
    st.header("新功能")
    # 你的代码

if __name__ == "__main__":
    main()
```

页面会自动出现在侧边栏导航中。

---

## 部署到服务器

### 本地网络访问

```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

### 添加密码保护

创建 `ui/.streamlit/secrets.toml`:

```toml
[password]
salt = "random_salt_here"
```

---

## 常见问题

### Q1: 启动后浏览器未自动打开？

手动访问：http://localhost:8501

### Q2: 中文显示乱码？

确保文件编码为 UTF-8。

### Q3: 图表不显示？

检查是否安装了 plotly：

```bash
pip install plotly
```

---

## 技术栈

- **前端**: Streamlit (Python)
- **图表**: Plotly
- **数据处理**: Pandas, NumPy
- **后端集成**: 直接调用项目核心模块

---

## 开发路线图

### 已完成 (v1.0)
- [x] 主页面框架
- [x] 策略回测可视化
- [x] 特征工程页面
- [x] IC 分析页面

### 计划中 (v1.1)
- [ ] 实时回测进度条
- [ ] 策略对比功能
- [ ] 数据上传界面
- [ ] 模拟盘监控仪表盘

---

*最后更新：2026-04-17*  
*版本：v1.0*
