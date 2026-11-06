import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]/'scripts'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SCRIPTS))
from render_candidate import validate, make_html, render, verify_triplet
from discovery_registry import add_batch, revise, set_status, latest_data, show, score_similarity, set_profile
from route_project_intent import route


def candidate(n='仓储物料管理', scen='实验室仓储'):
    return {'title':f'基于单片机的{n}系统',
            'overview':f'在{scen}场景中，通过持续采集货位信息，帮助工作人员查看物资状态并发现库存不足。',
            'signature':{'scenario':scen,'domain':'仓储'},
            'features':[{'name':'库存监测','description':'持续采集每个货位的数据，并展示各货位当前的剩余数量。'},
                        {'name':'缺货告警','description':'当库存数量低于预设门限时，通知现场管理人员。'}]}


class DiscoveryTest(unittest.TestCase):
    def test_route_empty(self): self.assertEqual(route({})['flow'],'intake')
    def test_route_major(self): self.assertEqual(route({'major':'电子信息工程'})['entry'],'major')
    def test_route_hybrid(self):
        d=route({'major':'电子信息工程','technologies':['STM32'], 'budget':'300'})
        self.assertEqual(d['entry'],'technology_keywords')
    def test_route_idea(self): self.assertEqual(route({'title':'智能镜子','still_exploring':True})['entry'],'project_idea')
    def test_route_formal_missing(self):
        self.assertEqual(route({'intent':'formal','title':'智能镜子'})['missing'],['features'])
    def test_route_formal_ready(self):
        self.assertEqual(route({'intent':'formal','title':'智能镜子','features':['天气显示']})['status'],'READY')
    def test_no_feature_only_labels(self):
        d=candidate();d['features'][0]['description']='好'
        with self.assertRaises(ValueError):validate(d)
    def test_html_escape(self):
        d=candidate();d['overview']='通过可靠监测展示库存数据与状态，其中负载 < 50 时提示异常。'
        self.assertIn('&lt; 50',make_html(d))
        d['overview']='<script>alert(1)</script>通过可靠监测展示库存数据与状态。'
        with self.assertRaises(ValueError): make_html(d)
    def test_batch_max_10(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):add_batch(Path(tmp),{'projects':[candidate(str(i)) for i in range(11)]})
            self.assertFalse((Path(tmp)/'discovery'/'catalog.json').exists())
    def test_exactly_ten_unique_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=[candidate(f'项目类型{i}号',f'独立场景{i}号') for i in range(10)]
            r=add_batch(Path(tmp),{'projects':data})
            self.assertEqual(r['created_count'],10)
            self.assertEqual(len(list((Path(tmp)/'projects').glob('PROJECT-*'))),10)
    def test_missing_user_confirm_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);r=add_batch(root,{'projects':[candidate()]})
            pid=r['created'][0]['project_id']
            set_status(root,pid,'interested')
            with self.assertRaisesRegex(ValueError,'--user-confirmed'):
                set_status(root,pid,'confirmed')
    def test_batch_independent_triplets_and_dup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            first=candidate();second=candidate('苗圃灌溉提醒','农业苗圃')
            result=add_batch(root,{'projects':[first, second]})
            self.assertEqual(result['created_count'],2)
            for item in result['created']:
                p=root/'projects'/item['project_id']/'versions'/'v1.0'
                self.assertEqual(len(list(p.iterdir())),3)
                verify_triplet([p/'项目概览.md',p/'项目概览.docx',p/'项目概览.html'])
                self.assertNotIn('推荐理由',(p/'项目概览.md').read_text('utf-8'))
            dupe=candidate('仓储物料管理','实验室仓储')
            result2=add_batch(root,{'projects':[dupe]})
            self.assertEqual(result2['created_count'],0)
            self.assertEqual(len(result2['skipped']),1)
    def test_reject_persists_and_reconsider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);r=add_batch(root,{'projects':[candidate()]});id=r['created'][0]['project_id']
            set_status(root,id,'rejected')
            self.assertEqual(add_batch(root,{'projects':[candidate()]})['created_count'],0)
            with self.assertRaises(ValueError):set_status(root,id,'interested')
            set_status(root,id,'interested',reconsider=True)
            self.assertEqual(latest_data(root,id)['status'],'interested')
            self.assertTrue((root/'discovery'/'rejected-projects.json').exists())
    def test_revise_same_id_version_and_confirm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);r=add_batch(root,{'projects':[candidate()]});id=r['created'][0]['project_id']
            with self.assertRaises(ValueError):set_status(root,id,'confirmed')
            set_status(root,id,'interested')
            modified=candidate();modified['features'].append({'name':'身份识别','description':'通过 RFID 卡片识别人员信息，并关联本次存取操作。'})
            result=revise(root,id,modified)
            self.assertEqual(result['version'],'v1.1')
            self.assertTrue((root/'projects'/id/'versions'/'v1.0'/'项目概览.docx').is_file())
            self.assertTrue((root/'projects'/id/'versions'/'v1.1'/'项目概览.docx').is_file())
            with self.assertRaises(ValueError):set_status(root,id,'confirmed')
            set_status(root,id,'confirmed',user_confirmed=True)
            with self.assertRaises(ValueError):revise(root,id,candidate('另外一个'))
            self.assertEqual(show(root)['total'],1)
    def test_profile_preserves_previous_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);set_profile(root,{'major':'电子信息'});set_profile(root,{'technologies':['STM32']})
            d=json.loads((root/'discovery'/'profile.json').read_text('utf-8'))
            self.assertEqual(d['known']['major'],'电子信息')
            self.assertEqual(d['known']['technologies'],['STM32'])
    def test_same_scenario_same_features_synonym_title(self):
        a=candidate('环境检测','仓储环境');b=candidate('环境采集','仓储环境')
        self.assertGreaterEqual(score_similarity(a,b),.82)

