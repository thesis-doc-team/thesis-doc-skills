import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from fill_midterm import fill_docx
from validate_midterm import validate
from template_tools import DEFAULT_TEMPLATE,sha256,lock_check

TEXT1='本次模拟文字只用于代码自测，不代表任何真实毕业设计项目的实际工作进展。'*9
TEXT2='测试段落用于验证官方表格正文和落款不会被覆盖，并验证跨页情况下文书仍可编辑。'*9


def draft():
    return {'title':'仅用于测试的模拟毕业设计题目',
            'student_name':'','class_name':'',
            'progress_paragraphs':[TEXT1,TEXT2],
            'issue_pairs':[{'problem':'系统联调过程中仍需对数据采集链路进行分项检查，明确传感器数据稳定性以及校验失败处理路径，并记录连续采集期间不同工况的原始数据用于后续分析。', 'action':'分模块建立数据采集和异常回归用例，采集原始日志并与标准仪表读数对比，形成可复核的测试记录，同时记录异常重试次数与恢复时间用于评估改进效果。'}, {'problem':'通信链路在网络不稳定条件下尚缺充分验证，远程数据连续性和断线重传机制仍待记录，暂不能直接断言通信在现场条件下可靠。', 'action':'构造断网恢复和弱信号工况，检查重发队列、错误记录以及恢复后的完整性，以多轮测试统计数据作为验收依据，并将改进后的测试报告归档到项目资产中。'}],
            'teacher_opinion_paragraphs':[TEXT1,TEXT2],
            'teacher_opinion_is_draft':True,
            'asset_reference_ids':[],'asset_fact_ids':[],'asset_progress_ids':[]}

