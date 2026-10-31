#!/usr/bin/env python3
"""Zero-dependency SVG renderer for an intentionally small Mermaid flowchart subset.

This is a layout renderer, not a technical inference engine. It preserves exact
node labels / edges and refuses complex or ambiguous Mermaid. No installed
Graphviz, npm, or browser needed. SVG output must still be visually reviewed.
"""
from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
import re
import textwrap
from xml.etree import ElementTree as ET

HEADER = re.compile(r'^\s*(?:flowchart|graph)\s+(TD|TB|LR|RL|BT)\s*$', re.I)
NODE = re.compile(r'^([A-Za-z][A-Za-z0-9_-]{0,60})(?:\s*(\[(.*?)\]|\((.*?)\)|\{(.*?)\}))?\s*$')
EDGE = re.compile(r'\s+-->|\s*-->\s*')
ROOT = 'http://www.w3.org/2000/svg'
ET.register_namespace('', ROOT)


def parse(source):
    lines = [t.strip().rstrip(';') for t in source.splitlines()
             if t.strip() and not t.lstrip().startswith('%%')]
    if not lines or not (header := HEADER.fullmatch(lines[0])):
        raise ValueError('stdlib SVG 回退只支持 flowchart/graph TD/TB/LR/RL/BT')
    direction = header.group(1).upper()
    labels, edges = {}, []

    def node(expression):
        m = NODE.fullmatch(expression.strip())
        if not m:
            raise ValueError('不支持的节点语法或包含图形指令：' + expression[:55])
        ident = m.group(1)
        label = (m.group(3) or m.group(4) or m.group(5) or ident).strip()
        # Mermaid 的 ["..."]/("...") 引号只用于转义边角字符，语义就是内层文本。
        if len(label) >= 2 and label.startswith('"') and label.endswith('"'):
            label = label[1:-1].strip()
        if not label or len(label) > 90 or any(x in label for x in ('<', '>', '`', '"')):
            raise ValueError('节点标签需要人工处理：' + label[:55])
        if ident in labels and labels[ident] != ident and label == ident:
            return ident
        if ident in labels and labels[ident] not in (ident, label):
            raise ValueError('同一节点定义不一致：' + ident)
        labels[ident] = label
        if len(labels) > 40:
            raise ValueError('节点超过 40 个，拒绝画出不可读的巨大图')
        return ident

    for line in lines[1:]:
        if '-->' in line:
            edge_label = None
            m = re.match(r'^(.+?)\s*-->\s*\|([^|]{1,20})\|\s*(.+)$', line)   # A -->|标签| B
            if m:
                left, edge_label, right = m.group(1), m.group(2).strip(), m.group(3)
            else:
                m = re.match(r'^(.+?)\s*--\s+(.+?)\s*-->\s*(.+)$', line)     # A -- 标签 --> B
                if m:
                    left, edge_label, right = m.group(1), m.group(2).strip(), m.group(3)
                else:
                    parts = re.split(r'\s*-->\s*', line)
                    if len(parts) != 2:
                        raise ValueError('暂不支持链式箭头，使用复杂 Mermaid 渲染器')
                    left, right = parts
            if edge_label is not None:
                if not edge_label or len(edge_label) > 24 or any(x in edge_label for x in ('<', '>', '`', '"', '|')):
                    raise ValueError('边标签需要人工处理：' + edge_label[:30])
            a, b = map(node, (left, right))
            if a == b: raise ValueError('自循环图不属于安全回退范围')
            edges.append((a, b, edge_label))
        else:
            node(line)
        if len(edges) > 75: raise ValueError('连接线超过 75 条')
    if not edges: raise ValueError('没有关系边，不能渲染为框架/流程图')
    # Refuse cycles and other cases where a naive diagram would distort structure.
    parents = {n: 0 for n in labels}
    adj = defaultdict(list)
    for a, b, _ in edges:
        adj[a].append(b)
        parents[b] += 1
    queue = deque([n for n, degree in parents.items() if degree == 0])
    order, level = [], {n: 0 for n in labels}
    while queue:
        n = queue.popleft()
        order.append(n)
        for v in adj[n]:
            level[v] = max(level[v], level[n] + 1)
            parents[v] -= 1
            if parents[v] == 0: queue.append(v)
    if len(order) != len(labels):
        raise ValueError('流程存在环路；零依赖简化布局拒绝可能误导的连线')
    return direction, labels, edges, level


def _wrap(label, limit=15):
    lines = []
    for line in label.split('\\n'):
        # char-based to handle Chinese labels with no spaces.
        lines += [line[i:i+limit] for i in range(0, len(line), limit)] or ['']
    if len(lines) > 6:
        raise ValueError('节点标签过长；请缩短或采用已有 Mermaid/Graphviz 引擎')
    return lines


