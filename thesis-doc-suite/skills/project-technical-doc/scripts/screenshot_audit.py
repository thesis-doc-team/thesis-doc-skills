#!/usr/bin/env python3
"""Screenshot-verification guards for project-technical-doc (stdlib only).

Subcommands against the classic headless-browser measurement traps and the
"SVG rendered broken but checks stayed green" incident:

  dupcheck <img...>
      Screenshots that are byte-identical mean the capture failed (e.g. the
      page never scrolled to the anchor), NOT that two views look the same.
      Exits 1 when any two files share a SHA-256.

  probe --html FILE [--width N] [--height H] ...
      Before declaring horizontal overflow FAIL, MEASURE the real layout
      (body scrollWidth vs viewport width) instead of eyeballing a possibly
      cropped screenshot.  Windows headless Chrome clamps the layout viewport
      to ~512px, so a "--window-size=390" screenshot is a 512px layout CROPPED
      to 390px — that cut edge is an artifact, not a page bug.  The probe
      forces a true narrow layout viewport with a fixed-width iframe and runs
      viewport_probe.js inside it.  Prints JSON; exit 0 = no real overflow,
      1 = real overflow, 2 = probe could not run.

  harness --html FILE --offset N --height H --width N --out FILE
      Emit a static negative-offset iframe page for chapter slicing.
      `--screenshot` always starts at the document top (anchors and
      scrollIntoView are ignored), so chapter shots are taken by placing the
      page in an iframe shifted up by --offset.

  renderprobe --html FILE
      Per-diagram render checks (diagram_probe.js): svg height ratio vs
      viewBox natural height (squash detection), diagram-container inner
      scrollbar detection (diagrams must display fully), computed node fills
      vs default black (style-closure breakage signature) and label-text vs
      node-fill contrast.  exit 0 = clean, 1 = problems, 2 = probe failed.

  pixelprobe IMAGE | --svg FILE
      Pixel evidence from a screenshot (or a standalone svg rendered and
      captured first): distinct-color count and near-black ratio.  A broken
      black-block diagram is ~monochrome; a healthy one has >= 3 colors.
      exit 0 = colorful, 1 = mono/suspect, 2 = cannot analyze.

  coverage --manifest shots.json
      Screenshot coverage matrix: 1440/768/390 x home/diagram/interactive
      must all be present, every file must exist, and no two files may be
      byte-identical (that is the dupcheck "capture failed" case).  exit
      0 = complete, 1 = missing slot or duplicate, 2 = manifest error.

Browser discovery: --browser PATH, then env TDS_BROWSER, then chrome/msedge on
PATH, then common Windows install locations.
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')

import argparse
import hashlib
import html as html_mod
import json
import os
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

PROBE_JS = Path(__file__).with_name('viewport_probe.js')
DIAGRAM_PROBE_JS = Path(__file__).with_name('diagram_probe.js')
PRE_ID = 'screenshot-audit-probe'
PRE_RE = re.compile(r'<pre id="' + PRE_ID + r'"[^>]*>([\s\S]*?)</pre>')

# Aggregator for the probe harness: the iframe result lives in a file:// child
# document, so the parent polls it (with --allow-file-access-from-files) and
# writes it ONCE into its own <pre>.  Single write avoids the re-measure trap.
AGGREGATOR_JS = """
(function () {
  var done = false, tries = 0;
  var out = document.getElementById('screenshot-audit-probe');
  function finish(text) {
    if (done) return;
    done = true;
    out.textContent = text;
  }
  var timer = setInterval(function () {
    tries++;
    try {
      var f = document.getElementById('frame');
      var d = f.contentDocument;
      var pre = d && d.getElementById('screenshot-audit-probe');
      if (pre && pre.textContent) { clearInterval(timer); finish(pre.textContent); return; }
    } catch (e) { /* child not readable yet */ }
    if (tries >= 120) {
      clearInterval(timer);
      finish('{"ok":false,"probe":"screenshot-audit","error":"probe timeout: iframe result never appeared"}');
    }
  }, 50);
})();
"""


def find_browser(explicit=None):
    if explicit:
        return explicit
    env = os.environ.get('TDS_BROWSER')
    if env:
        return env
    for name in ('chrome', 'msedge', 'google-chrome', 'chromium', 'chromium-browser'):
        found = shutil.which(name)
        if found:
            return found
    for cand in (r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                 r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                 r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
                 r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'):
        if Path(cand).is_file():
            return cand
    return None


def cmd_dupcheck(paths):
    groups = {}
    for p in paths:
        f = Path(p)
        if not f.is_file():
            print(f'不存在：{f}')
            return 2
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        groups.setdefault(digest, []).append(str(f))
    dup = {h: names for h, names in groups.items() if len(names) > 1}
    for h, names in dup.items():
        print(f'字节级重复（拍摄失败嫌疑） sha256={h[:16]}…')
        for n in names:
            print(f'  - {n}')
    if dup:
        print('结论：以上截图内容完全相同——大概率是锚点未滚动/状态未切换导致拍摄失败，必须重拍，不得当作"两处一致"。')
        return 1
    print(f'OK：{len(paths)} 张截图哈希互不相同。')
    return 0


def make_harness(src_uri, width, height, out_path, offset=0, with_aggregator=False):
    script = AGGREGATOR_JS if with_aggregator else ''
    pre = f'<pre id="{PRE_ID}" style="display:none"></pre>' if with_aggregator else ''
    doc = (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<title>screenshot-audit-harness</title>'
        f'<style>html,body{{margin:0;padding:0;overflow:hidden;background:#fff}}'
        f'#frame{{border:0;width:{int(width)}px;height:{int(height)}px;display:block;'
        f'position:absolute;left:0;top:-{int(offset)}px}}</style></head><body>'
        f'<iframe id="frame" src="{src_uri}"></iframe>{pre}'
        f'<script>{script}</script></body></html>'
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, 'utf-8', newline='\n')
    return out_path


def run_browser_dump(browser, harness, width, height, budget):
    last_err = ''
    for headless in ('--headless=new', '--headless'):
        cmd = [browser, headless, '--disable-gpu', '--no-first-run',
               '--allow-file-access-from-files',
               f'--window-size={int(width)},{int(height)}',
               f'--virtual-time-budget={int(budget)}', '--dump-dom', str(harness)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  encoding='utf-8', errors='replace', timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, f'浏览器执行失败：{exc}'
        m = PRE_RE.search(proc.stdout or '')
        if m:
            return html_mod.unescape(m.group(1)), None
        last_err = (proc.stderr or proc.stdout or '')[-400:]
    return None, f'未取到探针结果（dump-dom 无 {PRE_ID}）；浏览器输出尾部：{last_err}'


def run_page_probe(page, js_file, browser, width=390, height=800, work=None, budget=8000):
    """Inject a single-shot probe script into a page copy and read its one-shot
    JSON result through the iframe aggregator.  Returns (data, err)."""
    page = Path(page)
    work = Path(work) if work else page.parent / '.screenshot-audit-tmp'
    work.mkdir(parents=True, exist_ok=True)
    src = page.read_text('utf-8-sig')
    probe_js = Path(js_file).read_text('utf-8')
    tag = '</body>'
    pos = src.lower().rfind(tag)
    injected = (src[:pos] + f'<script>{probe_js}</script>' + src[pos:]) if pos >= 0 else (src + f'<script>{probe_js}</script>')
    probe_copy = work / (page.stem + '.probe.html')
    probe_copy.write_text(injected, 'utf-8', newline='\n')
    harness = make_harness(probe_copy.as_uri(), width, height, work / 'probe-harness.html', with_aggregator=True)
    raw, err = run_browser_dump(browser, harness, width, height, budget)
    if err:
        return None, err
    try:
        return json.loads(raw), None
    except json.JSONDecodeError:
        return None, '探针输出不是合法 JSON：' + str(raw)[:300]


def cmd_probe(args):
    page = Path(args.html).expanduser().resolve()
    if not page.is_file():
        print(f'HTML 不存在：{page}')
        return 2
    browser = find_browser(args.browser)
    if not browser:
        print('未找到 Chrome/Edge：请用 --browser 指定，或设置环境变量 TDS_BROWSER。')
        return 2
    if not PROBE_JS.is_file():
        print(f'缺少探针脚本：{PROBE_JS}')
        return 2
    work = Path(args.work_dir).expanduser().resolve() if args.work_dir else page.parent / '.screenshot-audit-tmp'
    data, err = run_page_probe(page, PROBE_JS, browser, args.width, args.height, work, args.budget)
    if err:
        print(err)
        return 2
    out = {'probe': 'screenshot-audit', 'viewport': {'width': args.width, 'height': args.height},
           'browser': browser, 'data': data}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not data.get('ok'):
        return 2
    return 1 if data.get('result', {}).get('realHorizontalOverflow') else 0


def cmd_harness(args):
    page = Path(args.html).expanduser().resolve()
    if not page.is_file():
        print(f'HTML 不存在：{page}')
        return 2
    out = Path(args.out).expanduser().resolve()
    make_harness(page.as_uri(), args.width, args.height, out, offset=args.offset)
    print(f'已生成切片 harness：{out}（窗口开 {int(args.width)}x{int(args.height)} 截图即为偏移 {int(args.offset)}px 处的章节）')
    return 0


# ---------- PNG 像素统计（仅标准库：zlib 解 IDAT + 还原行滤波） ----------

def decode_png(data):
    """Return (w, h, channels, rows, plte) for an 8-bit non-interlaced PNG."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('不是 PNG 文件')
    pos, idat, meta, plte = 8, [], {}, None
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos:pos+4], 'big')
        ctype = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+length]
        pos += 12 + length
        if ctype == b'IHDR':
            meta['w'] = int.from_bytes(chunk[0:4], 'big')
            meta['h'] = int.from_bytes(chunk[4:8], 'big')
            meta['depth'], meta['color'], meta['interlace'] = chunk[8], chunk[9], chunk[12]
        elif ctype == b'IDAT':
            idat.append(chunk)
        elif ctype == b'PLTE':
            plte = chunk
        elif ctype == b'IEND':
            break
    if meta.get('depth') != 8 or meta.get('interlace') != 0:
        raise ValueError(f"不支持的 PNG（位深 {meta.get('depth')} / 隔行 {meta.get('interlace')}）")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(meta.get('color'))
    if not channels:
        raise ValueError(f"不支持的 PNG 颜色类型 {meta.get('color')}")
    raw = zlib.decompress(b''.join(idat))
    w, h, stride = meta['w'], meta['h'], meta['w'] * channels
    rows, prev, pos = [], bytearray(stride), 0
    for _ in range(h):
        f = raw[pos]
        line = bytearray(raw[pos+1:pos+1+stride])
        pos += 1 + stride
        if f == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i-channels]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                a = line[i-channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = line[i-channels] if i >= channels else 0
                b = prev[i]
                c = prev[i-channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
                line[i] = (line[i] + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))) & 0xFF
        elif f != 0:
            raise ValueError(f'未知 PNG 行滤波 {f}')
        rows.append(bytes(line))
        prev = line
    return w, h, channels, rows, plte


