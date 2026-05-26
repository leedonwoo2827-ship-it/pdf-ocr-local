# 사용법

## 입출력 규약

- 입력: `_assets/before--<이름>.pdf`
- 출력: `_assets/after--<이름>.pdf` (검색가능 PDF) + `_assets/after--<이름>.md` (Markdown)
- `before--` 접두사가 없으면 출력은 `<원본 stem>_ocr.pdf` 가 됩니다.

## Gradio UI

```bash
./run.sh        # Linux/macOS
run.bat         # Windows
```
브라우저: <http://127.0.0.1:7860>

- **[단일 파일] 탭**: PDF를 드롭 → 좌측에 원본 미리보기 → "변환 시작" → 우측에 결과 PDF + 다운로드 (PDF, MD)
- **[폴더 배치] 탭**: 기본 경로 `_assets/` 의 `before--*.pdf` 가 자동 목록화 → "일괄 변환 시작"
- 사이드바
  - **Fast / Quality** 라디오
  - **VLM 보강** 체크박스 (Ollama 미실행 시 비활성)
  - **VLM 임계값** 슬라이더 (페이지 평균 신뢰도)
  - **Markdown 도 저장** 체크박스
  - **이미 있는 after--*.pdf 덮어쓰기**

## CLI

```bash
# 단일 파일
python -m pipeline.runner _assets/before--myscan.pdf

# 폴더 배치 (모든 before--*.pdf 처리)
python -m pipeline.runner _assets

# Quality 모드 (DPI 300, doc_unwarping, textline_orientation)
python -m pipeline.runner _assets/before--myscan.pdf --quality

# VLM 보강 + 임계값
python -m pipeline.runner _assets/before--myscan.pdf --vlm --threshold 0.7

# Markdown 미생성
python -m pipeline.runner _assets/before--myscan.pdf --no-md

# 이미 있는 결과 덮어쓰기
python -m pipeline.runner _assets/before--myscan.pdf --overwrite
```

## 모드 비교 (A4 84p 기준 RTX 4070 8GB)

| 모드 | DPI | 추가 옵션 | 처리시간 | 용도 |
|---|---|---|---|---|
| **Fast** (기본) | 200 | det+rec | ~2분 | 깨끗한 인쇄물 스캔 |
| **Quality** | 300 | + cls + textline_orientation + doc_unwarping | ~5분 | 비스듬한 스캔, 작은 글자, 흐릿한 원본 |
| **VLM 보강** | (위에 추가) | 평균 신뢰도 < 임계값인 페이지만 `qwen2.5vl:7b` 호출 | +초/페이지 | 손글씨, 복잡한 표, 특수 레이아웃 |

**VLM 보강 동작**:
1. PaddleOCR가 모든 페이지를 1차 처리하고 페이지별 `rec_scores` 평균을 계산
2. 평균이 임계값(기본 0.7) 미만인 페이지만 `qwen2.5vl:7b` 가 다시 텍스트 추출
3. **검색가능 PDF의 텍스트 레이어는 PaddleOCR bbox 기준 유지** (VLM은 bbox를 안 줌)
4. **Markdown 파일에서 해당 페이지만 VLM 출력으로 치환**

## 결과 검증

```python
import fitz
doc = fitz.open("_assets/after--myscan.pdf")
print("총 글자 수:", sum(len(p.get_text()) for p in doc))
print("'테이블' 검색:", sum(1 for p in doc if '테이블' in p.get_text()), "페이지")
```

PDF 뷰어에서 직접 확인할 점:
- [ ] 원본 페이지가 그대로 보이는지 (이미지 변형 없음)
- [ ] 본문 텍스트를 마우스로 드래그하면 선택 영역이 잡히는지
- [ ] Ctrl+F / Cmd+F 검색이 동작하는지
- [ ] 글자가 두 번 보이지 않는지 (= `render_mode=3` invisible 적용 확인)

## FAQ

**Q. 다른 언어 (영어/일본어/중국어)도 가능한가요?**
A. `pipeline/ocr_engine.py` 의 `lang="korean"` 을 `english`, `japan`, `ch` 등으로 바꾸면 됩니다. PaddleOCR이 80+ 언어를 지원합니다.

**Q. CPU만으로도 쓸 수 있나요?**
A. 가능합니다. setup 스크립트가 자동으로 CPU 빌드를 설치합니다. 다만 84p 기준 10–20분이 걸릴 수 있어 단일 페이지 테스트 외엔 비추천.

**Q. Quality 모드인데도 인식이 너무 나빠요**
A. (1) 원본 스캔 해상도가 너무 낮은 경우 (150 DPI 미만)는 한계 — 가능하면 300 DPI로 재스캔. (2) 그 외엔 `--vlm` 옵션으로 어려운 페이지만 LLM이 보강하도록 활성화.

**Q. Markdown 결과의 단락 구분이 어색해요**
A. PaddleOCR은 라인 단위로 텍스트를 주고 본 구현은 단순한 Y-band 기준 reading order 정렬을 합니다. 정확한 구조가 필요하면 `--vlm` 을 켜서 VLM이 페이지를 Markdown으로 직접 재구성하게 하세요.

**Q. 결과 PDF 용량이 커지는데 줄일 수 있나요?**
A. `pipeline/pdf_writer.py` 의 `doc.save(..., garbage=4, deflate=True)` 가 기본 적용되어 있습니다. 그 이상은 원본 이미지 해상도 자체를 다운샘플링해야 합니다.

**Q. ScansSnap이나 다른 스캐너 출력 PDF인데 그대로 넣어도 되나요?**
A. 네. 원본 페이지 이미지를 보존하면서 텍스트 레이어만 새로 얹습니다. 기존 OCR 텍스트 레이어가 이미 있으면 그 위에 한 겹 더 얹혀 글자가 두 번 검색될 수 있으니, 그런 경우엔 텍스트 레이어 없는 원본을 사용하세요.
