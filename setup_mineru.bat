@echo off
chcp 65001 > nul
REM ============================================================
REM  MinerU first-run model download (Windows only)
REM
REM  Self-elevates to admin (UAC popup) so the Hugging Face Hub cache
REM  can create symlinks. Downloads ~2-3 GB on first run; later
REM  invocations skip this script entirely.
REM
REM  Double-click this file -> click "Yes" on the UAC dialog -> wait
REM  5-15 minutes -> done.
REM ============================================================

REM --- check admin privileges; self-elevate if missing ---
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo Requesting administrator privileges for MinerU model cache symlinks ...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

REM --- admin context: jump to script directory ---
cd /d "%~dp0"

echo.
echo === MinerU first-run model download ===
echo This downloads about 2-3 GB from Hugging Face Hub.
echo Expected time: 5-15 minutes (depending on bandwidth).
echo Models will be cached at: %USERPROFILE%\.cache\huggingface\
echo.

REM --- sanity: mineru CLI present? ---
where mineru >nul 2>&1
if errorlevel 1 (
    echo [ERROR] mineru CLI not found. Run setup.bat first.
    pause
    exit /b 1
)

REM --- generate a tiny 1-page PDF to trigger MinerU end-to-end ---
echo Creating temporary 1-page PDF to trigger model downloads ...
python -c "import fitz; d=fitz.open(); p=d.new_page(); p.insert_text((72,72),'init'); d.save(r'_tmp_mineru_init.pdf'); d.close()"
if errorlevel 1 (
    echo [ERROR] Could not create temp PDF. Is PyMuPDF installed? Run setup.bat first.
    pause
    exit /b 1
)

REM --- run mineru on the dummy PDF; this is what fetches the models ---
echo Running MinerU once to populate the model cache ...
mineru -p _tmp_mineru_init.pdf -o _tmp_mineru_out -m auto -b pipeline -l korean -s 0 -e 0
set "MINERU_RC=%errorlevel%"

REM --- cleanup temp files ---
del _tmp_mineru_init.pdf 2>nul
if exist _tmp_mineru_out rmdir /s /q _tmp_mineru_out

echo.
if "%MINERU_RC%"=="0" (
    echo === MinerU is ready ===
    echo You can now close this window and run run.bat as normal.
    echo From now on, MinerU works without admin privileges.
) else (
    echo [WARN] MinerU returned code %MINERU_RC%. Check the messages above.
    echo Possible causes: no internet, antivirus blocking, or disk full.
)
echo.
pause
