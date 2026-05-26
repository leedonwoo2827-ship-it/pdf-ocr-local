# 📄 Local OCR (KR)

스캔 PDF → **검색가능 PDF + Markdown**. 한글+영문 혼합 문서에 최적화, 100% 로컬.

엔진: **PaddleOCR PP-OCRv5 (한국어)** · UI: **Gradio** · 선택: **Ollama qwen2.5vl:7b** 보강
지원: **Windows · Linux · macOS** (NVIDIA GPU 권장, CPU도 동작)

## 빠른 시작

```bash
# Windows
setup.bat
run.bat

# Linux / macOS
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

브라우저: <http://127.0.0.1:7860>

변환할 PDF를 `_assets/before--<이름>.pdf` 로 두면 결과가 `_assets/after--<이름>.pdf` + `.md` 로 저장됩니다.

CLI:
```bash
python -m pipeline.runner _assets/before--myscan.pdf
python -m pipeline.runner _assets                       # 폴더 일괄
python -m pipeline.runner _assets/... --quality --vlm   # 고품질 + VLM 보강
```

## 폴더 구조

```
.
├── _assets/    📦  내 PDF 를 두는 곳 (.gitignore 됨 → GitHub 에 절대 안 올라감)
│               입력 before--*.pdf  /  결과 after--*.pdf  +  after--*.md
├── assets/    🔤  앱 동봉 리소스 (git 추적). NanumGothic.ttf (한글 폰트, OFL)
├── pipeline/  🧠  OCR 파이프라인 코드 (renderer / ocr_engine / pdf_writer ...)
├── docs/      📖  설치·사용·아키텍처 상세
├── app.py     🖥  Gradio UI 진입점
├── setup.{bat,sh}  /  run.{bat,sh}
└── requirements.txt, .gitignore, .gitattributes, README.md
```

**핵심**: `_assets/` 안에 어떤 PDF·MD·이미지를 넣어도 GitHub 에 올라가지 않습니다.
저작권이 있는 교재 스캔본도 안심하고 거기 두세요. (실제 동작은 `git check-ignore` 로 검증 완료)
오직 `_assets/.gitkeep` 파일만 git 에 올라가 빈 폴더 구조를 유지합니다.

Gradio UI 에서 다운로드한 결과 PDF 도 `_assets/` 에 옮겨두면, 다음 실행 시 [폴더 배치] 탭에 자동으로 잡힙니다.

## 더 보기

- 📥 [설치 / 트러블슈팅](docs/install.md)
- 📖 [사용법 / 모드 / FAQ](docs/usage.md)
- 🧩 [아키텍처 / 디렉토리 / 좌표 변환](docs/architecture.md)

## 라이선스

코드 MIT · NanumGothic OFL · PyMuPDF는 AGPL (재배포 시 검토).
입력 PDF는 사용자 권리 자료여야 합니다.
