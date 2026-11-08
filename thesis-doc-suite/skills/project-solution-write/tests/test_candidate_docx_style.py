"""Regression tests for the C-version magazine-style candidate DOCX.

Checks layout tokens/structures, dynamic feature counts, long text, no sample
content leakage, and that a revised version regenerates the same DOCX style.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from docx import Document
from docx.oxml.ns import qn
from render_candidate import make_docx
from discovery_registry import add_batch, revise


def generic_data(n=7, title=None, overview=None, desc_repeat=1):
    names = [
        '温度采集', '湿度采集', '光照采集', '本地显示',
        '超限报警', '无线上传', '阈值配置', '传感器异常提示',
        '历史记录', '页面切换',
    ]
    descs = [
        '采集环境温度并每 5 秒刷新显示，超过阈值时进入报警。',
        '采集空气湿度并显示当前值，低于阈值时提示干燥。',
        '采集光照强度并显示，用于判断是否需要补光。',
        '用 OLED 显示各环境量与状态，短按按键切换页面。',
        '环境量超限时蜂鸣器间歇鸣叫并在屏幕标记，恢复后解除。',
        '按周期把环境量与报警状态上传到管理页面。',
        '按场景设置报警阈值，保存后断电重启仍生效。',
        '传感器断线或超量程时显示故障标记，不误报。',
        '记录最近 50 次环境变化，按键可翻页查看。',
        '短按切页键在总览页、详情页和状态页之间切换。',
    ]
    features = [
        {'name': names[i], 'description': descs[i] * desc_repeat}
        for i in range(n)
    ]
    return {
        'title': title or '面向温室大棚的环境监测与预警系统',
        'overview': overview or '面向温室大棚，连续采集温度、湿度与光照，在本地屏幕显示并在超限时提醒；数据按周期上传到管理页面。',
        'signature': {'scenario': '温室大棚环境监测', 'domain': '设施农业'},
        'features': features,
    }


class TestCandidateDocxStyle(unittest.TestCase):
    def _make(self, data):
        tmp = tempfile.mkdtemp()
        path = Path(tmp) / '项目概览.docx'
        make_docx(data, path)
        return path, Document(path)

    def test_c_style_page_and_structure(self):
        path, doc = self._make(generic_data())
        sec = doc.sections[0]
        self.assertAlmostEqual(sec.page_width.cm, 21.0, places=1)
        self.assertAlmostEqual(sec.page_height.cm, 29.7, places=1)
        self.assertAlmostEqual(sec.top_margin.cm, 2.0, places=1)
        self.assertAlmostEqual(sec.bottom_margin.cm, 1.5, places=1)
        self.assertAlmostEqual(sec.left_margin.cm, 2.0, places=1)
        self.assertAlmostEqual(sec.right_margin.cm, 1.9, places=1)

        kicker = doc.paragraphs[0]
        self.assertEqual(kicker.text, 'P R O J E C T    O V E R V I E W')
        kr = kicker.runs[0]
        self.assertEqual(kr.font.name, 'Noto Sans CJK SC')
        self.assertAlmostEqual(kr.font.size.pt, 8.5, places=1)
        self.assertEqual(str(kr.font.color.rgb), 'B15A36')
        self.assertTrue(kr.bold)

        title = doc.paragraphs[1]
        self.assertEqual(title.text, generic_data()['title'])
        tr = title.runs[0]
        self.assertEqual(tr.font.name, 'Noto Serif CJK SC')
        self.assertAlmostEqual(tr.font.size.pt, 21.0, places=1)
        self.assertEqual(str(tr.font.color.rgb), '23302E')
        self.assertTrue(tr.bold)

        self.assertGreaterEqual(len(doc.tables), 2)
        overview = doc.tables[0]
        self.assertEqual(len(overview.rows), 1)
        self.assertEqual(len(overview.columns), 2)
        left, right = overview.rows[0].cells
        self.assertEqual(left._tc.tcPr.find(qn('w:shd')).get(qn('w:fill')), 'BC754D')
        self.assertEqual(right._tc.tcPr.find(qn('w:shd')).get(qn('w:fill')), 'FAF6F0')
        self.assertIn('项目概述', right.text)
        self.assertIn(generic_data()['overview'], right.text)

        features = doc.tables[1]
        self.assertEqual(len(features.columns), 3)
        self.assertEqual(len(features.rows), 7)
        for row in features.rows:
            self.assertIsNotNone(row._tr.trPr.find(qn('w:cantSplit')))
            for cell in row.cells:
                bottom = cell._tc.tcPr.find(qn('w:tcBorders')).find(qn('w:bottom'))
                self.assertEqual(bottom.get(qn('w:color')), 'E4DAD0')
        first = features.rows[0]
        self.assertEqual(first.cells[0].text, '01')
        self.assertEqual(first.cells[1].text, '温度采集')
        num = first.cells[0].paragraphs[0].runs[0]
        name = first.cells[1].paragraphs[0].runs[0]
        desc = first.cells[2].paragraphs[0].runs[0]
        self.assertEqual(num.font.name, 'Noto Serif CJK SC')
        self.assertAlmostEqual(num.font.size.pt, 12.0, places=1)
        self.assertEqual(str(num.font.color.rgb), 'BA754D')
        self.assertEqual(name.font.name, 'Noto Sans CJK SC')
        self.assertAlmostEqual(name.font.size.pt, 10.0, places=1)
        self.assertEqual(str(name.font.color.rgb), '293C37')
        self.assertAlmostEqual(desc.font.size.pt, 9.5, places=1)
        self.assertEqual(str(desc.font.color.rgb), '56635F')

        footer = sec.footer.paragraphs[0]
        self.assertIn('PROJECT OVERVIEW', footer.text)
        self.assertIn('项目概览', footer.text)
        top = footer._p.pPr.find(qn('w:pBdr')).find(qn('w:top'))
        self.assertEqual(top.get(qn('w:color')), 'BA754D')

    def test_dynamic_feature_counts(self):
        for count in (3, 7, 10):
            data = generic_data(count)
            path, doc = self._make(data)
            table = doc.tables[1]
            self.assertEqual(len(table.rows), count)
            doc_text = '\n'.join(cell.text for row in table.rows for cell in row.cells)
            for f in data['features']:
                self.assertIn(f['name'], doc_text)
                self.assertIn(f['description'], doc_text)

    def test_long_title_overview_and_description(self):
        long_title = '面向校园教学楼、实验楼与宿舍楼多场景的室内环境质量连续监测与异常分级提醒系统'
        long_overview = '面向校园多类室内场景，连续采集温度、湿度、二氧化碳与颗粒物，并在本地显示、分级报警和周期上传；网络中断时本地继续工作。' * 3
        data = generic_data(10, title=long_title, overview=long_overview, desc_repeat=3)
        path, doc = self._make(data)
        self.assertEqual(doc.paragraphs[1].text, long_title)
        self.assertIn(long_overview, doc.tables[0].rows[0].cells[1].text)
        table = doc.tables[1]
        self.assertEqual(len(table.rows), 10)
        for f in data['features']:
            self.assertIn(f['description'], '\n'.join(c.text for c in table.rows[data['features'].index(f)].cells))

    def test_generic_output_has_no_c_sample_text(self):
        path, doc = self._make(generic_data())
        all_text = '\n'.join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells])
        for forbidden in ('MPU6050', '老人助行拐杖', '倾倒检测', '夜间寻杖', 'HC-SR04'):
            self.assertNotIn(forbidden, all_text)

    def test_revised_version_regenerates_c_style_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = generic_data(7)
            created = add_batch(root, {'projects': [base]})
            pid = created['created'][0]['project_id']
            revised = generic_data(8)
            revised['features'][7]['name'] = '操作记录'
            revised['features'][7]['description'] = '记录最近 50 次库存变化的时间与增减数量，按键可翻页查看。'
            result = revise(root, pid, {**revised, 'change_summary': '新增操作记录'})
            self.assertEqual(result['version'], 'v1.1')
            v10 = root / 'projects' / pid / 'versions' / 'v1.0' / '项目概览.docx'
            v11 = root / 'projects' / pid / 'versions' / 'v1.1' / '项目概览.docx'
            self.assertTrue(v10.is_file())
            self.assertTrue(v11.is_file())
            self.assertEqual(len(Document(v10).tables[1].rows), 7)
            self.assertEqual(len(Document(v11).tables[1].rows), 8)

    def test_skill_references_c_style(self):
        skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('candidate-docx-magazine-style.md', skill)
        self.assertTrue((ROOT / 'assets' / 'reference-samples' / 'candidate-overview-reference-C.docx').is_file())
        self.assertTrue((ROOT / 'references' / 'candidate-docx-magazine-style.md').is_file())


if __name__ == '__main__':
    unittest.main()