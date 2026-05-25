@echo off
REM ============================================================
REM  Local OCR (KR) — 1회 설치 스크립트
REM  - paddlepaddle-gpu (CUDA 12.x), pymupdf, gradio_pdf 등 설치
REM  - NanumGothic.ttf 확인 (없으면 안내)
REM ============================================================
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo.
echo === [1/4] Python 버전 확인 ===
python --version
if errorlevel 1 (
    echo [에러] Python이 PATH에 없습니다. https://www.python.org/ 에서 3.10 이상 설치 후 다시 실행하세요.
    pause
    exit /b 1
)

echo.
echo === [2/4] paddlepaddle-gpu (CUDA 12.6) 설치 ===
python -c "import paddle; import sys; sys.exit(0 if paddle.device.is_compiled_with_cuda() else 1)" 2>nul
if errorlevel 1 (
    echo paddlepaddle-gpu 미설치 또는 CPU-only — GPU 빌드를 설치합니다 ...
    python -m pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
    if errorlevel 1 (
        echo [에러] paddlepaddle-gpu 설치 실패. NVIDIA 드라이버/CUDA 환경을 확인하세요.
        pause
        exit /b 1
    )
) else (
    echo paddlepaddle-gpu (CUDA) 이미 설치됨 — 건너뜀
)

echo.
echo === [3/4] 나머지 패키지 설치 (requirements.txt) ===
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [에러] requirements.txt 설치 실패
    pause
    exit /b 1
)

echo.
echo === [4/4] 한글 폰트 확인 ===
if exist "assets\fonts\NanumGothic.ttf" (
    echo NanumGothic.ttf 존재 — OK
) else (
    echo NanumGothic.ttf 가 없습니다. 다운로드를 시도합니다 ...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf' -OutFile 'assets\fonts\NanumGothic.ttf' -UseBasicParsing"
    if errorlevel 1 (
        echo [경고] 폰트 다운로드 실패. 수동으로 assets\fonts\NanumGothic.ttf 에 배치해주세요.
    )
)

echo.
echo === 설치 완료 ===
echo  - GPU 인식 확인: python -c "import paddle; print(paddle.device.cuda.device_count())"
echo  - Gradio 실행:    run.bat
echo  - CLI 실행:       python -m pipeline.runner _assets\before--xxx.pdf
echo.
pause
