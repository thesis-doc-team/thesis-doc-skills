#!/usr/bin/env python3
"""Deterministic orthogonal edge router for A4 engineering diagrams.

No third-party dependency.  The router turns source-backed node/edge relations
into horizontal/vertical polylines, chooses sensible ports, keeps clear of node
boxes, and refuses to emit diagonal connectors.

Design goals
------------
* horizontal / vertical segments only (90-degree bends);
* top-to-bottom main flow, left-to-right secondary flow;
* decision branches use stable ports (yes=bottom, no=side);
* node interiors and group labels are obstacles;
* crossing / overlapping-segment penalties, not blind shortest path;
* deterministic output for the same input spec.
"""
from __future__ import annotations

import copy
import heapq
import math
from collections import defaultdict

EPS = 1e-6
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]  # right, down, left, up


class RoutingError(ValueError):
    """Raised when no orthogonal path exists without crossing a node."""


def _r(node):
    return (float(node["x"]), float(node["y"]), float(node["w"]), float(node["h"]))


def _center(r):
    return (r[0] + r[2] / 2.0, r[1] + r[3] / 2.0)


def _interior_hit(seg, rect, pad=0.0):
    """True if an axis-aligned segment passes through a rectangle interior."""
    x1, y1, x2, y2 = seg
    rx, ry, rw, rh = rect
    if rw <= 0 or rh <= 0:
        return False
    left, top = rx - pad, ry - pad
    right, bottom = rx + rw + pad, ry + rh + pad
    if abs(y1 - y2) < EPS:  # horizontal
        y = y1
        lo, hi = sorted((x1, x2))
        if not (top + EPS < y < bottom - EPS):
            return False
        # ignore mere boundary touch
        return hi > left + EPS and lo < right - EPS
    if abs(x1 - x2) < EPS:  # vertical
        x = x1
        lo, hi = sorted((y1, y2))
        if not (left + EPS < x < right - EPS):
            return False
        return hi > top + EPS and lo < bottom - EPS
    raise ValueError("non-orthogonal segment in collision check")


def _point_strict_inside(pt, rect, pad=0.0):
    x, y = pt
    rx, ry, rw, rh = rect
    return (rx - pad + EPS < x < rx + rw + pad - EPS and
            ry - pad + EPS < y < ry + rh + pad - EPS)


