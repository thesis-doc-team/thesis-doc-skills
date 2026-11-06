#!/usr/bin/env python3
"""Regression: figure_qc must emit a FAIL report, not crash, when spec geometry fails.

The original bug: check_spec() returns None after a BLOCK, then
``result["drawio"] = ...`` raised TypeError instead of printing the FAIL JSON.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QC = ROOT / 'scripts' / 'figure_qc.py'
EXAMPLES = ROOT / 'examples'


def failing_spec():
    # Overlapping nodes: route_spec raises RoutingError, check_spec returns None.
    return {
        'figure_number': '4-1',
        'caption_zh': '测试失败图',
        'caption_en': 'Failure Path Test Diagram',
        'source_refs': [{'section': '测试', 'lines': [1], 'evidence': 'synthetic regression'}],
        'width_mm': 155, 'height_mm': 120, 'font_pt': 9.5,
        'nodes': [
            {'id': 'a', 'label': '节点 A', 'x': 10, 'y': 10, 'w': 60, 'h': 20},
            {'id': 'b', 'label': '节点 B', 'x': 20, 'y': 10, 'w': 60, 'h': 20},
        ],
        'edges': [{'from': 'a', 'to': 'b'}],
    }


class FigureQCFailurePathTests(unittest.TestCase):
    def test_geometry_block_with_drawio_still_returns_fail_json(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            spec = folder / 'bad.json'
            spec.write_text(json.dumps(failing_spec(), ensure_ascii=False), 'utf-8')
            proc = subprocess.run(
                [sys.executable, str(QC), '--spec', str(spec),
                 '--drawio', str(EXAMPLES / 'orthogonal-flow-example.drawio')],
                capture_output=True, text=True, encoding='utf-8', errors='replace')
            self.assertEqual(proc.returncode, 2, (proc.stdout, proc.stderr))
            self.assertNotIn('Traceback', proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report['status'], 'FAIL')
            self.assertTrue(any(x.get('code') == 'GEOMETRY_OR_CAPTION_BLOCK'
                                for x in report['issues']), report)

    def test_geometry_block_with_all_optional_inputs_still_returns_fail_json(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            spec = folder / 'bad.json'
            spec.write_text(json.dumps(failing_spec(), ensure_ascii=False), 'utf-8')
            proc = subprocess.run(
                [sys.executable, str(QC), '--spec', str(spec),
                 '--svg', str(EXAMPLES / 'orthogonal-flow-example.svg'),
                 '--drawio', str(EXAMPLES / 'orthogonal-flow-example.drawio'),
                 '--vsdx', str(EXAMPLES / 'orthogonal-flow-example.vsdx')],
                capture_output=True, text=True, encoding='utf-8', errors='replace')
            self.assertEqual(proc.returncode, 2, (proc.stdout, proc.stderr))
            self.assertNotIn('Traceback', proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()