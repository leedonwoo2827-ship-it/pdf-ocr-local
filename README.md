# 📄 Local OCR (KR) — `before--*.pdf` → `after--*.pdf`

스캔된 PDF를 **100% 로컬**에서 OCR 처리하여, 원본 이미지를 그대로 보존하면서
**검색·복사 가능한 텍스트 레이어**가 얹힌 PDF로 변환합니다.
한글+영문 혼합 문서(교재, 시험지 등)에 최적화.

- **엔진**: PaddleOCR PP-OCRv5 (한국어 멀티링구얼 모델) — bbox가 정확해 invisible text layer 삽입에 적합
- **부가**: Ollama `qwen2.5vl:7b` 비전 모델로 저신뢰 페이지/Markdown 보강(선택)
- **UI**: Gradio (좌-원본 / 우-결과 PDF 미리보기, 폴더 배치 처리 탭 포함)
- **출력**: ① 검색가능 PDF(`after--*.pdf`) + ② Markdown(`after--*.md`)

---

## 요구 사양

| 항목 | 권장 |
|---|---|
| OS | Windows 10/11 (64-bit) |
| Python | 3.10 이상 (테스트: 3.12.9) |
| GPU | NVIDIA, **VRAM 6GB 이상** (RTX 3060 / 4060 / 4070 등) |
| CUDA | 12.x 드라이버 설치 (NVIDIA 공식 최신 권장) |
| RAM | 16GB 이상 |
| 디스크 | 약 5GB (PaddleOCR 모델 캐시 포함) |

CPU-only 모드로도 동작 가능하나, 84p A4 기준 GPU에서 약 2–3분, CPU는 10–20분 정도로 차이가 큽니다.

---

## 빠른 시작

```bat
:: 1. 의존성 설치 (1회)
setup.bat

:: 2. 변환할 PDF를 _assets 폴더에 복사
::    파일명을 before--<원하는이름>.pdf 형태로 두면 결과는 after--<같은이름>.pdf 로 저장됩니다.
copy "C:\path\to\my-scan.pdf" "_assets\before--my-scan.pdf"

:: 3. Gradio UI 실행 → 브라우저로 http://127.0.0.1:7860
run.bat
```

또는 CLI 직접 실행:

```bat
python -m pipeline.runner _assets\before--my-scan.pdf              :: 단일 파일
python -m pipeline.runner _assets                                  :: 폴더 배치 (모든 before--*.pdf)
python -m pipeline.runner _assets\before--my-scan.pdf --quality    :: Quality 모드 (DPI 300, unwarp)
python -m pipeline.runner _assets\... --vlm --threshold 0.7         :: 저신뢰 페이지 VLM 보강
python -m pipeline.runner _assets\... --overwrite                  :: 기존 결과 덮어쓰기
```

---

## 모드

| 모드 | DPI | 옵션 | 속도(A4 84p) | 용도 |
|---|---|---|---|---|
| **Fast** (기본) | 200 | det+rec | ~2분 | 일반적인 깨끗한 스캔 |
| **Quality** | 300 | + cls + textline_orientation + doc_unwarping | ~5분 | 비스듬한 스캔, 글자 작거나 흐릿할 때 |
| **VLM 보강** | (모드 위에 추가) | Paddle 평균 신뢰도 < 임계값인 페이지에 한해 Ollama qwen2.5vl 호출 | +ms/페이지 | 손글씨/표 어려움/특수 레이아웃 |

VLM 보강은 **Ollama 데몬이 켜져 있고** `qwen2.5vl:7b` 모델이 `ollama list`에 보일 때만 활성화됩니다.

---

## 디렉토리 구조

```
.
├── app.py                       # Gradio UI 진입점 (run.bat 가 실행)
├── setup.bat                    # 의존성 1회 설치
├── run.bat                      # Gradio UI 실행
├── requirements.txt
├── pipeline/
│   ├── renderer.py              # pypdfium2: PDF 페이지 → PIL Image
│   ├── ocr_engine.py            # PaddleOCR PP-OCRv5 래퍼 (Fast/Quality)
│   ├── coord.py                 # 이미지 px ↔ PDF pt 좌표 변환
│   ├── pdf_writer.py            # PyMuPDF: invisible text layer 삽입
│   ├── vlm_engine.py            # Ollama qwen2.5vl:7b HTTP 호출 (옵션)
│   └── runner.py                # 파이프라인 + CLI 엔트리
├── assets/
│   └── fonts/NanumGothic.ttf    # 한글 임베딩용 폰트 (OFL)
└── _assets/                     # 입출력 폴더 (PDF는 gitignore)
    ├── before--*.pdf            # ← 입력 파일을 여기에
    ├── after--*.pdf             # → 검색가능 PDF
    └── after--*.md              # → Markdown
```

---

## 동작 원리

1. `pypdfium2` 로 각 페이지를 DPI 200/300 이미지로 렌더
2. `PaddleOCR PP-OCRv5 (lang="korean")` 가 4점 polygon bbox + 텍스트 + 신뢰도 반환
3. 픽셀 좌표를 PDF point 좌표로 변환 (`scale = 72/dpi`)
4. `PyMuPDF` 의 `page.insert_text(..., render_mode=3)` 로 **보이지 않는** 텍스트를 원본 위에 덮어 씀
5. 원본 이미지는 그대로 유지되고, 텍스트는 선택/복사/검색만 가능한 레이어로 존재
6. Markdown은 각 페이지 텍스트를 reading order로 정렬해 별도 저장 (VLM 활성 시 어려운 페이지는 VLM 출력으로 치환)

PaddleOCR 모델은 첫 실행 시 자동 다운로드되며 `C:\Users\<user>\.paddlex\official_models\` 에 캐시됩니다.

---

## 자주 묻는 질문

**Q. 결과 PDF에서 글자가 두 번 보입니다 (원본 위에 OCR 글자가 같이 출력)**
A. `render_mode=3` 이 적용되지 않은 경우입니다. PyMuPDF가 정상 설치돼 있는지(`python -c "import fitz; print(fitz.__version__)"`) 확인하세요.

**Q. GPU를 안 잡습니다 (`cuda devices: 0`)**
A. `nvidia-smi` 가 동작하는지 확인하고, `python -m pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/` 으로 재설치하세요. CUDA 12.x 드라이버가 필요합니다.

**Q. 영어/일본어 등 다른 언어도 가능한가요?**
A. `pipeline/ocr_engine.py` 의 `lang="korean"` 을 `english`, `japan`, `ch` 등으로 변경하면 됩니다 (PaddleOCR이 지원하는 80+ 언어).

**Q. macOS / Linux에서도 동작합니까?**
A. Python 코드 자체는 크로스플랫폼이지만 paddlepaddle 휠과 CUDA 인덱스가 OS별로 다릅니다. setup.bat 를 참고해 OS에 맞게 설치하세요.

---

## 라이선스

- 코드: MIT
- 동봉된 NanumGothic 폰트: SIL Open Font License (OFL)
- PaddleOCR / PyMuPDF / Gradio 등 의존성은 각 라이브러리의 라이선스를 따릅니다 (PyMuPDF는 AGPL이므로 재배포 시 검토 필요)
- `_assets/` 폴더에 들어가는 PDF는 사용자가 권리를 가진 자료여야 합니다.