def png_color_stats(path, max_samples=150000):
    """Distinct-color / near-black statistics; mono image ≈ broken black-block diagram.

    Samples pixels on an even grid (bounded work on large screenshots) and
    quantizes to 4 bits/channel for the distinct-color count.
    """
    w, h, channels, rows, plte = decode_png(Path(path).read_bytes())
    step = max(1, int(((w * h) / max_samples) ** 0.5))
    colors = set()
    black = sampled = 0
    for y in range(0, h, step):
        row = rows[y]
        for x in range(0, w, step):
            off = x * channels
            if channels == 1:
                r = g = b = row[off]
            elif channels == 2:
                r = g = b = row[off]
            elif channels == 3:
                r, g, b = row[off], row[off+1], row[off+2]
            elif channels == 4:
                r, g, b = row[off], row[off+1], row[off+2]
            else:
                r = g = b = 0
            if channels == 1 and plte:
                idx = row[off] * 3
                r, g, b = plte[idx], plte[idx+1], plte[idx+2]
            sampled += 1
            colors.add((r >> 4, g >> 4, b >> 4))
            if max(r, g, b) <= 32:
                black += 1
    near_black = round(black / sampled, 4) if sampled else None
    distinct = len(colors)
    mono = bool(distinct <= 2 or (near_black is not None and near_black >= 0.90))
    return {'png': str(path), 'width': w, 'height': h,
            'distinct_colors_q4': distinct, 'near_black_ratio': near_black,
            'sampled_pixels': sampled, 'mono': mono,
            'verdict': 'mono/黑块嫌疑' if mono else 'colorful'}


