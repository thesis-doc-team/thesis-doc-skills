#!/usr/bin/env python3
"""工具链结构测试：文献是刻意编造的本地模拟条目，测试产物绝不能提交用户/学校。"""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'assets/official-taskbook-template.docx'
EXPECTED_SHA256 = '49e0983db300ca1729d7d298b3f849dfce3d8d189c4b3cc4c8c2ce87b5085590'


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fill = load('fill_taskbook')
valid = load('validate_taskbook')


class Pipeline(unittest.TestCase):
    def fixture(self):
        return {
            'title': '软件系统示例（仅测试，不可提交）',
            'thesis_content': ['仅为测试生成位置而编写的无具体课题事实文本。', '检验段落及分页，不代表任何实际项目。'],
            'schedule': [{'from_week': 1, 'to_week': 4, 'task': '测试阶段一。'},
                         {'from_week': 5, 'to_week': 30, 'task': '测试阶段二。'}],
            'total_weeks': 30,
            'references': [{'citation': f'测试用虚构条目{i}（严禁作为正式参考文献）[J]. 测试, 2020.',
                            'source_url': 'https://example.org/test-only', 'source_type': 'journal',
                            'verified': True} for i in range(1, 11)],
            'issuer_opinion': '这是专门用于填充和结构不变量检查的虚构导师意见文本。它没有任何真实的导师审核、签名或任务批准含义。正式执行时必须根据真实项目的学术内容重新编写、检索可靠参考文献并进行实际验收。'
        }

    def test_template_hash(self):
        self.assertEqual(hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(), EXPECTED_SHA256)

    def test_refs_gate(self):
        data = self.fixture()
        data['references'] = data['references'][:9]
        with self.assertRaises(ValueError):
            fill.validate_input(data)

    def test_roundtrip_structure(self):
        data = self.fixture()
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'test-only.docx'
            fill.write(data, TEMPLATE, out)
            from docx import Document
            source, output = Document(TEMPLATE), Document(out)
            self.assertEqual(valid.compare_structure(source, output), [])
            self.assertEqual(valid.check_content(output, data)[0], [])
            self.assertEqual(hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(), EXPECTED_SHA256)


if __name__ == '__main__':
    unittest.main()
