#!/usr/bin/env python3
"""physical-modules.json generator regression (synthetic data only)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / 'scripts' / 'gen_physical_modules.py'

MD = '''# 测试系统 — 技术文档

## 6. 模块详解

### 6.1 D1 粉尘检测模块
D1 粉尘传感器通过 USART2 输出，周期性读取，帧同步校验。源文件 D1.c、D1.h。

### 6.2 SHT40 温湿度模块
SHT40 温湿度传感器通过 I2C1 读取，CRC 校验。源文件 SHT40.c。

### 6.3 OLED 显示模块
0.96 寸 OLED 通过 PB8/PB9 软件 I2C 显示。源文件 OLED.c。

### 6.4 uart_comm 串口框架
通信抽象层，软件模块，不应列入。

### 6.5 Warn 告警逻辑
纯逻辑，不应列入。

### 6.6 main 主程序
主程序，不应列入。
'''

MD_NO_MODULES = '''# 纯软件系统 — 技术文档

## 1. 项目概述
没有实物模块。
'''


class PhysicalModuleGeneratorTests(unittest.TestCase):
    def run_gen(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        folder = Path(tmp.name)
        md = folder / '测试系统-技术文档.md'
        md.write_text(text, 'utf-8')
        proc = subprocess.run([sys.executable, str(GEN), str(md)],
                              capture_output=True, text=True,
                              encoding='utf-8', errors='replace')
        return proc, folder, json.loads(proc.stdout)

    def test_generates_only_physical_modules_in_document_order(self):
        proc, folder, result = self.run_gen(MD)
        self.assertEqual(proc.returncode, 0, result)
        self.assertEqual(result['status'], 'PASS', result)
        data = json.loads((folder / 'physical-modules.json').read_text('utf-8'))
        self.assertEqual(data['schema_version'], 1)
        self.assertEqual(data['generated_by'], 'project-technical-doc')
        codes = [m['code'] for m in data['modules']]
        self.assertEqual(codes, ['D1', 'SHT40', 'OLED'])
        self.assertEqual([m['category'] for m in data['modules']],
                         ['sensor', 'sensor', 'display'])
        self.assertEqual(data['modules'][0]['source_files'], ['D1.c', 'D1.h'])
        self.assertEqual(data['modules'][0]['pins'], 'USART2')
        self.assertTrue(all(m['hardware'] for m in data['modules']))
        self.assertTrue(all('uart_comm' not in m['code'] and 'Warn' not in m['code']
                            and 'main' not in m['code'] for m in data['modules']))
        # 生成器必须同时通过契约检查器，而不是只写文件。
        check = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'check_physical_modules.py'),
                                str(folder / '测试系统-技术文档.md')],
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertEqual(json.loads(check.stdout)['status'], 'PASS')

    def test_no_module_chapter_writes_empty_array(self):
        proc, folder, result = self.run_gen(MD_NO_MODULES)
        self.assertEqual(proc.returncode, 0, result)
        data = json.loads((folder / 'physical-modules.json').read_text('utf-8'))
        self.assertEqual(data['modules'], [])
        self.assertEqual(result['status'], 'PASS', result)

    def test_invalid_markdown_path_fails(self):
        proc = subprocess.run([sys.executable, str(GEN), '不存在的文件.md'],
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
        self.assertNotEqual(proc.returncode, 0)


if __name__ == '__main__':
    unittest.main()