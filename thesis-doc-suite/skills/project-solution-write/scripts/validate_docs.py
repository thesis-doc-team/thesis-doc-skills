#!/usr/bin/env python3
"""project-solution-write: static (not hardware) QA for two Markdown deliverables.

Return 0: PASS or WARN; 2: FAIL. Python standard library only.
The checker intentionally does not pretend to verify circuit correctness or API behavior.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path


FORBIDDEN_HEADING_PATTERNS = [
    r'工程实施交付说明', r'付费交付说明', r'收费(?:策略|建议|说明)',
    r'免费.?付费', r'销售(?:建议|策略)', r'商业转化',
    # 与 thesis-doc-suite 六件套同一“变相章节”边界：独立成章的问题/不足/改进/优化/风险/展望
    # 即使换名仍属越界（实施前提、选型依据、异常与排障是必要技术内容，不在其列）。
    r'已知问题', r'存在的问题', r'问题与(?:改进|优化|建议)', r'问题分析与改进',
    r'不足与(?:改进|优化)', r'改进建议', r'改进方向', r'优化建议', r'优化方向',
    r'风险与对策', r'风险分析', r'风险评估',
    r'未来展望', r'技术展望', r'后续规划', r'后续计划', r'升级建议', r'升级计划',
    r'技术演进', r'未来工作', r'发展规划',
    r'后续(?:优化|扩展|改进)建议', r'可增加(?:的)?功能', r'其他建议',
    r'作者(?:总结|的话)', r'AI(?: 的)?建议',
    r'如何使用(?:本|这)(?:份)?(?:文档|文件)',
]
INTRO_LEAK = [r'GPIO\s*(?:引脚|分配|映射|表)', r'CubeMX\s*(?:配置|初始化)',
              r'\b(?:PA|PB|PC)[0-9]{1,2}\s*[：:]\s*(?:GPIO|UART|USART|I2C)',
              r'(?:CRC(?:8|16|32)?|Modbus).*?(?:多项式|0x[0-9A-Fa-f]{2,})']
KEYWORD_SETS = {
    'introduction': [('项目概况', ['项目概述', '项目简介', '项目定位', '项目介绍']),
                     ('功能说明', ['功能说明', '功能介绍', '核心功能', '功能模块']),
                     ('使用或交互', ['使用流程', '交互流程', '运行流程', '使用方式', '交互方式', '体验流程'])],
    'implementation': [('设计范围', ['范围', '需求', '设计基线', '项目目标']),
                       ('架构', ['架构', '系统拓扑', '系统组成']),
                       ('实现', ['实现', '设计', '模块']),
                       ('实施步骤', ['实施步骤', '开发步骤', '实施阶段', '分阶段开发']),
                       ('验收', ['验收', '测试'])]
}


def inspect_doc(path: Path, kind: str, title: str | None) -> dict:
    res = {'path': str(path), 'kind': kind, 'checks': [], 'errors': [], 'warnings': []}
    if not path.exists():
        res['errors'].append('文件不存在')
        return res
    raw = path.read_bytes()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        res['errors'].append('文件不是有效 UTF-8')
        return res
    if len(text.strip()) < 250:
        res['errors'].append('文档内容过少，不是可独立使用的方案')
    if not re.search(r'^#\s+\S+', text, re.M):
        res['errors'].append('缺少一级标题')
    if not re.search(r'^##\s+', text, re.M):
        res['errors'].append('缺少二级章节')
    if title and title not in text:
        res['warnings'].append('正文未直接出现完整项目题目，需核对命名是否一致')
    headings = [m.group(1) for m in re.finditer(r'^\s{0,3}#{1,6}\s+(.+?)\s*$', text, re.M)]
    for h in headings:
        for p in FORBIDDEN_HEADING_PATTERNS:
            if re.search(p, h, re.I):
                res['errors'].append(f'越界章节：{h}')
                break
    if re.search(r'(?:付费版|收费版|免费版|付费文档|面向付费)', text, re.I):
        res['errors'].append('正式文档中含免费/付费/收费包装措辞')
    for label, synonyms in KEYWORD_SETS[kind]:
        if not any(s in text for s in synonyms):
            res['warnings'].append(f'未明显找到“{label}”相关内容，需检查适用性')
    if kind == 'introduction':
        # Flow diagrams are presentation content, not implementation leakage.
        # Allow text/mermaid fences; reject programming, shell and protocol examples.
        fences = re.findall(r'^```([^\n]*)\n(.*?)^```\s*$', text, re.M | re.S)
        for language, content in fences:
            lang = language.strip().lower()
            if lang not in ('', 'text', 'plain', 'mermaid'):
                res['errors'].append(f'介绍文档出现实施代码围栏：{lang}')
            elif lang in ('', 'text', 'plain') and re.search(r'(?m)^(?:\s*#include\b|\s*curl\s+|\s*\{\s*\"(?:method|params|action)\")', content):
                res['errors'].append('介绍文档的文本围栏中出现代码/协议示例')
        if text.count('```') % 2:
            res['errors'].append('Markdown 代码围栏未闭合')
        for p in INTRO_LEAK:
            if re.search(p, text, re.I | re.S):
                res['errors'].append('介绍文档出现实施层技术细节：'+p)
        if re.search(r'(?m)^\|[^\n]*(?:GPIO|USART\d|API 接口|CRC16|DMA).*?\|',text):
            res['errors'].append('介绍文档包含实施层参数表')
    res['checks'].append('UTF-8/基本结构/禁止章节/内容层级静态扫描')
    return res


def check_requirements(data: dict, intro: dict | None, impl: dict | None) -> list[dict]:
    result=[]
    requirements = data.get('requirements') or data.get('items') or []
    for i,req in enumerate(requirements):
        name = req if isinstance(req,str) else req.get('name','')
        if not name:
            continue
        status = 'confirmed' if isinstance(req,str) else req.get('status','confirmed')
        if status not in ['confirmed','assumed','unknown']:
            status='confirmed'
        row={'name':name,'status':status,'coverage':{}}
        for d in [intro,impl]:
            if not d or 'text' not in d:
                continue
            exact = name in d['text']
            row['coverage'][d['kind']] = exact
            if status=='confirmed' and not exact:
                d['warnings'].append(f'需求名称未直接出现：{name}；若采用同义表达须人工审查')
        result.append(row)
    return result



PRIORITY_LABELS = {
    'cost': '成本优先', 'performance': '性能优先',
    'function': '功能优先', 'balanced': '均衡方案',
}


def check_optimization(data: dict, intro: dict | None, impl: dict | None) -> dict | None:
    """Only static documentation checks; this does not evaluate real tradeoff quality."""
    opt = data.get('optimization')
    if opt is None:
        return None
    if not isinstance(opt, dict):
        if impl: impl['errors'].append('optimization 必须为对象')
        elif intro: intro['errors'].append('optimization 必须为对象')
        return {'error': 'invalid optimization data'}
    priority = opt.get('priority')
    if priority not in PRIORITY_LABELS:
        if impl: impl['errors'].append('optimization.priority 必须是 cost/performance/function/balanced')
        elif intro: intro['errors'].append('optimization.priority 必须是 cost/performance/function/balanced')
        return {'priority': priority, 'error': 'invalid priority'}
    label = PRIORITY_LABELS[priority]
    secondary = opt.get('secondary_priority')
    if secondary is not None and (secondary not in PRIORITY_LABELS or secondary == priority):
        target = impl or intro
        if target: target['errors'].append('optimization.secondary_priority 必须不同于主优先级，且属于四种合法方向')
    weights = opt.get('custom_weights')
    target = impl or intro
    if weights is not None:
        keys = ['cost', 'performance', 'function', 'complexity']
        if not isinstance(weights, dict) or any(k not in weights for k in keys):
            if target: target['errors'].append('自定义权重需完整提供成本/性能/功能/复杂度四项')
        elif any(not isinstance(weights[k], (int, float)) or isinstance(weights[k], bool) or weights[k] < 0 for k in keys) or abs(sum(weights[k] for k in keys)-100)>1e-6:
            if target: target['errors'].append('自定义权重必须是非负数字且合计为100')
    if impl and 'text' in impl:
        content = impl['text']
        if label not in content:
            impl['errors'].append(f'工程实施方案未明确体现已选目标“{label}”')
        if not re.search(r'方案权衡|候选方案|技术路线对比|方案对比|选型对照', content):
            impl['errors'].append('工程实施方案缺少候选路线比较和选型权衡')
        if not all(word in content for word in ('成本', '性能', '功能')):
            impl['warnings'].append('方案对比尚未明确覆盖成本、性能和已确认功能三维，请人工核实')
        if not re.search(r'最终选择|选定方案|选型结论|推荐采用|选择方案|确定采用', content):
            impl['warnings'].append('未明显发现最终路线选择与取舍结论，请人工核实')
        # These are static heuristics; a reviewer must still judge whether choices are real.
        if not re.search(r'(?:方案\s*[ABC123][：:]|候选\s*[ABC123][：:]|方案\s*[ABC123].{0,24}(?:采用|主控|软件|通信|接口)|唯一可行|同解)', content):
            impl['warnings'].append('候选方案缺少可识别的具体路线差异；请人工检查是否仅给出空泛标签')
        if not re.search(r'取舍代价|舍弃|放弃|未选(?:择)?原因|不选(?:择)?|主要取舍|代价|权衡得失|同解', content):
            impl['warnings'].append('未明确说明选定路线舍弃的优点或代价，需审查实际权衡')
        if not re.search(r'影响实施|实施变化|决策影响|方案落地|选型影响|对.{0,20}(?:模块|协议|资源|性能|验收)的影响|同解', content):
            impl['warnings'].append('未明确追踪偏好对硬件/软件/协议/验收的实际影响')
    if intro and 'text' in intro:
        if re.search(r'成本优先|性能优先|功能优先|均衡方案|方案权衡|选型评分', intro['text']):
            intro['warnings'].append('介绍文档出现设计权衡/优先级内部用语，需检查是否越界')
    return {'priority': priority, 'secondary_priority': secondary, 'label': label, 'status': opt.get('status', 'unknown'), 'static_only': True}

def main(argv=None):
    ap=argparse.ArgumentParser(description='Check MD project introduction and implementation plan bounds')
    ap.add_argument('--intro',type=Path)
    ap.add_argument('--implementation',type=Path)
    ap.add_argument('--title')
    ap.add_argument('--requirements',type=Path,help='Optional JSON with requirements array')
    ap.add_argument('--root',type=Path,help='项目根目录（可选）：校验 --title 与 project-assets/project.json 的 name 一致')
    ap.add_argument('--report',type=Path)
    args=ap.parse_args(argv)
    if args.intro is None and args.implementation is None:
        ap.error('Provide --intro and/or --implementation')
    docs=[]
    for kind,path in [('introduction',args.intro),('implementation',args.implementation)]:
        if path is None: continue
        result=inspect_doc(path,kind,args.title)
        if path.is_file():
            try: result['text']=path.read_text(encoding='utf-8-sig')
            except UnicodeError: pass
        docs.append(result)
    if args.root and args.title:
        import unicodedata
        project_file=Path(args.root)/'project-assets'/'project.json'
        if project_file.is_file():
            project=json.loads(project_file.read_text(encoding='utf-8'))
            project_name=project.get('name') or (project.get('metadata') or {}).get('title')
            def _norm_title(value):
                return re.sub(r'\s+','',unicodedata.normalize('NFKC',str(value or '')))
            if project_name and _norm_title(args.title)!=_norm_title(project_name):
                message=('题目与项目资产不一致：「'+str(args.title)+'」≠「'+str(project_name)
                         +'」；共享资产一个项目只有一个正式题目，确需变更时先更新 project.json 的 name 并留审计')
                for d in docs:
                    d['errors'].append(message)
    pairs=[]
    optimization_check=None
    if args.requirements:
        try:
            data=json.loads(args.requirements.read_text(encoding='utf-8'))
            pairs=check_requirements(data, *[next((d for d in docs if d['kind']==k),None) for k in ['introduction','implementation']])
            optimization_check=check_optimization(data, *[next((d for d in docs if d['kind']==k),None) for k in ['introduction','implementation']])
        except (OSError,ValueError,TypeError) as e:
            if docs: docs[0]['errors'].append(f'无法读取需求 JSON：{e}')
    intro=next((d for d in docs if d['kind']=='introduction'),None)
    impl=next((d for d in docs if d['kind']=='implementation'),None)
    if intro and impl:
        for d in docs:
            if 'text' not in d: continue
            # Only flag title mismatches when separately supplied full project title exists in one but not other.
            pass
    for d in docs: d.pop('text',None)
    errors=sum(len(d['errors']) for d in docs)
    warnings=sum(len(d['warnings']) for d in docs)
    status='FAIL' if errors else ('WARN' if warnings else 'PASS')
    report={'status':status, 'scope':'仅文档静态质量；不是硬件或软件运行验证',
            'documents':docs,'requirement_coverage':pairs, 'optimization_check':optimization_check, 'summary':{'errors':errors,'warnings':warnings}}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'errors':errors,'warnings':warnings},ensure_ascii=False))
    for d in docs:
        for e in d['errors']: print('ERROR:',d['kind'],e)
        for w in d['warnings']: print('WARN:',d['kind'],w)
    return 2 if errors else 0


if __name__=='__main__': sys.exit(main())
