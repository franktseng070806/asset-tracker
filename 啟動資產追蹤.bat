@echo off
cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.10+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b
)

python -m pip install --upgrade pip -q
python -m pip install streamlit plotly pandas yfinance requests -q

start http://localhost:8501
python -m streamlit run app.py --server.headless true

pause