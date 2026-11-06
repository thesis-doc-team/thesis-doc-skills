#!/usr/bin/env python3
"""Read-only visual coverage evidence planner (stdlib-only, never changes source).

It discovers *potential* prose/ASCII areas but does not invent module models,
classify pictures as real, approve facts, or produce new project diagrams.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from visual_assets import context, technical_md, digest, FENCE_RE, category_hint

CANDIDATE= re.compile(r'(?i)系统架构|系统框架|总体架构|功能架构|功能树|功能模块|控制流程|执行流程|数据流程|启动流程|架构图|流程图|分层架构|\barchitecture\b|\bworkflow\b')
TREE = re.compile(r'[├└]──|\|--')
ARROWS = re.compile(r'--> |\s→\s|\s->\s|\s⇒\s|\s=>\s')


def draft_windows(md):
    """Provide conservative ranges; must be read/adjusted before ASCII conversion."""
    rows = md.splitlines()
    windows=[];active=None
    for i, line in enumerate(rows,1):
        is_ascii=bool(TREE.search(line) or ARROWS.search(line))
        if is_ascii:
            if active is None: active=[i,i]
            elif i-active[1]<=2:active[1]=i
            else:windows.append(active);active=[i,i]
        elif active is not None and i-active[1]>2:
            windows.append(active);active=None
    if active:windows.append(active)
    output=[]
    for a,b in windows[:25]:
        if b-a+1 > 55:continue
        start=max(1,a-3);end=min(len(rows),b+2)
        prefix='\n'.join(rows[max(0,a-6):a])
        cat=category_hint(prefix) or 'unclassified'
        output.append({'suggested_start_line':start,'suggested_end_line':end,
            'evidence_lines':[a,b],'category_hint':cat,
            'preview':' | '.join(rows[a-1:min(b,a+2)])[:210],
            'status':'NEEDS_MANUAL_BOUNDARY_AND_FACT_REVIEW',
            'notice':'可能包含标题/代码栏，运行 draft-from-ascii 前应缩小到精确的根节点和连线范围'})
    return output


def make_plan(root,md, facts):
    text=md.read_text('utf-8-sig')
    headings=[]
    for no,line in enumerate(text.splitlines(),1):
        if re.match(r'^#{1,5} ',line) and CANDIDATE.search(line):
            headings.append({'line':no,'heading':line.lstrip('#').strip(),
                'category_hint':category_hint(line) or 'context-only'})
    mermaid=[]
    for m in FENCE_RE.finditer(text):
        context=text[max(0,m.start()-200):m.start()]
        mermaid.append({'line':text.count('\n',0,m.start())+1,
            'category_hint':category_hint(context) or 'unclassified',
            'editable_source_sha256':digest(m.group(1).strip().encode('utf-8')),
            'status':'CANDIDATE_NOT_APPROVED'})
    usable_facts=[{'id':k,'statement':str(v.get('statement',''))[:200],
        'status':v.get('status'),'source':v.get('source')}
        for k,v in facts.items() if v.get('status') in ('implemented','declared','proposed')]
    return {'status':'PLAN_ONLY','project_root':str(root),
        'technical_md':str(md), 'technical_md_sha256':digest(md.read_bytes()),
        'facts_available':usable_facts,'diagram_headings':headings[:50],
        'mermaid_candidates':mermaid,'ascii_candidates':draft_windows(text),
        'mandatory_categories':['system-framework','functional-architecture','flowchart','module-photo'],
        'requires_manual_scope':'模块实物图目标必须由Agent依据技术MD与FACT逐项确定，并明确整体对象层级',
        'downloaded':0,'installed_packages':0,
        'caution':'本命令只发现文本位置、图候选和已登记 FACT；不自动从标题猜节点/模块，也不代表已完成四类图'}


def main():
    ap=argparse.ArgumentParser(description='只读技术图需求盘点。无需网络、无需安装依赖')
    ap.add_argument('--root',required=True)
    ap.add_argument('--technical-md',required=True)
    ap.add_argument('--project-id')
    ap.add_argument('--output-json',help='可选：将报告保存到用户指定的项目运行区内')
    a=ap.parse_args()
    try:
        root,_,_,_,facts=context(a.root,a.project_id)
        md=technical_md(root,a.technical_md)
        data=make_plan(root,md,facts)
        if a.output_json:
            path=Path(a.output_json).expanduser().resolve()
            run=(root/'.skill-tmp'/'technical-visual-assets').resolve()
            if not path.is_relative_to(run) or not path.parent.is_dir():
                raise ValueError('报告只可写入当前项目的 technical-visual-assets 运行目录')
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')
        print(json.dumps(data,ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:
        print(json.dumps({'status':'BLOCK','error':str(e)},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
