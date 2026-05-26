# 아키텍처

## 파이프라인

```
PDF
  │  ① pypdfium2.PdfDocument(...).render(scale=dpi/72)
  ▼
PIL Image (DPI 200 또는 300)
  │  ② PaddleOCR(lang="korean", ocr_version="PP-OCRv5").predict(np_image)
  ▼
rec_texts[], rec_polys[], rec_scores[]
  │  ③ 4점 polygon (이미지 px) → PDF point 좌표 변환  (scale = 72 / dpi)
  ▼
TextLine[] (x_pt, y_pt, width_pt, height_pt, text, score, fontsize)
  │  ④ fitz.Page.insert_text(point, text, fontname="nanum",
  │                          fontfile="NanumGothic.ttf",
  │                          fontsize=line.fontsize,
  │                          render_mode=3)  ← invisible
  ▼
원본 페이지 + 보이지 않는 텍스트 레이어
  │  ⑤ doc.save(out, garbage=4, deflate=True)
  ▼
검색가능 PDF  (+ 옵션: Markdown / VLM 보강)
```

핵심: `render_mode=3` 은 PDF 텍스트 렌더링 모드 중 "신경 그리기"에 해당. 글자가 화면에 그려지지 않지만 텍스트 추출/선택/검색은 정상 동작합니다.

## 디렉토리

```
.
├── app.py                       # Gradio UI 진입점
├── setup.{bat,sh}               # OS별 1회 설치
├── run.{bat,sh}                 # Gradio 실행
├── requirements.txt
├── docs/                        # 본 문서
│   ├── install.md
│   ├── usage.md
│   └── architecture.md
├── pipeline/
│   ├── renderer.py              # pypdfium2 PDF → PIL Image
│   ├── ocr_engine.py            # PaddleOCR Fast/Quality 모드 싱글톤
│   ├── coord.py                 # 픽셀 → PDF point 변환
│   ├── pdf_writer.py            # PyMuPDF invisible text 레이어 삽입
│   ├── vlm_engine.py            # Ollama qwen2.5vl HTTP 호출
│   └── runner.py                # 오케스트레이션 + CLI
├── assets/fonts/NanumGothic.ttf # 한글 임베딩 폰트 (OFL)
└── _assets/                     # 입출력 (PDF는 gitignore)
```

## 엔진 선택 근거

| 엔진 | 한글 | bbox 정확도 | 검색가능 PDF 적합 | 위치 |
|---|---|---|---|---|
| **PaddleOCR PP-OCRv5** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ 최적 | **1차 엔진** |
| MinerU 3.x | ⭐⭐⭐⭐ | ⭐⭐ (md 위주) | ❌ | 사용 안 함 |
| Qwen2.5-VL 7B | ⭐⭐⭐⭐ | ❌ (VLM, bbox 없음) | ❌ | **보강 트랙** (저신뢰 페이지 / Markdown) |
| Surya OCR | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭕ | 향후 폴백 후보 |
| GOT-OCR2.0 | ⭐⭐ | ❌ | ❌ | 한글 약함 |

검색가능 PDF의 핵심은 **정확한 bbox**입니다. VLM은 텍스트는 잘 읽지만 bbox를 주지 않거나 부정확하므로, 텍스트 레이어 삽입엔 PaddleOCR이 적합하고 VLM은 "내용 자체"를 더 잘 읽어야 할 때 보조 트랙으로 활용합니다.

## VRAM 운용 (8GB 기준)

- PP-OCRv5 server full set (det+rec+cls+textline_orient+unwarp+layout): 약 3–4GB
- OCR 실행 동안에는 다른 GPU 모델(Ollama 모델 포함) 로드 금지 — 8GB 초과 위험
- 페이지는 GPU 1개에서 **순차 처리** (병렬은 OOM만 유발하고 가속 효과 미미)
- VLM 보강은 OCR 1차 처리가 끝난 뒤 별도 단계로 실행 — Ollama는 자동으로 GPU에 모델 로드

## 좌표 변환 주의사항

```
img (px, top-left origin)        PDF (point, fitz의 page 좌표계: 마찬가지로 top-left)
   ┌─────────┐                    ┌─────────┐
   │ A      B│   (x, y) ────►     │ A      B│   (x_pt, y_pt)
   │         │   scale = 72/dpi   │         │
   │ D      C│                    │ D      C│
   └─────────┘                    └─────────┘
   width_px x height_px            width_pt x height_pt
```

PyMuPDF의 page 좌표는 PDF 표준의 좌하단 원점이 아니라 **좌상단 원점**으로 노출되므로 별도 y-flip이 필요 없습니다. 단, `page.rotation` 이 0이 아닌 페이지는 보정이 필요 (현재 구현은 회전 0 가정).

`fitz.Page.insert_text` 는 baseline 위치를 기준으로 텍스트를 그리므로, bbox 상단(y_pt)이 아니라 `y_pt + height_pt * 0.85` 정도를 baseline으로 넘깁니다.

## 모델 캐시 위치

PaddleOCR이 첫 실행 시 자동 다운로드:
- Windows: `C:\Users\<user>\.paddlex\official_models\`
- Linux: `~/.paddlex/official_models/`
- macOS: `~/.paddlex/official_models/`

총 약 1GB. 한 번 받으면 오프라인 작동.

## 라이선스 주의

- **PyMuPDF는 AGPL** — 사내/개인 사용 OK, 서비스 형태 재배포 시 검토 필요
- PaddleOCR Apache-2.0
- Gradio Apache-2.0
- NanumGothic OFL (재배포 가능)
- 입력 PDF는 사용자 권리 자료여야 함 (저작권 있는 교재 스캔본 주의)
