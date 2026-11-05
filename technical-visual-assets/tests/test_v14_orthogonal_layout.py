"""v1.4.0 orthogonal-layout, caption and compatibility tests (A/B/C/E/G)."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import figure_qc as qc  # noqa: E402
import md_pipeline as m  # noqa: E402
import orthogonal_router as router  # noqa: E402
import visio_diagram as vd  # noqa: E402

SVG = "http://www.w3.org/2000/svg"


def meta(num="4-1", zh="阈值告警处理流程", en="Threshold Alarm Processing Flowchart"):
    return {
        "figure_number": num,
        "caption_zh": zh,
        "caption_en": en,
        "source_refs": [{"section": "测试用例", "lines": [1], "evidence": "合成测试图，不是项目事实"}],
    }


def linear_spec():
    s = {
        "width_mm": 155, "height_mm": 120, "font_pt": 9.5,
        "groups": [], "nodes": [
            {"id": "a", "label": "上电", "shape": "pill", "x": 40, "y": 8, "w": 75, "h": 14},
            {"id": "b", "label": "初始化外设", "shape": "rect", "x": 40, "y": 34, "w": 75, "h": 14},
            {"id": "c", "label": "读取传感器", "shape": "rect", "x": 40, "y": 60, "w": 75, "h": 14},
            {"id": "d", "label": "进入主循环", "shape": "pill", "x": 40, "y": 86, "w": 75, "h": 14},
        ],
        "edges": [
            {"from": "a", "to": "b"}, {"from": "b", "to": "c"}, {"from": "c", "to": "d"},
        ],
    }
    s.update(meta("4-1", "系统初始化流程", "System Initialization Flowchart"))
    return s


def decision_spec():
    s = {
        "width_mm": 155, "height_mm": 150, "font_pt": 9.5,
        "groups": [], "nodes": [
            {"id": "start", "label": "读取数据", "shape": "pill", "x": 40, "y": 6, "w": 75, "h": 14},
            {"id": "dec", "label": "是否越限?", "shape": "diamond", "x": 47, "y": 30, "w": 60, "h": 24},
            {"id": "yes", "label": "蜂鸣器告警", "shape": "rect", "x": 12, "y": 70, "w": 55, "h": 16},
            {"id": "no", "label": "保持正常", "shape": "rect", "x": 105, "y": 64, "w": 45, "h": 16},
            {"id": "merge", "label": "继续监测", "shape": "rect", "x": 45, "y": 108, "w": 65, "h": 16},
        ],
        "edges": [
            {"from": "start", "to": "dec"},
            {"from": "dec", "to": "yes", "label": "是"},
            {"from": "dec", "to": "no", "label": "否"},
            {"from": "yes", "to": "merge"},
            {"from": "no", "to": "merge"},
        ],
    }
    s.update(meta("4-2", "阈值判断分支流程", "Threshold Decision Branch Flowchart"))
    return s


def nested_spec():
    s = {
        "width_mm": 155, "height_mm": 200, "font_pt": 9.5,
        "groups": [], "nodes": [
            {"id": "start", "label": "开始", "shape": "pill", "x": 45, "y": 6, "w": 65, "h": 14},
            {"id": "d1", "label": "条件一?", "shape": "diamond", "x": 47, "y": 28, "w": 60, "h": 24},
            {"id": "a", "label": "处理 A", "shape": "rect", "x": 2, "y": 68, "w": 42, "h": 14},
            {"id": "d2", "label": "条件二?", "shape": "diamond", "x": 52, "y": 68, "w": 50, "h": 24},
            {"id": "b", "label": "处理 B", "shape": "rect", "x": 108, "y": 68, "w": 42, "h": 14},
            {"id": "c", "label": "处理 C", "shape": "rect", "x": 2, "y": 112, "w": 42, "h": 14},
            {"id": "merge", "label": "汇合", "shape": "rect", "x": 50, "y": 150, "w": 55, "h": 14},
            {"id": "end", "label": "结束", "shape": "pill", "x": 50, "y": 176, "w": 55, "h": 14},
        ],
        "edges": [
            {"from": "start", "to": "d1"},
            {"from": "d1", "to": "a", "label": "是"},
            {"from": "d1", "to": "d2", "label": "否"},
            {"from": "d2", "to": "b", "label": "是"},
            {"from": "d2", "to": "c", "label": "否"},
            {"from": "a", "to": "merge"},
            {"from": "b", "to": "merge"},
            {"from": "c", "to": "merge"},
            {"from": "merge", "to": "end"},
        ],
    }
    s.update(meta("4-3", "嵌套条件处理流程", "Nested Conditional Processing Flowchart"))
    return s


class OrthogonalLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)

    def render(self, spec):
        svg = vd.svg_diagram(spec, self.out / "f.svg", require_caption=True)
        drawio = vd.drawio_diagram(spec, self.out / "f.drawio", require_caption=True)
        return svg, drawio

    def test_a_simple_linear_flow_is_orthogonal(self):
        spec = linear_spec()
        routed, w, h, font, coords = vd.prepare_spec(spec, require_caption=True)
        for e in routed["edges"]:
            self.assertTrue(router.is_orthogonal(e["points"]), e)
        self.assertEqual(router.count_crossings(routed), 0)
        self.assertEqual(router.audit_routing(routed), [])
        res, issues, warnings = qc.check_spec(spec, None, require_caption=True, formal=True)
        self.assertEqual(issues, [])
        svg, drawio = self.render(spec)
        self.assertEqual(qc.check_svg(svg, res["routed_spec"])[1], [])
        self.assertEqual(qc.check_drawio(drawio)[1], [])
        # no diagonal polyline in the actual SVG
        root = ET.fromstring(svg.read_bytes())
        for pl in root.findall(f".//{{{SVG}}}polyline"):
            pts = [tuple(map(float, p.split(","))) for p in pl.attrib["points"].split()]
            self.assertTrue(router.is_orthogonal(pts))

    def test_b_decision_branches_labels_and_merge(self):
        spec = decision_spec()
        routed, *_ = vd.prepare_spec(spec, require_caption=True)
        dec_edges = [e for e in routed["edges"] if e["from"] == "dec"]
        self.assertEqual({e["label"] for e in dec_edges}, {"是", "否"})
        for e in dec_edges:
            self.assertIn("label_pos", e)
            self.assertTrue(e["points"])
        yes = next(e for e in dec_edges if e["label"] == "是")
        no = next(e for e in dec_edges if e["label"] == "否")
        self.assertEqual(yes.get("from_port"), "bottom")
        self.assertIn(no.get("from_port"), {"left", "right"})
        merge_in = [e for e in routed["edges"] if e["to"] == "merge"]
        self.assertEqual(len(merge_in), 2)
        for e in routed["edges"]:
            self.assertTrue(router.is_orthogonal(e["points"]))
        res, issues, warnings = qc.check_spec(spec, None, require_caption=True, formal=True)
        self.assertEqual(issues, [])

    def test_c_nested_decisions_do_not_cross_nodes(self):
        spec = nested_spec()
        routed, *_ = vd.prepare_spec(spec, require_caption=True)
        self.assertEqual(router.audit_routing(routed), [])
        self.assertLessEqual(router.count_crossings(routed), 1)
        for e in routed["edges"]:
            self.assertTrue(router.is_orthogonal(e["points"]))
            self.assertLessEqual(len(e["points"]) - 2, 10)
        res, issues, warnings = qc.check_spec(spec, None, require_caption=True, formal=True)
        self.assertEqual(issues, [])
        svg, _ = self.render(spec)
        self.assertEqual(qc.check_svg(svg, res["routed_spec"])[1], [])

    def test_negative_diagonal_is_not_orthogonal(self):
        self.assertFalse(router.is_orthogonal([[0, 0], [10, 10]]))
        bad = linear_spec()
        bad["edges"][0]["points"] = [[77, 22], [100, 40]]
        routed, *_ = vd.prepare_spec(bad, require_caption=True)
        for e in routed["edges"]:
            self.assertTrue(router.is_orthogonal(e["points"]))

    def test_e_caption_rules_and_not_drawn_in_pixels(self):
        good = meta()
        cap = vd.validate_caption(good, require=True)
        self.assertEqual(cap["figure_number"], "4-1")
        self.assertEqual(cap["caption_en_full"], "Fig. 4-1 Threshold Alarm Processing Flowchart")
        with self.assertRaisesRegex(ValueError, "不完整"):
            vd.validate_caption({"caption_zh": "只有中文"}, require=True)
        with self.assertRaisesRegex(ValueError, "笼统"):
            vd.validate_caption({"figure_number": "4-1", "caption_zh": "流程图",
                                 "caption_en": "System Diagram"}, require=True)
        with self.assertRaisesRegex(ValueError, "章节编号"):
            vd.validate_caption({"figure_number": "4", "caption_zh": "阈值告警流程",
                                 "caption_en": "Threshold Alarm Flowchart"}, require=True)
        mismatch = vd.validate_caption({"figure_number": "4-1", "caption_zh": "阈值告警处理流程",
                                        "caption_en": "Data Acquisition Flowchart"}, require=True)
        self.assertEqual(mismatch["semantic_check"], "heuristic-mismatch")
        spec = linear_spec()
        svg, _ = self.render(spec)
        text = svg.read_text("utf-8")
        root = ET.fromstring(text)
        for t in root.findall(f".//{{{SVG}}}text"):
            self.assertNotIn("图 4-1", "".join(t.itertext()))
        self.assertIn("<title>图 4-1", text)
        self.assertIn("Fig. 4-1", text)

    def test_g_pipeline_binds_caption_metadata(self):
        root = self.out / "project"
        (root / "project-assets").mkdir(parents=True)
        (root / "project-assets" / "project.json").write_text(
            json.dumps({"schema_version": 1, "project_id": "P14"}), "utf-8")
        md = root / "deliverables" / "technical-document" / "tech.md"
        md.parent.mkdir(parents=True)
        md.write_text("# T\n## 1. 系统总体架构\n```mermaid\nflowchart TD\n A[开始] --> B[结束]\n```\n", "utf-8")
        base = dict(root=str(root), technical_md=str(md), project_id="P14", save=False,
                    module_id="", file="", rights_declaration="", id="", decision="approved",
                    evidence="", reviewer="human")
        m.execute(Namespace(command="sync", **base))
        cat = m.load_catalog(root, "P14")
        item = next(x for x in cat["items"] if x["kind"] == "mermaid")
        spec = linear_spec()
        svg = root / "project-assets" / "resource-catalog" / "diagrams" / "f.svg"
        drawio = svg.with_suffix(".drawio")
        meta_path = svg.with_suffix(".figure.json")
        vd.svg_diagram(spec, svg, require_caption=True)
        vd.drawio_diagram(spec, drawio, require_caption=True)
        routed, *_ = vd.prepare_spec(spec, require_caption=True)
        meta_path.write_text(json.dumps(vd.figure_metadata(routed, svg, drawio), ensure_ascii=False), "utf-8")
        args = dict(base, id=item["id"], svg=str(svg), drawio=str(drawio),
                    template=str(ROOT / "examples" / "A4-图表排版示例.docx"), section=1,
                    evidence="已逐条核对测试 MD 的节点与连线关系，节点与箭头均有原文依据",
                    figure_meta=str(meta_path), require_caption=True,
                    figure_number=None, caption_zh=None, caption_en=None)
        result = m.execute(Namespace(command="attach-layout", **args))
        self.assertEqual(result["status"], "A4_GEOMETRY_PASS_NEEDS_WORD_VISUAL_REVIEW")
        item2 = next(x for x in m.load_catalog(root, "P14")["items"] if x["id"] == item["id"])
        self.assertEqual(item2["figure_number"], "4-1")
        self.assertEqual(item2["caption_en"], "System Initialization Flowchart")
        self.assertEqual(item2["routing_status"], "orthogonal")
        self.assertEqual(item2["caption_review_status"], "pending-human-semantic-and-Word-page-review")
        # backward compatible: attach without captions still works in legacy mode
        args2 = dict(args); args2.pop("figure_meta"); args2["require_caption"] = False
        result2 = m.execute(Namespace(command="attach-layout", **args2))
        self.assertEqual(result2["status"], "A4_GEOMETRY_PASS_NEEDS_WORD_VISUAL_REVIEW")


if __name__ == "__main__":
    unittest.main()