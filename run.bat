@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo Starting Gradio at http://127.0.0.1:7860  (Ctrl+C to stop)
echo.
python app.py
pause
