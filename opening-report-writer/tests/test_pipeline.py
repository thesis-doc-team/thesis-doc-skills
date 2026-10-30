"""Structural smoke test only. Fake test fixtures MUST NOT be used as literature."""
import json
import re
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
import sys

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'scripts'))
from build_report import DEFAULT_TITLES, TEMPLATE, SHA_FILE, build, N, Q, text_of
from check_report import check

class TestPipeline(unittest.TestCase):
    def test_structure_without_editing_template(self):
        import hashlib
        before=hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()
        # All references below are deliberately synthetic & confined to the test environment.
        r=[{'text':f'测试作者{i}. 软件自动化格式校验占位文献[J]. 虚构测试刊物, 2020, 1(1): 1-2.',
            'source_url':f'https://example.invalid/synthetic/{i}', 'verified':True,'source_type':'journal'}
           for i in range(1,11)]
        sec=[]
        for j,t in enumerate(DEFAULT_TITLES,1):
            blocks=[] if j==7 else [{'type':'heading2','text':f'{j}.1 测试标题'},
                {'type':'paragraph','text':('这是一段专用于校验自动排版和版式约束的中文测试文字。'*12 + ('论证内容必须真实准确，尊重引用来源。'*40 if j<4 else '内容基于资料。'*18)) + ('[[cite:1-2]]' if j==1 else '')}]
            if j==6:
                blocks.append({'type':'schedule','items':[{'start_week':1,'end_week':2,'task':'准备环境并测试'}]})
            sec.append({'id':j,'title':t,'blocks':blocks})
        payload={'cover':{'title':'仅用于脚本测试'},'sections':sec,'references':r}
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'test.docx'
            build(payload,TEMPLATE,dest)
            report=check(TEMPLATE,dest,payload)
            self.assertEqual(report['status'],'PASS',report)
            self.assertEqual(report['metrics']['references'],10)
        self.assertEqual(before,hashlib.sha256(TEMPLATE.read_bytes()).hexdigest())

    def test_reference_paragraphs_are_left_aligned(self):
        """v2 回归：文献段落必须显式左对齐，避免两端对齐在长 URL 条目上拉伸大空隙。"""
        from lxml import etree
        r=[{'text':f'测试作者{i}. 对齐校验占位文献[J]. 虚构测试刊物, 2020, 1(1): 1-2.',
            'source_url':f'https://example.invalid/synthetic/{i}', 'verified':True,'source_type':'journal'}
           for i in range(1,11)]
        sec=[{'id':j,'title':t,'blocks':([] if j==7 else [{'type':'paragraph','text':'仅用于对齐检查的中文测试段落。'*20}])}
             for j,t in enumerate(DEFAULT_TITLES,1)]
        payload={'cover':{},'sections':sec,'references':r}
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'align.docx'
            build(payload,TEMPLATE,dest)
            with ZipFile(dest) as z:
                root=etree.fromstring(z.read('word/document.xml'))
            refs=[p for p in root.xpath('.//w:p',namespaces=N) if re.match(r'^\[\d+\]\s',text_of(p))]
            self.assertEqual(len(refs),10)
            for p in refs:
                jc=p.xpath('./w:pPr/w:jc',namespaces=N)
                self.assertEqual([x.get(Q('val')) for x in jc],['left'],text_of(p)[:30])

if __name__=='__main__':unittest.main()