def _segments(points):
    return [(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
            for i in range(len(points) - 1)]


def is_orthogonal(points, tol=1e-4):
    if len(points) < 2:
        return False
    for x1, y1, x2, y2 in _segments(points):
        if abs(x1 - x2) > tol and abs(y1 - y2) > tol:
            return False
        if abs(x1 - x2) <= tol and abs(y1 - y2) <= tol:
            return False
    return True


def simplify(points, tol=0.05):
    """Drop duplicate / collinear intermediate points; keep exact corners."""
    out = []
    for p in points:
        p = (round(float(p[0]), 4), round(float(p[1]), 4))
        if not out or abs(out[-1][0] - p[0]) > tol or abs(out[-1][1] - p[1]) > tol:
            out.append(p)
    changed = True
    while changed and len(out) > 2:
        changed = False
        merged = [out[0]]
        for i in range(1, len(out) - 1):
            a, b, c = merged[-1], out[i], out[i + 1]
            same_h = abs(a[1] - b[1]) <= tol and abs(b[1] - c[1]) <= tol
            same_v = abs(a[0] - b[0]) <= tol and abs(b[0] - c[0]) <= tol
            # Only remove a point that lies between its neighbours; a U-turn
            # (e.g. a port stub) must be preserved.
            if same_h and min(a[0], c[0]) - tol <= b[0] <= max(a[0], c[0]) + tol:
                changed = True
                continue
            if same_v and min(a[1], c[1]) - tol <= b[1] <= max(a[1], c[1]) + tol:
                changed = True
                continue
            merged.append(b)
        merged.append(out[-1])
        out = merged
    return out


def _port_points(r, gap=0.0):
    x, y, w, h = r
    return {
        "top": ((x + w / 2.0, y - gap), (0, -1)),
        "bottom": ((x + w / 2.0, y + h + gap), (0, 1)),
        "left": ((x - gap, y + h / 2.0), (-1, 0)),
        "right": ((x + w + gap, y + h / 2.0), (1, 0)),
    }


def _choose_ports(sr, tr, edge, canvas_w=155.0):
    """Return (from_port, to_port).  Explicit hints win; decisions are stable."""
    label = str(edge.get("label", "")).strip()
    yes = label in {"是", "Y", "Yes", "YES", "true", "True", "通过", "成功"}
    no = label in {"否", "N", "No", "NO", "false", "False", "失败", "不通过"}
    if edge.get("from_port"):
        fp = edge["from_port"]
    else:
        fp = None
    if edge.get("to_port"):
        tp = edge["to_port"]
    else:
        tp = None
    scx, scy = _center(sr)
    tcx, tcy = _center(tr)
    dx, dy = tcx - scx, tcy - scy
    below = dy > 4.0 and abs(dy) >= abs(dx) * 0.55
    above = dy < -4.0 and abs(dy) >= abs(dx) * 0.55
    # Stable decision-branch convention: a branch whose target is mainly below
    # leaves the bottom; a branch whose target is mainly to the side (or above)
    # leaves the facing side.  This mirrors the supplied Visio references.
    if fp is None and yes:
        fp = "bottom" if below else ("right" if dx >= 0 else "left")
    if fp is None and no:
        fp = "right" if dx >= 0 else "left"
    if fp is None:
        if below:
            fp = "bottom"
        elif above:
            fp = "top"
        else:
            fp = "right" if dx >= 0 else "left"
    # Back edges (target above source) route around the side, not through it.
    if fp == "bottom" and tcy < scy - 2 and abs(dx) < (sr[2] + tr[2]) / 2.0:
        fp = "left" if scx <= canvas_w / 2.0 else "right"
    if tp is None:
        if fp == "bottom":
            tp = "top" if tcy >= scy else "bottom"
        elif fp == "top":
            tp = "bottom" if tcy <= scy else "top"
        elif fp == "left":
            tp = "right" if dx > 0 else "left"
        else:  # source exits right
            tp = "left" if dx > 0 else "right"
    return fp, tp


def _obstacles(spec, clearance, skip_nodes=()):
    obs = []
    for n in spec.get("nodes", []):
        if n["id"] in skip_nodes:
            continue
        obs.append(_r(n))
    for g in spec.get("groups", []):
        if g.get("label"):
            # group labels sit at the top of the dashed region; reserve a strip
            fs = float(spec.get("font_pt", 9.5)) * 25.4 / 72.0
            cx = float(g["x"]) + float(g["w"]) / 2.0
            cy = float(g["y"]) + 3.0
            half = max(6.0, len(str(g["label"])) * fs * 0.62)
            obs.append((cx - half, cy - fs * 1.1, half * 2, fs * 2.2))
    return obs


def _candidate_axes(spec, sr, tr, clearance):
    w = float(spec["width_mm"])
    h = float(spec["height_mm"])
    xs = {0.0, w}
    ys = {0.0, h}
    for n in spec.get("nodes", []):
        x, y, nw, nh = _r(n)
        for v in (x - clearance, x, x + nw, x + nw + clearance, x + nw / 2.0):
            xs.add(round(min(w, max(0.0, v)), 4))
        for v in (y - clearance, y, y + nh, y + nh + clearance, y + nh / 2.0):
            ys.add(round(min(h, max(0.0, v)), 4))
    for g in spec.get("groups", []):
        gx, gy, gw, gh = (float(g[k]) for k in ("x", "y", "w", "h"))
        for v in (gx, gx + gw, gx + gw / 2.0):
            xs.add(round(min(w, max(0.0, v)), 4))
        for v in (gy, gy + gh, gy + gh / 2.0):
            ys.add(round(min(h, max(0.0, v)), 4))
    # open-space lattice (5 mm) lets the router escape crowded pockets
    step = 5.0
    v = 0.0
    while v < w:
        xs.add(round(v, 4))
        v += step
    v = 0.0
    while v < h:
        ys.add(round(v, 4))
        v += step
    for pt in (sr, tr):
        xs.add(round(min(w, max(0.0, pt[0])), 4))
        ys.add(round(min(h, max(0.0, pt[1])), 4))
    return sorted(xs), sorted(ys)


def _cross_point(s1, s2, allow_t_junction=False):
    """Return the perpendicular intersection point, or None.

    A proper crossing is interior to both segments.  A T-junction (endpoint of
    one segment on the interior of the other) is a legal branch/merge on a
    shared bus, so it is ignored by default; ``allow_t_junction=True`` keeps it
    for diagnostics.
    """
    x1, y1, x2, y2 = s1
    x3, y3, x4, y4 = s2
    h1, v1 = abs(y1 - y2) < EPS, abs(x1 - x2) < EPS
    h2, v2 = abs(y3 - y4) < EPS, abs(x3 - x4) < EPS
    if h1 and v2:
        x, y = x3, y1
    elif v1 and h2:
        x, y = x1, y3
    else:
        return None
    if not (min(x1, x2) - 0.05 <= x <= max(x1, x2) + 0.05 and
            min(y1, y2) - 0.05 <= y <= max(y1, y2) + 0.05 and
            min(x3, x4) - 0.05 <= x <= max(x3, x4) + 0.05 and
            min(y3, y4) - 0.05 <= y <= max(y3, y4) + 0.05):
        return None

    def interior(seg):
        a, b, c, d = seg
        if abs(b - d) < EPS:
            return min(a, c) + 0.3 < x < max(a, c) - 0.3
        return min(b, d) + 0.3 < y < max(b, d) - 0.3

    i1, i2 = interior(s1), interior(s2)
    if i1 and i2:
        return (x, y)
    if allow_t_junction and (i1 or i2):
        return (x, y)
    return None


def _segment_cost(seg, existing, cross_penalty=60.0, overlap_same=2.0, overlap_opposite=30.0):
    x1, y1, x2, y2 = seg
    cost = 0.0
    for ox1, oy1, ox2, oy2 in existing:
        # perpendicular crossing (including a T-junction, which is still visually a
        # possible collision point during A* search; explicit bus layouts are
        # kept before A* and are not penalised by _crosses_existing)
        if _cross_point(seg, (ox1, oy1, ox2, oy2), allow_t_junction=True) is not None:
            cost += cross_penalty
        h1, v1 = abs(y1 - y2) < EPS, abs(x1 - x2) < EPS
        h2, v2 = abs(oy1 - oy2) < EPS, abs(ox1 - ox2) < EPS
        if (h1 and h2 and abs(y1 - oy1) < 0.4) or (v1 and v2 and abs(x1 - ox1) < 0.4):
            # collinear overlap
            if h1:
                lo = max(min(x1, x2), min(ox1, ox2))
                hi = min(max(x1, x2), max(ox1, ox2))
            else:
                lo = max(min(y1, y2), min(oy1, oy2))
                hi = min(max(y1, y2), max(oy1, oy2))
            if hi - lo > 0.6:
                same = ((x2 - x1) * (ox2 - ox1) + (y2 - y1) * (oy2 - oy1)) >= 0
                cost += (overlap_same if same else overlap_opposite) * (hi - lo) / 5.0
    return cost


def _astar(spec, start, goal, clearance, existing, obstacles):
    xs, ys = _candidate_axes(spec, start, goal, clearance)
    xi = {v: i for i, v in enumerate(xs)}
    yi = {v: j for j, v in enumerate(ys)}
    # Snap start/goal to nearest grid vertex (axes already contain them).
    si = (xi[round(start[0], 4)], yi[round(start[1], 4)])
    gi = (xi[round(goal[0], 4)], yi[round(goal[1], 4)])
    W, H = len(xs), len(ys)
    blocked_h = [[False] * (W - 1) for _ in range(H)]
    blocked_v = [[False] * W for _ in range(H - 1)]
    pads = [(r, clearance) for r in obstacles]
    for j in range(H):
        for i in range(W - 1):
            seg = (xs[i], ys[j], xs[i + 1], ys[j])
            if any(_interior_hit(seg, r, pad) for r, pad in pads):
                blocked_h[j][i] = True
    for j in range(H - 1):
        for i in range(W):
            seg = (xs[i], ys[j], xs[i], ys[j + 1])
            if any(_interior_hit(seg, r, pad) for r, pad in pads):
                blocked_v[j][i] = True
    # A* over (i, j, direction); direction -1 at start.
    def hfun(i, j):
        return abs(xs[i] - xs[gi[0]]) + abs(ys[j] - ys[gi[1]])
    start_state = (si[0], si[1], -1)
    pq = [(hfun(*si), 0.0, start_state)]
    best = {start_state: 0.0}
    parent = {}
    while pq:
        _, g, st = heapq.heappop(pq)
        if g > best.get(st, 1e18) + EPS:
            continue
        i, j, d = st
        if (i, j) == gi:
            path = [(xs[i], ys[j])]
            cur = st
            while cur in parent:
                cur = parent[cur]
                path.append((xs[cur[0]], ys[cur[1]]))
            path.reverse()
            return path
        for nd, (dx, dy) in enumerate(DIRS):
            ni, nj = i + dx, j + dy
            if not (0 <= ni < W and 0 <= nj < H):
                continue
            if dx == 1 and blocked_h[j][i]:
                continue
            if dx == -1 and blocked_h[j][ni]:
                continue
            if dy == 1 and blocked_v[j][i]:
                continue
            if dy == -1 and blocked_v[nj][i]:
                continue
            length = abs(xs[ni] - xs[i]) + abs(ys[nj] - ys[j])
            if length <= EPS:
                continue
            bend = 0.0 if d in (-1, nd) else 8.0
            seg = (xs[i], ys[j], xs[ni], ys[nj])
            extra = _segment_cost(seg, existing)
            ng = g + length + bend + extra
            ns = (ni, nj, nd)
            if ng + EPS < best.get(ns, 1e18):
                best[ns] = ng
                parent[ns] = st
                heapq.heappush(pq, (ng + hfun(ni, nj), ng, ns))
    return None


def _crosses_existing(pts, existing):
    for seg in _segments(pts):
        for ex in existing:
            if _cross_point(seg, ex) is not None:
                return True
    return False


def _route_one(spec, edge, existing, clearance):
    nodes = {n["id"]: n for n in spec["nodes"]}
    a, b = edge.get("from"), edge.get("to")
    if a not in nodes or b not in nodes:
        raise RoutingError("edge references unknown node: %r -> %r" % (a, b))
    sr, tr = _r(nodes[a]), _r(nodes[b])
    fp, tp = _choose_ports(sr, tr, edge, float(spec.get("width_mm", 155.0)))
    # Ports on the actual boundary; stubs outside the clearance ring.
    spt, sdir = _port_points(sr, 0.0)[fp]
    tpt, tdir = _port_points(tr, 0.0)[tp]
    stub = max(1.5, clearance)
    sstub = (min(spec["width_mm"], max(0.0, spt[0] + sdir[0] * stub)),
             min(spec["height_mm"], max(0.0, spt[1] + sdir[1] * stub)))
    tstub = (min(spec["width_mm"], max(0.0, tpt[0] + tdir[0] * stub)),
             min(spec["height_mm"], max(0.0, tpt[1] + tdir[1] * stub)))
    # Tightly packed nodes (gap smaller than two clearance rings): connect the
    # two facing ports with a small orthogonal jog in the gap, not an A* loop.
    gap_x = tpt[0] - spt[0]
    gap_y = tpt[1] - spt[1]
    direct = None
    if sdir == (1, 0) and tdir == (-1, 0) and 0 < gap_x <= 2 * stub and abs(gap_y) <= 4:
        mid = (spt[0] + tpt[0]) / 2.0
        direct = [spt, (mid, spt[1]), (mid, tpt[1]), tpt]
    elif sdir == (-1, 0) and tdir == (1, 0) and 0 < -gap_x <= 2 * stub and abs(gap_y) <= 4:
        mid = (spt[0] + tpt[0]) / 2.0
        direct = [spt, (mid, spt[1]), (mid, tpt[1]), tpt]
    elif sdir == (0, 1) and tdir == (0, -1) and 0 < gap_y <= 2 * stub and abs(gap_x) <= 4:
        mid = (spt[1] + tpt[1]) / 2.0
        direct = [spt, (spt[0], mid), (tpt[0], mid), tpt]
    elif sdir == (0, -1) and tdir == (0, 1) and 0 < -gap_y <= 2 * stub and abs(gap_x) <= 4:
        mid = (spt[1] + tpt[1]) / 2.0
        direct = [spt, (spt[0], mid), (tpt[0], mid), tpt]
    if direct:
        direct = simplify(direct)
        if is_orthogonal(direct) and not _penetrates(direct, spec["nodes"], a, b):
            return direct, fp, tp
    obstacles = _obstacles(spec, clearance)
    path = _astar(spec, sstub, tstub, clearance, existing, obstacles)
    if path is None:
        return None, fp, tp
    pts = [(spt[0], spt[1]), (sstub[0], sstub[1])] + path + \
          [(tstub[0], tstub[1]), (tpt[0], tpt[1])]
    pts = simplify(pts)
    if not is_orthogonal(pts):
        raise RoutingError("router produced a non-orthogonal path for %s->%s" % (a, b))
    return pts, fp, tp


def _penetrates(pts, nodes, a, b):
    last = len(pts) - 2
    for seg_i, seg in enumerate(_segments(pts)):
        for n in nodes:
            if n["id"] == a and seg_i == 0:
                continue
            if n["id"] == b and seg_i == last:
                continue
            if _interior_hit(seg, _r(n), 0.0):
                return n["id"]
    return None


def _nearest_segment_for_label(points, nodes):
    """Pick a stable segment for a branch label: prefer a vertical run."""
    segs = []
    for i in range(len(points) - 1):
        x1, y1, x2, y2 = points[i] + points[i + 1]
        length = abs(x2 - x1) + abs(y2 - y1)
        if length < 6:
            continue
        vertical = abs(x1 - x2) < EPS
        segs.append((i, length, vertical))
    if not segs:
        return 0
    verticals = [s for s in segs if s[2]]
    return (verticals or segs)[len(verticals or segs) // 2][0]


def place_label(edge, points, spec, placed):
    """Place a branch label beside a clear segment, never inside a node."""
    if not edge.get("label"):
        return None
    nodes = [_r(n) for n in spec.get("nodes", [])]
    fs = float(spec.get("font_pt", 9.5)) * 25.4 / 72.0
    tw = max(4.0, len(str(edge["label"])) * fs * 0.62)
    th = fs * 1.6
    candidates = []
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        length = abs(x2 - x1) + abs(y2 - y1)
        if length < 4:
            continue
        vertical = abs(x1 - x2) < EPS
        # try the middle and quarter points, then progressively larger offsets
        for t in (0.5, 0.35, 0.65, 0.2, 0.8):
            mx, my = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            for off in (2.4, -2.4, 4.0, -4.0, 6.0, -6.0, 8.0, -8.0):
                candidates.append((mx + (off if vertical else 0),
                                   my + (0 if vertical else off)))
    for tx, ty in candidates:
        box = (tx - tw / 2.0, ty - th / 2.0, tw, th)
        if box[0] < 0 or box[1] < 0 or box[0] + box[2] > spec["width_mm"] or \
           box[1] + box[3] > spec["height_mm"]:
            continue
        if any(_interior_hit((box[0], box[1], box[0] + box[2], box[1]),
                             n, 0.0) or _interior_hit((box[0], box[1] + box[3],
                                                      box[0] + box[2], box[1] + box[3]), n, 0.0) or
               _interior_hit((box[0], box[1], box[0], box[1] + box[3]), n, 0.0) or
               _interior_hit((box[0] + box[2], box[1], box[0] + box[2], box[1] + box[3]), n, 0.0)
               for n in nodes):
            continue
        if any(abs(tx - p[0]) < tw + 1 and abs(ty - p[1]) < th + 1 for p in placed):
            continue
        placed.append((tx, ty))
        return {"x": round(tx, 3), "y": round(ty, 3), "w": round(tw, 3), "h": round(th, 3)}
    # A fallback is intentionally left for QC to flag, never silently accepted.
    return None


def route_spec(spec, clearance=2.5, force=False):
    """Return a deep copy with orthogonal edge points and label boxes."""
    out = copy.deepcopy(spec)
    nodes = out.get("nodes", [])
    if not nodes:
        raise RoutingError("spec has no nodes")
    # Node overlap is a layout error, not something the router can fix.
    for i, a in enumerate(nodes):
        ra = _r(a)
        for b in nodes[i + 1:]:
            rb = _r(b)
            if (ra[0] < rb[0] + rb[2] - EPS and ra[0] + ra[2] > rb[0] + EPS and
                    ra[1] < rb[1] + rb[3] - EPS and ra[1] + ra[3] > rb[1] + EPS):
                raise RoutingError("nodes overlap: %s / %s" % (a["id"], b["id"]))
    existing = []
    placed_labels = []
    for edge in out.get("edges", []):
        original = edge.get("points")
        keep = (not force and original and is_orthogonal(original) and
                not _penetrates(original, nodes, edge.get("from"), edge.get("to")) and
                not _crosses_existing(original, existing))
        if keep:
            pts = simplify(original)
            fp = edge.get("from_port")
            tp = edge.get("to_port")
        else:
            pts = None
            fp = tp = None
            for cl in (clearance, clearance * 0.7, clearance * 0.45, 0.6):
                pts, fp, tp = _route_one(out, edge, existing, cl)
                if pts is not None:
                    break
            if pts is None:
                raise RoutingError(
                    "no orthogonal path for %s -> %s; move nodes apart, enlarge "
                    "the canvas, or split the figure" % (edge.get("from"), edge.get("to")))
            if _penetrates(pts, nodes, edge.get("from"), edge.get("to")):
                raise RoutingError("routed edge %s->%s passes through a node" %
                                   (edge.get("from"), edge.get("to")))
        edge["points"] = [[round(x, 3), round(y, 3)] for x, y in pts]
        if fp:
            edge["from_port"] = fp
        if tp:
            edge["to_port"] = tp
        edge["routing"] = "kept" if keep else "auto-orthogonal"
        edge["label_pos"] = place_label(edge, pts, out, placed_labels)
        existing.extend(_segments(pts))
    return out


def audit_routing(spec, tolerance=1e-4):
    """Return a list of geometric defects; empty means clean."""
    issues = []
    nodes = spec.get("nodes", [])
    for n in nodes:
        r = _r(n)
        if r[2] <= 0 or r[3] <= 0:
            issues.append("node %s has non-positive size" % n["id"])
    for edge in spec.get("edges", []):
        pts = edge.get("points") or []
        eid = "%s->%s" % (edge.get("from"), edge.get("to"))
        if len(pts) < 2:
            issues.append("edge %s has no path" % eid)
            continue
        if not is_orthogonal(pts, tolerance):
            issues.append("edge %s has a non-orthogonal segment" % eid)
        for seg_i, seg in enumerate(_segments(pts)):
            for n in nodes:
                is_source = n["id"] == edge.get("from")
                is_target = n["id"] == edge.get("to")
                # The short port stub may touch its own node boundary; the
                # remaining segments must never re-enter source/target either.
                if is_source and seg_i == 0:
                    continue
                if is_target and seg_i == len(pts) - 2:
                    continue
                if _interior_hit(seg, _r(n), 0.0):
                    issues.append("edge %s passes through node %s" % (eid, n["id"]))
                    break
        # endpoint must touch the declared source/target boundary
        src = next((n for n in nodes if n["id"] == edge.get("from")), None)
        dst = next((n for n in nodes if n["id"] == edge.get("to")), None)
        if src and not _on_boundary(pts[0], _r(src)):
            issues.append("edge %s does not start on source boundary" % eid)
        if dst and not _on_boundary(pts[-1], _r(dst)):
            issues.append("edge %s does not end on target boundary" % eid)
    return issues


def _on_boundary(pt, r, tol=0.6):
    x, y = pt
    rx, ry, rw, rh = r
    on_v = (abs(x - rx) <= tol or abs(x - (rx + rw)) <= tol) and ry - tol <= y <= ry + rh + tol
    on_h = (abs(y - ry) <= tol or abs(y - (ry + rh)) <= tol) and rx - tol <= x <= rx + rw + tol
    return on_v or on_h


def count_crossings(spec):
    """Count perpendicular edge intersections not at a shared endpoint."""
    pairs = []
    for e in spec.get("edges", []):
        pts = e.get("points") or []
        for seg in _segments(pts):
            pairs.append((e.get("from"), e.get("to"), seg))
    n = 0
    for i in range(len(pairs)):
        a, b, s1 = pairs[i]
        for j in range(i + 1, len(pairs)):
            c, d, s2 = pairs[j]
            if {a, b} & {c, d}:
                continue
            if _cross_point(s1, s2) is not None:
                n += 1
    return n


def _perpendicular_cross(s1, s2):
    x1, y1, x2, y2 = s1
    x3, y3, x4, y4 = s2
    h1, v1 = abs(y1 - y2) < EPS, abs(x1 - x2) < EPS
    h2, v2 = abs(y3 - y4) < EPS, abs(x3 - x4) < EPS
    if h1 and v2:
        y, x = y1, x3
        return (min(x1, x2) + 0.6 < x < max(x1, x2) - 0.6 and
                min(y3, y4) + 0.6 < y < max(y3, y4) - 0.6)
    if v1 and h2:
        x, y = x1, y3
        return (min(y1, y2) + 0.6 < y < max(y1, y2) - 0.6 and
                min(x3, x4) + 0.6 < x < max(x3, x4) - 0.6)
    return False


def decision_branch_issues(spec):
    issues = []
    nodes = {n["id"]: n for n in spec.get("nodes", [])}
    outgoing = defaultdict(list)
    for e in spec.get("edges", []):
        outgoing[e.get("from")].append(e)
    for nid, n in nodes.items():
        if n.get("shape") != "diamond":
            continue
        outs = outgoing.get(nid, [])
        if len(outs) < 2:
            continue
        unlabeled = [e for e in outs if not str(e.get("label", "")).strip()]
        if unlabeled:
            issues.append("decision %s has unlabeled branch(es)" % nid)
        labels = [str(e.get("label", "")).strip() for e in outs]
        if len(set(labels)) != len(labels):
            issues.append("decision %s has duplicate branch labels" % nid)
    return issues