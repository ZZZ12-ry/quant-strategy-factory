@echo off
echo ======================================================================
echo ML/DL + 多因子 深化 - 安装脚本
echo ======================================================================
echo.

echo [Step 1/3] 安装 XGBoost...
pip install xgboost -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [FAIL] XGBoost 安装失败，尝试备用源...
    pip install xgboost
)

echo.
echo [Step 2/3] 安装 LightGBM...
pip install lightgbm -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [FAIL] LightGBM 安装失败，尝试备用源...
    pip install lightgbm
)

echo.
echo [Step 3/3] 安装 CatBoost...
pip install catboost -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [FAIL] CatBoost 安装失败，尝试备用源...
    pip install catboost
)

echo.
echo ======================================================================
echo 安装完成！验证安装...
echo ======================================================================

python -c "import xgboost; print(f'XGBoost 版本：{xgboost.__version__}')"
python -c "import lightgbm; print(f'LightGBM 版本：{lightgbm.__version__}')"
python -c "import catboost; print(f'CatBoost 版本：{catboost.__version__}')"

echo.
echo ======================================================================
echo 运行 ML 模型测试...
echo ======================================================================

cd /d %~dp0
python src\ml\advanced_models.py

pause
