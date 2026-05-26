"""Gradio UI for local OCR (scanned PDF -> searchable PDF + Markdown).

Tabs:
  - Single file: drop a PDF, see original on the left and result on the right.
  - Folder batch: process every before--*.pdf under a folder.

Run:  python app.py
Open: http://127.0.0.1:7860
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import List, Tuple

import gradio as gr
from gradio_pdf import PDF

from pipeline.runner import PipelineConfig, run_pipeline, derive_out_paths
from pipeline.vlm_engine import ollama_available
from pipeline.mineru_engine import mineru_available

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
DEFAULT_BATCH_DIR = str(ASSETS_DIR)


def _import_into_assets(src: Path) -> Path:
    """Copy a Gradio-uploaded PDF into assets/ so outputs land there too.

    The pipeline writes after--*.pdf / .md next to the input PDF, so by
    moving the input into a stable folder we get a stable output location
    that users can browse in Explorer without going through the Gradio
    download buttons.
    """
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    target = ASSETS_DIR / src.name
    try:
        if target.resolve() == src.resolve():
            return target
    except (OSError, ValueError):
        pass
    shutil.copyfile(src, target)
    return target


def _build_cfg(
    mode: str,
    md_engine: str,
    use_vlm: bool,
    threshold: float,
    emit_md: bool,
    overwrite: bool,
) -> PipelineConfig:
    return PipelineConfig(
        quality=(mode == "Quality"),
        emit_markdown=emit_md,
        markdown_engine=md_engine.lower(),
        use_vlm=use_vlm,
        vlm_threshold=threshold,
        overwrite=overwrite,
    )


# ---------- Single-file tab ----------

def process_single(
    pdf_file,
    mode: str,
    md_engine: str,
    use_vlm: bool,
    threshold: float,
    emit_md: bool,
    overwrite: bool,
    progress=gr.Progress(),
):
    if pdf_file is None:
        return None, None, "PDF를 먼저 업로드하세요.", gr.update(visible=False), gr.update(visible=False)

    src_path = Path(pdf_file if isinstance(pdf_file, str) else pdf_file.name)
    # Move/copy the upload into assets/ so outputs land in a stable folder
    # the user can browse directly in Explorer (no need to click Download).
    src_path = _import_into_assets(src_path)
    cfg = _build_cfg(mode, md_engine, use_vlm, threshold, emit_md, overwrite)

    log_lines: List[str] = [
        f"Source: {src_path}",
        f"Mode: {mode}, Markdown engine: {md_engine}, VLM: {use_vlm}, threshold: {threshold:.2f}",
    ]
    # Echo the header to the launching cmd so users who double-clicked run.bat
    # can see the same context they would see from `python -m pipeline.runner`.
    for line in log_lines:
        print(line, flush=True)

    def cb(done, total, msg):
        if total > 0:
            progress(done / total, desc=msg)
        line = f"[{done}/{total}] {msg}"
        log_lines.append(line)
        print(line, flush=True)  # mirror per-page progress to stdout (cmd)

    try:
        out_pdf, out_md = run_pipeline(src_path, cfg, progress_cb=cb)
    except Exception as e:
        log_lines.append(f"ERROR: {e}")
        return None, None, "\n".join(log_lines), gr.update(visible=False), gr.update(visible=False)

    # Force the progress widget to 100% so Gradio stops spinning the counter.
    progress(1.0, desc="Done")
    log_lines.append(f"-> {out_pdf}")
    if out_md:
        log_lines.append(f"-> {out_md}")
    log = "\n".join(log_lines)
    md_visible = out_md is not None
    return (
        str(out_pdf),                                                 # result PDF preview
        str(out_pdf),                                                 # download (pdf)
        log,                                                          # log textbox
        gr.update(value=str(out_md) if md_visible else None, visible=md_visible),  # download md
        gr.update(visible=True),                                      # download pdf visible
    )


# ---------- Folder-batch tab ----------

def list_folder(folder: str):
    folder = (folder or "").strip() or DEFAULT_BATCH_DIR
    p = Path(folder)
    if not p.is_dir():
        return [], f"폴더가 존재하지 않습니다: {folder}"
    rows = []
    for f in sorted(p.glob("before--*.pdf")):
        out_pdf, _ = derive_out_paths(f)
        status = "완료" if out_pdf.exists() else "대기"
        rows.append([f.name, status, out_pdf.name])
    return rows, f"{len(rows)}개 파일 발견 ({folder})"


def process_folder(
    folder: str,
    mode: str,
    md_engine: str,
    use_vlm: bool,
    threshold: float,
    emit_md: bool,
    overwrite: bool,
    progress=gr.Progress(),
):
    folder = (folder or "").strip() or DEFAULT_BATCH_DIR
    p = Path(folder)
    if not p.is_dir():
        return [], f"폴더가 존재하지 않습니다: {folder}"

    pdfs = sorted(p.glob("before--*.pdf"))
    if not pdfs:
        return [], "before--*.pdf 파일이 없습니다."

    cfg = _build_cfg(mode, md_engine, use_vlm, threshold, emit_md, overwrite)
    rows: List[List[str]] = []
    logs: List[str] = []

    def _emit(msg: str):
        logs.append(msg)
        print(msg, flush=True)

    _emit(f"Folder batch: {len(pdfs)} file(s) under {folder}")

    for i, f in enumerate(pdfs):
        progress(i / len(pdfs), desc=f"[{i+1}/{len(pdfs)}] {f.name}")
        _emit(f"[{i+1}/{len(pdfs)}] {f.name}")

        out_pdf, _ = derive_out_paths(f)
        if out_pdf.exists() and not overwrite:
            rows.append([f.name, "스킵(존재)", out_pdf.name])
            _emit(f"  skip {f.name}")
            continue

        def _file_cb(done, total, msg):
            line = f"    [{done}/{total}] {msg}"
            print(line, flush=True)

        try:
            opdf, omd = run_pipeline(f, cfg, progress_cb=_file_cb)
            rows.append([f.name, "완료", opdf.name])
            _emit(f"  done {f.name} -> {opdf.name}")
        except Exception as e:
            rows.append([f.name, f"실패: {e}", ""])
            _emit(f"  FAIL {f.name}: {e}")

    progress(1.0, desc="배치 완료")
    _emit("Batch complete")
    return rows, "\n".join(logs)


# ---------- UI ----------

with gr.Blocks(title="Local OCR — before→after PDF", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# 📄 Local OCR — before→after PDF\n"
        "스캔 PDF에 보이지 않는 텍스트 레이어를 얹어 검색·복사 가능한 PDF로 변환합니다. "
        "엔진: **PaddleOCR PP-OCRv5 (한글)** · 옵션: **Qwen2.5-VL 7B (Ollama)** 보강 · 100% 로컬."
    )

    with gr.Row():
        mode = gr.Radio(["Fast", "Quality"], value="Quality", label="OCR 모드", info="Fast=DPI200 빠름, Quality=DPI300 + unwarp 권장")
        emit_md = gr.Checkbox(value=True, label="Markdown(.md) 도 함께 저장")
        overwrite = gr.Checkbox(value=True, label="이미 있는 after--*.pdf 덮어쓰기")

    with gr.Row():
        mineru_ok = mineru_available()
        md_engine_choices = ["paddle"] + (["mineru"] if mineru_ok else [])
        md_engine = gr.Radio(
            md_engine_choices,
            value=("mineru" if mineru_ok else "paddle"),
            label="Markdown 엔진",
            info=("mineru = 레이아웃 인식 마크다운 (표/제목/번호 구조 보존, 권장). "
                  "paddle = 빠른 라인 텍스트 (PDF 검색은 그대로)." if mineru_ok
                  else "mineru CLI 없음 → setup_mineru.bat 더블클릭 후 재시작하면 mineru도 선택 가능"),
        )

    with gr.Row():
        vlm_ok = ollama_available()
        # VLM 보강은 paddle 마크다운 트랙 전용 — mineru 선택 시 꺼두고 비활성화.
        initial_vlm_enabled = vlm_ok and not mineru_ok  # mineru 가 기본이면 VLM 꺼둠
        use_vlm = gr.Checkbox(
            value=False,
            label=f"VLM 보강 (Ollama qwen2.5vl:7b){'' if vlm_ok else ' — Ollama 응답 없음'}",
            interactive=initial_vlm_enabled,
        )
        threshold = gr.Slider(
            0.0, 1.0, value=0.7, step=0.05,
            label="VLM 트리거: 페이지 평균 신뢰도 임계값",
            interactive=initial_vlm_enabled,
        )

    # mineru 일 때 VLM 컨트롤 회색 처리 (paddle 마크다운에서만 의미 있음)
    def _toggle_vlm_controls(engine: str):
        is_paddle = (engine == "paddle")
        return (
            gr.update(interactive=(is_paddle and vlm_ok), value=False),
            gr.update(interactive=(is_paddle and vlm_ok)),
        )
    md_engine.change(_toggle_vlm_controls, inputs=md_engine, outputs=[use_vlm, threshold])

    with gr.Tabs():
        # ----- Single file -----
        with gr.Tab("단일 파일"):
            with gr.Row():
                with gr.Column():
                    in_file = gr.File(label="PDF 파일 (drag & drop)", file_types=[".pdf"], type="filepath")
                    in_pdf_preview = PDF(label="원본 미리보기", interactive=False)
                    in_file.change(lambda x: x, inputs=in_file, outputs=in_pdf_preview)
                    run_btn = gr.Button("변환 시작", variant="primary")
                with gr.Column():
                    out_pdf_preview = PDF(label="결과 미리보기 (검색가능 PDF)", interactive=False)
                    out_pdf_dl = gr.File(label="검색가능 PDF 다운로드", visible=False)
                    out_md_dl = gr.File(label="Markdown 다운로드", visible=False)
            log_box = gr.Textbox(label="로그", lines=10, max_lines=20)
            run_btn.click(
                process_single,
                inputs=[in_file, mode, md_engine, use_vlm, threshold, emit_md, overwrite],
                outputs=[out_pdf_preview, out_pdf_dl, log_box, out_md_dl, out_pdf_dl],
            )

        # ----- Folder batch -----
        with gr.Tab("폴더 배치"):
            with gr.Row():
                folder_path = gr.Textbox(value=DEFAULT_BATCH_DIR, label="폴더 경로 (before--*.pdf 검색)")
                list_btn = gr.Button("목록 새로고침")
            files_table = gr.Dataframe(
                headers=["입력파일", "상태", "출력파일"],
                column_count=(3, "fixed"),
                row_count=(0, "dynamic"),
                interactive=False,
                label="대상 파일",
            )
            list_status = gr.Textbox(label="상태", lines=1)
            run_batch_btn = gr.Button("일괄 변환 시작", variant="primary")
            batch_log = gr.Textbox(label="배치 로그", lines=12, max_lines=30)

            list_btn.click(list_folder, inputs=folder_path, outputs=[files_table, list_status])
            run_batch_btn.click(
                process_folder,
                inputs=[folder_path, mode, md_engine, use_vlm, threshold, emit_md, overwrite],
                outputs=[files_table, batch_log],
            )
            demo.load(list_folder, inputs=folder_path, outputs=[files_table, list_status])


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=False, show_error=True)
