#!/usr/bin/env python3
"""Geometry/visual QC regression for rendered SVG diagrams (synthetic data)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import diagram_qc  # noqa: E402


def svg(viewbox, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">{body}</svg>'


class DiagramGeometryQCTests(unittest.TestCase):
    def test_too_wide_and_tiny_font_fails(self):
        body = ('<rect x="10" y="10" width="200" height="80"/>'
                '<rect x="400" y="10" width="200" height="80"/>'
                '<text x="110" y="55" font-size="12" text-anchor="middle">节点A</text>'
                '<text x="500" y="55" font-size="12" text-anchor="middle">节点B</text>')
        report = diagram_qc.check_svg(svg('0 0 3000 300', body))
        self.assertEqual(report['status'], 'FAIL')
        self.assertTrue(any('最小字号' in e or '图过宽' in e for e in report['errors']), report)

    def test_moderately_wide_is_warning_not_failure(self):
        body = ('<rect x="10" y="10" width="100" height="50"/>'
                '<rect x="500" y="10" width="100" height="50"/>'
                '<text x="60" y="40" font-size="16" text-anchor="middle">A</text>'
                '<text x="550" y="40" font-size="16" text-anchor="middle">B</text>')
        report = diagram_qc.check_svg(svg('0 0 700 100', body))
        self.assertEqual(report['status'], 'WARN', report)
        self.assertTrue(any('图偏宽' in w for w in report['warnings']), report)

    def test_detached_edge_fails(self):
        body = ('<defs><marker id="arrow"><path d="M0,0 L6,3 L0,6 z"/></marker></defs>'
                '<rect x="20" y="20" width="100" height="60"/>'
                '<rect x="260" y="20" width="100" height="60"/>'
                '<path d="M 130 50 L 200 50" marker-end="url(#arrow)"/>')
        report = diagram_qc.check_svg(svg('0 0 400 200', body))
        self.assertEqual(report['status'], 'FAIL')
        self.assertTrue(any('端点未接到节点' in e for e in report['errors']), report)

    def test_overlapping_text_fails(self):
        body = ('<rect x="20" y="20" width="100" height="60"/>'
                '<rect x="200" y="20" width="100" height="60"/>'
                '<text x="70" y="50" font-size="20" text-anchor="middle">中文文字</text>'
                '<text x="90" y="50" font-size="20" text-anchor="middle">中文文字</text>')
        report = diagram_qc.check_svg(svg('0 0 400 200', body))
        self.assertEqual(report['status'], 'FAIL')
        self.assertTrue(any('文字重叠' in e for e in report['errors']), report)

    def test_overlapping_nodes_fails(self):
        body = ('<rect x="20" y="20" width="100" height="60"/>'
                '<rect x="60" y="20" width="100" height="60"/>'
                '<text x="70" y="50" font-size="12">A</text>'
                '<text x="110" y="50" font-size="12">B</text>')
        report = diagram_qc.check_svg(svg('0 0 400 200', body))
        self.assertEqual(report['status'], 'FAIL')
        self.assertTrue(any('节点重叠' in e for e in report['errors']), report)

    def test_many_nodes_in_architecture_are_not_penalized_by_count(self):
        # 60 readable, non-overlapping nodes: information completeness matters,
        # node count alone must not fail or warn.
        parts = []
        for i in range(60):
            x = (i % 10) * 110 + 10
            y = (i // 10) * 70 + 10
            parts.append(f'<rect x="{x}" y="{y}" width="90" height="42"/>')
            parts.append(f'<text x="{x + 45}" y="{y + 28}" font-size="14" text-anchor="middle">节点{i}</text>')
        report = diagram_qc.check_svg(svg('0 0 1200 500', ''.join(parts)))
        self.assertIn(report['status'], ('PASS', 'WARN'), report)
        self.assertFalse(any('节点数' in w or '图过密' in w for w in report['warnings']), report)

    def test_good_diagram_passes(self):
        body = ('<defs><marker id="arrow"><path d="M0,0 L6,3 L0,6 z"/></marker></defs>'
                '<rect x="20" y="40" width="100" height="60"/>'
                '<rect x="260" y="40" width="100" height="60"/>'
                '<path d="M 120 70 L 260 70" marker-end="url(#arrow)"/>'
                '<text x="70" y="75" font-size="14" text-anchor="middle">A</text>'
                '<text x="310" y="75" font-size="14" text-anchor="middle">B</text>')
        report = diagram_qc.check_svg(svg('0 0 400 200', body))
        self.assertEqual(report['status'], 'PASS', report)


if __name__ == '__main__':
    unittest.main()