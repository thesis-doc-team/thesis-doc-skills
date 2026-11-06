"""v1.4.1: native VSDX generation, structural validation and RES binding."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from argparse import Namespace
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import figure_qc as qc  # noqa: E402
import md_pipeline as m  # noqa: E402
import visio_diagram as vd  # noqa: E402
import vsdx_writer as vw  # noqa: E402

MAIN = "http://schemas.microsoft.com/office/visio/2012/main"


def example_spec():
    s = json.loads((ROOT / "examples" / "visio-style-example.json").read_text("utf-8"))
    return s


class VsdxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def make(self):
        spec = example_spec()
        routed, *_ = vd.prepare_spec(spec, require_caption=True)
        out = self.dir / "figure.vsdx"
        report = vw.write_vsdx(routed, out)
        return routed, out, report

    def test_vsdx_has_required_parts_and_native_shapes(self):
        _, path, report = self.make()
        self.assertEqual(report["status"], "STRUCTURALLY_VALID_VSDX")
        self.assertEqual(report["issues"], [])
        self.assertTrue(report["native_visio_format"])
        self.assertEqual(report["visio_open_verification"], "pending-visio-open")
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            for part in ("[Content_Types].xml", "_rels/.rels", "visio/document.xml",
                         "visio/pages/pages.xml", "visio/pages/page1.xml",
                         "visio/windows.xml"):
                self.assertIn(part, names)
            root = ET.fromstring(z.read("visio/pages/page1.xml"))
            shapes = root.findall(f".//{{{MAIN}}}Shape")
            self.assertGreaterEqual(len(shapes), 5)
            texts = [(s.findtext(f"{{{MAIN}}}Text") or "") for s in shapes]
            self.assertTrue(any("数据采集" in t for t in texts))
            self.assertTrue(any("图 3-1" in t for t in texts))
            self.assertTrue(any("Fig. 3-1" in t for t in texts))

    def test_vsdx_rejects_missing_page_part(self):
        _, path, _ = self.make()
        broken = self.dir / "broken.vsdx"
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(broken, "w") as dst:
            for name in src.namelist():
                if name != "visio/pages/page1.xml":
                    dst.writestr(name, src.read(name))
        report = vw.validate_vsdx(broken)
        self.assertEqual(report["status"], "INVALID_VSDX")
        self.assertTrue(any("page1.xml" in x for x in report["issues"]))

    def test_figure_qc_checks_vsdx(self):
        _, path, _ = self.make()
        report, issues = qc.check_vsdx(path)
        self.assertEqual(report["status"], "STRUCTURALLY_VALID_VSDX")
        self.assertEqual(issues, [])

    def test_metadata_records_vsdx_and_pending_verification(self):
        routed, path, _ = self.make()
        svg = self.dir / "figure.svg"
        drawio = self.dir / "figure.drawio"
        vd.svg_diagram(example_spec(), svg, require_caption=True)
        vd.drawio_diagram(example_spec(), drawio, require_caption=True)
        meta = vd.figure_metadata(routed, svg, drawio, vsdx=vw.validate_vsdx(path) | {"path": str(path)})
        self.assertTrue(meta["native_visio_vsdx"])
        self.assertEqual(meta["print_vsdx"], str(path))
        self.assertEqual(meta["vsdx_verification"], "pending-visio-open")

    def test_attach_layout_binds_vsdx(self):
        root = self.dir / "project"
        (root / "project-assets").mkdir(parents=True)
        (root / "project-assets" / "project.json").write_text(
            json.dumps({"schema_version": 1, "project_id": "P141"}), "utf-8")
        md = root / "deliverables" / "technical-document" / "tech.md"
        md.parent.mkdir(parents=True)
        md.write_text("# T\n## 1. 系统总体架构\n```mermaid\nflowchart TD\n A[开始] --> B[结束]\n```\n", "utf-8")
        base = dict(root=str(root), technical_md=str(md), project_id="P141", save=False,
                    module_id="", file="", rights_declaration="", id="", decision="approved",
                    evidence="", reviewer="human")
        m.execute(Namespace(command="sync", **base))
        cat = m.load_catalog(root, "P141")
        item = next(x for x in cat["items"] if x["kind"] == "mermaid")
        spec = example_spec()
        routed, *_ = vd.prepare_spec(spec, require_caption=True)
        diagrams = root / "project-assets" / "resource-catalog" / "diagrams"
        svg = diagrams / "figure.svg"
        drawio = diagrams / "figure.drawio"
        vsdx = diagrams / "figure.vsdx"
        meta_path = diagrams / "figure.figure.json"
        vd.svg_diagram(spec, svg, require_caption=True)
        vd.drawio_diagram(spec, drawio, require_caption=True)
        vw.write_vsdx(routed, vsdx)
        meta_path.write_text(json.dumps(vd.figure_metadata(routed, svg, drawio,
                                                           vsdx=vw.validate_vsdx(vsdx) | {"path": str(vsdx)}),
                                        ensure_ascii=False), "utf-8")
        args = dict(base, id=item["id"], svg=str(svg), drawio=str(drawio), vsdx=str(vsdx),
                    template=str(ROOT / "examples" / "A4-图表排版示例.docx"), section=1,
                    evidence="已逐条核对测试 MD 的节点与连线关系，节点与箭头均有原文依据",
                    figure_meta=str(meta_path), require_caption=True,
                    figure_number=None, caption_zh=None, caption_en=None)
        result = m.execute(Namespace(command="attach-layout", **args))
        self.assertEqual(result["status"], "A4_GEOMETRY_PASS_NEEDS_WORD_VISUAL_REVIEW")
        self.assertTrue(result["print_vsdx"].endswith(".vsdx"))
        item2 = next(x for x in m.load_catalog(root, "P141")["items"] if x["id"] == item["id"])
        self.assertTrue(item2["native_visio_vsdx"])
        self.assertEqual(item2["vsdx_verification"], "pending-visio-open")
        self.assertTrue((root / item2["print_vsdx"]).is_file())


if __name__ == "__main__":
    unittest.main()