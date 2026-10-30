import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import project_assets as a
from tests.test_pipeline import draft

class TestAssetCompatibility(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory()
        self.root=Path(self.td.name)
        a.init(Namespace(root=str(self.root),project_id='EXAMPLE-ONLY',name='离线测试项目',actor='test'))
    def tearDown(self):self.td.cleanup()

    def test_existing_schema_and_safe_runtime(self):
        base=self.root/'project-assets'
        self.assertEqual(a.load(base/'project.json')['schema_version'],1)
        self.assertTrue((base/'facts.json').exists())
        a.create_workdir(Namespace(root=str(self.root),run_id='test-run'))
        work=self.root/'.skill-tmp'/'thesis-midterm-check-write'/'test-run'
        self.assertTrue((work/a.MARKER).exists())
        with self.assertRaises(ValueError):a.cleanup(Namespace(root=str(self.root),run_id='../test-run'))
        a.cleanup(Namespace(root=str(self.root),run_id='test-run'))
        self.assertFalse(work.exists())
        self.assertTrue(base.exists())

    def test_shared_progress_and_compose(self):
        base=self.root/'project-assets'
        inp=self.root/'import.json'
        inp.write_text(json.dumps({'project_id':'EXAMPLE-ONLY','items':[{'id':'PROG-001',
                'category':'in_progress','status':'draft','as_of':'2026-10-30',
                'description':'测试记录','source':'本地离线测试文件'}]},ensure_ascii=False),encoding='utf-8')
        a.merge(Namespace(root=str(self.root),kind='progress',input=str(inp),replace=False,reason='',actor='test'))
        self.assertEqual(a.load(base/'progress.json')['items'][0]['id'],'PROG-001')
        d=draft();d['project_id']='EXAMPLE-ONLY';d['asset_progress_ids']=['PROG-001']
        path=self.root/'draft.json';out=self.root/'composed.json'
        path.write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
        a.compose(Namespace(root=str(self.root),draft=str(path),out=str(out)))
        self.assertEqual(a.load(out)['asset_trace']['progress'],['PROG-001'])

    def test_project_mismatch_is_blocked(self):
        with self.assertRaises(ValueError):
            a.init(Namespace(root=str(self.root),project_id='SECOND',name='另一项目',actor='test'))

if __name__=='__main__':unittest.main()