class TestValidateDiscovery(unittest.TestCase):
    def _validate_candidate(self, data, purpose='graduation_capstone'):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'cand.json'; f.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            cp = subprocess.run([sys.executable, str(ROOT/'scripts'/'validate_discovery.py'),
                '--candidate-file', str(f), '--purpose', purpose, '--report', str(Path(tmp)/'qa.json')],
                capture_output=True, text=True, encoding='utf-8', env=env)
            report = json.loads((Path(tmp)/'qa.json').read_text('utf-8')) if (Path(tmp)/'qa.json').exists() else {}
            return cp, report

    def test_five_features_pass(self):
        d = candidate(); d['features'] = [{'name': f'功能{i}', 'description': f'执行第{i}项采集并显示结果。'} for i in range(1, 6)]
        cp, report = self._validate_candidate(d)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual(report['status'], 'PASS')

    def test_only_two_features_fail(self):
        d = candidate(); d['features'] = d['features'][:2]
        cp, report = self._validate_candidate(d)
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any('功能数量不足' in e for e in (report.get('candidate', {}).get('errors') or [])), report)

    def test_overview_with_scene_passes(self):
        d = candidate(); d['features'] = [{'name': f'功能{i}', 'description': f'执行第{i}项采集并显示结果。'} for i in range(1, 6)]
        d['overview'] = '用于温室大棚环境监测，采集温湿度并显示。'
        cp, report = self._validate_candidate(d)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def test_overview_without_scene_warns(self):
        d = candidate(); d['features'] = [{'name': f'功能{i}', 'description': f'执行{i}项采集。'} for i in range(1, 6)]
        d['overview'] = '本系统进行环境监测。'
        cp, report = self._validate_candidate(d)
        self.assertEqual(cp.returncode, 0)
        self.assertTrue(any('概述未出现具体服务场所' in w for w in (report.get('candidate', {}).get('warnings') or [])), report)

    def test_banned_term_self_made_pcb_fails(self):
        d = candidate(); d['features'] = [{'name': f'功能{i}', 'description': f'执行{i}项采集。'} for i in range(1, 6)]
        d['overview'] = '温室大棚环境监测。'
        d['features'][0]['description'] = '需要自绘 PCB 并手工焊接传感器电路。'
        cp, report = self._validate_candidate(d)
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any('禁止要求用户自绘 PCB' in e for e in (report.get('candidate', {}).get('errors') or [])), report)

    def test_vague_feature_only_label_fails(self):
        d = candidate(); d['features'] = [{'name': '智能监测'}, {'name': '数据分析'}, {'name': '云平台控制'},
            {'name': '功能4', 'description': '执行采集。'}, {'name': '功能5', 'description': '执行显示。'}]
        for f in d['features']:
            if 'description' not in f: f['description'] = '执行相应任务。'
        d['overview'] = '用于温室大棚环境监测。'
        cp, report = self._validate_candidate(d)
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any('空洞功能名' in e for e in (report.get('candidate', {}).get('errors') or [])), report)

    def test_profile_with_budget_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'prof.json'; f.write_text(json.dumps({'known': {'budget': 5000, 'major': '电子'}}, ensure_ascii=False), encoding='utf-8')
            env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            cp = subprocess.run([sys.executable, str(ROOT/'scripts'/'validate_discovery.py'),
                '--profile-file', str(f), '--report', str(Path(tmp)/'qa.json')],
                capture_output=True, text=True, encoding='utf-8', env=env)
            self.assertEqual(cp.returncode, 2)
            report = json.loads((Path(tmp)/'qa.json').read_text('utf-8'))
            self.assertTrue(any('budget' in e for e in report.get('profile', {}).get('errors') or []), report)

    def test_router_no_budget_in_preserve_context(self):
        from route_project_intent import route
        r = route({'intent': 'formal', 'title': '智能镜子', 'features': ['天气显示']})
        self.assertNotIn('budget', r.get('preserve_context', []))

    def test_revise_accepts_change_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = add_batch(root, {'projects': [candidate()]})
            pid = created['created'][0]['project_id']
            modified = candidate()
            modified['features'].append({'name': '身份识别', 'description': '通过 RFID 卡片识别人员信息，并关联本次存取操作。'})
            result = revise(root, pid, {**modified, 'change_summary': '新增身份识别'})
            self.assertEqual(result['version'], 'v1.1')
            log = (root / 'discovery' / 'history.jsonl').read_text(encoding='utf-8')
            self.assertIn('新增身份识别', log)

    def test_no_stale_three_entry_wording(self):
        for rel in (
            'SKILL.md', 'README.md',
            'references/discovery-mode-router.md', 'references/quality-gates.md',
            'templates/discovery-intake-message.md', 'scripts/route_project_intent.py',
        ):
            text = (ROOT / rel).read_text(encoding='utf-8')
            self.assertNotIn('三入口', text, rel)
            self.assertNotIn('三种入口', text, rel)

    def test_default_intake_asks_topic_direction(self):
        text = (ROOT / 'templates' / 'discovery-intake-message.md').read_text(encoding='utf-8')
        self.assertIn('你想找什么方向的毕设', text)
        self.assertNotIn('预算', text)
        self.assertNotIn('任选其一', text)

if __name__=='__main__':unittest.main()
