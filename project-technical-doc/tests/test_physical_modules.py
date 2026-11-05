#!/usr/bin/env python3
"""physical-modules.json 契约校验回归：全部为合成数据，不依赖真实项目。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'check_physical_modules.py'

MD_WITH_MODULES = '''# 测试系统 — 技术文档

## 6. 模块详解

### 6.1 D1 粉尘检测模块

职责与接口见正文。

### 6.2 SHT40 温湿度模块

职责与接口见正文。

### 6.3 uart_comm 串口框架

通信抽象层，实现细节见正文。
'''

MD_NO_CHAPTER = '''# 测试系统 — 技术文档

## 1. 项目概述

纯软件项目，无实物模块。
'''


def manifest(modules):
    return {'schema_version': 1, 'generated_by': 'project-technical-doc', 'modules': modules}


def mod(code, **extra):
    base = {'code': code, 'name': f'{code} 模块', 'hardware': f'{code} 实物器件'}
    base.update(extra)
    return base


class TestPhysicalModules(unittest.TestCase):
    def run_check(self, modules, md_text=MD_WITH_MODULES, write=True, extra_files=None):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            md = td / '测试系统-技术文档.md'
            md.write_text(md_text, 'utf-8')
            if write:
                payload = manifest(modules) if not isinstance(modules, dict) else modules
                (td / 'physical-modules.json').write_text(
                    json.dumps(payload, ensure_ascii=False), 'utf-8')
            proc = subprocess.run([sys.executable, str(SCRIPT), str(md)],
                                  capture_output=True, text=True,
                                  encoding='utf-8', errors='replace')
            return proc, json.loads(proc.stdout)

    def test_valid_manifest_passes(self):
        proc, rep = self.run_check([
            mod('D1', category='sensor', source_files=['D1.c', 'D1.h'], pins='USART2', note='周期性读取'),
            mod('SHT40', category='sensor', pins='I2C1'),
        ])
        self.assertEqual(proc.returncode, 0, rep)
        self.assertEqual(rep['status'], 'PASS', rep)

    def test_missing_manifest_rejected(self):
        proc, rep = self.run_check([], write=False)
        self.assertEqual(proc.returncode, 1, rep)
        self.assertTrue(any('缺少实物模块清单' in e for e in rep['errors']), rep)

    def test_code_must_match_module_section(self):
        proc, rep = self.run_check([mod('D1'), mod('GPS')])
        self.assertEqual(proc.returncode, 1, rep)
        self.assertTrue(any('GPS' in e and '模块详解' in e for e in rep['errors']), rep)

    def test_token_boundary_d1_does_not_match_d10(self):
        md = MD_WITH_MODULES.replace('### 6.1 D1 粉尘检测模块', '### 6.1 D10 甲醛检测模块')
        # D1 出现在 D10 前缀里但不构成独立标识，必须判未找到
        proc, rep = self.run_check([mod('D1')], md_text=md)
        self.assertEqual(proc.returncode, 1, rep)
        self.assertTrue(any('D1' in e and '模块详解' in e for e in rep['errors']), rep)

    def test_duplicate_code_rejected(self):
        proc, rep = self.run_check([mod('D1'), mod('d1')])
        self.assertEqual(proc.returncode, 1, rep)
        self.assertTrue(any('重复' in e for e in rep['errors']), rep)

    def test_order_must_follow_document(self):
        proc, rep = self.run_check([mod('SHT40'), mod('D1')])
        self.assertEqual(proc.returncode, 1, rep)
        self.assertTrue(any('顺序' in e for e in rep['errors']), rep)

    def test_same_section_ties_allowed(self):
        md = MD_WITH_MODULES.replace('### 6.2 SHT40 温湿度模块', '### 6.2 OLED / Buzzer / LED（人机交互）')
        proc, rep = self.run_check([mod('OLED'), mod('Buzzer'), mod('LED')], md_text=md)
        self.assertEqual(proc.returncode, 0, rep)

    def test_empty_modules_allowed(self):
        proc, rep = self.run_check([], md_text=MD_NO_CHAPTER)
        self.assertEqual(proc.returncode, 0, rep)
        self.assertEqual(rep['status'], 'PASS', rep)

    def test_software_like_code_warns_but_passes(self):
        proc, rep = self.run_check([mod('uart_comm')])
        self.assertEqual(proc.returncode, 0, rep)
        self.assertEqual(rep['status'], 'WARN', rep)
        self.assertTrue(any('软件模块' in w for w in rep['warnings']), rep)

    def test_unknown_category_is_warning_only(self):
        proc, rep = self.run_check([mod('D1', category='misc')])
        self.assertEqual(proc.returncode, 0, rep)
        self.assertEqual(rep['status'], 'WARN', rep)
        self.assertTrue(any('category' in w for w in rep['warnings']), rep)

    def test_base64_and_absolute_path_rejected(self):
        proc, rep = self.run_check([
            mod('D1', hardware='E:\\photos\\d1.png'),
            mod('SHT40', note='见 data:image/png;base64,AAAA'),
        ])
        self.assertEqual(proc.returncode, 1, rep)
        self.assertTrue(any('绝对路径' in e for e in rep['errors']), rep)
        self.assertTrue(any('base64' in e for e in rep['errors']), rep)

    def test_source_files_must_be_bare_names(self):
        proc, rep = self.run_check([mod('D1', source_files=['Core/Src/D1.c'])])
        self.assertEqual(proc.returncode, 1, rep)
        self.assertTrue(any('裸文件名' in e for e in rep['errors']), rep)

    def test_schema_and_generator_mismatch_rejected(self):
        proc, rep = self.run_check({'schema_version': 2, 'generated_by': 'other', 'modules': []},
                                   md_text=MD_NO_CHAPTER)
        self.assertEqual(proc.returncode, 1, rep)
        self.assertTrue(any('schema_version' in e for e in rep['errors']), rep)
        self.assertTrue(any('generated_by' in e for e in rep['errors']), rep)


if __name__ == '__main__':
    unittest.main()