def render(source: str, destination: Path):
    direction, labels, edges, levels = parse(source)
    grouped = defaultdict(list)
    for node in labels: grouped[levels[node]].append(node)
    max_depth = max(grouped)
    max_width = max(len(r) for r in grouped.values())
    horizontal = direction in ('LR', 'RL')
    box_w, box_h, gap_x, gap_y, pad = 210, 76, 72, 85, 44
    columns = (max_depth + 1) if horizontal else max_width
    rows = max_width if horizontal else (max_depth + 1)
    svg_w = pad*2 + columns*box_w + (columns-1)*gap_x
    svg_h = pad*2 + rows*box_h + (rows-1)*gap_y
    if svg_w > 6000 or svg_h > 7000:
        raise ValueError('图表过大，拒绝输出不可读 SVG')
    reverse = direction in ('BT', 'RL')
    coords = {}
    for depth, ids in grouped.items():
        for ix, ident in enumerate(ids):
            row = (max_depth-depth) if reverse and not horizontal else (depth if not horizontal else ix)
            col = (max_depth-depth) if reverse and horizontal else (depth if horizontal else ix)
            if horizontal:
                row = ix
            coords[ident] = (pad+col*(box_w+gap_x), pad+row*(box_h+gap_y))
    root = ET.Element(f'{{{ROOT}}}svg', {
        'width': str(svg_w), 'height': str(svg_h), 'viewBox': f'0 0 {svg_w} {svg_h}',
        'role': 'img', 'aria-label': '技术图示（仅基于已登记节点和箭头渲染）'})
    defs = ET.SubElement(root, f'{{{ROOT}}}defs')
    marker = ET.SubElement(defs, f'{{{ROOT}}}marker', {
        'id':'arrow', 'viewBox':'0 0 10 10', 'refX':'9', 'refY':'5',
        'markerWidth':'6', 'markerHeight':'6', 'orient':'auto-start-reverse'})
    ET.SubElement(marker,f'{{{ROOT}}}path',{'d':'M 0 0 L 10 5 L 0 10 z','fill':'#6573a0'})
    for a,b,elabel in edges:
        ax,ay=coords[a]; bx,by=coords[b]
        if horizontal:
            forward=1 if bx>ax else -1
            sx=ax+(box_w if forward==1 else 0); sy=ay+box_h/2
            ex=bx+(0 if forward==1 else box_w); ey=by+box_h/2
            mid=(sx+ex)/2
            path=f'M {sx} {sy} L {mid} {sy} L {mid} {ey} L {ex} {ey}'
            lx,ly=mid,(sy+ey)/2
        else:
            forward=1 if by>ay else -1
            sx=ax+box_w/2; sy=ay+(box_h if forward==1 else 0)
            ex=bx+box_w/2; ey=by+(0 if forward==1 else box_h)
            mid=(sy+ey)/2
            path=f'M {sx} {sy} L {sx} {mid} L {ex} {mid} L {ex} {ey}'
            lx,ly=(sx+ex)/2,mid
        ET.SubElement(root,f'{{{ROOT}}}path',{
            'd':path,'fill':'none','stroke':'#6573a0','stroke-width':'2',
            'marker-end':'url(#arrow)'})
        if elabel:
            t=ET.SubElement(root,f'{{{ROOT}}}text',{'x':str(lx),'y':str(ly-7),
                'fill':'#4a5578','font-size':'13','text-anchor':'middle',
                'font-family':'Noto Sans CJK SC, Microsoft YaHei, sans-serif',
                'stroke':'#ffffff','stroke-width':'3','paint-order':'stroke'})
            t.text=elabel
    for ident, (x,y) in coords.items():
        ET.SubElement(root,f'{{{ROOT}}}rect',{'x':str(x),'y':str(y),'width':str(box_w),
            'height':str(box_h),'rx':'12','fill':'#f0f5fe','stroke':'#7e9bc9','stroke-width':'1.4'})
        ls=_wrap(labels[ident]); first_y=y+box_h/2-(len(ls)-1)*9+5
        t=ET.SubElement(root,f'{{{ROOT}}}text',{'x':str(x+box_w/2),'y':str(first_y),
            'fill':'#243458','font-size':'15','text-anchor':'middle',
            'font-family':'Noto Sans CJK SC, Microsoft YaHei, sans-serif'})
        for idx, part in enumerate(ls):
            span=ET.SubElement(t,f'{{{ROOT}}}tspan',{'x':str(x+box_w/2), 'dy':'0' if idx==0 else '19'})
            span.text=part
    dest=Path(destination)
    dest.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(dest, encoding='utf-8', xml_declaration=True)
    return {'engine':'stdlib-svg-subset','node_count':len(labels),'edge_count':len(edges)}
