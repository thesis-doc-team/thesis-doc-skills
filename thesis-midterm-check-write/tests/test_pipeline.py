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
            'issues_paragraphs':[TEXT2,TEXT1],
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
            d=draft();d['issues_paragraphs']=['只有几句话，字数不达标']
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,d,Path(td)/'out.docx')

    def test_college_requires_authorization(self):
        with tempfile.TemporaryDirectory() as td:
            d=draft();d['college_opinion_paragraphs']=['不得擅自填写学院意见']
            with self.assertRaises(ValueError):fill_docx(DEFAULT_TEMPLATE,d,Path(td)/'out.docx')

if __name__=='__main__':unittest.main()
