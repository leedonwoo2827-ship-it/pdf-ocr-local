# 설치 가이드

지원 OS: **Windows · Linux · macOS** / Python **3.10 이상** / 권장 GPU: **NVIDIA VRAM 6GB+**

자동 스크립트가 OS와 GPU 유무를 감지해 알맞은 PaddlePaddle 빌드를 설치합니다.

## Windows (탐색기 더블클릭)

1. **`setup.bat`** 더블클릭 — 기본 의존성 설치
2. *(선택)* **`setup_mineru.bat`** 더블클릭 — MinerU 모델 받기. **UAC 팝업이 뜨면 "예"**. 자동 관리자 권한 elevation 후 모델 ~2–3GB 다운로드 (5–15분). 끝나면 일반 권한으로 동작.
3. **`run.bat`** 더블클릭 — Gradio 가 뜨고 약 6초 후 브라우저가 자동으로 <http://127.0.0.1:7860> 열림

## Linux / macOS
```bash
chmod +x setup.sh setup_mineru.sh run.sh    :: clone 직후 1회
./setup.sh
./setup_mineru.sh    # (선택) MinerU 마크다운 엔진 모델 받기
./run.sh
```

> Linux 에서 NVIDIA GPU 가 있으면 `paddlepaddle-gpu` (CUDA 12.6 wheel)가, 없으면 CPU 빌드가 설치됩니다. macOS 는 PaddlePaddle GPU 빌드가 없어 CPU 만 사용합니다 (Apple Silicon arm64 휠 지원). Linux/macOS 는 Windows 의 symlink 권한 이슈가 없어 `setup_mineru.sh` 는 sudo 가 필요 없습니다.

## 수동 설치 (스크립트가 실패할 때)

```bash
# 1. (선택) 가상환경
python3 -m venv .venv && source .venv/bin/activate     # Linux/macOS
python -m venv .venv && .venv\Scripts\activate         # Windows

# 2. PaddlePaddle
#   Linux + NVIDIA CUDA 12.x:
pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
#   Windows + NVIDIA CUDA 12.x: 위와 동일
#   CPU-only (macOS, GPU 없는 Linux, GPU 없는 Windows):
pip install paddlepaddle==3.0.0

# 3. 나머지
pip install -r requirements.txt

# 4. 한글 폰트
curl -L -o assets/fonts/NanumGothic.ttf \
  https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf
```

## 설치 확인

```bash
python -c "import paddle; print('cuda devices:', paddle.device.cuda.device_count())"
python -c "import fitz; print('pymupdf', fitz.__version__)"
python -c "from gradio_pdf import PDF; import gradio; print('gradio', gradio.__version__)"
```

`cuda devices: 1` 이상이 나오면 GPU 인식 OK. `0` 이면 CPU 모드로 작동합니다 (10–20× 느림).

## (선택) VLM 보강 — Ollama 설치

`qwen2.5vl:7b` 비전 모델로 저신뢰 페이지를 재처리하고 싶을 때만 필요합니다.

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windows: https://ollama.com/download 에서 인스톨러 다운로드

# 공통: 모델 받기
ollama pull qwen2.5vl:7b
ollama serve     # (Linux/macOS, 데몬이 자동 실행되지 않을 경우)
```

## 자주 막히는 곳

| 증상 | 원인 / 해결 |
|---|---|
| `ModuleNotFoundError: paddle` | paddlepaddle 자체가 설치되지 않음. setup 스크립트가 실패한 경우 위 "수동 설치" 참고 |
| `cuda devices: 0` (GPU 있는데) | NVIDIA 드라이버 또는 CUDA 12.x 미설치. `nvidia-smi` 동작 확인 |
| 결과 PDF에서 글자가 두 번 보임 | PyMuPDF 미설치 / 이전 출력 잔존. `pip install pymupdf` 후 `--overwrite` 로 재생성 |
| `paddlepaddle-gpu` Linux 휠 못 찾음 | `https://www.paddlepaddle.org.cn/packages/stable/cu126/` 인덱스를 일시적으로 못 받을 수 있음 — 잠시 후 재시도 |
| macOS 인식률 낮음 | CPU 모드 + DPI 200 기본값 한계. `--quality` 로 DPI 300 사용 권장 |
