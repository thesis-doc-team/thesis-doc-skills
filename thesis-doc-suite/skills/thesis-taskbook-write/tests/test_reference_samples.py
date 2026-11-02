"""Audit the bundled read-only anonymized samples, template lock and output immutability."""
import sys,hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from docx import Document
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from template_lock import verify
from inspect_reference_styles import audit
from fill_taskbook import write

class SampleAndLockTests(unittest.TestCase):
    def test_four_samples_are_readable_and_anonymous(self):
        folder=ROOT/'assets/reference-samples'
        data=json.loads((folder/'samples-manifest.json').read_text(encoding='utf8'))
        self.assertEqual(len(data['samples']),4)
        # Only generic failure markers are embedded in distributable tests. Never
        # ship the names/student IDs of original document authors in test source.
        forbidden=('WPS Office_', 'Air724UG', '阿里云平台', 'STM32F103')
        for x in data['samples']:
            file=folder/x['file']
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),x['sha256'])
            doc=Document(file)
            self.assertEqual((len(doc.tables),len(doc.tables[0].rows),len(doc.tables[0].columns)),(1,9,4))
            with zipfile.ZipFile(file) as z:
                text='\n'.join(z.read(n).decode('utf8','ignore') for n in z.namelist() if n.endswith(('.xml','.rels')))
                self.assertFalse(any(s in text for s in forbidden),file.name)
                self.assertNotIn('docProps/custom.xml',z.namelist())
                self.assertFalse(any(x.startswith('customXml/') for x in z.namelist()))
                self.assertFalse(any(x.startswith('word/fonts/') for x in z.namelist()))
                self.assertNotIn('word/_rels/fontTable.xml.rels',z.namelist())
                self.assertNotIn('WPS Office_',text)
                self.assertNotIn('lastPrinted',text)
                self.assertNotIn('2025-05-',text)
            self.assertNotIn('504',doc.tables[0].cell(1,3).text)
            self.assertIn('示例',doc.tables[0].cell(1,1).text)
            self.assertIn('示例',doc.tables[0].cell(4,1).text)
            for paragraph in doc.tables[0].cell(6,0).paragraphs:
                if '仅展示引用排版' in paragraph.text and paragraph._p.xpath('./w:pPr/w:numPr'):
                    self.assertFalse(paragraph.text.lstrip().startswith('['),file.name)

    def test_style_audit_is_reproducible(self):
        paths=sorted((ROOT/'assets/reference-samples').glob('sample-*.docx'))
        got=audit(paths)
        saved=json.loads((ROOT/'references/sample-style-audit.json').read_text(encoding='utf8'))
        self.assertEqual(got,saved)
        self.assertEqual(got['roles']['进度']['count'],24)

    def test_locked_template_original(self):
        self.assertEqual(len(verify(ROOT/'assets/official-taskbook-template.docx')),64)
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'other.docx'
            bad.write_bytes((ROOT/'assets/official-taskbook-template.docx').read_bytes()+b'X')
            with self.assertRaises(ValueError):verify(bad)


    def test_midterm_progress_asset_coexistence(self):
        # A midterm-progress asset is shared, but cannot be silently converted to a taskbook schedule.
        import subprocess
        tool=ROOT/'scripts/project_assets.py'
        with tempfile.TemporaryDirectory() as td:
            project=Path(td)
            def call(*args):
                p=subprocess.run([sys.executable,str(tool),*args],capture_output=True,text=True)
                if p.returncode!=0:raise AssertionError(p.stderr)
                return p.stdout
            call('init','--root',str(project),'--project-id','SHARED-PROJECT','--name','联调测试')
            aset=project/'project-assets'
            f=Path(td)/'progress-incoming.json'
            f.write_text(json.dumps({'project_id':'SHARED-PROJECT','items':[{'id':'PROG-001','as_of':'2026-10-01',
              'category':'in_progress','status':'draft','description':'仅供软件兼容性测试的示例进度',
              'source':'测试用例；非真实技术证据'}]},ensure_ascii=False),encoding='utf8')
            call('merge','--root',str(project),'--kind','progress','--input',str(f))
            before=(aset/'progress.json').read_bytes()
            status=json.loads(call('status','--root',str(project)))
            self.assertEqual(status['progress'],1)
            # Running the taskbook init a second time must not overwrite midterm progress.
            call('init','--root',str(project),'--project-id','SHARED-PROJECT','--name','联调测试')
            self.assertEqual((aset/'progress.json').read_bytes(),before)
            self.assertIsNone(json.loads((aset/'schedule.json').read_text(encoding='utf8'))['plan'])
            # A duplicate ID conflict requires explicit override with reason.
            old=json.loads(f.read_text(encoding='utf8'))
            old['items'][0]['description']='冲突修改'
            f.write_text(json.dumps(old,ensure_ascii=False),encoding='utf8')
            p=subprocess.run([sys.executable,str(tool),'merge','--root',str(project),'--kind','progress','--input',str(f)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertEqual((aset/'progress.json').read_bytes(),before)

    def test_final_version_never_overwritten(self):
        t=ROOT/'assets/official-taskbook-template.docx'
        d={'title':'仅测试，不是正式任务书','thesis_content':['仅供软件自动测试，禁止提交。'*4],
           'schedule':[{'from_week':1,'to_week':30,'task':'测试'}],'total_weeks':30,
           'issuer_opinion':'这段意见仅为自动化测试而填写，不存在真实教师审批、验收或签署等任何实际行为。'*3,
           'references':[{'citation':f'无效测试来源{i}[J]. 测试,20XX.','source_url':'https://example.invalid/test',
                          'source_type':'journal','verified':True} for i in range(10)]}
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'test-v1.docx'
            write(d,t,out)
            h=hashlib.sha256(out.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):write(d,t,out)
            self.assertEqual(h,hashlib.sha256(out.read_bytes()).hexdigest())

if __name__=='__main__':unittest.main()
