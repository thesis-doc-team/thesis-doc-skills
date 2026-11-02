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
 def test_xx_text_not_false_flagged(self):
  # 复盘回归：张XX/20XX 等脱敏名与年份是合法正文，不得被宽字面 'XX' 探针误伤
  with tempfile.TemporaryDirectory() as td:
   data=json.loads((BASE/'tests/format-smoke-input.json').read_text(encoding='utf-8'))
   data['records'][0]['issue_pairs'][0]['problem']='联系人张XX的联系电话字段格式需核对，20XX 编码规则尚未在状态字典中定义。'
   data['records'][0]['issue_pairs'][0]['action']='补充号码字段正则与 20XX 编码对照表，用三条真实号码样本回放校验解析结果。'
   inp=Path(td)/'draft.json';inp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
   out=Path(td)/'guide.docx'
   call(BASE/'scripts/fill_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--out',out)
   call(BASE/'scripts/validate_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--file',out,'--report',Path(td)/'qa.json')
   self.assertEqual(json.loads((Path(td)/'qa.json').read_text(encoding='utf-8'))['result'],'PASS')
 def test_example_residue_flagged_precisely(self):
  # 复盘回归：官方示例残留按精确片段拦截并给专属报错（不再宽字面拦 'XX'）
  with tempfile.TemporaryDirectory() as td:
   data=json.loads((BASE/'tests/format-smoke-input.json').read_text(encoding='utf-8'))
   data['records'][0]['issue_pairs'][0]['problem']='分条列出。如：替换后仍保留示例引导句的问题描述占位内容。'
   data['records'][0]['issue_pairs'][0]['action']='删除示例引导句与 3.XX 占位后按两段标签重写本条真实内容。'
   inp=Path(td)/'draft.json';inp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
   out=Path(td)/'guide.docx'
   call(BASE/'scripts/fill_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--out',out)
   r=call(BASE/'scripts/validate_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--file',out,'--report',Path(td)/'qa.json',ok=False)
   self.assertNotEqual(r.returncode,0)
   rep=json.loads((Path(td)/'qa.json').read_text(encoding='utf-8'))
   self.assertEqual(rep['result'],'FAIL')
   joined=' '.join(rep['errors'])
   self.assertIn('示例引导句',joined);self.assertIn('示例占位',joined)
 def test_append_record_tool_end_to_end(self):
  # 复盘回归：逐条落盘官方工具（--init + --pair x8）替代自造 frag+append 脚本
  with tempfile.TemporaryDirectory() as td:
   td=Path(td);draft=td/'draft.json'
   call(BASE/'scripts/append_record.py','--draft',draft,'--init','--project-id','demo-guidance-002','--title','基于STM32与4G通信的安全监测系统')
   for i in range(8):
    call(BASE/'scripts/append_record.py','--draft',draft,'--pair',f'第{i+1}阶段缺少可核对的输出清单，影响进度确认与后续安排。||补充该阶段交付清单与核对方法，用一次完整回放确认结果可复现。')
   out=td/'guide.docx'
   call(BASE/'scripts/fill_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',draft,'--out',out)
   call(BASE/'scripts/validate_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',draft,'--file',out,'--report',td/'qa.json')
   self.assertEqual(json.loads((td/'qa.json').read_text(encoding='utf-8'))['result'],'PASS')
 def test_vague_action_warning_non_blocking(self):
  # 复盘回归：空泛元动作只进 warnings 提示人工复核，不一刀切 FAIL（带判据的“进行验证”属正例）
  with tempfile.TemporaryDirectory() as td:
   data=json.loads((BASE/'tests/format-smoke-input.json').read_text(encoding='utf-8'))
   data['records'][0]['issue_pairs'][0]['action']='认真研究相关资料并继续完善，进行验证后建立机制。'
   inp=Path(td)/'draft.json';inp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
   out=Path(td)/'guide.docx'
   call(BASE/'scripts/fill_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--out',out)
   call(BASE/'scripts/validate_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--file',out,'--report',Path(td)/'qa.json')
   rep=json.loads((Path(td)/'qa.json').read_text(encoding='utf-8'))
   self.assertEqual(rep['result'],'PASS')
   self.assertGreaterEqual(rep['vague_action_hits'],1)
   self.assertTrue(any('空泛' in w for w in rep['warnings']))

if __name__=='__main__':unittest.main()
