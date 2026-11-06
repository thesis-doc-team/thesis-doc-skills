#!/usr/bin/env python3
"""Subgraph-aware layout + label normalization for technical-visual-assets.

The authored spec may carry dashed partition frames (``groups``) and optional
node membership (``node["group"] = group_id``).  This module:

* normalizes Mermaid-style ``<br/>`` labels to real newlines;
* infers membership from the current geometry when not declared;
* re-computes each group frame from its member nodes (content + label padding);
* stacks group frames vertically (or wraps them into rows) so frames never
  overlap each other or unrelated nodes;
* re-grids nodes inside each group with readable gaps.

It does **not** change technical semantics or drop nodes; edges are re-routed by
orthogonal_router after layout.
"""
from __future__ import annotations

import copy
import math
import re

BR = re.compile(r'<br\s*/?>', re.I)
TAG = re.compile(r'<[^>]+>')


def normalize_labels(spec):
    spec = copy.deepcopy(spec)
    for n in spec.get('nodes', []):
        if isinstance(n.get('label'), str):
            n['label'] = TAG.sub('', BR.sub('\n', n['label']))
    for e in spec.get('edges', []):
        if isinstance(e.get('label'), str):
            e['label'] = TAG.sub('', BR.sub('\n', e['label']))
    return spec


def _rect(node):
    return (float(node['x']), float(node['y']), float(node['w']), float(node['h']))


def _inside(pt, rect):
    x, y = pt
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh


def _overlap(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[0] + a[2], b[0] + b[2]); y2 = min(a[1] + a[3], b[1] + b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _contains(outer, inner):
    area = inner[2] * inner[3]
    return area > 0 and _overlap(outer, inner) / area >= 0.95


def _infer_members(spec):
    """Assign each node to the smallest group frame that contains its centre."""
    groups = spec.get('groups', [])
    if not groups:
        return {}
    boxes = {g.get('id', f'g{i}'): (float(g['x']), float(g['y']), float(g['w']), float(g['h']))
             for i, g in enumerate(groups)}
    members = {gid: [] for gid in boxes}
    for n in spec.get('nodes', []):
        gid = n.get('group') or n.get('group_id')
        if gid in members:
            members[gid].append(n)
            continue
        cx = float(n['x']) + float(n['w']) / 2.0
        cy = float(n['y']) + float(n['h']) / 2.0
        hits = [gid for gid, box in boxes.items() if _inside((cx, cy), box)]
        if hits:
            hits.sort(key=lambda gid: boxes[gid][2] * boxes[gid][3])
            n['group'] = hits[0]
            members[hits[0]].append(n)
    return members


def _grid_nodes(nodes, pad, gap, label_h, max_width):
    if not nodes:
        return 0.0, 0.0
    max_w = max(float(n['w']) for n in nodes)
    max_h = max(float(n['h']) for n in nodes)
    cols = 1
    for candidate in (3, 2):
        if len(nodes) < candidate:
            continue
        needed = candidate * max_w + (candidate - 1) * gap + 2 * pad
        if needed <= max_width:
            cols = candidate
            break
    rows = math.ceil(len(nodes) / cols)
    cell_w = max_w + gap
    cell_h = max_h + gap
    for i, n in enumerate(nodes):
        row, col = divmod(i, cols)
        n['x'] = pad + col * cell_w + (max_w - float(n['w'])) / 2.0
        n['y'] = pad + label_h + row * cell_h
    width = cols * max_w + (cols - 1) * gap + 2 * pad
    height = label_h + rows * max_h + (rows - 1) * gap + 2 * pad
    return width, height


def layout(spec, padding=5.0, group_gap=12.0, node_gap=6.0, max_height=282.0):
    """Return a copy with group frames and member nodes re-laid out.

    - group frames are re-computed from members; labels stay at top;
    - frames stack vertically (wrap into rows if they fit side by side);
    - node coordinates inside groups are re-gridded;
    - explicit edge points are dropped so orthogonal_router re-routes them.
    """
    spec = normalize_labels(spec)
    canvas_w = float(spec.get('width_mm', 155))
    font = float(spec.get('font_pt', 9.5))
    label_h = max(4.5, font * 25.4 / 72.0 * 1.7)
    groups = spec.get('groups', [])
    nodes = spec.get('nodes', [])
    if not groups:
        # no partitions: grid all nodes (still useful for crowded graphs)
        w, h = _grid_nodes(nodes, padding, node_gap, 0.0, canvas_w - 4)
        spec['height_mm'] = min(max_height, max(float(spec.get('height_mm', 100)), h + 4))
    else:
        members = _infer_members(spec)
        blocks = []
        for i, g in enumerate(groups):
            gid = g.get('id', f'g{i}')
            g['id'] = gid
            member_nodes = members.get(gid, [])
            if not member_nodes:
                # keep an explicitly authored empty frame, but do not let it
                # overlap; it gets a minimal box.
                g['x'], g['y'] = 2.0, 2.0
                g['w'] = max(20.0, float(g.get('w', 20)))
                g['h'] = max(label_h + 8.0, float(g.get('h', 12)))
                blocks.append((g, member_nodes))
                continue
            bw, bh = _grid_nodes(member_nodes, padding, node_gap, label_h, canvas_w - 6)
            g['w'], g['h'] = bw, bh
            blocks.append((g, member_nodes))
        # Stack frames vertically. If two small frames fit side by side in a
        # row, place them in the same row to reduce height.
        x, y, row_h = 2.0, 2.0, 0.0
        for g, _ in blocks:
            gw = float(g['w'])
            if x + gw > canvas_w - 2 and x > 2.0:
                x = 2.0
                y += row_h + group_gap
                row_h = 0.0
            g['x'], g['y'] = x, y
            x += gw + group_gap
            row_h = max(row_h, float(g['h']))
        total_h = y + row_h + 2.0
        if total_h > max_height:
            raise ValueError(f'子图布局高度 {total_h:.1f}mm 超过 A4 可用上限 {max_height}mm；请拆图或减少分组')
        # center each frame's member nodes within the frame (already gridded
        # relative to frame origin: shift by group position).
        for g, member_nodes in blocks:
            if not member_nodes:
                continue
            # _grid_nodes wrote local coordinates; shift to absolute group pos.
            for n in member_nodes:
                n['x'] = float(g['x']) + float(n['x'])
                n['y'] = float(g['y']) + float(n['y'])
                n['group'] = g['id']
        spec['height_mm'] = min(max_height, max(float(spec.get('height_mm', 100)), total_h))
    for e in spec.get('edges', []):
        e.pop('points', None)
        e.pop('label_pos', None)
    spec['layout'] = 'subgraph-grid'
    return spec
