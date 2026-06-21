@echo off
cd /d "%~dp0"

echo ================================================
echo  同步程式碼到 GitHub / Streamlit Cloud
echo ================================================
echo.

git add .

set /p msg="請輸入這次修改的說明（直接按 Enter 使用預設文字）: "
if "%msg%"=="" set msg=update

git commit -m "%msg%"
git push

echo.
echo ================================================
echo  同步完成！請等待 1-2 分鐘讓雲端重新部署
echo ================================================
pause