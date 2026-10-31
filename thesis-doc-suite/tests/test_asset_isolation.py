#!/usr/bin/env python3
"""Cross-Skill asset sharing & isolation tests (synthetic data only).

Verifies the plugin's core contract:
  - two different Skills share ONE project asset bundle via stable IDs
  - different projects are fully isolated (no cross-project merge)
  - already-confirmed shared assets are never silently overwritten across Skills
  - run-dir cleanup only touches the calling Skill's own run directory
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]


def load(skill_name):
    path = ROOT / 'skills' / skill_name / 'scripts' / 'project_assets.py'
    spec = importlib.util.spec_from_file_location(f'iso_{skill_name}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ref(ref_id):
    return {'id': ref_id, 'citation': f'示例作者. 合成文献{ref_id}[J]. 示例期刊, 2099.',
            'source_url': 'https://example.invalid/x', 'source_type': 'journal',
            'verified': True, 'checked_at': '2099-01-01'}


def plan(plan_id='PLAN-001', status='draft'):
    return {'id': plan_id, 'status': status, 'total_weeks': 4,
            'stages': [{'id': 'S1', 'from_week': 1, 'to_week': 2, 'task': '合成阶段一'},
                       {'id': 'S2', 'from_week': 3, 'to_week': 4, 'task': '合成阶段二'}]}


class SharingAndIsolation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'proj'
        self.root.mkdir()
        self.taskbook = load('thesis-taskbook-write')
        self.midterm = load('thesis-midterm-check-write')
        self.litrev = load('literature-review-write')
        for m in (self.taskbook, self.midterm):
            m.init(NS(root=self.root, project_id='SHARED-PROJ', name='共享测试', actor='test'))

    def merge(self, mod, kind, payload, replace=False, reason=''):
        inp = Path(self.temp.name) / f'in-{kind}-{id(mod)}.json'
        inp.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        mod.merge(NS(root=self.root, kind=kind, input=inp,
                     replace=replace, reason=reason, actor='test'))

    def test_two_skills_share_one_bundle(self):
        # taskbook contributes references and the schedule baseline
        self.merge(self.taskbook, 'references', {'items': [ref('REF-001'), ref('REF-002')]})
        self.merge(self.taskbook, 'schedule', {'plan': plan()})
        # midterm reads the very same store and adds a progress snapshot
        self.merge(self.midterm, 'progress', {'items': [{
            'id': 'PROG-001', 'as_of': '2099-02-01', 'category': 'completed',
            'status': 'draft', 'description': '合成进展', 'source': '用户口述（测试）'}]})
        refs = json.loads((self.root / 'project-assets' / 'references.json').read_text(encoding='utf-8'))
        sched = json.loads((self.root / 'project-assets' / 'schedule.json').read_text(encoding='utf-8'))
        prog = json.loads((self.root / 'project-assets' / 'progress.json').read_text(encoding='utf-8'))
        self.assertEqual({r['id'] for r in refs['items']}, {'REF-001', 'REF-002'})
        self.assertEqual(sched['plan']['id'], 'PLAN-001')
        self.assertEqual(prog['items'][0]['id'], 'PROG-001')
        # both skills see the same project identity
        for mod in (self.taskbook, self.midterm):
            base, meta = mod.get_store(self.root)
            self.assertEqual(meta['project_id'], 'SHARED-PROJ')

    def test_no_silent_overwrite_across_skills(self):
        self.merge(self.taskbook, 'schedule', {'plan': plan(status='confirmed')})
        # midterm tries to swap the confirmed plan without evidence → refused
        with self.assertRaises(ValueError):
            self.merge(self.midterm, 'schedule', {'plan': plan('PLAN-002')})
        # with explicit replace + reason it is allowed and audited
        self.merge(self.midterm, 'schedule', {'plan': plan('PLAN-002')}, replace=True,
                   reason='依据用户新安排（测试）')
        ledger = (self.root / 'project-assets' / 'activity.jsonl').read_text(encoding='utf-8')
        self.assertIn('PLAN-002', ledger)

    def test_projects_are_isolated(self):
        self.merge(self.taskbook, 'references', {'items': [ref('REF-001')]})
        other = Path(self.temp.name) / 'other'
        other.mkdir()
        self.litrev.init(NS(root=other, project_id='OTHER-PROJ', name='另一个项目', actor='test'))
        inp = Path(self.temp.name) / 'in-other.json'
        # a payload belonging to SHARED-PROJ must not leak into OTHER-PROJ's store
        inp.write_text(json.dumps({'project_id': 'SHARED-PROJ',
                                   'items': [ref('REF-999')]}, ensure_ascii=False),
                       encoding='utf-8')
        with self.assertRaises(ValueError):
            self.litrev.merge(NS(root=other, kind='references', input=inp,
                                 replace=False, reason='', actor='test'))
        # OTHER-PROJ merges its own item into its own store only
        inp.write_text(json.dumps({'project_id': 'OTHER-PROJ',
                                   'items': [ref('REF-999')]}, ensure_ascii=False),
                       encoding='utf-8')
        self.litrev.merge(NS(root=other, kind='references', input=inp,
                             replace=False, reason='', actor='test'))
        a = json.loads((self.root / 'project-assets' / 'references.json').read_text(encoding='utf-8'))
        b = json.loads((other / 'project-assets' / 'references.json').read_text(encoding='utf-8'))
        self.assertEqual([r['id'] for r in a['items']], ['REF-001'])
        self.assertEqual([r['id'] for r in b['items']], ['REF-999'])

    def test_cleanup_never_crosses_skill_boundaries(self):
        self.taskbook.create_workdir(NS(root=self.root, run_id='tb-run'))
        self.midterm.create_workdir(NS(root=self.root, run_id='mt-run'))
        tb_dir = self.root / '.skill-tmp' / 'thesis-taskbook-write' / 'tb-run'
        mt_dir = self.root / '.skill-tmp' / 'thesis-midterm-check-write' / 'mt-run'
        # midterm cannot delete taskbook's run (different ownership base)
        with self.assertRaises(ValueError):
            self.midterm.cleanup(NS(root=self.root, run_id='tb-run'))
        # taskbook cannot delete midterm's run
        with self.assertRaises(ValueError):
            self.taskbook.cleanup(NS(root=self.root, run_id='mt-run'))
        self.assertTrue(tb_dir.is_dir())
        self.assertTrue(mt_dir.is_dir())
        # each cleans its own; assets and deliverables survive
        self.taskbook.cleanup(NS(root=self.root, run_id='tb-run'))
        self.midterm.cleanup(NS(root=self.root, run_id='mt-run'))
        self.assertFalse(tb_dir.exists())
        self.assertFalse(mt_dir.exists())
        self.assertTrue((self.root / 'project-assets' / 'project.json').is_file())
        self.assertTrue((self.root / 'project-assets' / 'references.json').is_file())


if __name__ == '__main__':
    unittest.main(verbosity=1)
