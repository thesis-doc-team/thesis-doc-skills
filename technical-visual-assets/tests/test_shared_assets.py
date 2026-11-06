#!/usr/bin/env python3
"""共享资产契约测试：项目隔离、facts 可选、运行区所有权标记（与六件套同一契约）。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'visual_assets.py'


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def init_project(root):
    base = root / 'project-assets'
    base.mkdir(parents=True, exist_ok=True)
    (base / 'project.json').write_text(json.dumps(
        {'schema_version': 1, 'project_id': 'demo-tva-001', 'name': '演示项目'},
        ensure_ascii=False), 'utf-8')
    return base


class TestSharedAssets(unittest.TestCase):
    def test_workdir_without_facts(self):
        # 契约：facts.json 缺失按空库处理，不阻断（与其它 Skill 一致）
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_project(root)
            r = run('workdir', '--root', root, '--project-id', 'demo-tva-001')
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            run_id = json.loads(r.stdout)['run_id']
            marker = (root / '.skill-tmp' / 'technical-visual-assets' / run_id
                      / '.owned-by-technical-visual-assets')
            self.assertTrue(marker.is_file())
            # 新标记内容与其它 Skill 统一为技能名
            self.assertEqual(marker.read_text('utf-8').strip(), 'technical-visual-assets')

    def test_project_id_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_project(root)
            r = run('workdir', '--root', root, '--project-id', 'other-project')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('project_id', r.stderr + r.stdout)

    def test_cleanup_accepts_legacy_marker(self):
        # 兼容升级前以 project_id 作标记内容的旧运行目录
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_project(root)
            d = root / '.skill-tmp' / 'technical-visual-assets' / 'legacy-run'
            d.mkdir(parents=True)
            (d / '.owned-by-technical-visual-assets').write_text('demo-tva-001', 'utf-8')
            r = run('cleanup', '--root', root, '--project-id', 'demo-tva-001', '--run-id', 'legacy-run')
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertFalse(d.exists())

    def test_cleanup_refuses_foreign_marker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_project(root)
            d = root / '.skill-tmp' / 'technical-visual-assets' / 'foreign-run'
            d.mkdir(parents=True)
            (d / '.owned-by-technical-visual-assets').write_text('someone-else', 'utf-8')
            r = run('cleanup', '--root', root, '--project-id', 'demo-tva-001', '--run-id', 'foreign-run')
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(d.exists())


if __name__ == '__main__':
    unittest.main()