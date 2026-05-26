# 📄 Local OCR (KR)

스캔 PDF → **검색가능 PDF + Markdown**. 한글+영문 혼합 문서에 최적화, 100% 로컬.

엔진: **PaddleOCR PP-OCRv5 (한국어)** · UI: **Gradio** · 마크다운 강화: **MinerU** (선택) · VLM 보강: **Ollama qwen2.5vl:7b** (선택)
지원: **Windows · Linux · macOS** (NVIDIA GPU 권장, CPU 도 동작)

## 빠른 시작 (탐색기에서 더블클릭만)

### Windows

1. **`setup.bat`** 더블클릭 — 기본 의존성(PaddlePaddle, PyMuPDF, MinerU 패키지, 한글 폰트) 설치
2. *(선택)* **`setup_mineru.bat`** 더블클릭 — 레이아웃 인식 마크다운(MinerU) 을 쓰려면 한 번만 실행
   - UAC 팝업이 뜨면 **"예"** 클릭 → 자동으로 관리자 권한으로 다시 실행되어 모델 ~2–3GB 다운로드
   - 5–15분 소요. 다 끝나면 일반 권한으로 동작
3. **`run.bat`** 더블클릭 — Gradio UI 가 뜨고 약 6초 뒤 브라우저가 자동으로 <http://127.0.0.1:7860> 열림

### Linux / macOS

```bash
chmod +x setup.sh setup_mineru.sh run.sh
./setup.sh
./setup_mineru.sh        # (선택) MinerU 마크다운 엔진 모델 받기
./run.sh
```

## 사용 흐름

변환할 PDF 를 `_assets\before--<이름>.pdf` 로 두면 결과가 `_assets\after--<이름>.pdf` + `.md` 로 저장됩니다.

UI 사이드바에서:
- **OCR 모드**: Fast (DPI 200, ~2분/84p) / Quality (DPI 300, ~5분)
- **Markdown 엔진**: paddle (빠른 라인 텍스트) / mineru (표·제목·번호 구조 보존, `setup_mineru.bat` 실행한 경우 자동 활성화)
- **VLM 보강**: Ollama 가 켜져 있고 신뢰도가 낮은 페이지가 있을 때

CLI:
```bash
python -m pipeline.runner _assets/before--myscan.pdf                            # 기본
python -m pipeline.runner _assets                                               # 폴더 일괄
python -m pipeline.runner _assets/... --quality --md-engine mineru              # 고품질 + 레이아웃
```

## 폴더 구조

```
.
├── _assets/    📦  내 PDF 두는 곳 (.gitignore 됨 → GitHub 에 절대 안 올라감)
│               입력 before--*.pdf  /  결과 after--*.pdf  +  after--*.md
├── assets/    🔤  앱 동봉 리소스 (git 추적). NanumGothic.ttf (한글 폰트, OFL)
├── pipeline/  🧠  OCR 파이프라인 (renderer / ocr_engine / mineru_engine / pdf_writer ...)
├── docs/      📖  설치·사용·아키텍처 상세
├── app.py     🖥  Gradio UI 진입점
├── setup.bat / setup.sh             기본 설치
├── setup_mineru.bat / setup_mineru.sh   (선택) MinerU 모델 받기 — Windows 는 UAC 자동
├── run.bat   / run.sh               Gradio 실행
└── requirements.txt, .gitignore, .gitattributes, README.md
```

**핵심**: `_assets/` 안에 어떤 PDF/MD 를 넣어도 GitHub 에 올라가지 않습니다. 저작권 자료도 안심하고 거기 두세요. 오직 `_assets/.gitkeep` 만 git 에 올라가 빈 폴더 구조를 유지합니다.

Gradio UI 에서 다운로드한 결과 PDF 도 `_assets/` 로 옮겨두면 다음 실행 시 [폴더 배치] 탭에 자동 표시됩니다.

## 더 보기

- 📥 [설치 / 트러블슈팅](docs/install.md)
- 📖 [사용법 / 모드 / FAQ](docs/usage.md)
- 🧩 [아키텍처 / 디렉토리 / 좌표 변환](docs/architecture.md)

## 라이선스

코드 MIT · NanumGothic OFL · PyMuPDF 는 AGPL (재배포 시 검토) · MinerU AGPL · PaddleOCR/Gradio Apache-2.0.
입력 PDF 는 사용자 권리 자료여야 합니다.
