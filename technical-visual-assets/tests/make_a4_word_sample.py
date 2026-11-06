#!/usr/bin/env python3
"""Build and render the v1.4.0 A4 Word sample (figure + bilingual caption + 3-line table).

Requires python-docx (already used by three_line_table.py).  Word rendering is
performed through PowerShell COM; if Word is unavailable the script returns a
clear PENDING instead of pretending a page render happened.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
import a4_layout  # noqa: E402
import figure_qc  # noqa: E402
import three_line_table  # noqa: E402

PS = r"""
param([string]$Docx,[string]$Pdf)
$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($Docx, $false, $true)
  $doc.ExportAsFixedFormat($Pdf, 17)
  $doc.Close([ref]$false)
} finally {
  $word.Quit()
}
"""


def set_run_font(run, name="SimSun", size=10.5, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def build(docx_path, png_path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin = sec.bottom_margin = Cm(2.5)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("A4 正交流程图与英文图题验证样例（非学校官方模板）")
    set_run_font(r, "SimHei", 14, True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    p.add_run().add_picture(str(png_path), width=Cm(15.5))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(0)
    set_run_font(p.add_run("图 3-1 数据采集、清洗、校验与入库流程"), "SimSun", 10.5)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(8)
    set_run_font(p.add_run("Fig. 3-1 Data Acquisition, Cleaning, Validation and Storage Flowchart"),
                 "Times New Roman", 10.5)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run_font(p.add_run("表 3-1 工程图质量门禁检查项（示例）"), "SimSun", 10.5)

    table = doc.add_table(rows=4, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    data = [
        ("检查项", "结果", "说明"),
        ("正交连线", "通过", "所有连接线仅含水平/垂直线段"),
        ("中英文图题", "通过", "图号按章节编号，图题位于图下"),
        ("三线表", "通过", "仅表顶、表头下、表底三条横线"),
    ]
    for i, row in enumerate(data):
        for j, text in enumerate(row):
            cell = table.cell(i, j)
            cell.text = ""
            para = cell.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_run_font(para.add_run(text), "SimSun", 9.0)

    doc.save(str(docx_path))
    return docx_path


def render_word(docx_path, pdf_path):
    ps1 = HERE / "_render_word.ps1"
    ps1.write_text(PS, "utf-8")
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
           str(ps1), "-Docx", str(Path(docx_path).resolve()),
           "-Pdf", str(Path(pdf_path).resolve())]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0 or not Path(pdf_path).exists():
        raise RuntimeError((p.stderr or p.stdout or "Word COM render failed")[-800:])
    return pdf_path


def render_pdf_pages(pdf_path, out_dir, dpi=150):
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError("需要 PyMuPDF 才能把 Word PDF 渲染为页面 PNG") from exc
    doc = fitz.open(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(dpi=dpi)
        path = out_dir / f"page-{i}.png"
        pix.save(str(path))
        pages.append({"page": i, "png": str(path), "width_px": pix.width, "height_px": pix.height})
    return pages


def main():
    ap = argparse.ArgumentParser(description="生成并渲染 A4 正交流程图 + 中英文图题 + 三线表样例")
    ap.add_argument("--out-docx", default=str(ROOT / "examples" / "A4-正交流程图与英文图题示例.docx"))
    ap.add_argument("--png", default=str(ROOT / "examples" / "orthogonal-flow-example-300dpi.png"))
    ap.add_argument("--no-word-render", action="store_true")
    args = ap.parse_args()
    out_docx = Path(args.out_docx)
    tmp_docx = out_docx.with_name("_tmp_" + out_docx.name)
    build(tmp_docx, Path(args.png))
    # Convert table 1 to a strict three-line table in a copy, then replace.
    from three_line_table import apply_three_line
    d = Document(str(tmp_docx))
    apply_three_line(d.tables[0])
    d.save(str(out_docx))
    tmp_docx.unlink(missing_ok=True)

    layout = a4_layout.audit_docx(str(out_docx))
    caps = figure_qc.caption_audit_docx(str(out_docx))
    table_audit = three_line_table.audit_three_line(Document(str(out_docx)).tables[0])
    report = {"status": "A4_WORD_SAMPLE_BUILT",
              "docx": str(out_docx),
              "layout": layout,
              "captions": caps,
              "table_audit": table_audit,
              "word_render": "SKIPPED"}
    if not args.no_word_render:
        pdf = out_docx.with_suffix(".pdf")
        try:
            render_word(out_docx, pdf)
            pages = render_pdf_pages(pdf, out_docx.parent)
            report["word_render"] = {"status": "RENDERED", "pdf": str(pdf), "pages": pages}
        except Exception as exc:  # noqa: BLE001 - report the exact environment gap
            report["word_render"] = {"status": "PENDING", "reason": str(exc)}
    audit_path = out_docx.with_name(out_docx.stem + "-audit.json")
    audit_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())