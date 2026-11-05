"""Canary regression for the SVG render pipeline ("broken render, green checks" incident).

Run from the skill root: python tests/test_svg_pipeline.py

Layered honesty:
- CSS lint / prefix closure / damaged-sample detection / coverage matrix run
  everywhere (pure static, no engine needed).
- Full-pipeline canaries skip with an explicit message when Mermaid CLI (or
  Graphviz) is unavailable; render-level pixel/computed assertions skip when no
  Chrome/Edge exists.  They FAIL when the engine/browser exists but the probe
  cannot run — never a silent pass.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))

import diagram_svg  # noqa: E402
import render_html  # noqa: E402
import screenshot_audit  # noqa: E402
import validate_html  # noqa: E402

MD_TEXT = """# 合成示例 — 技术文档

> 仅用于防线测试，不含真实项目结论。

## 1. 系统总体架构
架构说明文字。

```mermaid
flowchart TD
  A[接收数据] --> B{质量校验}
  B -- 通过 --> C[输出结果]
```

## 2. 关键流程
流程说明文字。

```mermaid
flowchart LR
  D[等待指令] --> E[执行动作]
```
"""

TALL_MD_TEXT = """# 合成示例 — 技术文档

> 仅用于防线测试，不含真实项目结论。

## 1. 系统总体架构
架构说明文字。

```mermaid
flowchart TD
  N1[上电初始化] --> N2[读取传感器]
  N2 --> N3{数据有效?}
  N3 -- 是 --> N4[打包 JSON]
  N3 -- 否 --> N5[重试计数]
  N4 --> N6[UART 发送]
  N5 --> N2
  N6 --> N7[DTU 透传]
  N7 --> N8[云端确认]
```

## 2. 关键流程
流程说明文字。
"""

# 手工合成 SVG：标签文本与 MD_TEXT 的 Mermaid 源标签一一对应，自带闭合样式。
CRAFTED_SVG = (
    '<svg id="my-svg" class="flowchart" viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg">'
    '<style>#my-svg .node rect{fill:#f4f2ff;stroke:#8b88d8}#my-svg text{fill:#33415d}</style>'
    '<defs><linearGradient id="grad"><stop offset="0" stop-color="#f4f2ff"/></linearGradient></defs>'
    '<rect id="node-a" class="node" x="10" y="10" width="120" height="40" fill="url(#grad)"/>'
    '<text x="30" y="35">接收数据</text>'
    '<text x="30" y="95">质量校验</text>'
    '<text x="180" y="35">通过</text>'
    '<text x="30" y="155">输出结果</text>'
    '</svg>'
)

# 第二幅合成 SVG：对应 MD_TEXT 第 2 章的 Mermaid 源标签。
CRAFTED_SVG_2 = (
    '<svg id="my-svg" class="flowchart" viewBox="0 0 300 120" xmlns="http://www.w3.org/2000/svg">'
    '<style>#my-svg .node rect{fill:#f4f2ff;stroke:#8b88d8}#my-svg text{fill:#33415d}</style>'
    '<rect id="node-d" class="node" x="10" y="30" width="110" height="40" fill="#f4f2ff"/>'
    '<rect id="node-e" class="node" x="170" y="30" width="110" height="40" fill="#f4f2ff"/>'
    '<text x="35" y="55">等待指令</text>'
    '<text x="195" y="55">执行动作</text>'
    '</svg>'
)


def build_page(tmp, svg_texts=(CRAFTED_SVG, CRAFTED_SVG_2), md_text=MD_TEXT):
    """Run the real embed pipeline (sanitize -> prefix_svg_ids -> layout.html)."""
    svgdir = tmp / 'svg'
    svgdir.mkdir(exist_ok=True)
    for i, svg_text in enumerate(svg_texts, 1):
        (svgdir / f'{i}.svg').write_text(svg_text, 'utf-8', newline='\n')
    markup, _ = render_html.build({}, md_text, '合成示例-技术文档.md', svgdir, tmp)
    page = tmp / 'out.html'
    page.write_text(markup, 'utf-8', newline='\n')
    md = tmp / 'doc.md'
    md.write_text(md_text, 'utf-8', newline='\n')
    return page, md


def run_validate(page, md):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return validate_html.validate(str(page), str(md))


class TestCssLint(unittest.TestCase):
    """模板 CSS lint：未作用域元素选择器禁入；图区禁止压缩/滚动（全局显示）。"""

    def test_unscoped_element_selectors_flagged(self):
        css = 'svg{fill:#f00}\ndiv p{margin:0}\nspan{color:#333}\nsvg path{stroke:#000}\n'
        errors = validate_html.check_css_scope(css)
        self.assertEqual(len(errors), 4, errors)
        self.assertTrue(any('svg' in e for e in errors))
        self.assertTrue(any('div p' in e for e in errors))

    def test_scoped_selectors_are_legal(self):
        css = ('.chapter-contents p{margin:0}\n.vector-diagram svg{max-width:100%}\n'
               '.brand-icon svg{width:30px}\n#progress{width:0}\nbutton,input{font:inherit}\n'
               '*{box-sizing:border-box}\n')
        self.assertEqual(validate_html.check_css_scope(css), [])

    def test_squash_and_scroll_rules_flagged(self):
        # 事故根因③：max-height 压扁 + overflow 滚动条隐藏溢出；用户要求整图全局显示
        for css in ('.vector-diagram svg{max-height:685px}',
                    '.vector-diagram{overflow:auto;max-height:720px}',
                    '.vector-diagram svg{min-width:430px}'):
            errors = validate_html.check_diagram_display(css)
            self.assertTrue(errors, f'必须拦下：{css}')

    def test_scroll_rule_inside_media_query_flagged(self):
        css = '@media (max-width:760px){.vector-diagram svg{max-width:none;min-width:430px}}'
        self.assertTrue(validate_html.check_diagram_display(css))

    def test_layout_template_passes_lint(self):
        template = (SKILL_ROOT / 'assets' / 'layout.html').read_text('utf-8')
        css = '\n'.join(m for m in __import__('re').findall(r'<style>([\s\S]*?)</style>', template))
        self.assertEqual(validate_html.check_css_scope(css), [], 'layout.html 不得含未作用域元素选择器')
        self.assertEqual(validate_html.check_diagram_display(css), [], 'layout.html 不得压缩/滚动流程图')


class TestPrefixClosure(unittest.TestCase):
    """金丝雀 C：prefix_svg_ids 后零孤立 # 引用（钉事故根因①）。"""

    def test_prefix_keeps_style_closed(self):
        markup = render_html.svg_markup(CRAFTED_SVG)
        prefixed = render_html.prefix_svg_ids(markup, 'diagram-1-')
        from bs4 import BeautifulSoup
        closure = validate_html.svg_style_closure(BeautifulSoup(prefixed, 'html.parser'))
        self.assertTrue(closure['style_closure_ok'], closure)
        self.assertEqual(closure['orphan_refs'], [], '前缀化后不允许孤立 # 引用')
        self.assertTrue(closure['root_id_covered'])

    def test_unsynced_style_refs_are_detected(self):
        # 事故根因①的特征签名：<style> 选择器停在旧 id 上 → 必须被闭合检查抓住
        markup = render_html.svg_markup(CRAFTED_SVG)
        prefixed = render_html.prefix_svg_ids(markup, 'diagram-1-')
        broken = prefixed.replace('#diagram-1-', '#')
        from bs4 import BeautifulSoup
        closure = validate_html.svg_style_closure(BeautifulSoup(broken, 'html.parser'))
        self.assertFalse(closure['style_closure_ok'])
        self.assertTrue(closure['orphan_refs'])