class TestStrictTemplate(unittest.TestCase):
    def test_build_and_validate_without_modifying_original(self):
        before=sha256(DEFAULT_TEMPLATE)
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/'example.docx'
            d=draft()
            fill_docx(DEFAULT_TEMPLATE,d,file)
            check=validate(DEFAULT_TEMPLATE,file,d)
            self.assertTrue(check['passed'],check['problems'])
            self.assertEqual(check['rows'],6)
            self.assertEqual(len(check['word_counts']),3)
        self.assertEqual(sha256(DEFAULT_TEMPLATE),before)

    def test_real_first_line_indent_and_no_unused_blank_lines(self):
        from docx import Document
        from docx.shared import Pt
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'regression.docx'
            d=draft()
            fill_docx(DEFAULT_TEMPLATE,d,f)
            doc=Document(f)
            for row,key,indent in ((2,'progress_paragraphs',12),(3,'issues_paragraphs',24),(4,'teacher_opinion_paragraphs',24)):
                from fill_midterm import issue_paragraphs,indent_for
                texts=issue_paragraphs(d) if key=='issues_paragraphs' else d[key]
                body=doc.tables[0].cell(row,0).paragraphs[1:1+len(texts)]
                for p in body:
                    self.assertEqual(p.paragraph_format.first_line_indent,Pt(indent_for(p.text,row)))
                    self.assertEqual(p.paragraph_format.line_spacing,1.5)
                self.assertFalse(any(not p.text.strip() for p in doc.tables[0].cell(row,0).paragraphs[1:1+len(texts)]))

    def test_old_no_indentation_is_rejected(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'good.docx';bad=Path(td)/'bad.docx'
            d=draft()
            fill_docx(DEFAULT_TEMPLATE,d,f)
            doc=Document(f)
            doc.tables[0].cell(2,0).paragraphs[1].paragraph_format.first_line_indent=None
            doc.save(bad)
            r=validate(DEFAULT_TEMPLATE,bad,d)
            self.assertFalse(r['passed'])
            self.assertTrue(any('首行缩进' in x for x in r['problems']))

    def test_overwrite_existing_version_forbidden(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'existing-v1.docx'
            fill_docx(DEFAULT_TEMPLATE,draft(),f)
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,draft(),f)

    def test_prevent_draft_teacher_false(self):
        with tempfile.TemporaryDirectory() as td:
            d=draft();d['teacher_opinion_is_draft']=False
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,d,Path(td)/'out.docx')

    def test_template_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            other=Path(td)/'new.docx'
            other.write_bytes(DEFAULT_TEMPLATE.read_bytes()+b' ')
            with self.assertRaises(ValueError):lock_check(other)

    def test_underlength_fails(self):
        with tempfile.TemporaryDirectory() as td:
            d=draft();d.pop('issue_pairs');d['issues_paragraphs']=['只有几句话，字数不达标']
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,d,Path(td)/'out.docx')

    def test_issues_are_numbered_and_pair_checked(self):
        from fill_midterm import issue_paragraphs,validate_issue_structure
        d=draft();parts=issue_paragraphs(d)
        self.assertEqual(parts[0],'存在问题：')
        self.assertEqual(parts[3],'整改措施：')
        self.assertEqual(validate_issue_structure(parts)['issue_count'],2)
        self.assertTrue(parts[1].startswith('（1）'))
        self.assertTrue(parts[4].startswith('（1）'))

    def test_missing_remedy_point_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d=draft();d.pop('issue_pairs')
            item='本项包含足够具体的技术对象及待验证的问题，必须通过明确检查加以改进。'
            d['issues_paragraphs']=['存在问题：','（1）'+item,'（2）'+item,'整改措施：','（1）'+item,'（3）'+item]
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,d,Path(td)/'bad.docx')

    def test_unstructured_problem_text_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d=draft();d.pop('issue_pairs');d['issues_paragraphs']=[TEXT1,TEXT2]
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,d,Path(td)/'bad.docx')

    def test_reference_examples_are_anonymous(self):
        from zipfile import ZipFile
        from docx import Document
        samples=ROOT/'assets/reference-samples'
        docs=sorted(samples.glob('sample-*.docx'))
        self.assertEqual(len(docs),4)
        for path in docs:
            d=Document(path)
            self.assertEqual(len(d.tables),1)
            self.assertEqual(len(d.tables[0].rows),6)
            with ZipFile(path) as zipf:
                allxml='\n'.join(zipf.read(n).decode('utf8','ignore') for n in zipf.namelist() if n.endswith('.xml'))
            for t in ('赵彬','崔帅杰','夏骏豪','母祥坤','2021级1班','2025年4月10日','2025年4月11日'):
                self.assertNotIn(t,allxml)

    def test_college_requires_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            d=draft();d['college_opinion_paragraphs']=['不得擅自填写学院意见']
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,d,Path(td)/'out.docx')

    def test_teacher_opinion_in_text_hint_rejected(self):
        # 用户要求：教师意见正文不加“（本栏为拟稿，供指导教师审定）”提示语；拟稿属性走 teacher_opinion_is_draft 与执行报告
        with tempfile.TemporaryDirectory() as td:
            d=draft()
            d['teacher_opinion_paragraphs']=[TEXT1,TEXT2+'（本栏为拟稿，供指导教师审定）']
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,d,Path(td)/'out.docx')

    def test_validate_flags_in_text_hint(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'clean.docx'
            fill_docx(DEFAULT_TEMPLATE,draft(),f)
            d2=draft()
            d2['teacher_opinion_paragraphs']=[TEXT1,TEXT2+'（本栏为拟稿，供指导教师审定）']
            r=validate(DEFAULT_TEMPLATE,f,d2)
            self.assertFalse(r['passed'])
            self.assertTrue(any('提示语' in x for x in r['problems']),r['problems'])

    def test_meta_tail_rejected(self):
        # 用户反馈：'最终评价以指导教师审定为准。'是画蛇添足元话语，正文不写、脚本拦截
        with tempfile.TemporaryDirectory() as td:
            d=draft()
            d['teacher_opinion_paragraphs']=[TEXT1,TEXT2+'建议按整改意见继续推进下一阶段工作，最终评价以指导教师审定为准。']
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,d,Path(td)/'out.docx')

    def test_validate_flags_meta_tail(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'clean.docx'
            fill_docx(DEFAULT_TEMPLATE,draft(),f)
            d2=draft()
            d2['teacher_opinion_paragraphs']=[TEXT1,TEXT2+'最终评价以指导教师审定为准。']
            r=validate(DEFAULT_TEMPLATE,f,d2)
            self.assertFalse(r['passed'])
            self.assertTrue(any('提示语' in x for x in r['problems']),r['problems'])

    def test_bare_count_ref_warns_non_blocking(self):
        # 用户截图复盘：'6 个 pytest 测试用例尚未执行'式裸数量/工具名指代意义不明——机器提示命中但不阻断，改写由语义复核判罚
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'doc.docx'
            d=draft()
            d['issue_pairs'][0]['problem']='语音链路的 6 个 pytest 测试用例尚未执行，识别成功率与响应时延没有任何实测记录可供核对，实际效果无法判断。'
            d['progress_paragraphs']=[TEXT1,'目前 6 个单元测试用例已编写但尚未执行，识别效果与资源占用都还没有实测数据，后续按计划补充。'*2]
            fill_docx(DEFAULT_TEMPLATE,d,f)
            r=validate(DEFAULT_TEMPLATE,f,d)
            self.assertTrue(r['passed'],r['problems'])
            self.assertGreaterEqual(r['clarity_hits'],2)
            self.assertTrue(any('pytest' in w for w in r['warnings']),r['warnings'])
            self.assertTrue(any('点名' in w for w in r['warnings']),r['warnings'])

    def test_named_plain_rewriting_not_flagged(self):
        # 点名对象的平实改写（'语音唤醒、指令识别等 6 项单元测试'）不命中，防误杀
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'doc.docx'
            d=draft()
            d['issue_pairs'][0]['problem']='语音唤醒、指令识别、JSON 解析等 6 项单元测试已编写但尚未运行，识别成功率与响应时延没有实测数据可核对，实际效果无法判断。'
            d['progress_paragraphs']=[TEXT1,'目前语音唤醒、端点检测等 6 项单元测试已编写但尚未运行，识别效果与资源占用都还没有实测数据，后续按计划补充。'*2]
            fill_docx(DEFAULT_TEMPLATE,d,f)
            r=validate(DEFAULT_TEMPLATE,f,d)
            self.assertTrue(r['passed'],r['problems'])
            self.assertEqual(r['clarity_hits'],0,r['warnings'])

    def test_meta_tail_variant_rejected(self):
        # 用户复盘实撞：'最终评价以指导教师审定结果为准。'（插"结果"骗过子串守卫）同属元话语尾巴，fill 必拒
        with tempfile.TemporaryDirectory() as td:
            d=draft()
            d['teacher_opinion_paragraphs']=[TEXT1,TEXT2+'建议按整改意见继续推进下一阶段工作，最终评价以指导教师审定结果为准。']
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,d,Path(td)/'out.docx')

    def test_validate_flags_meta_tail_variant(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'clean.docx'
            fill_docx(DEFAULT_TEMPLATE,draft(),f)
            d2=draft()
            d2['teacher_opinion_paragraphs']=[TEXT1,TEXT2+'最终评价以指导教师审定结果为准。']
            r=validate(DEFAULT_TEMPLATE,f,d2)
            self.assertFalse(r['passed'])
            self.assertTrue(any('提示语' in x for x in r['problems']),r['problems'])

    def test_spec_sample_closing_passes_gates(self):
        # 防回归（用户审计）：SKILL §3.2 ⑤ 收束句样例喂给门禁必须通过——规范文案与可执行门禁不得再分叉
        import re as _re
        text=(ROOT/'SKILL.md').read_text(encoding='utf-8')
        m=_re.search(r'→⑤收束`([^`]+)`',text)
        self.assertIsNotNone(m,'SKILL §3.2 ⑤ 收束句样例未找到')
        closing=m.group(1)
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'spec.docx'
            d=draft()
            d['teacher_opinion_paragraphs']=[TEXT1,TEXT2+closing]
            fill_docx(DEFAULT_TEMPLATE,d,f)
            r=validate(DEFAULT_TEMPLATE,f,d)
            self.assertTrue(r['passed'],r['problems'])

if __name__=='__main__':unittest.main()