def _run_screenshot(browser, page_uri, out_png, width, height, budget):
    for headless in ('--headless=new', '--headless'):
        cmd = [browser, headless, '--disable-gpu', '--no-first-run', '--hide-scrollbars',
               f'--window-size={int(width)},{int(height)}',
               f'--virtual-time-budget={int(budget)}', f'--screenshot={out_png}', page_uri]
        try:
            subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if Path(out_png).is_file() and Path(out_png).stat().st_size > 0:
            return True
    return False


def pixel_probe_svg(svg_text, browser=None, work_dir=None, budget=8000):
    """Render one standalone SVG in headless Chrome and return pixel evidence."""
    browser = browser or find_browser()
    if not browser:
        return {'available': False, 'reason': '未找到 Chrome/Edge，pixel_probe 未执行'}
    m = re.search(r'viewBox="([\d.\s-]+)"', svg_text)
    vb_w = vb_h = 400.0
    if m:
        parts = m.group(1).split()
        if len(parts) == 4:
            vb_w, vb_h = float(parts[2]), float(parts[3])
    work = Path(work_dir) if work_dir else Path.cwd() / '.screenshot-audit-tmp'
    work.mkdir(parents=True, exist_ok=True)
    page = work / 'pixel-probe.html'
    page.write_text('<!doctype html><html><head><meta charset="utf-8">'
                    '<style>html,body{margin:0;background:#fff}svg{display:block}</style>'
                    '</head><body>' + svg_text + '</body></html>', 'utf-8', newline='\n')
    out_png = work / 'pixel-probe.png'
    width = min(max(int(vb_w) + 16, 240), 1600)
    height = min(max(int(vb_h) + 16, 240), 1600)
    if not _run_screenshot(browser, page.as_uri(), out_png, width, height, budget):
        return {'available': False, 'reason': '浏览器截图失败，pixel_probe 未执行'}
    try:
        stats = png_color_stats(out_png)
    except ValueError as exc:
        return {'available': False, 'reason': f'截图无法解析：{exc}'}
    stats['available'] = True
    return stats