class TestValidateDamageSamples(unittest.TestCase):
    """验收 1：故意破坏的样本必须被 validate 内容断言判 FAIL。"""

    def test_good_synthetic_page_passes(self):
        with tempfile.TemporaryDirectory() as td:
            page, md = build_page(Path(td))
            errors, warnings, info = run_validate(page, md)
            self.assertEqual(errors, [], errors)
            self.assertEqual(len(info['diagram_checks']), 2)
            for check in info['diagram_checks']:
                self.assertEqual(check['style_closure'], 'OK', check)
                self.assertEqual(check['label_hit_rate'], 1.0, check)

    def test_damage_orphan_style_selectors_fails(self):
        with tempfile.TemporaryDirectory() as td:
            page, md = build_page(Path(td))
            broken = page.read_text('utf-8').replace('#diagram-1-', '#')
            page.write_text(broken, 'utf-8', newline='\n')
            errors, _, _ = run_validate(page, md)
            self.assertTrue(any('样式不闭合' in e for e in errors), errors)

    def test_damage_removed_text_fails(self):
        with tempfile.TemporaryDirectory() as td:
            page, md = build_page(Path(td))
            import re as _re
            broken = _re.sub(r'<text[^>]*>[\s\S]*?</text>', '', page.read_text('utf-8'))
            page.write_text(broken, 'utf-8', newline='\n')
            errors, _, _ = run_validate(page, md)
            self.assertTrue(any('标签未全部存活' in e for e in errors), errors)

    def test_damage_max_height_squash_fails(self):
        with tempfile.TemporaryDirectory() as td:
            page, md = build_page(Path(td))
            broken = page.read_text('utf-8').replace(
                '</head>', '<style>.vector-diagram svg{max-height:685px}</style></head>')
            page.write_text(broken, 'utf-8', newline='\n')
            errors, _, _ = run_validate(page, md)
            self.assertTrue(any('全局显示' in e for e in errors), errors)


