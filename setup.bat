@echo off
chcp 65001 > nul
REM ============================================================
REM  Local OCR (KR) - one-time install script
REM  - installs paddlepaddle-gpu (CUDA 12.x), pymupdf, gradio_pdf, ...
REM  - downloads NanumGothic.ttf if missing
REM ============================================================
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo.
echo === [1/4] Python version ===
python --version
if errorlevel 1 (
    echo [ERROR] Python not on PATH. Install Python 3.10+ from https://www.python.org/ and rerun.
    pause
    exit /b 1
)

echo.
echo === [2/4] paddlepaddle-gpu (CUDA 12.6) ===
python -c "import paddle, sys; sys.exit(0 if paddle.device.is_compiled_with_cuda() else 1)" 2>nul
if errorlevel 1 (
    echo paddlepaddle-gpu not installed or CPU-only -- installing GPU build ...
    python -m pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
    if errorlevel 1 (
        echo [ERROR] paddlepaddle-gpu install failed. Check NVIDIA driver / CUDA.
        pause
        exit /b 1
    )
) else (
    echo paddlepaddle-gpu already installed -- skipping
)

echo.
echo === [3/4] Other packages (requirements.txt) ===
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] requirements.txt install failed
    pause
    exit /b 1
)

echo.
echo === [4/4] Korean font ===
if exist "assets\fonts\NanumGothic.ttf" (
    echo NanumGothic.ttf present -- OK
) else (
    echo NanumGothic.ttf missing -- downloading ...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf' -OutFile 'assets\fonts\NanumGothic.ttf' -UseBasicParsing"
    if errorlevel 1 (
        echo [WARN] Font download failed. Place NanumGothic.ttf at assets\fonts\NanumGothic.ttf manually.
    )
)

echo.
echo === Setup complete ===
echo  - Verify GPU : python -c "import paddle; print(paddle.device.cuda.device_count())"
echo  - Run UI     : run.bat                       (double-click also OK)
echo  - CLI        : python -m pipeline.runner assets\before--xxx.pdf
echo.
echo --- Optional: MinerU layout-aware Markdown ---
echo  If you want the high-quality "mineru" markdown engine (preserves
echo  tables / headings / numbered lists), double-click setup_mineru.bat
echo  ONCE to fetch its models (~2-3 GB). It will request admin rights.
echo  Skip this if you only need the basic markdown / searchable PDF.
echo.
pause