def render_probe_page(html_path, browser=None, width=1440, height=1200, work=None, budget=8000):
    """Run diagram_probe.js against the real page: per-diagram computed evidence."""
    browser = browser or find_browser()
    if not browser:
        return None, '未找到 Chrome/Edge，renderprobe 未执行'
    if not DIAGRAM_PROBE_JS.is_file():
        return None, f'缺少图区探针脚本：{DIAGRAM_PROBE_JS}'
    data, err = run_page_probe(Path(html_path), DIAGRAM_PROBE_JS, browser, width, height, work, budget)
    if err:
        return None, err
    if not data.get('ok'):
        return None, '图区探针返回失败：' + json.dumps(data, ensure_ascii=False)[:300]
    return data.get('result', {}), None


def render_probe_verdict(result):
    """Turn computed diagram evidence into human-readable problems (empty = clean)."""
    problems = []
    for d in (result or {}).get('diagrams', []):
        idx = d.get('index')
        ratio = d.get('height_ratio')
        if ratio is not None and ratio < 0.9:
            problems.append(f'图 {idx}：渲染高度仅为 viewBox 自然高度的 {ratio}（被 CSS 压扁）')
        if d.get('container_scroll'):
            problems.append(f'图 {idx}：图容器出现内层滚动条（图必须全局显示）')
        total = d.get('shape_fill_total') or 0
        if total and d.get('black_fill_ratio', 0) > 0.5:
            problems.append(f'图 {idx}：{d.get("black_shape_fills")}/{total} 个图元填充为纯黑（样式失配/黑块特征）')
        if not d.get('text_count'):
            problems.append(f'图 {idx}：SVG 中没有任何 <text>（标签文字消失）')
        else:
            shape_fills = d.get('shape_fills') or {}
            text_fills = d.get('text_fills') or {}
            node_fill = max(shape_fills, key=shape_fills.get) if shape_fills else None
            text_fill = max(text_fills, key=text_fills.get) if text_fills else None
            if node_fill and text_fill and node_fill == text_fill:
                problems.append(f'图 {idx}：标签文字颜色与节点底色相同（{text_fill}），无可读对比')
    return problems


