#!/usr/bin/env python3
"""Export an SVG to an exact-size PNG with a locally installed Chrome/Edge.

No package installation, no network.  The SVG's millimetre width/height is read
from the root element; the browser is asked for ``dpi/96`` device scale so the
PNG is a true 300 dpi (or requested dpi) raster at the physical size.

This is a convenience for WPS / older Word; the SVG remains the vector source.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_browser(explicit=None):
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    for p in BROWSERS:
        if Path(p).is_file():
            return Path(p)
    return None


def svg_size(svg_text):
    m = re.search(r'<svg[^>]*\bwidth="([\d.]+)mm"[^>]*\bheight="([\d.]+)mm"', svg_text)
    if not m:
        m = re.search(r'<svg[^>]*\bheight="([\d.]+)mm"[^>]*\bwidth="([\d.]+)mm"', svg_text)
        if m:
            return float(m.group(2)), float(m.group(1))
        raise ValueError("SVG 根元素必须显式声明 width/height（mm）")
    return float(m.group(1)), float(m.group(2))


def export(svg_path, out_path, dpi=300, browser=None):
    svg_path, out_path = Path(svg_path), Path(out_path)
    text = svg_path.read_text("utf-8")
    w_mm, h_mm = svg_size(text)
    exe = find_browser(browser)
    if exe is None:
        raise RuntimeError("未找到 Chrome/Edge；请用 --browser 指定，或保留 SVG 由 Word/WPS 直接插入")
    w_px = round(w_mm * 96 / 25.4)
    h_px = round(h_mm * 96 / 25.4)
    scale = dpi / 96.0
    # Inline the SVG so the page has no body margin and cannot be clipped.
    body = re.sub(r'<svg([^>]*)>', r'<svg\1 style="width:100%;height:100%;display:block">', text, count=1)
    html = ("<!doctype html><meta charset='utf-8'><style>"
            "html,body{margin:0;padding:0;overflow:hidden;background:#fff}"
            "svg{width:100%!important;height:100%!important;display:block}</style>" + body)
    with tempfile.TemporaryDirectory(prefix="tva-png-") as td:
        hp = Path(td) / "figure.html"
        hp.write_text(html, "utf-8")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [str(exe), "--headless=new", "--disable-gpu", "--hide-scrollbars",
               f"--force-device-scale-factor={scale:g}",
               f"--screenshot={out_path.resolve()}", f"--window-size={w_px},{h_px}",
               hp.resolve().as_uri()]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0 or not out_path.exists():
            raise RuntimeError("浏览器导出失败：" + (p.stderr or p.stdout)[-500:])
    d = out_path.read_bytes()[:33]
    width, height = struct.unpack(">II", d[16:24])
    actual_dpi = round(width / (w_mm / 25.4), 1)
    return {"status": "PNG_EXPORTED", "png": str(out_path), "width_px": width,
            "height_px": height, "physical_mm": [w_mm, h_mm],
            "requested_dpi": dpi, "actual_dpi": actual_dpi,
            "notice": "PNG 仅作 WPS/旧版 Word 兼容位图；SVG 仍为矢量与可编辑源。"}


def main():
    ap = argparse.ArgumentParser(description="SVG → 指定 dpi PNG（本地 Chrome/Edge，不联网）")
    ap.add_argument("--svg", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=float, default=300)
    ap.add_argument("--browser")
    args = ap.parse_args()
    try:
        print(json.dumps(export(args.svg, args.out, args.dpi, args.browser),
                         ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as e:
        print(json.dumps({"status": "BLOCK", "reason": str(e)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())