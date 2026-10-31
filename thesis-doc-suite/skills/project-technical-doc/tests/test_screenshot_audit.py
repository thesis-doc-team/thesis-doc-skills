"""Regression tests for screenshot_audit.py / diagram_svg.py engine pre-flight /
check_markdown.py mandatory-diagram gate.

Run from the skill root: python tests/test_screenshot_audit.py
Browser-dependent probe cases skip when no Chrome/Edge is available (and say
so honestly); they FAIL if a browser exists but the probe cannot run.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))

import check_markdown  # noqa: E402
import diagram_svg  # noqa: E402
import screenshot_audit  # noqa: E402

GOOD_MD = """# 示例系统技术文档

## 1. 项目概述
简介正文。

## 2. 系统总体架构
架构说明。

```mermaid
flowchart TD
    A[感知层] --> B[控制层]
```

## 3. 关键流程
采集流程。

```mermaid
flowchart LR
    S[采集] --> T[判断]
```
"""


class TestDupcheck(unittest.TestCase):
    def test_identical_screenshots_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / 'a.png'; b = Path(td) / 'b.png'; c = Path(td) / 'c.png'
            a.write_bytes(b'PNG-FAKE-CONTENT')
            b.write_bytes(b'PNG-FAKE-CONTENT')
            c.write_bytes(b'PNG-OTHER-CONTENT')
            rc = screenshot_audit.cmd_dupcheck([str(a), str(b), str(c)])
            self.assertEqual(rc, 1, '字节级相同的截图必须被判为拍摄失败嫌疑')

    def test_distinct_screenshots_pass(self):
        with tempfile.TemporaryDirectory() as td:
            files = []
            for i in range(3):
                f = Path(td) / f'{i}.png'
                f.write_bytes(b'PNG-' + bytes([i]))
                files.append(str(f))
            self.assertEqual(screenshot_audit.cmd_dupcheck(files), 0)

    def test_missing_file_reports_error(self):
        self.assertEqual(screenshot_audit.cmd_dupcheck(['no-such-file.png']), 2)


class TestHarness(unittest.TestCase):
    def test_negative_offset_iframe_generated(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'h.html'
            screenshot_audit.make_harness('file:///E:/x/page.html', 1440, 900, out, offset=10319)
            text = out.read_text('utf-8')
            self.assertIn('top:-10319px', text)
            self.assertIn('width:1440px', text)
            self.assertIn('src="file:///E:/x/page.html"', text)
            self.assertIn('overflow:hidden', text)


class TestProbeParsing(unittest.TestCase):
    def test_pre_regex_extracts_json(self):
        payload = json.dumps({'ok': True, 'result': {'realHorizontalOverflow': False}})
        dom = f'<html><body><pre id="screenshot-audit-probe" style="display:none">{payload}</pre></body></html>'
        m = screenshot_audit.PRE_RE.search(dom)
        self.assertIsNotNone(m)
        self.assertEqual(json.loads(m.group(1))['ok'], True)

    def test_aggregator_writes_once(self):
        self.assertIn('finish', screenshot_audit.AGGREGATOR_JS)
        self.assertIn('setInterval', screenshot_audit.AGGREGATOR_JS)


class TestEnginePreFlight(unittest.TestCase):
    def test_engine_status_shape(self):
        status = diagram_svg.engine_status()
        self.assertIn('svg_capable', status)
        self.assertIn('install_hint', status)
        self.assertIn('mmdc_version', status)
        # 诚实能力：mmdc 必须有浏览器（puppeteer）才算可渲染，防"装了引擎却零 SVG"假绿
        expected = bool((status['mermaid_cli'] and status['puppeteer_browser']) or status['graphviz_dot'])
        self.assertEqual(status['svg_capable'], expected)

    def test_engine_cli_exit_matches_capability(self):
        import subprocess
        proc = subprocess.run([sys.executable, str(SKILL_ROOT / 'scripts' / 'diagram_svg.py'), 'engine'],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        data = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0 if data['svg_capable'] else 2)


class TestMarkdownDiagramMandate(unittest.TestCase):
    """MD 必须自带 Mermaid 图（强制）：无图 MD 不得进入 HTML 阶段。"""

    def _check(self, text):
        with tempfile.TemporaryDirectory() as td:
            md = Path(td) / 'doc.md'
            md.write_text(text, 'utf-8', newline='\n')
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                return check_markdown.check(md), buf.getvalue()

    def test_good_md_with_diagrams_passes(self):
        rc, _ = self._check(GOOD_MD)
        self.assertEqual(rc, 0, '含架构图与流程图的 MD 必须通过')

    def test_md_without_any_mermaid_fails(self):
        rc, out = self._check('# 只有文字\n\n## 1. 项目概述\n无图正文。\n')
        self.assertEqual(rc, 1, '一幅 Mermaid 图都没有的 MD 必须 FAIL')
        self.assertIn('未包含任何 Mermaid 图', out)

    def test_architecture_chapter_without_diagram_fails(self):
        md = GOOD_MD.replace('```mermaid\nflowchart TD\n    A[感知层] --> B[控制层]\n```', '架构只有文字。')
        rc, out = self._check(md)
        self.assertEqual(rc, 1, '「系统总体架构」章无图必须 FAIL')
        self.assertIn('系统总体架构', out)

    def test_flow_chapter_without_diagram_fails(self):
        md = GOOD_MD.replace('```mermaid\nflowchart LR\n    S[采集] --> T[判断]\n```', '流程只有文字。')
        rc, out = self._check(md)
        self.assertEqual(rc, 1, '「关键流程」章无图必须 FAIL')
        self.assertIn('关键流程', out)


class TestProbeEndToEnd(unittest.TestCase):
    def _probe(self, body_html, width):
        with tempfile.TemporaryDirectory() as td:
            page = Path(td) / 'page.html'
            page.write_text('<!doctype html><html><head><meta charset="utf-8">'
                            '<style>body{margin:0}</style></head><body>' + body_html + '</body></html>',
                            'utf-8', newline='\n')
            return screenshot_audit.main(['probe', '--html', str(page), '--width', str(width),
                                          '--work-dir', str(Path(td) / 'run')])

    def test_overflow_measurement(self):
        if not screenshot_audit.find_browser():
            self.skipTest('本机无 Chrome/Edge：probe 端到端未测试（不谎称通过）')
        rc_no = self._probe('<p style="width:100%">正常内容</p>', 390)
        self.assertEqual(rc_no, 0, '无溢出页面必须量测为无真溢出')
        rc_yes = self._probe('<div style="width:600px;height:20px"></div>', 390)
        self.assertEqual(rc_yes, 1, '600px 固定宽元素在 390 视口必须量测为真溢出')


if __name__ == '__main__':
    unittest.main(verbosity=2)
