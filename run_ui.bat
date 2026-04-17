@echo off
echo 正在安装 UI 依赖...
pip install streamlit plotly -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo 安装完成！正在启动 UI...
cd ui
streamlit run app.py
