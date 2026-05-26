# 📄 Local OCR (KR)

스캔 PDF → **검색가능 PDF + Markdown**. 한글+영문 혼합 문서에 최적화, 100% 로컬.

엔진: **PaddleOCR PP-OCRv5 (한국어)** · 마크다운 강화: **MinerU** (선택) · VLM 보강: **Ollama qwen2.5vl:7b** (선택)
UI: **Gradio** · 지원: **Windows · Linux · macOS** (NVIDIA GPU 권장, CPU 도 동작)

## 빠른 시작 (탐색기에서 더블클릭만)

### Windows

1. **`setup.bat`** 더블클릭 — 기본 의존성(PaddlePaddle, PyMuPDF, MinerU 패키지, 한글 폰트) 설치
2. *(선택)* **`setup_mineru.bat`** 더블클릭 — 레이아웃 인식 마크다운(MinerU) 쓰려면 한 번만 실행
   - UAC 팝업이 뜨면 **"예"** 클릭 → 자동 관리자 권한 elevation → 모델 ~2–3GB 다운로드 (5–15분)
   - 끝나면 일반 권한으로 동작
3. **`run.bat`** 더블클릭 — Gradio UI 가 뜨고 약 6초 뒤 브라우저가 자동으로 <http://127.0.0.1:7860> 열림

### Linux / macOS

```bash
chmod +x setup.sh setup_mineru.sh run.sh
./setup.sh
./setup_mineru.sh        # (선택) MinerU 모델 받기
./run.sh
```

## 사용 흐름

1. 변환할 PDF 를 UI 에 드래그&드롭 (또는 `assets/` 폴더에 직접 복사)
2. **변환 시작** 클릭
3. **결과는 `assets/` 폴더에 자동으로 저장**됩니다 — 다운로드 버튼 누를 필요 없이 탐색기에서 바로 확인:
   - `assets/after--<이름>.pdf` (검색가능 PDF)
   - `assets/after--<이름>.md` (Markdown)

옵션:
- **OCR 모드**: Fast (DPI 200) / Quality (DPI 300 + unwarp)
- **Markdown 엔진**: mineru (표·제목·번호 구조 보존, 권장) / paddle (라인 텍스트, 빠름)
- **VLM 보강**: paddle 엔진일 때만. 어려운 페이지에 한해 Ollama qwen2.5vl:7b 가 재처리
- **덮어쓰기**: 기본 ON. 같은 이름 결과를 새로 만듦

CLI:
```bash
python -m pipeline.runner assets/before--myscan.pdf                            # 기본
python -m pipeline.runner assets                                               # 폴더 일괄
python -m pipeline.runner assets/... --quality --md-engine mineru              # 고품질 + 레이아웃
```

## 폴더 구조

```
.
├── assets/    📦  입출력 + 동봉 폰트
│               • before--*.pdf / after--*.pdf / .md 가 모두 여기 (사용자 데이터는 .gitignore)
│               • fonts/NanumGothic.ttf (한글 폰트, OFL, git 추적)
├── pipeline/  🧠  OCR 파이프라인 (renderer / ocr_engine / mineru_engine / pdf_writer ...)
├── docs/      📖  설치·사용·아키텍처 상세
├── app.py     🖥  Gradio UI 진입점
├── setup.bat / setup.sh             기본 설치
├── setup_mineru.bat / setup_mineru.sh   (선택) MinerU 모델 받기 — Windows 는 UAC 자동
├── run.bat   / run.sh               Gradio 실행
└── requirements.txt, .gitignore, .gitattributes, README.md
```

`assets/` 안의 PDF/MD/이미지는 모두 `.gitignore` 로 차단됩니다. 저작권 자료도 안심하고 거기 두세요. 오직 `assets/fonts/` 만 git 추적됩니다.

## 더 보기

- 📥 [설치 / 트러블슈팅](docs/install.md)
- 📖 [사용법 / 모드 / FAQ](docs/usage.md)
- 🧩 [아키텍처 / 디렉토리 / 좌표 변환](docs/architecture.md)

## 라이선스

코드 MIT · NanumGothic OFL · PyMuPDF 는 AGPL (재배포 시 검토) · MinerU AGPL · PaddleOCR/Gradio Apache-2.0.
입력 PDF 는 사용자 권리 자료여야 합니다.
