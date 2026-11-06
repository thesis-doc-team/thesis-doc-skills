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
   call(tool,'init','--root',root,'--project-id','demo-guidance-001','--name','基于STM32与4G通信的胡杨林安全监测系统')
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
 def test_blank_page_detection_and_render_flag(self):
  # 用户要求：Word 成品不得出现空白页——任意页空白检测与渲染 problems 硬拦截
  sys.path.insert(0,str(BASE/'scripts'))
  try:
   import fitz
  except ImportError:
   self.skipTest('PyMuPDF 未安装')
  from render_visual import blank_page_kind,render
  doc=fitz.open();self.assertEqual(blank_page_kind(doc.new_page()),'blank')
  num=doc.new_page();num.insert_text((72,72),'- 2 -');self.assertEqual(blank_page_kind(num),'blank')
  ok=doc.new_page();ok.insert_text((72,72),'指导记录正文内容示例，用于验证正常页不被误判为空白页。');self.assertIsNone(blank_page_kind(ok));doc.close()
  with tempfile.TemporaryDirectory() as td:
   td=Path(td);src=td/'fake.docx';src.write_bytes(b'X')
   proc=fitz.open();c=proc.new_page();c.insert_text((72,72),'指导记录正文内容示例，用于验证正常页不被误判为空白页。');proc.new_page()
   pdf=td/'b.pdf';proc.save(str(pdf));proc.close()
   rep=render(src,td/'render',pdf_in=pdf)
   self.assertFalse(rep['auto_precheck_passed'])
   self.assertTrue(any('第2页为空白页' in p for p in rep['problems']),rep['problems'])
 def test_fill_adds_invisible_blank_page_guard(self):
  # 复盘实锤：官方模板以表格收尾、末行恰达版心底线必溢出空白页（空白原件第5页、真实成品第11页）；
  # 填充件补表尾 1pt 防空白页尾段无损消除，且校验器只放行这一种额外段落
  from docx.oxml.ns import qn
  with tempfile.TemporaryDirectory() as td:
   td=Path(td);src=BASE/'assets/official-guidance-template.docx'
   out=td/'guide.docx'
   call(BASE/'scripts/fill_guidance.py','--template',src,'--data',BASE/'tests/format-smoke-input.json','--out',out)
   doc=Document(out);tpl=Document(src)
   self.assertEqual(len(doc.paragraphs),len(tpl.paragraphs)+1)
   guard=doc.paragraphs[-1]
   self.assertEqual(guard.text.strip(),'')
   sz=guard._p.find('.//'+qn('w:sz'))
   self.assertIsNotNone(sz);self.assertEqual(sz.get(qn('w:val')),'2')
   call(BASE/'scripts/validate_guidance.py','--template',src,'--data',BASE/'tests/format-smoke-input.json','--file',out,'--report',td/'qa.json')
   self.assertEqual(json.loads((td/'qa.json').read_text(encoding='utf-8'))['result'],'PASS')
   doc.add_paragraph('不该出现的额外段落')
   doc.save(out)
   r=call(BASE/'scripts/validate_guidance.py','--template',src,'--data',BASE/'tests/format-smoke-input.json','--file',out,'--report',td/'qa2.json',ok=False)
   self.assertNotEqual(r.returncode,0)
   self.assertIn('非授权额外段落',' '.join(json.loads((td/'qa2.json').read_text(encoding='utf-8'))['errors']))
 def test_overlong_content_rejected_by_fill(self):
  # 用户截图复盘：指导内容超长压盖下一行——官方行高 exact，fill 按 17 行硬预算拒绝
  with tempfile.TemporaryDirectory() as td:
   data=json.loads((BASE/'tests/format-smoke-input.json').read_text(encoding='utf-8'))
   long='核对系统时钟与外设时钟配置的一致性，并按实际时钟核算各串口波特率误差，记录超差链路与恢复验证结果。'*4
   data['records'][0]['issue_pairs']=[{'problem':long,'action':long} for _ in range(3)]
   inp=Path(td)/'d.json';inp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
   r=call(BASE/'scripts/fill_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--out',Path(td)/'x.docx',ok=False)
   self.assertNotEqual(r.returncode,0)
   self.assertIn('行预算',r.stdout+r.stderr)
 def test_validate_flags_overlong_content(self):
  # 校验器独立复核：绕过 fill 直改文档也要被拦
  with tempfile.TemporaryDirectory() as td:
   td=Path(td);out=td/'guide.docx'
   call(BASE/'scripts/fill_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',BASE/'tests/format-smoke-input.json','--out',out)
   doc=Document(out);cell=doc.tables[1].cell(5,1)
   long='核对系统时钟与外设时钟配置的一致性，并按实际时钟核算各串口波特率误差，记录超差链路与恢复验证结果。'*4
   for _ in range(3):cell.add_paragraph(long)
   doc.save(out)
   r=call(BASE/'scripts/validate_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',BASE/'tests/format-smoke-input.json','--file',out,'--report',td/'qa.json',ok=False)
   self.assertNotEqual(r.returncode,0)
   self.assertIn('行预算',' '.join(json.loads((td/'qa.json').read_text(encoding='utf-8'))['errors']))
 def test_long_item_warning_non_blocking(self):
  # 单条 90~135 字但行预算内：软提示"宜概括"，不阻断——概括口径可灵活，不一刀切
  with tempfile.TemporaryDirectory() as td:
   data=json.loads((BASE/'tests/format-smoke-input.json').read_text(encoding='utf-8'))
   item='核对系统时钟与外设时钟配置的一致性，并按实际时钟核算各串口波特率误差，记录超差链路与恢复验证结果。'*3
   data['records'][0]['issue_pairs']=[{'problem':item,'action':item}]
   inp=Path(td)/'d.json';inp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
   out=Path(td)/'guide.docx'
   call(BASE/'scripts/fill_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--out',out)
   call(BASE/'scripts/validate_guidance.py','--template',BASE/'assets/official-guidance-template.docx','--data',inp,'--file',out,'--report',Path(td)/'qa.json')
   rep=json.loads((Path(td)/'qa.json').read_text(encoding='utf-8'))
   self.assertEqual(rep['result'],'PASS')
   self.assertTrue(any('超过 90 字' in w for w in rep['warnings']),rep['warnings'])
 def test_compose_rejects_title_mismatch(self):
  # 共享资产一个项目只有一个正式题目：compose 必须拦截与 project.json name 不一致的题目
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   tool=BASE/'scripts/project_assets.py'
   call(tool,'init','--root',root,'--project-id','demo-guidance-001','--name','基于STM32与4G通信的胡杨林安全监测系统')
   data=json.loads((BASE/'tests/format-smoke-input.json').read_text(encoding='utf-8'))
   data['title']='另一个项目的题目'
   inp=Path(td)/'draft.json';inp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
   r=call(tool,'compose','--root',root,'--draft',inp,'--out',Path(td)/'out.json',ok=False)
   self.assertNotEqual(r.returncode,0)
   self.assertIn('题目',r.stdout+r.stderr)

if __name__=='__main__':unittest.main()
