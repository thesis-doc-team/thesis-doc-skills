"""v4 tests: midterm-style manifest separation + first-line indentation regression."""
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_report import TEMPLATE, DEFAULT_TITLES, build, N, Q, text_of
from check_report import check

class UpgradedContract(unittest.TestCase):
    def test_official_template_lock(self):
        j=json.loads((ROOT/'assets/template-lock.json').read_text(encoding='utf-8'))
        self.assertEqual(j['sha256'],hashlib.sha256(TEMPLATE.read_bytes()).hexdigest())
        self.assertEqual(j['bytes'],TEMPLATE.stat().st_size)
        self.assertEqual(j['table_rows'],[2])

    def test_sample_manifest(self):
        j=json.loads((ROOT/'assets/reference-samples/samples-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(j['samples']),1)
        for s in j['samples']:
            path=ROOT/'assets/reference-samples'/s['file']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),s['sha256'])
            self.assertNotEqual(hashlib.sha256(path.read_bytes()).hexdigest(),hashlib.sha256(TEMPLATE.read_bytes()).hexdigest())

    def test_render_precheck_detects_blank_last_page(self):
        import inspect
        from render_visual import render
        code=inspect.getsource(render)
        self.assertIn("page_rows[-1]['text_chars'] < 30",code)

    def test_qa_rejects_missing_firstline_indent(self):
        refs=[{'text':f'测试{i}号. 自动化测试占位文献[J]. 虚构刊物, 2020, 2(1): 1-4.',
               'source_url':f'https://example.invalid/test/{i}','verified':True,'source_type':'journal'}
               for i in range(1,11)]
        sections=[{'id':i,'title':t,'blocks':([] if i==7 else
             [{'type':'paragraph','text':'这个段落只用于验证真实首行缩进属性是否丢失。'*150}])}
             for i,t in enumerate(DEFAULT_TITLES,1)]
        payload={'cover':{},'sections':sections,'references':refs,
                 'teacher_opinion':'该生围绕自动化测试方向选题，能够查阅并整理相关文献，对国内外研究现状有较为系统的把握；开题报告结构完整、条理清晰，引用文献真实可查，写作规范。建议开题并按计划开展课题工作。'}
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); dest=d/'good.docx'; corrupt=d/'bad.docx'
            build(payload,TEMPLATE,dest)
            self.assertEqual(check(TEMPLATE,dest,payload)['status'],'PASS')
            with ZipFile(dest) as z:
                xml=etree.fromstring(z.read('word/document.xml'))
                ps=xml.xpath('./w:body/w:tbl/w:tr[1]/w:tc/w:p',namespaces=N)
                victim=next(p for p in ps if '这个段落只用于验证' in text_of(p))
                victim.xpath('./w:pPr/w:ind',namespaces=N)[0].attrib.pop(Q('firstLine'))
                updated=etree.tostring(xml,xml_declaration=True,encoding='UTF-8',standalone=True)
                with ZipFile(corrupt,'w') as w:
                    for ent in z.infolist(): w.writestr(ent,updated if ent.filename=='word/document.xml' else z.read(ent.filename))
            result=check(TEMPLATE,corrupt,payload)
            self.assertEqual(result['status'],'FAIL')
            self.assertTrue(any('首行缩进' in x for x in result['errors']))

if __name__=='__main__': unittest.main()
