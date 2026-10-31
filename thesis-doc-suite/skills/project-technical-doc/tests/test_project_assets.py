"""project_assets.py 烟测：init/merge/record-use/workdir/cleanup 的安全边界。

只在系统临时目录内运行，不触碰真实项目资料。
运行：python -m unittest discover tests
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'project_assets.py'


def run(*args):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    return subprocess.run([sys.executable, str(SCRIPT), *[str(a) for a in args]],
                          capture_output=True, text=True, encoding='utf-8', errors='replace',
                          env=env)


class ProjectAssetsSmoke(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='pa-test-'))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.inputs = self.root / 'in'
        self.inputs.mkdir()

    def write_json(self, name, payload):
        path = self.inputs / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding='utf-8')
        return path

    def test_full_cycle_and_safety(self):
        root = self.root
        # init：创建一次；同 id 幂等；换 id 拒绝
        r = run('init', '--root', root, '--project-id', 'PROJ-T',
                '--name', '测试项目', '--actor', 'unit-test')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('CREATED', r.stdout)
        r = run('init', '--root', root, '--project-id', 'PROJ-T', '--name', '测试项目')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('EXISTS', r.stdout)
        r = run('init', '--root', root, '--project-id', 'PROJ-OTHER', '--name', 'x')
        self.assertEqual(r.returncode, 2)

        # references：新增 → 幂等 → 改内容须 --replace --reason
        ref1 = {'id': 'REF-001', 'citation': '作者. 题名[J]. 期刊, 2025, 1(1): 1-9.',
                'source_url': 'https://example.org/a', 'source_type': 'journal',
                'verified': True, 'checked_at': '2026-01-01', 'tags': ['iot'],
                'project_relevance': '烟测', 'notes': 'unit'}
        ref2 = {'id': 'REF-002', 'citation': '作者. 题名2[C]//会议. 2024: 1-5.',
                'source_url': 'https://example.org/b', 'source_type': 'conference',
                'verified': True, 'checked_at': '2026-01-02', 'tags': [],
                'project_relevance': '烟测', 'notes': 'unit'}
        p = self.write_json('refs.json', {'project_id': 'PROJ-T', 'items': [ref1, ref2]})
        r = run('merge', '--root', root, '--kind', 'references', '--input', p,
                '--actor', 'unit-test')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('UPDATED', r.stdout)
        r = run('merge', '--root', root, '--kind', 'references', '--input', p)
        self.assertIn('UNCHANGED', r.stdout)
        changed = dict(ref1, citation='作者. 题名（更正）[J]. 期刊, 2025, 1(1): 1-9.')
        p2 = self.write_json('refs-changed.json',
                             {'project_id': 'PROJ-T', 'items': [changed]})
        r = run('merge', '--root', root, '--kind', 'references', '--input', p2)
        self.assertEqual(r.returncode, 2)
        r = run('merge', '--root', root, '--kind', 'references', '--input', p2,
                '--replace', '--reason', 'DOI 元数据更正', '--actor', 'unit-test')
        self.assertEqual(r.returncode, 0, r.stderr)
        # verified=true 缺 checked_at 拒绝
        bad_ref = dict(ref2, id='REF-003', checked_at=None)
        p3 = self.write_json('refs-bad.json', {'project_id': 'PROJ-T', 'items': [bad_ref]})
        r = run('merge', '--root', root, '--kind', 'references', '--input', p3)
        self.assertEqual(r.returncode, 2)

        # schedule：合法 draft 入库；缺周拒绝
        plan = {'id': 'PLAN-1', 'status': 'draft', 'total_weeks': 4,
                'stages': [{'id': 'STG-1', 'from_week': 1, 'to_week': 2, 'task': '需求分析'},
                           {'id': 'STG-2', 'from_week': 3, 'to_week': 4, 'task': '联调测试'}]}
        p = self.write_json('plan.json', {'project_id': 'PROJ-T', 'plan': plan})
        r = run('merge', '--root', root, '--kind', 'schedule', '--input', p,
                '--actor', 'unit-test')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('UPDATED', r.stdout)
        bad_plan = dict(plan, stages=[plan['stages'][0]])
        p = self.write_json('plan-bad.json', {'project_id': 'PROJ-T', 'plan': bad_plan})
        r = run('merge', '--root', root, '--kind', 'schedule', '--input', p)
        self.assertEqual(r.returncode, 2)

        # facts：合法入库；非法 status 拒绝
        fact = {'id': 'FACT-001', 'statement': '主控为测试芯片',
                'source': {'file': 'a.md', 'section': '§1'}, 'status': 'declared'}
        p = self.write_json('facts.json', {'project_id': 'PROJ-T', 'items': [fact]})
        r = run('merge', '--root', root, '--kind', 'facts', '--input', p,
                '--actor', 'unit-test')
        self.assertEqual(r.returncode, 0, r.stderr)
        bad_fact = dict(fact, id='FACT-002', status='done')
        p = self.write_json('facts-bad.json', {'project_id': 'PROJ-T', 'items': [bad_fact]})
        r = run('merge', '--root', root, '--kind', 'facts', '--input', p)
        self.assertEqual(r.returncode, 2)

        # record-use：真实成品登记；未知 REF 拒绝；临时目录内文件拒绝
        doc = root / 'deliverables' / 'doc.txt'
        doc.parent.mkdir()
        doc.write_text('final', encoding='utf-8')
        r = run('record-use', '--root', root, '--file', doc,
                '--doc-type', 'opening-report', '--ref-ids', 'REF-001,REF-002',
                '--actor', 'unit-test')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('RECORDED', r.stdout)
        r = run('record-use', '--root', root, '--file', doc,
                '--doc-type', 'x', '--ref-ids', 'REF-999')
        self.assertEqual(r.returncode, 2)

        # workdir/cleanup：所有权标记；外来标记目录拒绝删除
        r = run('workdir', '--root', root, '--run-id', 'run-1')
        self.assertEqual(r.returncode, 0, r.stderr)
        run_dir = Path(r.stdout.strip())
        markers = [q for q in run_dir.iterdir() if q.name.startswith('.owned-by')]
        self.assertEqual(len(markers), 1)
        tmp_file = run_dir / 'tmp.txt'
        tmp_file.write_text('x', encoding='utf-8')
        r = run('record-use', '--root', root, '--file', tmp_file,
                '--doc-type', 'x')
        self.assertEqual(r.returncode, 2)
        foreign = run_dir.parent / 'foreign'
        foreign.mkdir()
        (foreign / markers[0].name).write_text('intruder\n', encoding='utf-8')
        r = run('cleanup', '--root', root, '--run-id', 'foreign')
        self.assertEqual(r.returncode, 2)
        self.assertTrue(foreign.exists())
        r = run('cleanup', '--root', root, '--run-id', 'run-1')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(run_dir.exists())
        self.assertTrue(foreign.exists())

        # status：资产概览可解析
        r = run('status', '--root', root)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data['project_id'], 'PROJ-T')
        self.assertEqual(data['references'], 2)  # REF-001 已替换、REF-003 被拒
        self.assertEqual(data['facts'], 1)
        self.assertEqual(data['schedule']['total_weeks'], 4)


if __name__ == '__main__':
    unittest.main()
