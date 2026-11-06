#!/usr/bin/env python3
"""content-index.json classification regression (synthetic data only)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'classify_content.py'
sys.path.insert(0, str(ROOT / 'scripts'))
import classify_content  # noqa: E402
import content_rules as rules  # noqa: E402

MD = '''# 测试系统 — 技术文档

## 2 系统整体架构

### 2.1 总体架构

```mermaid
flowchart TD
  subgraph 感知层
    A[采集] --> B[处理]
  end
```

## 5 数据结构

### 5.1 SHT40 数据结构

| 字段 | 类型 | 单位 |
|---|---|---|
| Temperature | float | ℃ |
| Humidity | float | %RH |

### 5.2 RS485 数据结构

| 字段 | 类型 | 单位 |
|---|---|---|
| Data | uint8_t[9] | - |

### 5.3 Modbus RTU 帧

| 偏移 | 字段 | 解析用途 |
|---|---|---|
| 0 | 从站地址 | 未校验 |

## 6 模块详解

### 6.1 D1 粉尘检测模块
D1 粉尘传感器通过 USART2 输出，周期性读取。源文件 D1.c。

### 6.2 SHT40 温湿度模块
SHT40 温湿度传感器通过 I2C1 读取。源文件 SHT40.c。
'''


class ContentIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.md = self.folder / '测试系统-技术文档.md'
        self.md.write_text(MD, 'utf-8')
        proc = subprocess.run([sys.executable, str(SCRIPT), str(self.md)],
                              capture_output=True, text=True,
                              encoding='utf-8', errors='replace')
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.index = self.folder / 'content-index.json'
        self.data = json.loads(self.index.read_text('utf-8'))

    def test_classifies_tables_diagrams_modules_and_groups(self):
        self.assertEqual(self.data['schema_version'], 1)
        self.assertEqual(self.data['generated_by'], 'project-technical-doc')
        self.assertEqual(self.data['summary']['tables'], 3)
        self.assertEqual(self.data['summary']['diagrams'], 1)
        self.assertEqual(self.data['summary']['modules'], 2)
        by_id = {x['id']: x for x in self.data['items']}
        self.assertEqual(by_id['TBL-001']['category'], 'data-structure')
        self.assertEqual(by_id['TBL-001']['group_title'], 'SHT40 数据结构')
        self.assertEqual(by_id['TBL-002']['group_title'], 'RS485 数据结构')
        self.assertEqual(by_id['TBL-003']['category'], 'protocol')
        self.assertEqual(by_id['TBL-003']['group_title'], 'Modbus 通信协议')
        self.assertEqual(by_id['FIG-001']['category'], 'architecture')
        self.assertEqual(by_id['MOD-001']['category'], 'sensor')
        self.assertEqual(by_id['MOD-002']['category'], 'sensor')
        # Modules with the same physical category share one group.
        sensor_group = next(g for g in self.data['groups'] if g['title'] == '传感器模块')
        self.assertEqual(sensor_group['count'], 2)
        # Items are ordered by source line.
        lines = [x['line_start'] for x in self.data['items']]
        self.assertEqual(lines, sorted(lines))
        # Every item has a valid group.
        group_ids = {g['id'] for g in self.data['groups']}
        self.assertTrue(all(x['group_id'] in group_ids for x in self.data['items']))

    def test_header_and_caption_override_chapter_heading(self):
        # Regression for the real failure: a table under 「测试与结果」 whose
        # headers are 模拟量/表达式/取值范围 must be parameter-config, not test.
        self.assertEqual(
            rules.classify_table(['模拟量', '表达式', '取值范围'],
                                 '测试模式的数据注入机制', '表5-2 测试模式的数据注入机制'),
            'parameter-config')
        # Tables under 「附录」 are classified by their content, not the chapter.
        self.assertEqual(
            rules.classify_table(['器件', '地址', '说明'], 'I2C 器件地址速查', '表A-1 I2C 器件地址速查'),
            'interface-pin')
        self.assertEqual(
            rules.classify_table(['返回码', '含义', '说明'], '返回码速查', '表A-2 返回码速查'),
            'data-structure')
        self.assertEqual(
            rules.classify_table(['层级', '组成', '职责'], '系统架构', '表2-1 系统架构'),
            'architecture')
        self.assertEqual(
            rules.classify_table(['中断', '优先级', 'DMA', '缓冲区'], '资源分配', '表4-5 资源分配'),
            'hardware-resource')
        self.assertEqual(
            rules.classify_table(['状态', '转移', '动作', '异常'], '状态机', '表7-1 状态机'),
            'flow')
        self.assertEqual(
            rules.classify_table(['术语', '缩写', '定义'], '术语表', '表A-3 术语表'),
            'terminology')
        self.assertEqual(
            rules.classify_table(['索引', '编号', '目录'], '索引', '表A-4 索引'),
            'index')
        self.assertEqual(
            rules.classify_table(['资料', '文档', '标准'], '参考资料', '表A-5 参考资料'),
            'materials')

    def test_checker_passes_generated_index(self):
        report = classify_content.check_content_index(self.md, self.index)
        self.assertEqual(report['status'], 'PASS', report)
        self.assertEqual(report['coverage']['expected']['table'], 3)
        self.assertEqual(report['coverage']['expected']['diagram'], 1)
        self.assertEqual(report['coverage']['expected']['module'], 2)

    def test_checker_rejects_missing_block(self):
        broken = dict(self.data)
        broken['items'] = [x for x in self.data['items'] if x['id'] != 'TBL-002']
        path = self.folder / 'broken-index.json'
        path.write_text(json.dumps(broken, ensure_ascii=False), 'utf-8')
        report = classify_content.check_content_index(self.md, path)
        self.assertEqual(report['status'], 'FAIL')
        self.assertTrue(any('table 覆盖不完整' in e for e in report['errors']), report)

    def test_checker_rejects_source_hash_mismatch(self):
        broken = dict(self.data)
        broken['source_md_sha256'] = '0' * 64
        path = self.folder / 'broken-hash.json'
        path.write_text(json.dumps(broken, ensure_ascii=False), 'utf-8')
        report = classify_content.check_content_index(self.md, path)
        self.assertEqual(report['status'], 'FAIL')
        self.assertTrue(any('source_md_sha256' in e for e in report['errors']), report)


if __name__ == '__main__':
    unittest.main()