#!/usr/bin/env bash
# Local OCR (KR) — Linux / macOS 1회 설치 스크립트
# - OS / GPU 자동 감지
# - paddlepaddle / paddlepaddle-gpu, pymupdf, gradio 등 설치
# - NanumGothic.ttf 없으면 다운로드
set -e
cd "$(dirname "$0")"

# Pick the Python interpreter
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[ERROR] Python 3 not found. Install Python 3.10+ first." >&2
  exit 1
fi

echo "=== [1/4] Python ==="
$PY --version

OS="$(uname -s)"
echo
echo "=== [2/4] PaddlePaddle (OS=$OS) ==="

# Skip if already installed AND (on Linux with NVIDIA) GPU build present
HAS_PADDLE=$($PY -c "import paddle" 2>/dev/null && echo yes || echo no)
HAS_NVIDIA=no
if command -v nvidia-smi >/dev/null 2>&1; then
  if nvidia-smi >/dev/null 2>&1; then HAS_NVIDIA=yes; fi
fi

if [ "$HAS_PADDLE" = "yes" ]; then
  echo "paddle already installed — skipping"
else
  case "$OS" in
    Linux*)
      if [ "$HAS_NVIDIA" = "yes" ]; then
        echo "NVIDIA GPU detected -> paddlepaddle-gpu (CUDA 12.6 wheel)"
        $PY -m pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
      else
        echo "No NVIDIA GPU -> paddlepaddle (CPU build)"
        $PY -m pip install paddlepaddle==3.0.0
      fi
      ;;
    Darwin*)
      echo "macOS detected -> paddlepaddle CPU build (Apple Silicon supported)"
      $PY -m pip install paddlepaddle==3.0.0
      ;;
    *)
      echo "[WARN] Unknown OS ($OS) -> trying CPU paddlepaddle"
      $PY -m pip install paddlepaddle==3.0.0
      ;;
  esac
fi

echo
echo "=== [3/4] Other Python packages (requirements.txt) ==="
$PY -m pip install -r requirements.txt

echo
echo "=== [4/4] Korean font (NanumGothic) ==="
if [ -f "assets/fonts/NanumGothic.ttf" ]; then
  echo "NanumGothic.ttf present — OK"
else
  echo "Downloading NanumGothic ..."
  mkdir -p assets/fonts
  if command -v curl >/dev/null 2>&1; then
    curl -L -o assets/fonts/NanumGothic.ttf \
      https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf
  elif command -v wget >/dev/null 2>&1; then
    wget -O assets/fonts/NanumGothic.ttf \
      https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf
  else
    echo "[WARN] curl/wget 없음 — assets/fonts/NanumGothic.ttf 에 수동 배치하세요." >&2
  fi
fi

echo
echo "=== Setup complete ==="
echo "  Verify GPU :  $PY -c 'import paddle; print(paddle.device.cuda.device_count())'"
echo "  Run UI     :  ./run.sh"
echo "  CLI        :  $PY -m pipeline.runner assets/before--xxx.pdf"
echo
echo "--- Optional: MinerU layout-aware Markdown ---"
echo "  For the high-quality 'mineru' markdown engine (tables / headings /"
echo "  numbered lists preserved), run ./setup_mineru.sh ONCE to fetch its"
echo "  models (~2-3 GB). Skip if you only need basic markdown."