# ---------- 覆盖矩阵：截图集必须覆盖三宽度 × 首页/含图章节/交互态 ----------

COVERAGE_WIDTHS = (1440, 768, 390)
COVERAGE_ROLES = ('home', 'diagram', 'interactive')


def cmd_coverage(args):
    manifest = Path(args.manifest).expanduser().resolve()
    if not manifest.is_file():
        print(f'覆盖矩阵清单不存在：{manifest}')
        return 2
    try:
        data = json.loads(manifest.read_text('utf-8'))
        shots = data['shots']
        assert isinstance(shots, list)
    except Exception as exc:
        print(f'覆盖矩阵清单无法解析（需 JSON {{"shots": [{{"file","width","role"}}, …]}}）：{exc}')
        return 2
    problems = []
    slots = {}
    by_hash = {}
    for item in shots:
        try:
            f = Path(item['file'])
            width = int(item['width'])
            role = str(item['role'])
        except (KeyError, TypeError, ValueError):
            problems.append(f'清单项字段非法：{item}')
            continue
        if width not in COVERAGE_WIDTHS or role not in COVERAGE_ROLES:
            problems.append(f'清单项超出覆盖矩阵（width∈{COVERAGE_WIDTHS}，role∈{COVERAGE_ROLES}）：{item}')
            continue
        if not f.is_file():
            problems.append(f'截图文件缺失：{f}')
            continue
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        slots.setdefault((width, role), []).append(str(f))
        by_hash.setdefault(digest, []).append(str(f))
    for width in COVERAGE_WIDTHS:
        for role in COVERAGE_ROLES:
            if (width, role) not in slots:
                problems.append(f'覆盖矩阵缺项：width={width} role={role}')
    for digest, files in by_hash.items():
        if len(files) > 1:
            problems.append(f'字节级重复（拍摄失败嫌疑）sha256={digest[:16]}…：{files}')
    result = {'probe': 'coverage', 'manifest': str(manifest),
              'slots': {f'{w}/{r}': v for (w, r), v in sorted(slots.items())},
              'problems': problems, 'ok': not problems}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if problems:
        print('结论：截图集未通过覆盖矩阵——缺项或字节级重复（=拍摄失败）都必须补齐/重拍，才能进入 record-use 登记。')
        return 1
    print('OK：三宽度 × 首页/含图章节/交互态覆盖完整，且无字节级重复。')
    return 0


def cmd_renderprobe(args):
    page = Path(args.html).expanduser().resolve()
    if not page.is_file():
        print(f'HTML 不存在：{page}')
        return 2
    work = Path(args.work_dir).expanduser().resolve() if args.work_dir else page.parent / '.screenshot-audit-tmp'
    result, err = render_probe_page(page, args.browser, args.width, args.height, work, args.budget)
    if err:
        print(err)
        return 2
    problems = render_probe_verdict(result)
    out = {'probe': 'renderprobe', 'html': str(page), 'data': result,
           'problems': problems, 'ok': not problems}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if problems else 0


