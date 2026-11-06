import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VAL=ROOT/'scripts'/'validate_docs.py'
WORK=ROOT/'scripts'/'project_workspace.py'
INTAKE=ROOT/'scripts'/'check_input.py'

INTRO='''# 示例项目｜项目介绍与功能说明\n\n## 1. 项目概述\n本项目为实验环境的监测终端，提供基本采集功能。\n\n## 2. 功能介绍\n温湿度采集：显示本地温度和湿度，断开传感器时显示无效提示。无线通信：将测量数据转发给远端。\n\n## 3. 使用流程\n启动后查看页面，监测数据变化。正常情况下页面持续刷新。用户可在本机看到测量时间和最近数据，远端接收节点能够展示周期上报的监测参数。若设备暂时离线，页面以明确提示区分未获得数据与有效数值；当前文字属于拟实施的用户体验目标，而非已经完成的实测结果。需要结合现场情况确认。\n'''
IMPL='''# 示例项目｜工程实施方案\n\n## 1. 需求与范围\n温湿度采集和无线通信为核心功能。\n\n## 2. 系统架构\n传感器驱动读取数值、标志有效性并交给显示与通信模块。\n\n## 3. 功能实现\n使用数据结构保存数值及最后更新时间，错误时置无效标志。\n\n## 4. 分阶段开发实施步骤\n第一步确认采集，第二步接收发送，第三步联调。\n\n## 5. 测试验收\n断开传感器应出现无效提示，收发端数据一致。通过串口工具注入一条正确和一条缺字段的监测帧，验证接收端能只接收合法字段；对于数据超过既定时效的情况，标记为过期。最后对本机供电、总线和无线中断恢复进行分阶段检查，记录操作步骤、期望表现与待执行测试的区别，不把测试计划宣称为已经验证。\n'''

