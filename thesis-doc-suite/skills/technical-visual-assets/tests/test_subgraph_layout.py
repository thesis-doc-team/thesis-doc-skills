#!/usr/bin/env python3
"""Subgraph layout, group-frame style and <br/> normalization regression."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import figure_qc as qc  # noqa: E402
import subgraph_layout  # noqa: E402
import visio_diagram as vd  # noqa: E402

SVG = 'http://www.w3.org/2000/svg'


def grouped_spec():
    return {
        'figure_number': '7-3', 'caption_zh': '计时分组流程',
        'caption_en': 'Timing Group Flow',
        'source_refs': [{'section': '测试', 'lines': [1], 'evidence': 'synthetic'}],
        'width_mm': 155, 'height_mm': 140, 'font_pt': 9.5,
        'layout': 'subgraph', 'auto_layout': True,
        'groups': [
            {'id': 'g1', 'label': '计时分组 A', 'x': 2, 'y': 2, 'w': 60, 'h': 40},
            {'id': 'g2', 'label': '计时分组 B', 'x': 40, 'y': 20, 'w': 60, 'h': 40},
        ],
        'nodes': [
            {'id': 'a', 'label': 'D1_Process()<br/>读 USART2', 'shape': 'rect',
             'x': 10, 'y': 10, 'w': 40, 'h': 16, 'group': 'g1'},
            {'id': 'b', 'label': 'SHT40_ReadTick()<br/>I2C 读 6 字节', 'shape': 'rect',
             'x': 10, 'y': 30, 'w': 40, 'h': 16, 'group': 'g1'},
            {'id': 'c', 'label': 'RS485_Process()<br/>收 9 字节并 CRC', 'shape': 'rect',
             'x': 50, 'y': 20, 'w': 40, 'h': 16, 'group': 'g2'},
            {'id': 'd', 'label': 'Warn_Process()<br/>越限判定', 'shape': 'rect',
             'x': 50, 'y': 40, 'w': 40, 'h': 16, 'group': 'g2'},
        ],
        'edges': [{'from': 'a', 'to': 'c'}, {'from': 'b', 'to': 'd'}, {'from': 'c', 'to': 'd'}],
    }


class SubgraphLayoutTests(unittest.TestCase):
    def test_layout_separates_groups_and_keeps_members_inside(self):
        spec = subgraph_layout.layout(grouped_spec())
        groups = spec['groups']
        self.assertEqual(len(groups), 2)
        # frames do not overlap
        a, b = groups[0], groups[1]
        overlap_x = max(0, min(a['x'] + a['w'], b['x'] + b['w']) - max(a['x'], b['x']))
        overlap_y = max(0, min(a['y'] + a['h'], b['y'] + b['h']) - max(a['y'], b['y']))
        self.assertEqual(overlap_x * overlap_y, 0, (a, b))
        # member nodes are fully inside their own frame
        for n in spec['nodes']:
            g = next(x for x in groups if x['id'] == n['group'])
            self.assertGreaterEqual(n['x'], g['x'])
            self.assertGreaterEqual(n['y'], g['y'])
            self.assertLessEqual(n['x'] + n['w'], g['x'] + g['w'] + 0.01)
            self.assertLessEqual(n['y'] + n['h'], g['y'] + g['h'] + 0.01)
        # layout must not drop nodes or edges
        self.assertEqual(len(spec['nodes']), 4)
        self.assertEqual(len(spec['edges']), 3)

    def test_br_labels_are_normalized(self):
        spec = subgraph_layout.normalize_labels(grouped_spec())
        for n in spec['nodes']:
            self.assertNotIn('<br', n['label'].lower())
        self.assertIn('\n', spec['nodes'][0]['label'])

    def test_render_has_dashed_filled_labelled_groups(self):
        routed, w, h, font, coords = vd.prepare_spec(grouped_spec(), require_caption=True)
        with tempfile.TemporaryDirectory() as td:
            svg = vd.svg_diagram(grouped_spec(), Path(td) / 'g.svg', require_caption=True)
            root = ET.fromstring(svg.read_bytes())
            groups = root.findall(f".//{{{SVG}}}rect[@data-group='1']")
            self.assertEqual(len(groups), 2)
            for g in groups:
                self.assertEqual(g.attrib.get('stroke-dasharray'), '2.2,1.35')
                self.assertNotEqual(g.attrib.get('fill', 'none'), 'none')
            labels = root.findall(f".//{{{SVG}}}text[@data-group-label='1']")
            self.assertEqual(len(labels), 2)
            for t in root.findall(f".//{{{SVG}}}text"):
                self.assertNotIn('<br', ''.join(t.itertext()).lower())
            report, issues, warnings = qc.check_spec(grouped_spec(), require_caption=True)
            self.assertEqual(issues, [], report)
            self.assertEqual(report['group_issues'], [])

    def test_overlapping_group_frames_are_rejected_by_qc(self):
        spec = grouped_spec()
        spec.pop('layout', None)
        spec.pop('auto_layout', None)
        # Force overlapping frames; no auto layout.
        spec['groups'] = [
            {'id': 'g1', 'label': '计时分组 A', 'x': 2, 'y': 2, 'w': 100, 'h': 60},
            {'id': 'g2', 'label': '计时分组 B', 'x': 40, 'y': 20, 'w': 100, 'h': 60},
        ]
        report, issues, warnings = qc.check_spec(spec, require_caption=True)
        self.assertTrue(any(x['code'] == 'GROUP_LAYOUT' for x in issues), issues)


if __name__ == '__main__':
    unittest.main()