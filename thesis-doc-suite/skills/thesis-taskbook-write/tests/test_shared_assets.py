#!/usr/bin/env python3
"""Shared-asset contract regression. All example references are synthetic TEST data."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('project_assets', ROOT / 'scripts/project_assets.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SharedAssets(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.outside = self.root / 'user-original.md'
        self.outside.write_text('USER ORIGINAL - DO NOT DELETE', encoding='utf-8')
        mod.init(NS(root=self.root, project_id='PROJECT-A', name='测试项目', actor='test'))
        self.base = self.root / 'project-assets'
        self.work = self.root.joinpath(*mod.WORK_BASE)

    def fixture_references(self):
        return {'project_id': 'PROJECT-A', 'items': [
            {'id': f'REF-{i:03d}',
             'citation': f'TEST ONLY author{i}. Fictional paper {i}[J]. NotReal, 2026.',
             'source_url': f'https://example.org/TEST-ONLY/{i}',
             'source_type': 'journal', 'verified': True, 'checked_at': '2026-10-30'}
            for i in range(1, 13)]}

    def fixture_schedule(self):
        return {'project_id': 'PROJECT-A', 'plan': {
            'id': 'PLAN-1', 'status': 'draft', 'total_weeks': 6,
            'stages': [
                {'id':'STAGE-1', 'from_week':1,'to_week':2,'task':'TEST ONLY: literature'},
                {'id':'STAGE-2', 'from_week':3,'to_week':6,'task':'TEST ONLY: implementation'}]}}

    def write(self, name, content):
        file = self.root / name
        file.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
        return file

    def merge(self, kind, content, **kw):
        file = self.write('in.json', content)
        mod.merge(NS(root=self.root, kind=kind, input=file, replace=kw.get('replace', False),
                     reason=kw.get('reason', ''), actor='test'))

    def test_asset_reuse_compose_and_audit(self):
        self.merge('references', self.fixture_references())
        self.merge('schedule', self.fixture_schedule())
        draft = self.write('draft.json', {
            'project_id':'PROJECT-A', 'title':'测试项目',
            'thesis_content':['TEST ONLY CONTENT'],
            'issuer_opinion':'示例意见用于测试，真实意见必须由当前项目单独起草并经指导教师审核' * 3,
            'selected_reference_ids':[f'REF-{i:03d}' for i in range(12, 2, -1)]})
        out = self.root / 'composed.json'
        mod.compose(NS(root=self.root, draft=draft, out=out))
        data = mod.load(out)
        self.assertEqual(len(data['references']), 10)
        self.assertIn('Fictional paper 12', data['references'][0]['citation'])
        self.assertIn('Fictional paper 3', data['references'][-1]['citation'])
        self.assertEqual(data['total_weeks'], 6)
        self.assertEqual(len(data['schedule']), 2)
        self.assertTrue((self.base / 'activity.jsonl').is_file())
        self.assertEqual(len(mod.load(self.base/'references.json')['items']), 12)
        self.assertEqual(mod.load(self.base/'schedule.json')['plan']['status'], 'draft')

    def test_conflicts_require_reason(self):
        refs = self.fixture_references()
        self.merge('references', refs)
        changed = {'project_id':'PROJECT-A', 'items':[dict(refs['items'][0], citation='NEW TEXT TEST')]}
        with self.assertRaises(ValueError):
            self.merge('references', changed)
        self.assertEqual(mod.load(self.base/'references.json')['items'][0]['citation'],
                         refs['items'][0]['citation'])
        self.merge('references', changed, replace=True, reason='人工确认的更正（测试）')
        self.assertEqual(mod.load(self.base/'references.json')['items'][0]['citation'], 'NEW TEXT TEST')

    def test_cross_project_and_schedule_gap_blocked(self):
        with self.assertRaises(ValueError):
            self.merge('references', {'project_id':'PROJECT-B', 'items': self.fixture_references()['items']})
        plan = self.fixture_schedule()
        plan['plan']['stages'][1]['from_week'] = 4
        with self.assertRaises(ValueError):
            self.merge('schedule', plan)

    def test_unverified_cannot_compose(self):
        refs = self.fixture_references()
        refs['items'][0]['verified'] = False
        refs['items'][0]['checked_at'] = None
        self.merge('references', refs)
        self.merge('schedule', self.fixture_schedule())
        draft = self.write('draft.json', {
            'title':'测试', 'thesis_content':['测试'], 'issuer_opinion':'测' * 55,
            'selected_reference_ids':[f'REF-{i:03d}' for i in range(1, 11)]})
        with self.assertRaises(ValueError):
            mod.compose(NS(root=self.root, draft=draft, out=self.root/'result.json'))

    def test_cleanup_only_owned_run(self):
        mod.create_workdir(NS(root=self.root, run_id='run-valid'))
        path = self.work/'run-valid'
        (path/'preview.png').write_bytes(b'not-a-real-preview')
        (path/'working-data.json').write_text('{}', encoding='utf-8')
        mod.cleanup(NS(root=self.root, run_id='run-valid'))
        self.assertFalse(path.exists())
        self.assertTrue(self.outside.exists())
        self.assertTrue(self.base.joinpath('project.json').exists())
        # Unmarked folders and escape attempts must never be deleted.
        (self.work/'unmarked').mkdir(parents=True)
        with self.assertRaises(ValueError):
            mod.cleanup(NS(root=self.root, run_id='unmarked'))
        with self.assertRaises(ValueError):
            mod.cleanup(NS(root=self.root, run_id='..'))
        self.assertTrue((self.work/'unmarked').exists())

    def test_full_asset_to_word_pipeline(self):
        """All references are synthetic placeholders; only the temporary test docx is built."""
        self.merge('references', self.fixture_references())
        self.merge('schedule', self.fixture_schedule())
        mod.create_workdir(NS(root=self.root, run_id='full-flow'))
        wd = self.work/'full-flow'
        draft = wd/'draft.json'
        draft.write_text(json.dumps({
            'title':'测试项目',
            'thesis_content':['测试用系统描述，不代表任何实际项目。'*3],
            'issuer_opinion':'测试说明，仅用来测试模板写入和共享资产接口，请勿作为真实任务书意见。'*4,
            'selected_reference_ids':[f'REF-{i:03d}' for i in range(1,11)]},
            ensure_ascii=False), encoding='utf-8')
        datafile = wd/'data.json'
        mod.compose(NS(root=self.root, draft=draft, out=datafile))
        fill = __import__('importlib').util.spec_from_file_location(
            'fill_taskbook_e2e', ROOT/'scripts/fill_taskbook.py')
        fillmod = __import__('importlib').util.module_from_spec(fill)
        fill.loader.exec_module(fillmod)
        validate = __import__('importlib').util.spec_from_file_location(
            'validate_taskbook_e2e', ROOT/'scripts/validate_taskbook.py')
        valmod = __import__('importlib').util.module_from_spec(validate)
        validate.loader.exec_module(valmod)
        final = self.root/'deliverables'/'taskbook'/'sample-test.docx'
        final.parent.mkdir(parents=True)
        fillmod.write(mod.load(datafile), ROOT/'assets/official-taskbook-template.docx', final)
        from docx import Document
        self.assertEqual(valmod.compare_structure(Document(ROOT/'assets/official-taskbook-template.docx'),
                                                  Document(final)), [])
        self.assertEqual(valmod.check_content(Document(final), mod.load(datafile))[0], [])
        mod.cleanup(NS(root=self.root, run_id='full-flow'))
        self.assertFalse(wd.exists())
        self.assertTrue(final.exists())
        self.assertTrue((self.base/'references.json').exists())
        self.assertTrue(self.outside.exists())

    def test_symlinked_workbase_blocked(self):
        outside_base = self.root/'outside-temp'
        outside_base.mkdir()
        temp_root = self.root/'.skill-tmp'
        try:
            temp_root.symlink_to(outside_base, target_is_directory=True)
        except (OSError, NotImplementedError):
            # Windows without管理员权限/开发者模式不允许创建符号链接，跳过而不误报失败
            self.skipTest('symlink creation not permitted on this system')
        with self.assertRaises(ValueError):
            mod.create_workdir(NS(root=self.root, run_id='unsafe'))
        self.assertFalse((outside_base/'thesis-taskbook-write'/'unsafe').exists())

    def test_record_use_relative_path_resolves_against_root(self):
        # 复盘回归：--file 相对路径按 --root 解析，不随进程 cwd 漂移（曾报"最终文件不存在"误导排查）
        import os
        self.merge('references', self.fixture_references())
        final = self.root/'deliverables'/'taskbook'/'final.docx'
        final.parent.mkdir(parents=True)
        final.write_bytes(b'SYNTHETIC TEST - NOT DOCX')
        cwd = Path.cwd()
        try:
            os.chdir(tempfile.gettempdir())
            mod.record_use(NS(root=self.root, file='deliverables/taskbook/final.docx',
                              doc_type='taskbook', ref_ids='REF-001', actor='test'))
        finally:
            os.chdir(cwd)

    def test_final_record_only_existing_file(self):
        self.merge('references', self.fixture_references())
        with self.assertRaises(ValueError):
            mod.record_use(NS(root=self.root, file=self.root/'missing.docx',
                              doc_type='taskbook', ref_ids='REF-001', actor='test'))
        final = self.root/'deliverables'/'taskbook'/'final.docx'
        final.parent.mkdir(parents=True)
        final.write_bytes(b'SYNTHETIC TEST - NOT DOCX')
        mod.record_use(NS(root=self.root, file=final, doc_type='taskbook',
                          ref_ids='REF-001,REF-002', actor='test'))
        ledger = (self.base/'activity.jsonl').read_text(encoding='utf-8')
        self.assertIn('document-published', ledger)
        self.assertIn('REF-002', ledger)

    def test_title_mismatch_blocked(self):
        # 共享资产一个项目只有一个正式题目：compose 必须拦截与 project.json name 不一致的题目
        self.merge('references', self.fixture_references())
        self.merge('schedule', self.fixture_schedule())
        draft = self.write('draft-bad-title.json', {
            'project_id':'PROJECT-A', 'title':'另一个项目的题目',
            'thesis_content':['TEST ONLY CONTENT'],
            'issuer_opinion':'示例意见用于测试，真实意见必须由当前项目单独起草并经指导教师审核' * 3,
            'selected_reference_ids':[f'REF-{i:03d}' for i in range(1, 11)]})
        with self.assertRaisesRegex(ValueError, '题目'):
            mod.compose(NS(root=self.root, draft=draft, out=self.root/'bad-out.json'))


if __name__ == '__main__':
    unittest.main()