class TestProjectSolution(unittest.TestCase):
    def validate(self,intro,impl,requirements=True):
        with tempfile.TemporaryDirectory() as t:
            tmp=Path(t); (tmp/'intro.md').write_text(intro,encoding='utf-8')
            (tmp/'impl.md').write_text(impl,encoding='utf-8')
            cmd=[sys.executable,str(VAL),'--intro',str(tmp/'intro.md'),'--implementation',str(tmp/'impl.md'),'--title','示例项目','--report',str(tmp/'qa.json')]
            if requirements:
                (tmp/'req.json').write_text(json.dumps({'requirements':[{'name':'温湿度采集','status':'confirmed'},{'name':'无线通信','status':'confirmed'}]},ensure_ascii=False),encoding='utf-8')
                cmd += ['--requirements',str(tmp/'req.json')]
            cp=subprocess.run(cmd,encoding='utf-8',capture_output=True)
            report=json.loads((tmp/'qa.json').read_text(encoding='utf-8'))
            return cp,report

    def test_valid_documents(self):
        cp,report=self.validate(INTRO,IMPL)
        self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
        self.assertIn(report['status'],('PASS','WARN'))
        self.assertEqual(report['summary']['errors'],0)

    def test_forbidden_meta_heading(self):
        cp,report=self.validate(INTRO+'\n## 9. 工程实施交付说明\n说明。\n',IMPL)
        self.assertEqual(cp.returncode,2)
        self.assertTrue(any('越界章节' in e for e in report['documents'][0]['errors']))

    def test_forbidden_business_label(self):
        cp,report=self.validate(INTRO,IMPL+'\n本付费文档提供方案。\n')
        self.assertEqual(cp.returncode,2)

    def test_introduction_cannot_have_code(self):
        cp,report=self.validate(INTRO+'\n```c\nint a=1;\n```\n',IMPL)
        self.assertEqual(cp.returncode,2)

    def test_missing_requirement_warn(self):
        cp,report=self.validate(INTRO.replace('无线通信','远端功能'),IMPL)
        self.assertEqual(cp.returncode,0)
        self.assertGreaterEqual(report['summary']['warnings'],1)

    def test_introduction_text_flow_allowed(self):
        cp,report=self.validate(INTRO+'\n```text\n设备启动 → 常驻显示 → 交互结束\n```\n',IMPL)
        self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)

    def test_optimization_cost_choice_is_valid(self):
        plan=IMPL+"\n## 6. 方案权衡与选型依据\n本轮成本优先，候选方案 A 与 B 先核实必需功能后比较成本、性能和实施复杂度。最终选择 A，因其总成本较低、性能达标、功能完整且风险较小。\n"
        cp, report=self.validate_with_priority(INTRO, plan, 'cost')
        self.assertEqual(cp.returncode, 0, cp.stdout+cp.stderr)
        self.assertEqual(report['optimization_check']['priority'], 'cost')

    def test_optimization_missing_candidate_comparison_fails(self):
        plan=IMPL+'\n当前成本优先。\n'
        cp, report=self.validate_with_priority(INTRO, plan, 'cost')
        self.assertEqual(cp.returncode,2)
        self.assertTrue(any('候选路线' in e for e in report['documents'][1]['errors']))

    def test_optimization_priority_not_applied_fails(self):
        plan=IMPL+'\n## 6. 方案权衡与选型依据\n候选方案比较成本、性能和功能。最终选择 A。\n'
        cp, report=self.validate_with_priority(INTRO, plan, 'performance')
        self.assertEqual(cp.returncode,2)
        self.assertTrue(any('性能优先' in e for e in report['documents'][1]['errors']))

    def test_optimization_concrete_decision_trace_no_new_warnings(self):
        plan=IMPL+"\n## 6. 方案权衡与选型依据\n本轮成本优先。候选方案 A：采用成熟串口模块，采购/开发成本低但扩展余量有限；方案 B：采用可编程无线平台，开发维护投入较高但扩展性更好。最终选择 A，原因是全部已确认功能与最低性能达标；放弃了 B 的扩展性。实施变化：无线驱动采用 UART 透传，验收检查远端数据显示、传感器异常帧和实际总成本。\n"
        cp,report=self.validate_with_priority(INTRO,plan,'cost')
        self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
        warnings=report['documents'][1]['warnings']
        self.assertFalse(any('候选方案缺少' in w or '未明确说明选定路线' in w or '未明确追踪偏好' in w for w in warnings))

    def test_optimization_weak_tradeoff_warns(self):
        plan=IMPL+"\n## 6. 方案权衡与选型依据\n本轮成本优先。候选方案 A 与 B 比较成本、性能和功能，最终选择 A。\n"
        cp,report=self.validate_with_priority(INTRO,plan,'cost')
        self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
        warnings=report['documents'][1]['warnings']
        self.assertTrue(any('候选方案缺少' in w for w in warnings))
        self.assertTrue(any('未明确追踪偏好' in w for w in warnings))

    def test_optimization_secondary_same_as_primary_invalid(self):
        plan=IMPL+"\n## 6. 方案权衡与选型依据\n本轮性能优先，候选方案 A/B 比较成本、性能、功能，最终选择 A。\n"
        cp,report=self.validate_with_priority(INTRO,plan,'performance',secondary='performance')
        self.assertEqual(cp.returncode,2)
        self.assertTrue(any('secondary_priority' in e for e in report['documents'][1]['errors']))

    def test_optimization_secondary_distinct_valid(self):
        plan=IMPL+"\n## 6. 方案权衡与选型依据\n本轮性能优先，候选方案 A/B 比较成本、性能和功能，最终选择 A。\n"
        cp,report=self.validate_with_priority(INTRO,plan,'performance',secondary='cost')
        self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
        self.assertEqual(report['optimization_check']['secondary_priority'],'cost')

    def test_opt_invalid_weights_fails(self):
        plan=IMPL+'\n## 6. 方案权衡与选型依据\n本轮功能优先，候选方案 A、B 比较成本、性能与功能。最终选择 A。\n'
        cp, report=self.validate_with_priority(INTRO, plan, 'function', weights={'cost':30,'performance':30,'function':30,'complexity':30})
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any('合计为100' in e for e in report['documents'][1]['errors']))

    def test_opt_priorities_all_have_weights_sum_100(self):
        reference=(ROOT/'references'/'optimization-and-tradeoff.md').read_text(encoding='utf-8')
        import re
        rows=re.findall(r'^\| (成本优先|性能优先|功能优先|均衡方案) \| ([0-9]+)% \| ([0-9]+)% \| ([0-9]+)% \| ([0-9]+)% \|',reference,re.M)
        self.assertEqual(len(rows),4)
        for row in rows:
            self.assertEqual(sum(map(int,row[1:])),100)

    def test_function_priority_does_not_authorize_new_features(self):
        ref=(ROOT/'references'/'optimization-and-tradeoff.md').read_text(encoding='utf-8')
        self.assertIn('不能',ref)
        self.assertIn('全部已确认功能',ref)

    def validate_with_priority(self, intro, impl, priority, weights=None, secondary=None):
        with tempfile.TemporaryDirectory() as t:
            tmp=Path(t)
            (tmp/'intro.md').write_text(intro,encoding='utf-8')
            (tmp/'impl.md').write_text(impl,encoding='utf-8')
            payload={'requirements':[{'name':'温湿度采集','status':'confirmed'},{'name':'无线通信','status':'confirmed'}],
                     'optimization':{'priority':priority,'status':'confirmed','source':'user'}}
            if weights is not None: payload['optimization']['custom_weights']=weights
            if secondary is not None: payload['optimization']['secondary_priority']=secondary
            (tmp/'req.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
            cp=subprocess.run([sys.executable,str(VAL),'--intro',str(tmp/'intro.md'),'--implementation',str(tmp/'impl.md'),
                '--title','示例项目','--requirements',str(tmp/'req.json'),'--report',str(tmp/'qa.json')],capture_output=True,text=True,encoding='utf-8')
            report=json.loads((tmp/'qa.json').read_text(encoding='utf-8'))
            return cp, report

    def check_intake(self,payload):
        with tempfile.TemporaryDirectory() as t:
            data=Path(t)/"request.json"
            data.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
            cp=subprocess.run([sys.executable,str(INTAKE),"--input",str(data)],capture_output=True,text=True,encoding="utf-8")
            return cp,json.loads(cp.stdout)

    def test_first_invocation_asks_title_and_requirements(self):
        cp,result=self.check_intake({})
        self.assertEqual(cp.returncode,3)
        self.assertEqual(result['status'],'NEEDS_INPUT')
        self.assertEqual(result['missing'],['project_title','requirements'])
        self.assertIn('项目题目',result['question'])
        self.assertIn('具体功能',result['question'])
        self.assertFalse(result['generate_allowed'])

    def test_intake_only_title_asks_only_requirements(self):
        _,result=self.check_intake({'project_title':'智能交互镜'})
        self.assertEqual(result['missing'],['requirements'])
        self.assertNotIn('项目题目',result['question'])

    def test_intake_only_requirements_asks_only_title(self):
        _,result=self.check_intake({'requirements':[{'name':'温湿度采集'}]})
        self.assertEqual(result['missing'],['project_title'])
        self.assertNotIn('具体功能',result['question'])

    def test_intake_two_present_asks_priority_only(self):
        _,result=self.check_intake({'project_title':'LoRa 环境节点','requirements':[{'name':'温湿度采集'}]})
        self.assertEqual(result['status'],'NEEDS_PRIORITY')
        self.assertFalse(result['generate_allowed'])

    def test_intake_direct_generation_with_both_present(self):
        cp,result=self.check_intake({'project_title':'LoRa 环境节点','requirements':[{'name':'温湿度采集'}], 'direct_generate':True})
        self.assertEqual(cp.returncode,0)
        self.assertTrue(result['generate_allowed'])
        self.assertEqual(result['priority'],'balanced')
        self.assertEqual(result['priority_status'],'proposed')

    def test_intake_direct_does_not_override_missing_required_fields(self):
        cp,result=self.check_intake({'project_title':'智能交互镜','requirements':[], 'direct_generate':True})
        self.assertEqual(cp.returncode,3)
        self.assertEqual(result['missing'],['requirements'])
        self.assertFalse(result['generate_allowed'])

    def test_intake_placeholder_title_and_features_not_accepted(self):
        _,result=self.check_intake({'project_title':'项目名','requirements':[{'name':'待补充'}], 'optimization':{'priority':'cost'}})
        self.assertEqual(result['missing'],['project_title','requirements'])

    def test_intake_ready_with_priority(self):
        cp,result=self.check_intake({'project_title':'智能交互镜','requirements':[{'name':'实时时钟'}], 'optimization':{'priority':'performance','status':'confirmed'}})
        self.assertEqual(cp.returncode,0)
        self.assertEqual(result['status'],'READY')
        self.assertEqual(result['priority'],'performance')

    def test_workspace_not_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            cmd=[sys.executable,str(WORK),'init','--root',t,'--project-id','proj001','--title','项目1']
            self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            same=subprocess.run(cmd,capture_output=True)
            self.assertEqual(same.returncode,0)
            diff=cmd.copy(); diff[diff.index('proj001')]='proj002'
            self.assertEqual(subprocess.run(diff,capture_output=True).returncode,2)
            actual=json.loads((Path(t)/'project-assets'/'project.json').read_text())
            self.assertEqual(actual['project_id'],'proj001')

    def test_workspace_version(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'deliverables'/'implementation-plan'
            path.mkdir(parents=True)
            (path/'foo-v2.md').write_text('a')
            (path/'foo-v5.md').write_text('b')
            cp=subprocess.run([sys.executable,str(WORK),'next-version','--root',t,'--doc-type','implementation'],capture_output=True,text=True)
            self.assertEqual(cp.stdout.strip(),'v6')

    def test_init_creates_canonical_assets(self):
        # 与六件套同一契约：canonical project.json + 空 facts/references/schedule + init 审计事件
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            cp=subprocess.run([sys.executable,str(WORK),'init','--root',t,'--project-id','proj001','--title','项目1'],capture_output=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
            base=root/'project-assets'
            project=json.loads((base/'project.json').read_text(encoding='utf-8'))
            self.assertEqual(project['name'],'项目1')
            self.assertIn('metadata',project)
            for kind in ('facts','references','schedule'):
                data=json.loads((base/f'{kind}.json').read_text(encoding='utf-8'))
                self.assertEqual(data['project_id'],'proj001')
            events=[json.loads(x) for x in (base/'activity.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertTrue(any(e.get('action')=='init' for e in events))

    def test_workdir_cleanup_roundtrip(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            subprocess.run([sys.executable,str(WORK),'init','--root',t,'--project-id','proj001','--title','项目1'],capture_output=True)
            cp=subprocess.run([sys.executable,str(WORK),'workdir','--root',t,'--project-id','proj001'],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(cp.returncode,0,cp.stderr)
            run=json.loads(cp.stdout)['run_id']
            d=root/'.skill-tmp'/'project-solution-write'/run
            self.assertEqual((d/'.owned-by-project-solution-write').read_text(encoding='utf-8').strip(),'project-solution-write')
            cp=subprocess.run([sys.executable,str(WORK),'cleanup','--root',t,'--project-id','proj001','--run-id',run],capture_output=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
            self.assertFalse(d.exists())

    def test_cleanup_refuses_foreign_marker(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            subprocess.run([sys.executable,str(WORK),'init','--root',t,'--project-id','proj001','--title','项目1'],capture_output=True)
            d=root/'.skill-tmp'/'project-solution-write'/'foreign-run'
            d.mkdir(parents=True)
            (d/'.owned-by-project-solution-write').write_text('someone-else\n',encoding='utf-8')
            cp=subprocess.run([sys.executable,str(WORK),'cleanup','--root',t,'--project-id','proj001','--run-id','foreign-run'],capture_output=True)
            self.assertEqual(cp.returncode,2)
            self.assertTrue(d.exists())

    def test_record_use_appends_activity(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            subprocess.run([sys.executable,str(WORK),'init','--root',t,'--project-id','proj001','--title','项目1'],capture_output=True)
            doc=root/'deliverables'/'project-introduction'/'项目1-项目介绍与功能说明-v1.md'
            doc.parent.mkdir(parents=True); doc.write_text('# 文档\n',encoding='utf-8')
            cp=subprocess.run([sys.executable,str(WORK),'record-use','--root',t,'--project-id','proj001','--file',str(doc),'--doc-type','introduction'],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(cp.returncode,0,cp.stderr)
            events=[json.loads(x) for x in (root/'project-assets'/'activity.jsonl').read_text(encoding='utf-8').splitlines()]
            ev=[e for e in events if e.get('action')=='document-published']
            self.assertEqual(len(ev),1)
            self.assertEqual(ev[0]['doc_type'],'project-introduction')
            self.assertEqual(len(ev[0]['sha256']),64)
            runfile=root/'.skill-tmp'/'project-solution-write'/'x'/'draft.md'
            runfile.parent.mkdir(parents=True); runfile.write_text('x',encoding='utf-8')
            bad=subprocess.run([sys.executable,str(WORK),'record-use','--root',t,'--project-id','proj001','--file',str(runfile),'--doc-type','introduction'],capture_output=True)
            self.assertEqual(bad.returncode,2)

    def test_write_asset_project_guard(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            subprocess.run([sys.executable,str(WORK),'init','--root',t,'--project-id','proj001','--title','项目1'],capture_output=True)
            good=Path(t)/'req.json'; good.write_text(json.dumps({'schema_version':1,'project_id':'proj001','items':[{'id':'REQ-001','name':'采集','status':'confirmed'}]},ensure_ascii=False),encoding='utf-8')
            cp=subprocess.run([sys.executable,str(WORK),'write-asset','--root',t,'--project-id','proj001','--kind','requirements','--input',str(good)],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(cp.returncode,0,cp.stderr)
            self.assertTrue((root/'project-assets'/'requirements.json').is_file())
            bad=Path(t)/'bad.json'; bad.write_text(json.dumps({'schema_version':1,'project_id':'other','items':[]},ensure_ascii=False),encoding='utf-8')
            cp=subprocess.run([sys.executable,str(WORK),'write-asset','--root',t,'--project-id','proj001','--kind','requirements','--input',str(bad)],capture_output=True)
            self.assertEqual(cp.returncode,2)

    def test_variant_boundary_headings_rejected(self):
        # 与六件套同一“变相章节”边界：换名的问题/不足/改进/风险/展望章节同样越界
        for heading in ('存在的问题','问题与改进','不足与优化','改进建议','改进方向','优化建议',
                        '优化方向','风险与对策','风险分析','风险评估','未来展望','技术展望',
                        '后续规划','后续计划','升级建议','升级计划','技术演进','未来工作','发展规划'):
            cp,report=self.validate(INTRO+f'\n## 9. {heading}\n内容。\n',IMPL)
            self.assertEqual(cp.returncode,2,heading)
            self.assertTrue(any('越界章节' in e for e in report['documents'][0]['errors']),heading)

    def test_boundary_allowed_sections_pass(self):
        # 反向：实施前提/选型依据/异常与排障是必要技术内容，不得误杀
        allowed=IMPL+'\n## 9. 实施前提与未确认条件\n器件手册待核对。\n\n## 10. 技术方案比较与选型依据\n按资源约束取舍。\n\n## 11. 异常与排障\n断线重试与恢复步骤。\n'
        cp,report=self.validate(INTRO,allowed)
        self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
        self.assertEqual(report['summary']['errors'],0)

    def test_design_freeze_guard_present(self):
        # 写正文前的冻结防线：SKILL 必须引用冻结表和参考文件，且文件真实存在
        skill=(ROOT/'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('设计冻结', skill)
        self.assertIn('design-freeze.md', skill)
        self.assertTrue((ROOT/'references'/'design-freeze-and-consistency.md').is_file())
        self.assertTrue((ROOT/'templates'/'design-freeze.md').is_file())

    def test_design_freeze_template_covers_consistency_axes(self):
        # 冻结表至少覆盖八类跨文档不变量与变更记录，防止退化为一句口号
        freeze=(ROOT/'templates'/'design-freeze.md').read_text(encoding='utf-8')
        for token in ('术语与默认值','页面/交互映射','数据结构与配置布局','协议契约',
                      '状态枚举与优先级','资源与接口','失败分支与边界','需求/测试/验收追溯','变更记录'):
            self.assertIn(token, freeze, token)

    def test_design_freeze_quality_gate_and_order(self):
        gates=(ROOT/'references'/'quality-gates.md').read_text(encoding='utf-8')
        self.assertIn('设计冻结', gates)
        self.assertIn('静态 `validate_docs.py` PASS 只是初检', gates)
        skill=(ROOT/'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('7.5 **设计冻结', skill)
        self.assertIn('变更记录', skill)
    def test_validate_rejects_title_mismatch(self):
        # 共享资产一个项目只有一个正式题目：validate_docs --root 必须拦截不一致题目
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            (root/'project-assets').mkdir(parents=True)
            (root/'project-assets'/'project.json').write_text(json.dumps({'schema_version':1,'project_id':'P1','name':'示例项目'},ensure_ascii=False),encoding='utf-8')
            (root/'intro.md').write_text(INTRO,encoding='utf-8')
            (root/'impl.md').write_text(IMPL,encoding='utf-8')
            cmd=[sys.executable,str(VAL),'--root',str(root),'--intro',str(root/'intro.md'),'--implementation',str(root/'impl.md'),'--title','示例项目','--report',str(root/'qa.json')]
            cp=subprocess.run(cmd,encoding='utf-8',capture_output=True)
            self.assertEqual(cp.returncode,0,cp.stdout+cp.stderr)
            cmd[cmd.index('--title')+1]='别的项目'
            cp=subprocess.run(cmd,encoding='utf-8',capture_output=True)
            self.assertEqual(cp.returncode,2)
            report=json.loads((root/'qa.json').read_text(encoding='utf-8'))
            self.assertTrue(any('题目与项目资产不一致' in e for d in report['documents'] for e in d['errors']))


if __name__=='__main__': unittest.main()
