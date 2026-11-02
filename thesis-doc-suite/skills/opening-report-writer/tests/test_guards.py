"""Guardrail checks with synthetic internal data only."""
import sys, tempfile, json, zipfile
import unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'scripts'))
from build_report import build, validate_input, DEFAULT_TITLES, TEMPLATE
from check_report import check

class TestGuards(unittest.TestCase):
    def setUp(self):
        self.data={
            'cover':{},
            'sections':[{'id':i,'title':title,'blocks':([] if i==7 else [{'type':'paragraph','text':'仅供测试'}])} for i,title in enumerate(DEFAULT_TITLES,1)],
            'references':[{'text':f'模拟作者{i}. 非真实测试出处[J]. 软件测试, 2020, 1(1):1-2.', 'verified':True,'source_type':'journal','source_url':f'https://example.invalid/{i}'} for i in range(1,11)],
            'teacher_opinion':'该生围绕软件测试方向选题，能够查阅并整理相关文献，对国内外研究现状有较为系统的把握；开题报告结构完整、条理清晰，引用文献真实可查，写作规范。建议开题并按计划开展课题工作。'
        }
    def test_reject_meta_tail_opinion(self):
        """用户反馈回归：元话语尾巴（最终评价以指导教师审定为准 等）画蛇添足，validate_input 必须拦截。"""
        self.data['teacher_opinion']=self.data['teacher_opinion']+'最终评价以指导教师审定为准。'
        with self.assertRaises(ValueError):validate_input(self.data)
    def test_reject_unverified(self):
        self.data['references'][3]['verified']=False
        with self.assertRaisesRegex(ValueError,'未核查'):validate_input(self.data)
    def test_reject_non_source(self):
        self.data['references'][0]['source_url']='random words'
        with self.assertRaisesRegex(ValueError,'URL'):validate_input(self.data)
    def test_csdn_not_pretend_journal(self):
        self.data['references'][0]['source_url']='https://blog.csdn.net/test'
        with self.assertRaisesRegex(ValueError,'CSDN'):validate_input(self.data)
    def test_reject_direct_reference_text(self):
        self.data['sections'][0]['blocks'][0]['text']='正文错误引用[1]'
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'裸引用'):build(self.data,TEMPLATE,Path(d)/'bad.docx')
    def test_template_fixed(self):
        with tempfile.TemporaryDirectory() as d:
            clone=Path(d)/'official.docx'; clone.write_bytes(TEMPLATE.read_bytes()+b'123')
            with self.assertRaisesRegex(ValueError,'SHA256'):build(self.data,clone,Path(d)/'bad.docx')
    def test_check_rejects_justified_references(self):
        """v2 回归：终检必须拦下两端对齐的参考文献段落（防大空隙回归）。"""
        import re
        from zipfile import ZipFile, ZIP_DEFLATED
        from lxml import etree
        from build_report import N, Q, text_of
        with tempfile.TemporaryDirectory() as d:
            ok=Path(d)/'ok.docx'
            build(self.data,TEMPLATE,ok)
            with ZipFile(ok) as z:
                items={i.filename: z.read(i.filename) for i in z.infolist()}
            root=etree.fromstring(items['word/document.xml'])
            touched=0
            for p in root.xpath('.//w:p',namespaces=N):
                if re.match(r'^\[\d+\]\s',text_of(p)):
                    for jc in p.xpath('./w:pPr/w:jc',namespaces=N):
                        jc.set(Q('val'),'both'); touched+=1
            self.assertGreater(touched,0)
            items['word/document.xml']=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
            bad=Path(d)/'bad.docx'
            with ZipFile(bad,'w',ZIP_DEFLATED) as z:
                for n,b in items.items(): z.writestr(n,b)
            report=check(TEMPLATE,bad,self.data)
            self.assertEqual(report['status'],'FAIL')
            self.assertTrue(any('左对齐' in e for e in report['errors']),report['errors'])

    def test_reject_meta_tail_variant_opinion(self):
        # 用户复盘实撞：'最终评价以指导教师审定结果为准。'（插字绕禁语）同属元话语尾巴，validate_input/build 双拦
        self.data['teacher_opinion']=self.data['teacher_opinion']+'最终评价以指导教师审定结果为准。'
        with self.assertRaises(ValueError):validate_input(self.data)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):build(self.data,TEMPLATE,Path(d)/'bad.docx')
    def test_check_flags_meta_tail_variant(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as d:
            ok=Path(d)/'ok.docx';build(self.data,TEMPLATE,ok)
            mod=Document(ok)
            def all_paras(dd):
                for p in dd.paragraphs:yield p
                for t in dd.tables:
                    for row in t.rows:
                        for c in row.cells:
                            for p in c.paragraphs:yield p
            target=next(p for p in all_paras(mod) if '该生围绕软件测试方向选题' in p.text)
            target.add_run('最终评价以指导教师审定结果为准。')
            bad=Path(d)/'variant.docx';mod.save(bad)
            report=check(TEMPLATE,bad,self.data)
            self.assertEqual(report['status'],'FAIL')
            self.assertTrue(any('提示语' in e for e in report['errors']),report['errors'])
    def test_spec_sample_closing_passes_gates(self):
        # 防回归（用户审计）：SKILL 收束句样例喂给门禁必须通过——规范与门禁不得再分叉
        import re as _re
        m=_re.search(r'\*\*收束\*\*：`([^`]+)`',(BASE/'SKILL.md').read_text(encoding='utf-8'))
        self.assertIsNotNone(m,'SKILL 收束句样例未找到')
        closing=m.group(1)
        self.assertTrue(self.data['teacher_opinion'].endswith(closing))
        validate_input(self.data)
        data=dict(self.data)
        filler='本段为自动化测试合成文字，仅用于满足 check 正文 3000 汉字体量门槛，不含任何真实项目内容。'
        data['sections']=[dict(s,blocks=([{'type':'paragraph','text':filler*20}] if s['blocks'] else [])) for s in self.data['sections']]
        with tempfile.TemporaryDirectory() as d:
            ok=Path(d)/'ok.docx';build(data,TEMPLATE,ok)
            self.assertEqual(check(TEMPLATE,ok,data)['status'],'PASS')

if __name__=='__main__':unittest.main()
