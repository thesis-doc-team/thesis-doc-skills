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
            'references':[{'text':f'模拟作者{i}. 非真实测试出处[J]. 软件测试, 2020, 1(1):1-2.', 'verified':True,'source_type':'journal','source_url':f'https://example.invalid/{i}'} for i in range(1,11)]
        }
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

if __name__=='__main__':unittest.main()