def cmd_pixelprobe(args):
    if args.svg:
        svg_text = Path(args.svg).expanduser().resolve().read_text('utf-8')
        work = Path(args.work_dir).expanduser().resolve() if args.work_dir else Path.cwd() / '.screenshot-audit-tmp'
        stats = pixel_probe_svg(svg_text, args.browser, work, args.budget)
        print(json.dumps({'probe': 'pixelprobe', **stats}, ensure_ascii=False, indent=2))
        if not stats.get('available'):
            return 2
        return 1 if stats.get('mono') else 0
    if not args.image:
        print('pixelprobe 需要一张 PNG，或 --svg FILE')
        return 2
    try:
        stats = png_color_stats(Path(args.image).expanduser().resolve())
    except (OSError, ValueError) as exc:
        print(f'截图无法分析：{exc}')
        return 2
    print(json.dumps({'probe': 'pixelprobe', **stats}, ensure_ascii=False, indent=2))
    return 1 if stats.get('mono') else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('dupcheck', help='截图字节级查重（相同哈希=拍摄失败）')
    d.add_argument('images', nargs='+')
    pr = sub.add_parser('probe', help='量测真实布局，区分溢出与截图裁切伪象')
    pr.add_argument('--html', required=True)
    pr.add_argument('--width', type=int, default=390)
    pr.add_argument('--height', type=int, default=800)
    pr.add_argument('--browser', help='Chrome/Edge 可执行文件路径')
    pr.add_argument('--work-dir', help='探针运行目录，默认 <html 目录>/.screenshot-audit-tmp')
    pr.add_argument('--budget', type=int, default=8000, help='--virtual-time-budget 毫秒')
    h = sub.add_parser('harness', help='生成负偏移 iframe 章节切片页')
    h.add_argument('--html', required=True)
    h.add_argument('--offset', type=int, required=True, help='向上偏移的像素（该章节距文档顶部的距离）')
    h.add_argument('--width', type=int, default=1440)
    h.add_argument('--height', type=int, default=900)
    h.add_argument('--out', required=True)
    rp = sub.add_parser('renderprobe', help='每幅 SVG 的渲染级检查（压扁/滚动条/黑块/标签对比）')
    rp.add_argument('--html', required=True)
    rp.add_argument('--width', type=int, default=1440)
    rp.add_argument('--height', type=int, default=1200)
    rp.add_argument('--browser', help='Chrome/Edge 可执行文件路径')
    rp.add_argument('--work-dir')
    rp.add_argument('--budget', type=int, default=8000)
    px = sub.add_parser('pixelprobe', help='截图/单图色彩多样性统计（黑块图 ≈ 单色）')
    px.add_argument('image', nargs='?')
    px.add_argument('--svg', help='独立 SVG：先渲染截图再统计')
    px.add_argument('--browser', help='Chrome/Edge 可执行文件路径')
    px.add_argument('--work-dir')
    px.add_argument('--budget', type=int, default=8000)
    cv = sub.add_parser('coverage', help='截图覆盖矩阵校验（3 宽度 × 首页/含图章节/交互态）')
    cv.add_argument('--manifest', required=True, help='JSON 清单：{"shots":[{"file","width","role"}…]}')
    args = p.parse_args(argv)
    if args.cmd == 'dupcheck':
        return cmd_dupcheck(args.images)
    if args.cmd == 'probe':
        return cmd_probe(args)
    if args.cmd == 'renderprobe':
        return cmd_renderprobe(args)
    if args.cmd == 'pixelprobe':
        return cmd_pixelprobe(args)
    if args.cmd == 'coverage':
        return cmd_coverage(args)
    return cmd_harness(args)


if __name__ == '__main__':
    sys.exit(main())