class TestFullPipelineCanary(unittest.TestCase):
    """金丝雀 A/B：完整管线（mmdc 渲染 → 净化 → 前缀化 → 嵌入 layout.html）。"""

    def _require_engine(self):
        status = diagram_svg.engine_status()
        if not status['svg_capable']:
            self.skipTest(f"缺 Mermaid CLI/Graphviz 或浏览器：完整管线金丝雀未测试（不谎称通过）：{status['install_hint']}")
        return status

    def test_canary_a_labels_survive_as_text(self):
        self._require_engine()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            diagrams = diagram_svg.render_diagrams(MD_TEXT, tmp / 'svg')
            for d in diagrams:
                self.assertIsNotNone(d['engine'], f"引擎可用却渲染失败：{d['warning']}")
            svg_texts = tuple((tmp / 'svg' / f'{d["index"]}.svg').read_text('utf-8')
                              for d in diagrams)
            page, md = build_page(tmp, svg_texts=svg_texts)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page.read_text('utf-8'), 'html.parser')
            svg = soup.select_one('.vector-diagram svg')
            self.assertEqual(len(svg.select('foreignobject')), 0,
                             'htmlLabels 配置生效特征：foreignObject 计数必须为 0')
            texts = [t.get_text() for t in svg.select('text')]
            for label in ('接收数据', '质量校验', '通过', '输出结果'):
                self.assertTrue(any(label in t for t in texts),
                                f'标签「{label}」必须以 <text> 存活，实际 text：{texts}')
            closure = validate_html.svg_style_closure(svg)
            self.assertTrue(closure['style_closure_ok'], closure)
            errors, _, _ = run_validate(page, md)
            self.assertEqual(errors, [], errors)

    def test_canary_b_tall_diagram_not_squashed_no_scrollbar(self):
        self._require_engine()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            diagrams = diagram_svg.render_diagrams(TALL_MD_TEXT, tmp / 'svg')
            self.assertIsNotNone(diagrams[0]['engine'], diagrams[0]['warning'])
            svgdir = tmp / 'svg2'
            svgdir.mkdir()
            (svgdir / '1.svg').write_text((tmp / 'svg' / '1.svg').read_text('utf-8'), 'utf-8', newline='\n')
            markup, _ = render_html.build({}, TALL_MD_TEXT, '合成示例-技术文档.md', svgdir, tmp)
            page = tmp / 'tall.html'
            page.write_text(markup, 'utf-8', newline='\n')
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(markup, 'html.parser')
            css = '\n'.join(s.get_text() for s in soup.find_all('style') if not s.find_parent('svg'))
            self.assertEqual(validate_html.check_diagram_display(css), [],
                             '产物 CSS 不得对图区设 max-height/overflow/min-width')
            browser = screenshot_audit.find_browser()
            if not browser:
                self.skipTest('本机无 Chrome/Edge：高度实测未执行（CSS 静态断言已通过）')
            result, err = screenshot_audit.render_probe_page(page, work=tmp / 'probe')
            self.assertIsNone(err, err)
            d = result['diagrams'][0]
            self.assertGreaterEqual(d['height_ratio'], 0.9, f"纵向图疑似被压扁：{d}")
            self.assertFalse(d['container_scroll'], f"图容器出现滚动条（必须全局显示）：{d}")


class TestRenderAndPixelProbe(unittest.TestCase):
    """金丝雀 D（渲染级）：fill 非默认黑、标签与节点底色有对比、截图 ≥3 色。"""

    def test_computed_fills_and_pixel_colors(self):
        browser = screenshot_audit.find_browser()
        if not browser:
            self.skipTest('本机无 Chrome/Edge：渲染级断言未测试（不谎称通过）')
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            page, md = build_page(tmp)
            result, err = screenshot_audit.render_probe_page(page, browser, work=tmp / 'probe')
            self.assertIsNone(err, err)
            d = result['diagrams'][0]
            self.assertEqual(d['black_shape_fills'], 0,
                             f"节点/图元填充出现纯黑（样式失配特征）：{d['shape_fills']}")
            self.assertGreater(d['text_count'], 0, '标签文字消失')
            shape_fills, text_fills = d['shape_fills'], d['text_fills']
            node_fill = max(shape_fills, key=shape_fills.get)
            text_fill = max(text_fills, key=text_fills.get)
            self.assertNotEqual(node_fill, text_fill, '标签文字颜色与节点底色相同，无可读对比')
            stats = screenshot_audit.pixel_probe_svg((tmp / 'svg' / '1.svg').read_text('utf-8'),
                                                     browser, tmp / 'pixel')
            self.assertTrue(stats.get('available'), stats)
            self.assertFalse(stats['mono'], f'图区域疑似单色/黑块：{stats}')
            self.assertGreaterEqual(stats['distinct_colors_q4'], 3, f'图区域色彩不足 3 色：{stats}')
            # 反向校准：纯黑块必须被判为 mono——探针真的能识破"黑块冒充 SVG"
            black_svg = ('<svg viewBox="0 0 1000 800" width="1000" height="800" '
                         'xmlns="http://www.w3.org/2000/svg">'
                         '<rect x="0" y="0" width="1000" height="800" fill="#000000"/></svg>')
            bad = screenshot_audit.pixel_probe_svg(black_svg, browser, tmp / 'pixel-black')
            self.assertTrue(bad.get('available'), bad)
            self.assertTrue(bad['mono'], f'黑块未被识别为 mono/黑块嫌疑：{bad}')


