#!/usr/bin/env python3
"""Engineering-drawing quality gate for technical-visual-assets v1.4.0.

This tool checks what can be checked mechanically:
  geometry, orthogonality, node collisions, branch labels, A4 bounds,
  bilingual caption metadata, SVG/drawio integrity and catalog linkage.

It deliberately does NOT claim that technical logic or visual appearance is
correct.  Those require a human semantic + Word/WPS page review, and the report
always says so.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import orthogonal_router as router
import visio_diagram as vd

SVG = "http://www.w3.org/2000/svg"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
CAP_ZH = re.compile(r"^\s*图\s*(\d+(?:-\d+)+)\s*(\S.+)?$")
CAP_EN = re.compile(r"^\s*Fig\.?\s*(\d+(?:-\d+)+)\s*(\S.+)?$", re.I)


def _issue(bucket, code, msg, severity="error"):
    bucket.append({"code": code, "severity": severity, "message": msg})


def _label_boxes(spec):
    boxes = []
    for e in spec.get("edges", []):
        pos = e.get("label_pos")
        if pos:
            # place_label stores the label centre; convert to a top-left box.
            box = {"x": pos["x"] - pos["w"] / 2.0,
                   "y": pos["y"] - pos["h"] / 2.0,
                   "w": pos["w"], "h": pos["h"]}
            boxes.append((e.get("from"), e.get("to"), str(e.get("label", "")), box))
    return boxes


def _box_overlaps_rect(box, rect):
    return (box["x"] < rect[0] + rect[2] - 0.1 and
            box["x"] + box["w"] > rect[0] + 0.1 and
            box["y"] < rect[1] + rect[3] - 0.1 and
            box["y"] + box["h"] > rect[1] + 0.1)


def check_spec(spec, profile=None, require_caption=True, formal=True,
               max_crossings=0, max_bends=8):
    issues, warnings = [], []
    try:
        routed, w, h, font, coords = vd.prepare_spec(
            spec, profile, require_caption=require_caption)
    except (ValueError, KeyError) as exc:
        _issue(issues, "GEOMETRY_OR_CAPTION_BLOCK", str(exc))
        return None, issues, warnings
    # 1. orthogonal + node collision + endpoint boundary
    for msg in router.audit_routing(routed):
        _issue(issues, "ORTHOGONAL_OR_COLLISION", msg)
    # 2. decision branch labels
    for msg in router.decision_branch_issues(routed):
        _issue(issues, "DECISION_BRANCH_LABEL", msg)
    # 3. crossing count
    crossings = router.count_crossings(routed)
    if crossings > max_crossings:
        _issue(warnings, "EDGE_CROSSING", f"存在 {crossings} 处非共享端点交叉（上限 {max_crossings}）", "warning")
    # 4. bends per edge
    for e in routed.get("edges", []):
        pts = e.get("points") or []
        if len(pts) - 2 > max_bends:
            _issue(warnings, "TOO_MANY_BENDS",
                   f"{e.get('from')}->{e.get('to')} 有 {len(pts)-2} 个转折（上限 {max_bends}）", "warning")
    # 5. edge label boxes must not sit inside a node
    node_rects = [(n["id"], (n["x"], n["y"], n["w"], n["h"])) for n in routed["nodes"]]
    for a, b, text, box in _label_boxes(routed):
        for nid, rect in node_rects:
            if _box_overlaps_rect(box, rect):
                _issue(issues, "LABEL_INSIDE_NODE",
                       f"分支标签 {text!r} ({a}->{b}) 与节点 {nid} 重叠")
    # 6. source-backed technical facts
    refs = spec.get("source_refs") or []
    if formal:
        if not refs:
            _issue(issues, "MISSING_SOURCE_REFS", "正式技术图缺少 source_refs（章节/行号/证据）")
        else:
            for i, r in enumerate(refs):
                if not isinstance(r, dict) or not r.get("section") or not r.get("lines"):
                    _issue(issues, "INVALID_SOURCE_REFS", f"source_refs[{i}] 缺少 section 或 lines")
    # 7. caption metadata
    cap = vd.validate_caption(routed, require=require_caption)
    if require_caption and not cap:
        _issue(issues, "MISSING_CAPTION", "缺少中英文图题元数据")
    if cap:
        if cap.get("semantic_check") == "heuristic-mismatch":
            _issue(warnings, "CAPTION_SEMANTIC_WARNING",
                   "英文图题与中文图题未命中同一技术关键词；必须人工核对语义", "warning")
        if cap.get("figure_number") and spec.get("figure_number") and \
                cap["figure_number"] != str(spec["figure_number"]):
            _issue(issues, "CAPTION_NUMBER_MISMATCH", "图号与源 spec 不一致")
    # 8. A4 geometry
    geometry = {"width_mm": w, "height_mm": h, "font_pt": font}
    if profile:
        if w > profile["figure_max_width_mm"] or h > profile["figure_max_height_mm"]:
            _issue(issues, "A4_OVERFLOW", "图形超出版心")
    return {
        "routed_spec": routed,
        "geometry": geometry,
        "crossings": crossings,
        "caption": cap,
        "source_refs": refs,
        "node_count": len(routed["nodes"]),
        "edge_count": len(routed.get("edges", [])),
    }, issues, warnings


def check_svg(svg_path, routed):
    issues, warnings = [], []
    try:
        root = ET.fromstring(Path(svg_path).read_bytes())
    except (OSError, ET.ParseError) as exc:
        _issue(issues, "SVG_PARSE_FAIL", str(exc))
        return {}, issues, warnings
    if not root.tag.endswith("svg"):
        _issue(issues, "SVG_ROOT", "根元素不是 svg")
    width = root.attrib.get("width", "")
    height = root.attrib.get("height", "")
    if not width.endswith("mm") or not height.endswith("mm"):
        _issue(issues, "SVG_UNIT", "SVG 未显式声明毫米宽高")
    polylines = root.findall(f".//{{{SVG}}}polyline")
    for i, pl in enumerate(polylines, 1):
        pts = []
        for pair in pl.attrib.get("points", "").split():
            try:
                x, y = pair.split(",")
                pts.append((float(x), float(y)))
            except ValueError:
                _issue(issues, "SVG_POLYLINE", f"第 {i} 条折线点格式非法")
                break
        if len(pts) >= 2 and not router.is_orthogonal(pts):
            _issue(issues, "SVG_DIAGONAL", f"第 {i} 条连接线包含斜线")
        if pl.attrib.get("marker-end") != "url(#arrow)":
            _issue(issues, "SVG_ARROW", f"第 {i} 条连接线缺少箭头")
        if not pl.attrib.get("data-from") or not pl.attrib.get("data-to"):
            _issue(issues, "SVG_EDGE_META", f"第 {i} 条连接线缺少来源/目标元数据")
    if len(polylines) != len(routed.get("edges", [])):
        _issue(issues, "SVG_EDGE_COUNT", "SVG 连接线数量与 spec 不一致")
    title = root.find(f"{{{SVG}}}title")
    desc = root.find(f"{{{SVG}}}desc")
    if title is None or not (title.text or "").strip():
        _issue(issues, "SVG_CAPTION_TITLE", "SVG 缺少 <title> 图题元数据")
    if desc is None or not (desc.text or "").strip():
        _issue(issues, "SVG_CAPTION_DESC", "SVG 缺少 <desc> 英文图题元数据")
    return {"polyline_count": len(polylines), "width": width, "height": height}, issues, warnings


def check_drawio(path):
    issues, warnings = [], []
    try:
        root = ET.fromstring(Path(path).read_bytes())
    except (OSError, ET.ParseError) as exc:
        _issue(issues, "DRAWIO_PARSE_FAIL", str(exc))
        return {}, issues, warnings
    if root.tag != "mxfile":
        _issue(issues, "DRAWIO_ROOT", "根元素不是 mxfile")
    diagrams = root.findall("diagram")
    edges = root.findall(".//mxCell[@edge='1']")
    for i, e in enumerate(edges, 1):
        style = e.attrib.get("style", "")
        if "orthogonalEdgeStyle" not in style:
            _issue(issues, "DRAWIO_EDGE_STYLE", f"第 {i} 条连线未使用 orthogonalEdgeStyle")
        if not e.attrib.get("source") or not e.attrib.get("target"):
            _issue(issues, "DRAWIO_EDGE_ENDPOINT", f"第 {i} 条连线缺少 source/target")
    if not diagrams:
        _issue(issues, "DRAWIO_DIAGRAM", "缺少 diagram 节点")
    return {"edge_count": len(edges), "diagram_count": len(diagrams)}, issues, warnings


def check_catalog(catalog_path, res_id, svg_path, drawio_path):
    issues, warnings = [], []
    try:
        data = json.loads(Path(catalog_path).read_text("utf-8"))
        items = data.get("items") or data.get("resources") or []
        item = next((x for x in items if x.get("id") == res_id), None)
    except (OSError, json.JSONDecodeError) as exc:
        _issue(issues, "CATALOG_PARSE_FAIL", str(exc))
        return {}, issues, warnings
    if not item:
        _issue(issues, "CATALOG_ITEM_MISSING", f"目录中找不到 {res_id}")
        return {}, issues, warnings
    for key, path in (("print_svg", svg_path), ("editable_drawio", drawio_path)):
        if item.get(key) and Path(item[key]).name != Path(path).name:
            _issue(warnings, "CATALOG_PATH_MISMATCH",
                   f"{key} 目录记录与当前文件不同：{item[key]} vs {path}", "warning")
    if item.get("a4_layout_status") not in (None, "geometry-pass-pending-Word-page-review"):
        _issue(warnings, "CATALOG_A4_STATUS", f"目录 A4 状态为 {item.get('a4_layout_status')}", "warning")
    return {"res_id": res_id, "catalog_status": item.get("a4_layout_status")}, issues, warnings


def check_vsdx(path):
    """Structural VSDX check; never claims Visio opened the file."""
    import vsdx_writer
    report = vsdx_writer.validate_vsdx(path)
    issues = []
    if report.get("status") != "STRUCTURALLY_VALID_VSDX":
        issues.append({"code": "VSDX_STRUCTURE", "severity": "error",
                       "message": "；".join(report.get("issues", [])) or "VSDX 结构无效"})
    return report, issues


def caption_audit_docx(docx_path):
    """Check each inline image has Chinese + English captions below it."""
    issues, warnings = [], []
    try:
        with ZipFile(docx_path) as z:
            xml = z.read("word/document.xml")
        root = ET.fromstring(xml)
    except (OSError, KeyError, ET.ParseError) as exc:
        return {"status": "BLOCK", "issues": [{"code": "DOCX_PARSE_FAIL", "message": str(exc)}]}
    ns = {"w": W, "wp": WP}
    body = root.find("w:body", ns)
    if body is None:
        return {"status": "BLOCK", "issues": [{"code": "DOCX_BODY", "message": "缺少 w:body"}]}
    paras = body.findall("w:p", ns)
    picture_paras = []
    for idx, p in enumerate(paras):
        if p.findall(".//wp:inline", ns) or p.findall(".//wp:anchor", ns):
            picture_paras.append(idx)
    captions = []
    for idx, p in enumerate(paras):
        text = "".join(t.text or "" for t in p.findall(".//w:t", ns)).strip()
        if not text:
            continue
        mz, me = CAP_ZH.match(text), CAP_EN.match(text)
        if mz or me:
            jc = p.find("w:pPr/w:jc", ns)
            captions.append({
                "paragraph": idx, "text": text,
                "kind": "zh" if mz else "en",
                "number": (mz or me).group(1),
                "body": (mz or me).group(2) or "",
                "centered": jc is not None and jc.attrib.get("{%s}val" % W) == "center",
            })
    for i, pidx in enumerate(picture_paras, 1):
        after = [c for c in captions if c["paragraph"] > pidx]
        zh = next((c for c in after if c["kind"] == "zh"), None)
        en = next((c for c in after if c["kind"] == "en"), None)
        if not zh:
            _issue(issues, "DOCX_CAPTION_ZH_MISSING", f"第 {i} 张图下方缺少中文图题")
        if not en:
            _issue(issues, "DOCX_CAPTION_EN_MISSING", f"第 {i} 张图下方缺少英文图题 (Fig. X-Y ...)")
        for c in (zh, en):
            if c and not c["centered"]:
                _issue(warnings, "DOCX_CAPTION_ALIGN", f"图题未居中：{c['text']}", "warning")
            if c and zh and en and c["number"] != zh["number"]:
                _issue(issues, "DOCX_CAPTION_NUMBER", "中英文图号不一致")
    return {
        "status": "PASS" if not issues else "FAIL",
        "picture_count": len(picture_paras),
        "captions": captions,
        "issues": issues,
        "warnings": warnings,
        "notice": "图题分页是否与图片同页、是否压页脚，仍需 Word/WPS 实际渲染检查。",
    }


def main():
    ap = argparse.ArgumentParser(description="技术图正交/图题/A4 质量门禁")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--svg")
    ap.add_argument("--drawio")
    ap.add_argument("--template")
    ap.add_argument("--section", type=int, default=1)
    ap.add_argument("--catalog")
    ap.add_argument("--id")
    ap.add_argument("--docx")
    ap.add_argument("--vsdx")
    ap.add_argument("--json")
    ap.add_argument("--no-formal", action="store_true", help="allow specs without source_refs")
    ap.add_argument("--no-caption", action="store_true", help="allow figures without caption metadata")
    ap.add_argument("--max-crossings", type=int, default=0)
    args = ap.parse_args()
    issues, warnings = [], []
    try:
        spec = json.loads(Path(args.spec).read_text("utf-8"))
        profile = None
        if args.template:
            from a4_layout import inspect_template
            profile = inspect_template(args.template)["sections"][args.section - 1]
        result, i2, w2 = check_spec(
            spec, profile, require_caption=not args.no_caption,
            formal=not args.no_formal, max_crossings=args.max_crossings)
        issues += i2; warnings += w2
        if result and args.svg:
            r, i3, w3 = check_svg(args.svg, result["routed_spec"])
            result["svg"] = r; issues += i3; warnings += w3
        if args.drawio:
            r, i4, w4 = check_drawio(args.drawio)
            result["drawio"] = r if result else r
            issues += i4; warnings += w4
        if args.vsdx:
            r, i5v = check_vsdx(args.vsdx)
            if result is not None:
                result["vsdx"] = r
            issues += i5v
        if args.catalog and args.id and args.svg and args.drawio:
            r, i5, w5 = check_catalog(args.catalog, args.id, args.svg, args.drawio)
            if result:
                result["catalog"] = r
            issues += i5; warnings += w5
        if args.docx:
            r = caption_audit_docx(args.docx)
            if result is not None:
                result["docx_caption_audit"] = r
            issues += [dict(x, severity="error") for x in r.get("issues", [])]
            warnings += r.get("warnings", [])
        status = "FAIL" if issues else "PASS_GEOMETRY_NEEDS_SEMANTIC_AND_VISUAL_REVIEW"
        out = {
            "status": status,
            "issues": issues,
            "warnings": warnings,
            "semantic_review_required": True,
            "visual_review_required": True,
            "notice": "程序只能证明几何与元数据；技术逻辑、英文图题语义、Word 分页与实际视觉效果必须人工复核。",
        }
        if result:
            out.update({k: v for k, v in result.items() if k != "routed_spec"})
        if args.json:
            Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if status.startswith("PASS") else 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCK", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())