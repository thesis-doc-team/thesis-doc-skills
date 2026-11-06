#!/usr/bin/env python3
"""Offline Visio-LIKE printable diagrams (SVG + editable .drawio), stdlib.

v1.4.0 changes
--------------
* every connector is routed by ``orthogonal_router`` (H/V only);
* explicit diagonal points are re-routed, never emitted as-is;
* branch labels are placed beside a clear segment with a white backing box;
* Chinese + English captions live in metadata, not in the image pixels;
* A4 geometry, node overlap, edge-through-node and caption gates run before
  any file is written.

A structural native .vsdx is written by vsdx_writer.py; actual Visio opening is marked pending unless verified.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import orthogonal_router as router
import subgraph_layout
import vsdx_writer

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
MM_PT = 25.4 / 72
SHAPES = {"rect": "rectangle", "diamond": "rhombus", "pill": "rounded"}
GENERIC_EN = {"flowchart", "flow", "chart", "diagram", "figure", "system",
              "process", "processing", "graph", "schematic"}
GENERIC_ZH = {"流程图", "系统图", "示意图", "框图", "图", "系统框图"}

# Weak, auditable Chinese→English domain hints.  They are a warning aid, not a
# claim that semantic accuracy has been proven; a human visual review is still
# mandatory.
SEMANTIC_HINTS = [
    (("报警", "告警"), ("alarm", "alert", "warning"), False),
    (("阈值",), ("threshold", "limit"), False),
    (("采集",), ("acquisition", "collection", "sampling", "collect"), False),
    (("上传", "传输", "发送"), ("upload", "transmission", "sending", "send"), False),
    (("初始化", "上电", "启动"), ("initialization", "startup", "power-on", "boot"), False),
    (("主循环",), ("main loop", "main-loop", "scheduling"), False),
    (("数据",), ("data",), False),
    (("通信", "短信"), ("communication", "sms", "messaging"), False),
    (("页面", "切换"), ("page", "switching"), False),
    (("存储",), ("storage", "database"), False),
    (("判断", "处理"), ("decision", "judgment", "processing"), False),
    (("功能",), ("functional", "function"), True),
    (("架构",), ("architecture",), True),
    (("流程",), ("flowchart", "flow", "process"), True),
    (("系统",), ("system",), True),
]


def number(value, field):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not -100000 < float(value) < 100000:
        raise ValueError("非法数值: " + field)
    return float(value)


def validate(spec, profile=None):
    """Structural + A4 + label-overflow validation (no routing side effects)."""
    if not isinstance(spec, dict):
        raise ValueError("JSON 顶层必须是对象")
    w = number(spec.get("width_mm"), "width_mm")
    h = number(spec.get("height_mm"), "height_mm")
    if w < 70 or w > 210 or h < 50 or h > 285:
        raise ValueError("图稿尺寸不适合 A4 版心；按逻辑拆图或改排布")
    font = number(spec.get("font_pt", 9.5), "font_pt")
    if font < 9.0:
        raise ValueError("图中文字不应小于9pt")
    if profile:
        if w > profile["figure_max_width_mm"] or h > profile["figure_max_height_mm"]:
            raise ValueError("超过实际 DOCX 版心可用尺寸，禁止强行缩小；调整布局或拆分图")
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    groups = spec.get("groups", [])
    if not nodes or len(nodes) > 65 or len(edges) > 100 or len(groups) > 20:
        raise ValueError("节点或连线数量异常：拆成多幅独立图")
    coords = {}
    for n in nodes:
        ident = n.get("id")
        label = n.get("label")
        if not isinstance(ident, str) or not re.fullmatch(r"[a-zA-Z][\w-]{0,40}", ident) or ident in coords:
            raise ValueError("非法或重复节点 ID")
        if n.get("shape", "rect") not in SHAPES:
            raise ValueError("不支持的节点类型")
        if not isinstance(label, str) or not label.strip() or len(label) > 90:
            raise ValueError("标签无效或过长")
        if re.search(r'<br\s*/?>|<[^>]+>', label):
            raise ValueError(f'节点 {ident} 标签含 HTML/<br/>；请使用真实换行，prepare_spec 会自动归一化')
        x = number(n.get("x"), "node.x")
        y = number(n.get("y"), "node.y")
        nw = number(n.get("w"), "node.w")
        nh = number(n.get("h"), "node.h")
        if nw < 13 or nh < 9 or x < 0 or y < 0 or x + nw > w or y + nh > h:
            raise ValueError(f"节点 {ident} 超出版心/尺寸过小")
        rows = label.replace("\\n", "\n").split("\n")
        if len(rows) > 4:
            raise ValueError(f"节点 {ident} 文字超过4行，应该拆分")
        # In a Chinese thesis, ideographic character width is near font's em;
        # keep a safety margin; exact typography must still be visually checked.
        for text in rows:
            units = sum(1 if ord(c) > 255 else .58 for c in text)
            if units * font * MM_PT > nw - 4:
                raise ValueError(f"节点 {ident} 标签可能溢出；增加框宽/手动换行，不允许缩成小字")
        if len(rows) * font * MM_PT * 1.32 > nh - 2:
            raise ValueError(f"节点 {ident} 高度不足以容纳文字")
        coords[ident] = (x, y, nw, nh)
    for i, g in enumerate(groups):
        for dim in ("x", "y", "w", "h"):
            number(g.get(dim), f"group.{dim}")
        if g["x"] < 0 or g["y"] < 0 or g["x"] + g["w"] > w or g["y"] + g["h"] > h:
            raise ValueError("分区超出图稿范围")
    for e in edges:
        if e.get("from") not in coords or e.get("to") not in coords:
            raise ValueError("连接包含不存在的节点")
        pts = e.get("points", [])
        if len(pts) > 24:
            raise ValueError("过多转折点：应重新布局或拆分图")
        for x, y in pts:
            if not 0 <= number(x, "edge.x") <= w or not 0 <= number(y, "edge.y") <= h:
                raise ValueError("连接点越界")
        if len(str(e.get("label", ""))) > 12:
            raise ValueError("边标签过长")
    return w, h, font, coords


def validate_caption(spec, require=False):
    """Validate figure number + bilingual caption metadata (never drawn)."""
    zh = str(spec.get("caption_zh") or "").strip()
    en = str(spec.get("caption_en") or "").strip()
    num = str(spec.get("figure_number") or "").strip()
    present = bool(zh or en or num)
    if not present:
        if require:
            raise ValueError("正式技术图必须提供 figure_number / caption_zh / caption_en；图题不得画进图片像素")
        return None
    if require and not (zh and en and num):
        raise ValueError("图题元数据不完整：figure_number、caption_zh、caption_en 必须同时提供")
    if num and not re.fullmatch(r"\d+(?:-\d+)+", num):
        raise ValueError("figure_number 必须按章节编号，例如 4-1 / 3-2")
    if zh:
        if len(zh) < 2 or len(zh) > 60:
            raise ValueError("caption_zh 长度应为 2–60 字")
        if zh in GENERIC_ZH:
            raise ValueError("caption_zh 过于笼统，必须描述实际图形内容")
    if en:
        words = re.findall(r"[A-Za-z][A-Za-z0-9-]*", en)
        if not words:
            raise ValueError("caption_en 必须包含英文描述")
        if en[0].islower():
            raise ValueError("caption_en 首字母应大写")
        if len(words) < 3 or all(w.lower() in GENERIC_EN for w in words):
            raise ValueError("caption_en 过于笼统，必须包含具体技术对象（如 Threshold Alarm / Data Acquisition）")
    semantic = "not-applicable"
    if zh and en:
        low = en.lower()
        strong_checked = strong_ok = False
        weak_checked = weak_ok = False
        for zh_tokens, en_tokens, weak in SEMANTIC_HINTS:
            if any(t in zh for t in zh_tokens):
                matched = any(t in low for t in en_tokens)
                if weak:
                    weak_checked = True
                    weak_ok = weak_ok or matched
                else:
                    strong_checked = True
                    strong_ok = strong_ok or matched
        if strong_checked:
            semantic = "heuristic-match" if strong_ok else "heuristic-mismatch"
        elif weak_checked:
            semantic = "heuristic-match" if weak_ok else "heuristic-mismatch"
    return {
        "figure_number": num,
        "caption_zh": zh,
        "caption_en": en,
        "caption_zh_full": (f"图 {num} {zh}".strip() if num else zh),
        "caption_en_full": (f"Fig. {num} {en}".strip() if num else en),
        "caption_position": "below",
        "semantic_check": semantic,
        "semantic_review_required": True,
    }


def prepare_spec(spec, profile=None, force_route=False, require_caption=False):
    """Validate, route every edge orthogonally, then re-validate the result."""
    spec = subgraph_layout.normalize_labels(spec)
    if spec.get('layout') == 'subgraph' or spec.get('auto_layout'):
        spec = subgraph_layout.layout(spec)
    w, h, font, coords = validate(spec, profile)
    routed = router.route_spec(spec, force=force_route)
    w, h, font, coords = validate(routed, profile)
    issues = router.audit_routing(routed)
    if issues:
        raise ValueError("正交布线审计失败：" + "；".join(issues))
    branch_issues = router.decision_branch_issues(routed)
    if branch_issues:
        raise ValueError("判断分支审计失败：" + "；".join(branch_issues))
    cap = validate_caption(routed, require=require_caption)
    routed["_routing"] = {
        "status": "orthogonal",
        "crossings": router.count_crossings(routed),
        "routes": [{"from": e["from"], "to": e["to"], "routing": e.get("routing")}
                   for e in routed.get("edges", [])],
    }
    routed["_caption"] = cap
    return routed, w, h, font, coords


def _text_svg(parent, x, y, value, font, style="normal", **extra):
    attrs = {
        "x": str(x), "y": str(y), "text-anchor": "middle",
        "dominant-baseline": "middle", "font-size": str(round(font * MM_PT, 3)),
        "font-family": "SimSun,'Noto Serif CJK SC','Microsoft YaHei',serif",
        "font-weight": style, "fill": "#111"}
    attrs.update({str(k).replace("_", "-"): str(v) for k, v in extra.items()})
    t = ET.SubElement(parent, f"{{{SVG}}}text", attrs)
    t.text = value


def svg_diagram(spec, output, profile=None, force_route=False, require_caption=False):
    spec, w, h, font, coords = prepare_spec(
        spec, profile, force_route=force_route, require_caption=require_caption)
    cap = spec.get("_caption") or {}
    root = ET.Element(f"{{{SVG}}}svg", {
        "width": f"{w}mm", "height": f"{h}mm", "viewBox": f"0 0 {w} {h}",
        "role": "img",
        "aria-label": cap.get("caption_zh_full") or "依据正式技术MD生成的正交工程图",
        "data-figure-number": cap.get("figure_number", ""),
        "data-caption-zh": cap.get("caption_zh", ""),
        "data-caption-en": cap.get("caption_en", ""),
        "data-caption-position": "below" if cap else "",
    })
    title = ET.SubElement(root, f"{{{SVG}}}title")
    title.text = cap.get("caption_zh_full") or "技术图"
    desc = ET.SubElement(root, f"{{{SVG}}}desc")
    desc.text = cap.get("caption_en_full") or "Orthogonal engineering diagram generated from the technical Markdown."
    defs = ET.SubElement(root, f"{{{SVG}}}defs")
    marker = ET.SubElement(defs, f"{{{SVG}}}marker", {
        "id": "arrow", "markerWidth": "7", "markerHeight": "7",
        "refX": "6", "refY": "3", "orient": "auto", "markerUnits": "strokeWidth"})
    ET.SubElement(marker, f"{{{SVG}}}path", {"d": "M0,0 L6,3 L0,6 z", "fill": "#222"})
    ET.SubElement(root, f"{{{SVG}}}rect", {"width": str(w), "height": str(h), "fill": "#fff"})
    for g in spec.get("groups", []):
        # Partition frames must be dashed and (for complex diagrams) carry a
        # very light fill so node/edge lines do not visually merge with the
        # frame.  Labels get a white backing box so lines cannot cut the text.
        ET.SubElement(root, f"{{{SVG}}}rect", {
            "x": str(g["x"]), "y": str(g["y"]), "width": str(g["w"]), "height": str(g["h"]),
            "fill": str(g.get("fill") or "#F7F8FC"),
            "fill-opacity": str(g.get("fill_opacity", "0.55")),
            "stroke": "#4b4b4b", "stroke-width": "0.24",
            "stroke-dasharray": "2.2,1.35", "data-group": "1"})
        if g.get("label"):
            label = str(g["label"])
            fs = font * MM_PT
            tw = max(6.0, len(label) * fs * 0.62 + 2.0)
            th = fs * 1.8
            cx = g["x"] + g["w"] / 2.0
            cy = g["y"] + 3.0
            ET.SubElement(root, f"{{{SVG}}}rect", {
                "x": str(round(cx - tw / 2, 3)), "y": str(round(cy - th / 2, 3)),
                "width": str(round(tw, 3)), "height": str(round(th, 3)),
                "fill": "#fff", "stroke": "none", "data-group-label-bg": "1"})
            _text_svg(root, cx, cy, label, font, data_group_label="1")
    for e in spec.get("edges", []):
        p = e.get("points") or []
        if len(p) < 2:
            raise ValueError("一条边至少需要起止两个点")
        points = " ".join(f"{x},{y}" for x, y in p)
        ET.SubElement(root, f"{{{SVG}}}polyline", {
            "points": points, "fill": "none", "stroke": "#222",
            "stroke-width": "0.38", "stroke-linejoin": "miter",
            "marker-end": "url(#arrow)", "data-from": str(e["from"]),
            "data-to": str(e["to"]), "data-routing": str(e.get("routing", ""))})
        if e.get("label"):
            pos = e.get("label_pos") or {}
            lx = float(pos.get("x", p[0][0] + 3))
            ly = float(pos.get("y", p[0][1] - 2))
            lw = float(pos.get("w", max(6, len(str(e["label"])) * font * MM_PT * 0.7)))
            lh = float(pos.get("h", font * MM_PT * 1.8))
            ET.SubElement(root, f"{{{SVG}}}rect", {
                "x": str(round(lx - lw / 2, 3)), "y": str(round(ly - lh / 2, 3)),
                "width": str(round(lw, 3)), "height": str(round(lh, 3)),
                "fill": "#fff", "stroke": "none", "data-label-bg": "1"})
            _text_svg(root, lx, ly, str(e["label"]), max(9, font - 0.4),
                      data_edge_label="1")
    for n in spec["nodes"]:
        x, y, nw, nh = coords[n["id"]]
        shape = n.get("shape", "rect")
        common = {"fill": "#fff", "stroke": "#2b2b2b", "stroke-width": "0.35",
                  "data-node-id": n["id"], "data-shape": shape}
        if shape == "diamond":
            ET.SubElement(root, f"{{{SVG}}}polygon", dict(
                common, points=(f"{x + nw / 2},{y} {x + nw},{y + nh / 2} "
                                f"{x + nw / 2},{y + nh} {x},{y + nh / 2}")))
        else:
            props = dict(common, x=str(x), y=str(y), width=str(nw), height=str(nh))
            if shape == "pill":
                props["rx"] = str(nh / 2)
            ET.SubElement(root, f"{{{SVG}}}rect", props)
        rows = n["label"].replace("\\n", "\n").split("\n")
        for ix, line in enumerate(rows):
            yy = y + nh / 2 + (ix - (len(rows) - 1) / 2) * font * MM_PT * 1.3
            _text_svg(root, x + nw / 2, yy, line, font)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    return output


def drawio_diagram(spec, output, profile=None, force_route=False, require_caption=False):
    spec, w, h, font, coords = prepare_spec(
        spec, profile, force_route=force_route, require_caption=require_caption)
    cap = spec.get("_caption") or {}
    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "modified": "", "type": "device",
                                   "data-caption-en": cap.get("caption_en", "")})
    diagram = ET.SubElement(mxfile, "diagram", {
        "name": cap.get("caption_zh") or "A4-orthogonal-diagram", "id": "thesis-a4"})
    model = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "900", "dy": "700", "grid": "1", "gridSize": "10", "page": "1",
        "pageScale": "1", "pageWidth": str(round(w * 3.77953)),
        "pageHeight": str(round(h * 3.77953)), "math": "0", "shadow": "0"})
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    k = 3.77953  # mm to diagram editor pixels
    for i, g in enumerate(spec.get("groups", []), 1):
        cell = ET.SubElement(root, "mxCell", {
            "id": f"g{i}", "value": g.get("label", ""),
            "style": ("rounded=0;whiteSpace=wrap;html=0;dashed=1;dashPattern=5 4;"
                      "fillColor=#F7F8FC;opacity=55;strokeColor=#555555;"
                      "fontFamily=SimSun;fontSize=9;"),
            "vertex": "1", "parent": "1"})
        ET.SubElement(cell, "mxGeometry", {
            "x": str(g["x"] * k), "y": str(g["y"] * k),
            "width": str(g["w"] * k), "height": str(g["h"] * k), "as": "geometry"})
    for n in spec["nodes"]:
        x, y, nw, nh = coords[n["id"]]
        shape = n.get("shape", "rect")
        style = ("rounded=0;whiteSpace=wrap;html=0;fillColor=#FFFFFF;strokeColor=#222222;"
                 "strokeWidth=1;")
        if shape == "diamond":
            style += "shape=rhombus;"
        if shape == "pill":
            style += "rounded=1;arcSize=50;"
        style += (f"fontFamily=SimSun;fontSize={font};fontColor=#111111;"
                  "align=center;verticalAlign=middle;")
        cell = ET.SubElement(root, "mxCell", {
            "id": n["id"], "value": n["label"].replace("\\n", "\n"),
            "style": style, "vertex": "1", "parent": "1"})
        ET.SubElement(cell, "mxGeometry", {
            "x": str(x * k), "y": str(y * k), "width": str(nw * k),
            "height": str(nh * k), "as": "geometry"})
    for i, e in enumerate(spec.get("edges", []), 1):
        cell = ET.SubElement(root, "mxCell", {
            "id": f"edge{i}", "value": e.get("label", ""),
            "style": ("edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
                      "jettySize=auto;html=0;endArrow=classic;strokeColor=#222222;"
                      "fontFamily=SimSun;fontSize=9;labelBackgroundColor=#FFFFFF;"),
            "edge": "1", "parent": "1", "source": e["from"], "target": e["to"]})
        geom = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        pts = e.get("points", [])[1:-1]
        if pts:
            arr = ET.SubElement(geom, "Array", {"as": "points"})
            for x, y in pts:
                ET.SubElement(arr, "mxPoint", {"x": str(x * k), "y": str(y * k)})
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(mxfile).write(output, encoding="utf-8", xml_declaration=True)
    return output


def figure_metadata(spec, svg, drawio, profile=None, vsdx=None):
    cap = spec.get("_caption") or validate_caption(spec, require=False) or {}
    routing = spec.get("_routing") or {}
    return {
        "schema": "tva-figure-meta/1.0",
        "figure_number": cap.get("figure_number", ""),
        "caption_zh": cap.get("caption_zh", ""),
        "caption_en": cap.get("caption_en", ""),
        "caption_zh_full": cap.get("caption_zh_full", ""),
        "caption_en_full": cap.get("caption_en_full", ""),
        "caption_position": "below",
        "semantic_check": cap.get("semantic_check", "missing"),
        "semantic_review_required": True,
        "routing": routing.get("status", "unknown"),
        "crossings": routing.get("crossings"),
        "geometry_mm": [float(spec["width_mm"]), float(spec["height_mm"])],
        "font_pt": float(spec.get("font_pt", 9.5)),
        "svg": str(svg),
        "editable_drawio": str(drawio),
        "print_vsdx": (vsdx.get("path") if isinstance(vsdx, dict) else (str(vsdx) if vsdx else None)),
        "native_visio_vsdx": bool(vsdx),
        "vsdx_verification": ((vsdx or {}).get("visio_open_verification") if isinstance(vsdx, dict) else ("pending-visio-open" if vsdx else None)),
        "review_status": "pending-semantic-and-Word-page-review",
        "notice": "正交几何与 VSDX 包结构已由程序审计；Visio 实际打开、图题语义、Word 分页与视觉效果必须人工复核。",
    }


def main():
    ap = argparse.ArgumentParser(description="离线生成正交 SVG + draw.io + 原生 VSDX；Visio 打开验证状态如实标注")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--template")
    ap.add_argument("--section", type=int, default=1)
    ap.add_argument("--force-route", action="store_true",
                    help="ignore orthogonal explicit points and re-route every edge")
    ap.add_argument("--require-caption", action="store_true", default=True,
                    help="require figure_number/caption_zh/caption_en (default: on)")
    ap.add_argument("--no-require-caption", dest="require_caption", action="store_false")
    ap.add_argument("--vsdx", dest="vsdx", action="store_true", default=True,
                    help="同时生成原生 VSDX（默认开启）")
    ap.add_argument("--no-vsdx", dest="vsdx", action="store_false")
    ap.add_argument("--auto-layout", dest="auto_layout", action="store_true",
                    help="按 groups/成员自动重排子图与节点，再正交布线")
    args = ap.parse_args()
    try:
        spec = json.loads(Path(args.spec).read_text("utf-8"))
        if args.auto_layout:
            spec['auto_layout'] = True
        sec = None
        if args.template:
            from a4_layout import inspect_template
            sec = inspect_template(args.template)["sections"][args.section - 1]
        prefix = Path(args.out_prefix)
        svg = svg_diagram(spec, prefix.with_suffix(".svg"), sec,
                          force_route=args.force_route,
                          require_caption=args.require_caption)
        drawio = drawio_diagram(spec, prefix.with_suffix(".drawio"), sec,
                                force_route=args.force_route,
                                require_caption=args.require_caption)
        # Re-prepare for metadata (deterministic; also catches a stale spec file).
        routed, w, h, font, coords = prepare_spec(
            spec, sec, force_route=args.force_route,
            require_caption=args.require_caption)
        vsdx_report = None
        if args.vsdx:
            vsdx_report = vsdx_writer.write_vsdx(routed, prefix.with_suffix('.vsdx'))
            if vsdx_report.get('status') != 'STRUCTURALLY_VALID_VSDX':
                raise ValueError('VSDX 结构校验失败：' + '；'.join(vsdx_report.get('issues', [])))
        meta = figure_metadata(routed, svg, drawio, sec, vsdx_report)
        meta_path = prefix.with_suffix(".figure.json")
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        result = dict(meta)
        result.update({"status": "DRAWN_ORTHOGONAL_NEEDS_SEMANTIC_AND_WORD_REVIEW",
                       "meta": str(meta_path),
                       "vsdx": str(prefix.with_suffix('.vsdx')) if args.vsdx else None,
                       "font_pt": font,
                       "notice": "输出为可编辑 drawio + 正交 SVG + 原生 VSDX；VSDX 打开验证状态见 vsdx_verification，图题未画进图片。"})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, IndexError, json.JSONDecodeError) as e:
        print(json.dumps({"status": "BLOCK", "reason": str(e)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())