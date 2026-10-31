"""smoke/regression tests; run: python -m unittest discover -s tests -v"""
import tempfile,subprocess,json,unittest,sys,hashlib
from pathlib import Path
from docx import Document

BASE=Path(__file__).resolve().parents[1]

def call(*args,ok=True):
 r=subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True,encoding="utf-8",errors="replace")
 if ok and r.returncode:raise AssertionError(r.stdout+'\n'+r.stderr)
 return r

class Tests(unittest.TestCase):
 def test_generate_and_fixed_structure(self):
  with tempfile.TemporaryDirectory() as td:
   src=BASE/'assets/official-guidance-template.docx';h=hashlib.sha256(src.read_bytes()).hexdigest()
   inp=BASE/'tests/format-smoke-input.json';out=Path(td)/'guide.docx'
   call(BASE/'scripts/fill_guidance.py','--template',src,'--data',inp,'--out',out)
   call(BASE/'scripts/validate_guidance.py','--template',src,'--data',inp,'--file',out,'--report',Path(td)/'qa.json')
   self.assertEqual(h,hashlib.sha256(src.read_bytes()).hexdigest())
   self.assertEqual(len(Document(out).tables[1].rows),104)
   self.assertEqual(json.loads((Path(td)/'qa.json').read_text(encoding='utf-8'))['result'],'PASS')
 def test_reject_unverified_dates(self):
  with tempfile.TemporaryDirectory() as td:
   data=json.loads((BASE/'tests/format-smoke-input.json').read_text(encoding='utf-8'))
   data['records'][0]['date']='2026年4月1日'
   inp=Path(td)/'draft.json';inp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
   out=Path(td)/'refused.docx'
   r=call(BASE/'scripts/fill_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--out',out,ok=False)
   self.assertNotEqual(r.returncode,0)
   self.assertFalse(out.exists())
 def test_reject_low_count(self):
  with tempfile.TemporaryDirectory() as td:
   data=json.loads((BASE/'tests/format-smoke-input.json').read_text(encoding='utf-8'));data['records']=data['records'][:7]
   inp=Path(td)/'draft.json';inp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
   r=call(BASE/'scripts/fill_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--out',Path(td)/'refused.docx',ok=False)
   self.assertNotEqual(r.returncode,0)
 def test_template_lock(self):
  with tempfile.TemporaryDirectory() as td:
   src=BASE/'assets/official-guidance-template.docx';obj=Document(src)
   obj.paragraphs[5].add_run('x')
   mutated=Path(td)/'mutated.docx';obj.save(mutated)
   r=call(BASE/'scripts/fill_guidance.py','--template',mutated,'--data',BASE/'tests/format-smoke-input.json',
          '--out',Path(td)/'refused.docx',ok=False)
   self.assertNotEqual(r.returncode,0)
 def test_asset_package_compatibility(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   tool=BASE/'scripts/project_assets.py'
   call(tool,'init','--root',root,'--project-id','demo-guidance-001','--name','某安全监测系统')
   call(tool,'status','--root',root)
   inp=BASE/'tests/format-smoke-input.json';out=root/'combined.json'
   call(tool,'compose','--root',root,'--draft',inp,'--out',out)
   self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['asset_trace']['references'],[])
   run=call(tool,'workdir','--root',root,'--run-id','unit-test').stdout.strip()
   self.assertTrue((Path(run)/'.owned-by-thesis-guidance-record-write').exists())
   call(tool,'cleanup','--root',root,'--run-id','unit-test')
   self.assertFalse(Path(run).exists())
   self.assertTrue((root/'project-assets'/'project.json').exists())

if __name__=='__main__':unittest.main()
