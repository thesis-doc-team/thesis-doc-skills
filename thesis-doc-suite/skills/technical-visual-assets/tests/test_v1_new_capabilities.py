"""v1 complete self-contained, local tests. No network, no installs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
SCRIPTS = BASE / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from svg_fallback import parse, render
from ascii_to_mermaid import build_mermaid
from plan_visuals import draft_windows
from search_candidates import gather


class FullV1Tests(unittest.TestCase):
    def test_stdlib_svg_without_external_dependency(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'system.svg'
            detail = render('flowchart TD\n  A[主控] --> B[传感器]\n  B --> C[通信]\n', p)
            self.assertEqual(detail['engine'], 'stdlib-svg-subset')
            svg=p.read_text('utf-8')
            self.assertIn('<svg',svg)
            self.assertIn('传感器',svg)
            self.assertIn('通信',svg)
            self.assertIn('marker-end',svg)

    def test_svg_refuses_unsupported_mermaid(self):
        invalid = ['sequenceDiagram\n A->>B: hello',
                   'flowchart TD\n  subgraph s\n A --> B\n end',
                   'flowchart TD\n A --> B\n B --> A',
                   'flowchart TD\n A[仅节点]']
        for source in invalid:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):parse(source)

    def test_ascii_tree_and_arrow_roundtrip(self):
        tree=['项目功能', '├── 数据采集', '│   └── 环境采集', '└── 远程展示']
        src, prov=build_mermaid(tree,12,'functional-architecture')
        self.assertIn('项目功能',src)
        self.assertEqual(len(prov['edges']),3)
        with tempfile.TemporaryDirectory() as tmp:
            result=render(src,Path(tmp)/'tree.svg')
            self.assertEqual(result['node_count'],4)
        arrow=['采集 --> 过滤', '过滤 --> 上报']
        src,prov=build_mermaid(arrow,45,'flowchart')
        self.assertEqual(len(prov['edges']),2)
        self.assertIn('上报',src)

    def test_ascii_ambiguous_rejected(self):
        with self.assertRaises(ValueError):build_mermaid(['项目系统','传感器','通讯'],10,'system-framework')
        with self.assertRaises(ValueError):build_mermaid(['项目系统','├── A'],10,'flowchart')

    def test_visual_plan_pure_readonly(self):
        text='# 项目\n\n## 2.1 功能架构\n系统功能\n├── 采集\n└── 上传\n'
        boxes=draft_windows(text)
        self.assertTrue(boxes)
        self.assertEqual(boxes[0]['category_hint'],'functional-architecture')
        self.assertEqual(boxes[0]['status'],'NEEDS_MANUAL_BOUNDARY_AND_FACT_REVIEW')

    def test_search_auto_uses_openverse_commons_without_ddgs(self):
        with patch('search_candidates.importlib.util.find_spec',return_value=None), \
             patch('search_candidates.openverse_search',return_value=[{'image_url':'https://test.invalid/a','source_page_url':'https://test.invalid/p'}]), \
             patch('search_candidates.commons_search',return_value=[]) as commons:
            calls, results=gather('STM32F103',provider='auto',limit=3,max_queries=1)
            self.assertEqual(len(results),1)
            self.assertTrue(any(c['provider']=='openverse' for c in calls))
            self.assertEqual(len(calls),2)
            self.assertEqual(commons.call_count,1)

    def test_installer_preserves_other_skills(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)/'thesis-doc-suite'
            skill=base/'skills'/'technical-visual-assets'
            skill.mkdir(parents=True)
            (skill/'SKILL.md').write_text('---\nname: technical-visual-assets\n---\n',encoding='utf-8')
            d=base/'core'/'contracts';d.mkdir(parents=True)
            other={'name':'opening-report-writer','command':'/thesis-doc-suite:opening-report-writer','version':'4.1.0'}
            (d/'skill-catalog.json').write_text(json.dumps({'skills':[other]}),encoding='utf-8')
            script=None
            # tools/ 在仓库根（插件布局 parents[4]）或包顶层；向上查找以兼容原目录镜像布局
            for up in Path(__file__).resolve().parents:
                cand=up/'tools'/'register_skill.py'
                if cand.is_file():script=cand;break
            self.assertIsNotNone(script,'未找到 tools/register_skill.py（应在仓库根或包顶层）')
            # If running test after package extraction, tools lives at package top.
            for _ in range(2):
                run=subprocess.run([sys.executable,str(script),'--plugin-root',str(base),'--apply'],capture_output=True,text=True,encoding='utf-8',errors='replace')
                self.assertEqual(run.returncode,0,run.stderr)
            items=json.loads((d/'skill-catalog.json').read_text('utf-8'))['skills']
            self.assertEqual(len(items),2)
            self.assertEqual(items[0],other)
            self.assertEqual(items[1]['version'],'1.1.0')

    def test_source_does_not_install_packages(self):
        for path in SCRIPTS.glob('*.py'):
            s=path.read_text('utf-8')
            # A comment or message may mention forbidden commands; we look
            # specifically for invocation APIs that would execute an installer.
            self.assertNotIn('subprocess.run(["pip"',s)
            self.assertNotIn('os.system(',s)
            self.assertNotIn('pip.main(',s)

if __name__=='__main__':unittest.main()
