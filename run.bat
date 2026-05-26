@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo Starting Gradio at http://127.0.0.1:7860  (Ctrl+C to stop)
echo Your browser will open automatically in ~6 seconds.
echo.
REM Open the browser after a short delay so Gradio has time to bind to 7860
start "" cmd /c "timeout /t 6 /nobreak >nul && start http://127.0.0.1:7860"
python app.py
pause
