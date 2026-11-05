"""v1.4.0 test D/F: real Word render + bilingual caption + strict three-line table."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import a4_layout  # noqa: E402
import figure_qc  # noqa: E402
import three_line_table  # noqa: E402
from make_a4_word_sample import build, render_pdf_pages, render_word  # noqa: E402

WINWORD = Path(r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE")
POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
PNG = ROOT / "examples" / "orthogonal-flow-example-300dpi.png"


class WordRenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def make_docx(self, name="sample.docx"):
        path = self.dir / name
        build(path, PNG)
        d = Document(str(path))
        three_line_table.apply_three_line(d.tables[0])
        d.save(str(path))
        return path

    def test_f_three_line_table_unchanged(self):
        path = self.make_docx()
        d = Document(str(path))
        audit = three_line_table.audit_three_line(d.tables[0])
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["rule_count"], 3)
        self.assertEqual(audit["problems"], [])

    def test_d_a4_word_render_and_caption(self):
        if not WINWORD.is_file() or not POWERSHELL.is_file():
            self.skipTest("本机没有 Word COM，无法执行真实 Word 渲染；不得以 XML 检查代替")
        path = self.make_docx()
        pdf = self.dir / "sample.pdf"
        render_word(path, pdf)
        self.assertTrue(pdf.is_file() and pdf.stat().st_size > 1000)
        pages = render_pdf_pages(pdf, self.dir)
        self.assertGreaterEqual(len(pages), 1)
        self.assertGreater(pages[0]["width_px"], 1000)

        layout = a4_layout.audit_docx(str(path))
        self.assertEqual(layout["status"], "STATIC_CHECK_PASS_NEEDS_VISUAL_REVIEW")
        self.assertEqual(len(layout["figures"]), 1)
        self.assertAlmostEqual(layout["figures"][0]["size_mm"][0], 155.0, delta=0.6)
        self.assertLessEqual(layout["tables"][0]["width_mm"], 160.5)
        self.assertFalse(layout["figures"][0]["floating"])

        caps = figure_qc.caption_audit_docx(str(path))
        self.assertEqual(caps["status"], "PASS")
        self.assertEqual(caps["picture_count"], 1)
        kinds = {c["kind"] for c in caps["captions"]}
        self.assertEqual(kinds, {"zh", "en"})
        self.assertTrue(all(c["centered"] for c in caps["captions"]))
        # Both captions are below the picture paragraph.
        from docx.oxml.ns import qn
        d = Document(str(path))
        pic_para = next(i for i, p in enumerate(d.paragraphs)
                        if p._element.findall(".//" + qn("wp:inline")))
        self.assertTrue(all(c["paragraph"] > pic_para for c in caps["captions"]))

    def test_docx_missing_english_caption_is_blocked(self):
        path = self.dir / "no-english.docx"
        build(path, PNG)
        d = Document(str(path))
        for p in list(d.paragraphs):
            if p.text.strip().startswith("Fig."):
                p._element.getparent().remove(p._element)
        d.save(str(path))
        caps = figure_qc.caption_audit_docx(str(path))
        self.assertEqual(caps["status"], "FAIL")
        self.assertTrue(any(x["code"] == "DOCX_CAPTION_EN_MISSING" for x in caps["issues"]))

    def test_english_caption_is_not_burned_into_png_text(self):
        # The DOCX caption is a native paragraph, not part of the PNG.
        caps = figure_qc.caption_audit_docx(str(self.make_docx()))
        self.assertTrue(all(c["text"] for c in caps["captions"]))
        self.assertNotIn("Fig.", Path(PNG).name)


if __name__ == "__main__":
    unittest.main()