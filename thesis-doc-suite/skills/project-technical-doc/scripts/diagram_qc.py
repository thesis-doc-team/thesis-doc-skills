#!/usr/bin/env python3
"""Visual/geometry QC for rendered Mermaid/Graphviz SVG diagrams.

Catches the four real failure modes from user screenshots:
  1. diagram too wide for A4 / text shrinks below readable size;
  2. detached/broken connector endpoints;
  3. overlapping Chinese labels;
  4. overlapping nodes / crowded layout.

This is a *mechanical* gate. It cannot prove semantic correctness or replace
human visual review; it blocks the obvious "rendered but unusable" cases.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from bs4 import BeautifulSoup

MIN_FONT_PX = 9.0
NOMINAL_WIDTH_PX = 1080.0
MAX_ASPECT = 10.0
WARN_ASPECT = 6.0
NODE_OVERLAP_RATIO = 0.18
TEXT_OVERLAP_RATIO = 0.18
EDGE_TOLERANCE_PX = 18.0
MIN_NODE_AREA = 120.0


def _num(v, default=0.0):
    try:
        return float(str(v).replace('px', '').strip())
    except (TypeError, ValueError):
        return default


def _mat_mul(a, b):
    return (
        a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1],
        a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3],
        a[0] * b[4] + a[2] * b[5] + a[4],
        a[1] * b[4] + a[3] * b[5] + a[5],
    )


def _parse_transform(text):
    m = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    if not text:
        return m
    for name, args in re.findall(r'(\w+)\s*\(([^)]*)\)', str(text)):
        vals = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', args)]
        if not vals:
            continue
        if name == 'translate':
            tx = vals[0]
            ty = vals[1] if len(vals) > 1 else 0.0
            m = _mat_mul(m, (1, 0, 0, 1, tx, ty))
        elif name == 'scale':
            sx = vals[0]
            sy = vals[1] if len(vals) > 1 else sx
            m = _mat_mul(m, (sx, 0, 0, sy, 0, 0))
        elif name == 'matrix' and len(vals) >= 6:
            m = _mat_mul(m, tuple(vals[:6]))
        elif name == 'rotate':
            ang = math.radians(vals[0])
            c, s = math.cos(ang), math.sin(ang)
            r = (c, s, -s, c, 0, 0)
            if len(vals) >= 3:
                cx, cy = vals[1], vals[2]
                r = _mat_mul((1, 0, 0, 1, cx, cy), _mat_mul(r, (1, 0, 0, 1, -cx, -cy)))
            m = _mat_mul(m, r)
    return m


def _element_matrix(el):
    chain = []
    for p in [el] + list(el.parents):
        chain.append(_parse_transform(p.get('transform')))
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for part in reversed(chain):
        m = _mat_mul(m, part)
    return m


def _apply(m, x, y):
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def _transform_bbox(m, bbox):
    x, y, w, h = bbox
    pts = [_apply(m, x, y), _apply(m, x + w, y), _apply(m, x, y + h),
           _apply(m, x + w, y + h)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _inside_ignored(el):
    for p in el.parents:
        name = getattr(p, 'name', '')
        if name in ('defs', 'marker', 'clippath', 'pattern', 'symbol'):
            return True
    return False


def _shape_bbox(el):
    name = el.name
    if name == 'rect':
        return (_num(el.get('x')), _num(el.get('y')),
                _num(el.get('width')), _num(el.get('height')))
    if name == 'ellipse':
        cx, cy = _num(el.get('cx')), _num(el.get('cy'))
        rx, ry = _num(el.get('rx')), _num(el.get('ry'))
        return (cx - rx, cy - ry, 2 * rx, 2 * ry)
    if name == 'circle':
        cx, cy, r = _num(el.get('cx')), _num(el.get('cy')), _num(el.get('r'))
        return (cx - r, cy - r, 2 * r, 2 * r)
    if name == 'polygon':
        pts = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', el.get('points', ''))]
        if len(pts) < 6:
            return None
        xs, ys = pts[0::2], pts[1::2]
        return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    return None


def _center(b):
    return b[0] + b[2] / 2.0, b[1] + b[3] / 2.0


def _overlap(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[0] + a[2], b[0] + b[2]); y2 = min(a[1] + a[3], b[1] + b[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def _near_bbox(pt, bbox, tol=EDGE_TOLERANCE_PX):
    x, y = pt
    bx, by, bw, bh = bbox
    dx = max(bx - x, 0, x - (bx + bw))
    dy = max(by - y, 0, y - (by + bh))
    return math.hypot(dx, dy) <= tol


def _node_boxes(soup):
    """One outer box per node group; ignore nested label backgrounds."""
    groups = {}
    for el in soup.find_all(['rect', 'ellipse', 'circle', 'polygon']):
        if _inside_ignored(el):
            continue
        b = _shape_bbox(el)
        if not b or b[2] < 8 or b[3] < 6 or b[2] * b[3] < MIN_NODE_AREA:
            continue
        m = _element_matrix(el)
        b = _transform_bbox(m, b)
        if b[2] < 8 or b[3] < 6:
            continue
        group = None
        for p in el.parents:
            cls = ' '.join(p.get('class') or [])
            if 'node' in cls or 'cluster' in cls:
                group = id(p)
                break
        key = group or id(el)
        if key not in groups or b[2] * b[3] > groups[key][2] * groups[key][3]:
            groups[key] = b
    return list(groups.values())


def _text_boxes(soup):
    out = []
    for el in soup.find_all('text'):
        if _inside_ignored(el):
            continue
        text = ' '.join(el.get_text(' ', strip=True).split())
        if not text:
            continue
        size = _num(el.get('font-size'), 12.0)
        x, y = _num(el.get('x')), _num(el.get('y'))
        anchor = el.get('text-anchor') or 'start'
        width = sum(1.0 if ord(ch) > 255 else 0.58 for ch in text) * size
        height = size * 1.2
        if anchor == 'middle':
            x -= width / 2.0
        elif anchor == 'end':
            x -= width
        y -= height * 0.8
        m = _element_matrix(el)
        out.append((text, _transform_bbox(m, (x, y, width, height)), size))
    return out


def _path_points(d):
    """Return start/end points from a path 'd' (supports M/L/C absolute/relative)."""
    tokens = re.findall(r'([MLCQmlcqZz])|(-?\d+(?:\.\d+)?)', d or '')
    cmd = None
    vals = []
    pts = []
    cur = (0.0, 0.0)

    def flush():
        nonlocal cur, vals
        if cmd in ('M', 'L', 'm', 'l') and len(vals) >= 2:
            x, y = vals[0], vals[1]
            if cmd.islower():
                cur = (cur[0] + x, cur[1] + y)
            else:
                cur = (x, y)
            pts.append(cur)
        elif cmd in ('C', 'c') and len(vals) >= 6:
            x, y = vals[-2], vals[-1]
            if cmd.islower():
                cur = (cur[0] + x, cur[1] + y)
            else:
                cur = (x, y)
            pts.append(cur)
        elif cmd in ('Q', 'q') and len(vals) >= 4:
            x, y = vals[-2], vals[-1]
            if cmd.islower():
                cur = (cur[0] + x, cur[1] + y)
            else:
                cur = (x, y)
            pts.append(cur)
        vals = []

    for c, v in tokens:
        if c:
            flush()
            cmd = c
        elif v:
            vals.append(float(v))
    flush()
    return pts


def _edge_paths(soup):
    out = []
    for el in soup.find_all('path'):
        if _inside_ignored(el):
            continue
        marker = el.get('marker-end') or ''
        cls = ' '.join(el.get('class') or [])
        if not marker and 'edge' not in cls and 'flowchart-link' not in cls:
            continue
        pts = _path_points(el.get('d'))
        if len(pts) < 2:
            continue
        m = _element_matrix(el)
        out.append((_apply(m, *pts[0]), _apply(m, *pts[-1]), marker,
                    el.get('stroke-dasharray')))
    return out


def check_svg(svg_text, page_css='', nominal_width_px=NOMINAL_WIDTH_PX,
              min_font_px=MIN_FONT_PX):
    errors, warnings = [], []
    try:
        soup = BeautifulSoup(svg_text, 'html.parser')
    except Exception as exc:  # noqa: BLE001
        return {'status': 'FAIL', 'errors': [f'SVG 无法解析：{exc}'],
                'warnings': [], 'metrics': {}}
    root = soup.find('svg')
    if root is None:
        return {'status': 'FAIL', 'errors': ['缺少 svg 根元素'], 'warnings': [], 'metrics': {}}
    vb = (root.get('viewBox') or root.get('viewbox') or '').split()
    if len(vb) != 4:
        return {'status': 'FAIL', 'errors': ['SVG 缺少 viewBox，无法量测'], 'warnings': [], 'metrics': {}}
    vb_w, vb_h = float(vb[2]), float(vb[3])
    if vb_w <= 0 or vb_h <= 0:
        return {'status': 'FAIL', 'errors': ['SVG viewBox 尺寸非法'], 'warnings': [], 'metrics': {}}
    nodes = _node_boxes(soup)
    texts = _text_boxes(soup)
    edges = _edge_paths(soup)
    # 1. effective font after fitting to the content width
    min_font = min([t[2] for t in texts] or [12.0])
    scale = min(1.0, nominal_width_px / vb_w)
    # CSS max-height / max-width caps
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', page_css or ''):
        prelude, body = m.group(1), m.group(2)
        if 'vector-diagram' not in prelude and 'svg' not in prelude:
            continue
        mh = re.search(r'max-height:\s*([\d.]+)px', body)
        mw = re.search(r'max-width:\s*([\d.]+)px', body)
        if mh:
            scale = min(scale, float(mh.group(1)) / vb_h)
        if mw:
            scale = min(scale, float(mw.group(1)) / vb_w)
    effective_font = round(min_font * scale, 2)
    aspect = vb_w / vb_h if vb_h else 99
    if aspect > MAX_ASPECT:
        errors.append(f'图过宽：viewBox {vb_w:.0f}×{vb_h:.0f}，宽高比 {aspect:.2f} > {MAX_ASPECT}；A4 正文放不下，必须改方向（LR→TD）或拆图')
    elif aspect > WARN_ASPECT:
        warnings.append(f'图偏宽：宽高比 {aspect:.2f} > {WARN_ASPECT}；建议改方向（LR→TD）或拆图，但不直接判失败')
    if aspect < 1 / MAX_ASPECT:
        errors.append(f'图过高：viewBox {vb_w:.0f}×{vb_h:.0f}，宽高比 {aspect:.2f} < 1/{MAX_ASPECT}；必须拆图')
    if effective_font < min_font_px:
        errors.append(f'按正文宽 {nominal_width_px:.0f}px 适配后最小字号约 {effective_font}px < {min_font_px}px；禁止缩图，必须改方向/加大节点间距/拆图')
    # 2. node overlap
    node_overlaps = 0
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            area = _overlap(nodes[i], nodes[j])
            if area > NODE_OVERLAP_RATIO * min(nodes[i][2] * nodes[i][3],
                                               nodes[j][2] * nodes[j][3]):
                node_overlaps += 1
    if node_overlaps:
        errors.append(f'检测到 {node_overlaps} 处节点重叠：节点必须分开，必要时拆图')
    # 3. text overlap (CJK bbox estimate)
    text_overlaps = 0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            area = _overlap(texts[i][1], texts[j][1])
            if area > TEXT_OVERLAP_RATIO * min(texts[i][1][2] * texts[i][1][3],
                                               texts[j][1][2] * texts[j][1][3]):
                text_overlaps += 1
    if text_overlaps:
        errors.append(f'检测到 {text_overlaps} 处文字重叠：汉字/标签互相覆盖，必须加大间距、换行或拆图')
    # 4. detached edge endpoints
    detached = 0
    for start, end, marker, dash in edges:
        if nodes:
            if not any(_near_bbox(start, n) for n in nodes):
                detached += 1
            elif not any(_near_bbox(end, n) for n in nodes):
                detached += 1
        if marker:
            m = re.search(r'url\(\s*[\'"]?#([^)\'"]+)', marker)
            if m and not soup.find(id=m.group(1)):
                errors.append(f'箭头引用了不存在的 marker #{m.group(1)}，会导致线条/箭头断裂')
    if detached:
        errors.append(f'检测到 {detached} 条连线端点未接到节点：线条断裂/箭头悬空，必须修复布局或换渲染器')
    # 5. Information completeness: many nodes in a system architecture are
    # normal. Do not fail/warn on count alone; only geometry/readability counts.
    # The metrics expose density so the Agent can decide whether to split, but
    # never drop nodes to satisfy a count threshold.
    return {
        'status': 'FAIL' if errors else ('WARN' if warnings else 'PASS'),
        'errors': errors, 'warnings': warnings,
        'metrics': {'viewbox': [vb_w, vb_h], 'aspect': round(aspect, 2),
                    'scale': round(scale, 3), 'min_font_px': min_font,
                    'effective_font_px': effective_font,
                    'nodes': len(nodes), 'texts': len(texts), 'edges': len(edges),
                    'node_overlaps': node_overlaps, 'text_overlaps': text_overlaps,
                    'detached_edges': detached},
        'notice': '机械几何检查；流程语义与最终视觉仍需人工复核。'
    }


def check_file(path, page_css=''):
    return check_svg(Path(path).read_text('utf-8'), page_css)


def main():
    import argparse
    import json
    ap = argparse.ArgumentParser(description='检查渲染后的 SVG 图是否存在过宽/断线/文字重叠/节点重叠')
    ap.add_argument('svg')
    ap.add_argument('--css', default='', help='页面 CSS 文件；用于 max-height/max-width 估算')
    args = ap.parse_args()
    css = Path(args.css).read_text('utf-8') if args.css else ''
    report = check_file(args.svg, css)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] in ('PASS', 'WARN') else 1


if __name__ == '__main__':
    raise SystemExit(main())