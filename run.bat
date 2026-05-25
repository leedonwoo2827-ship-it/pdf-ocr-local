@echo off
REM Local OCR — Gradio UI 실행 (http://127.0.0.1:7860)
cd /d "%~dp0"
echo Gradio 서버를 시작합니다. 브라우저에서 http://127.0.0.1:7860 을 열어주세요.
echo (종료: Ctrl+C)
echo.
python app.py
pause