class TestCoverage(unittest.TestCase):
    """覆盖矩阵：3 宽度 × 首页/含图章节/交互态，缺项或字节级重复即不通过。"""

    def _manifest(self, td, slots):
        shots = []
        for i, (width, role, payload) in enumerate(slots):
            f = Path(td) / f'{role}-{width}-{i}.png'
            f.write_bytes(b'PNG-' + payload.encode())
            shots.append({'file': str(f), 'width': width, 'role': role})
        man = Path(td) / 'shots.json'
        man.write_text(json.dumps({'shots': shots}), 'utf-8', newline='\n')
        return man

    def _run(self, manifest):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            return screenshot_audit.main(['coverage', '--manifest', str(manifest)])

    def _full_matrix(self):
        return [(w, r, f'{w}-{r}-x') for w in (1440, 768, 390)
                for r in ('home', 'diagram', 'interactive')]

    def test_complete_matrix_passes(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(self._run(self._manifest(td, self._full_matrix())), 0)

    def test_missing_slot_fails(self):
        with tempfile.TemporaryDirectory() as td:
            slots = self._full_matrix()[:-1]
            self.assertEqual(self._run(self._manifest(td, slots)), 1)

    def test_duplicate_screenshots_fail(self):
        with tempfile.TemporaryDirectory() as td:
            man = self._manifest(td, self._full_matrix())
            data = json.loads(man.read_text('utf-8'))
            Path(data['shots'][1]['file']).write_bytes(Path(data['shots'][0]['file']).read_bytes())
            self.assertEqual(self._run(man), 1, '字节级重复 = 拍摄失败，必须重拍')

    def test_bad_manifest_errors(self):
        with tempfile.TemporaryDirectory() as td:
            man = Path(td) / 'shots.json'
            man.write_text('{"bad": 1}', 'utf-8', newline='\n')
            self.assertEqual(self._run(man), 2)


class TestPublishEvidence(unittest.TestCase):
    """验收 4：publish 报告逐图证据化 + <html>.audit.json 证据文件。"""

    def test_report_carries_per_diagram_evidence(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            md = tmp / '合成示例-技术文档.md'
            md.write_text(MD_TEXT, 'utf-8', newline='\n')
            (tmp / 'physical-modules.json').write_text(
                json.dumps({'schema_version': 1, 'generated_by': 'project-technical-doc', 'modules': []},
                           ensure_ascii=False), 'utf-8', newline='\n')
            proc = subprocess.run([sys.executable, str(SKILL_ROOT / 'scripts' / 'publish.py'),
                                   str(md), '--out-dir', str(tmp / 'out')],
                                  capture_output=True, text=True, encoding='utf-8',
                                  errors='replace', timeout=300)
            self.assertEqual(proc.returncode, 0, (proc.stdout, proc.stderr))
            report = json.loads((tmp / 'out' / '合成示例_用户展示.report.json').read_text('utf-8'))
            self.assertIn(report['status'], ('PASS', 'WARN'), report['errors'])
            self.assertTrue((tmp / 'out' / '合成示例_用户展示.audit.json').is_file(),
                            'record-use 登记证据 <html>.audit.json 必须生成')
            self.assertEqual(len(report['diagrams']), 2)
            for item in report['diagrams']:
                for key in ('mmdc_version', 'text_count', 'label_hit_rate', 'style_closure',
                            'estimated_min_font_px', 'pixel_probe'):
                    self.assertIn(key, item, f'report 逐图证据缺字段 {key}：{item}')
                if item['engine']:
                    self.assertEqual(item['label_hit_rate'], 1.0, item)
                    self.assertEqual(item['style_closure'], 'OK', item)
                    self.assertIsNotNone(item['estimated_min_font_px'], item)


if __name__ == '__main__':
    unittest.main(verbosity=2)
