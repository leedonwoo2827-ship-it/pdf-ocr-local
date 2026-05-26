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

## 더 보기

- 📥 [설치 / 트러블슈팅](docs/install.md)
- 📖 [사용법 / 모드 / FAQ](docs/usage.md)
- 🧩 [아키텍처 / 디렉토리 / 좌표 변환](docs/architecture.md)

## 라이선스

코드 MIT · NanumGothic OFL · PyMuPDF는 AGPL (재배포 시 검토).
입력 PDF는 사용자 권리 자료여야 합니다.
