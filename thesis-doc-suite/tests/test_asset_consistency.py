#!/usr/bin/env python3
"""Behavioral contract test for every project_assets implementation in the plugin.

The canonical core implementation and each Skill's protocol-compatible copy must
behave identically for the shared operations (init / merge / workdir / cleanup /
record-use / status). Each Skill copy must own exactly its own run directory.
All data is synthetic TEST data in temporary directories.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]

CANONICAL = ('thesis-doc-suite', ROOT / 'core' / 'asset-management' / 'project_assets.py')
SKILL_COPIES = [
    (d.name, d / 'scripts' / 'project_assets.py')
    for d in sorted((ROOT / 'skills').iterdir())
    if (d / 'scripts' / 'project_assets.py').is_file()
]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(f'pa_{name}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fixture_reference(ref_id='REF-001', verified=True):
    return {'id': ref_id, 'citation': f'示例作者. 示例论文{ref_id}[J]. 示例期刊, 2099, 1(1): 1-2.',
            'source_url': 'https://example.invalid/paper', 'source_type': 'journal',
            'verified': verified, 'checked_at': '2099-01-01'}


class ContractMixin:
    """Shared behavioral scenarios; mixed into one TestCase per implementation."""

    module = None
    owner = None  # expected owning skill name

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'
        self.root.mkdir()
        self.mod = self.module

    def init_store(self, project_id='TEST-PROJ'):
        self.mod.init(NS(root=self.root, project_id=project_id,
                         name='合成测试项目', actor='test'))

    def merge_file(self, kind, payload):
        inp = Path(self.temp.name) / f'{kind}-in.json'
        inp.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        return inp

    def test_init_is_idempotent_and_guarded(self):
        self.init_store()
        base = self.root / 'project-assets'
        self.assertTrue((base / 'project.json').is_file())
        self.assertTrue((base / 'references.json').is_file())
        # same id: no overwrite
        self.mod.init(NS(root=self.root, project_id='TEST-PROJ', name='改名企图', actor='test'))
        data = json.loads((base / 'project.json').read_text(encoding='utf-8'))
        self.assertEqual(data['name'], '合成测试项目')
        # different id: refuse
        with self.assertRaises(ValueError):
            self.mod.init(NS(root=self.root, project_id='OTHER-PROJ', name='x', actor='test'))

    def test_merge_refuses_silent_overwrite(self):
        self.init_store()
        inp = self.merge_file('references', {'items': [fixture_reference()]})
        self.mod.merge(NS(root=self.root, kind='references', input=inp,
                          replace=False, reason='', actor='test'))
        changed = fixture_reference()
        changed['citation'] = '改过的著录文本'
        inp2 = self.merge_file('references2', {'items': [changed]})
        with self.assertRaises(ValueError):
            self.mod.merge(NS(root=self.root, kind='references', input=inp2,
                              replace=False, reason='', actor='test'))
        # explicit replace with reason works
        self.mod.merge(NS(root=self.root, kind='references', input=inp2,
                          replace=True, reason='依据新检索修正著录', actor='test'))

    def test_merge_requires_verification_evidence(self):
        self.init_store()
        bad = fixture_reference(verified=True)
        del bad['checked_at']
        inp = self.merge_file('references', {'items': [bad]})
        with self.assertRaises(ValueError):
            self.mod.merge(NS(root=self.root, kind='references', input=inp,
                              replace=False, reason='', actor='test'))
        ok = fixture_reference(verified=False)
        del ok['checked_at']
        inp2 = self.merge_file('references2', {'items': [ok]})
        self.mod.merge(NS(root=self.root, kind='references', input=inp2,
                          replace=False, reason='', actor='test'))

    def test_cross_project_merge_refused(self):
        self.init_store(project_id='PROJ-A')
        inp = self.merge_file('references', {'project_id': 'PROJ-B', 'items': [fixture_reference()]})
        with self.assertRaises(ValueError):
            self.mod.merge(NS(root=self.root, kind='references', input=inp,
                              replace=False, reason='', actor='test'))

    def test_workdir_ownership_and_cleanup(self):
        self.init_store()
        self.mod.create_workdir(NS(root=self.root, run_id='run-001'))
        wd = self.root / '.skill-tmp' / self.mod.WORK_BASE[1] / 'run-001'
        self.assertTrue(wd.is_dir())
        marker = wd / self.mod.MARKER
        self.assertTrue(marker.is_file())
        # cleanup with wrong run id refuses
        with self.assertRaises(ValueError):
            self.mod.cleanup(NS(root=self.root, run_id='../escape'))
        # foreign marker refuses deletion
        (wd / self.mod.MARKER).write_text('someone-else\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.mod.cleanup(NS(root=self.root, run_id='run-001'))
        # marker content is '<owner>\n'
        (wd / self.mod.MARKER).write_text(self.mod.WORK_BASE[1] + '\n', encoding='utf-8')
        self.mod.cleanup(NS(root=self.root, run_id='run-001'))
        self.assertFalse(wd.exists())

    def test_record_use_refuses_temp_and_missing(self):
        self.init_store()
        self.mod.create_workdir(NS(root=self.root, run_id='run-002'))
        tmp_file = self.root / '.skill-tmp' / self.mod.WORK_BASE[1] / 'run-002' / 'x.docx'
        tmp_file.write_bytes(b'SYNTHETIC TEST - NOT DOCX')
        with self.assertRaises(ValueError):
            self.mod.record_use(NS(root=self.root, file=str(tmp_file), doc_type='taskbook',
                                   ref_ids='', actor='test'))
        with self.assertRaises(ValueError):
            self.mod.record_use(NS(root=self.root, file=str(self.root / 'missing.docx'),
                                   doc_type='taskbook', ref_ids='', actor='test'))
        final = self.root / 'deliverables' / 'demo' / 'final.docx'
        final.parent.mkdir(parents=True, exist_ok=True)
        final.write_bytes(b'SYNTHETIC TEST - NOT DOCX')
        self.mod.record_use(NS(root=self.root, file=str(final), doc_type='demo',
                               ref_ids='', actor='test'))
        ledger = (self.root / 'project-assets' / 'activity.jsonl').read_text(encoding='utf-8')
        self.assertIn('document-published', ledger)

    def test_status_reports_counts(self):
        self.init_store()
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.mod.status(NS(root=self.root))
        data = json.loads(buf.getvalue())
        self.assertEqual(data['project_id'], 'TEST-PROJ')
        self.assertEqual(data['references'], 0)

    def test_owner_constants_match_skill(self):
        if self.owner == 'thesis-doc-suite':
            self.assertEqual(self.mod.WORK_BASE, ('.skill-tmp', 'thesis-doc-suite'))
        else:
            self.assertEqual(self.mod.WORK_BASE[1], self.owner)
            self.assertEqual(self.mod.MARKER, f'.owned-by-{self.owner}')


def make_case(module, owner):
    name = 'Test_' + owner.replace('-', '_')
    cls = type(name, (ContractMixin, unittest.TestCase), {'module': module, 'owner': owner})
    return cls


MODULES = [CANONICAL] + SKILL_COPIES
for _mod_path_owner in MODULES:
    _name, _path = _mod_path_owner
    _loaded = load_module(_name, _path)
    globals()[f'Test_{_name.replace("-", "_")}'] = make_case(_loaded, _name)


if __name__ == '__main__':
    unittest.main(verbosity=1)
