#!/usr/bin/env python3
"""Make a literature-review rendering plan from the *same* project-assets registry as taskbook.

Draft input (JSON): {project_id,title,title_lines?,cover?,sections:[{heading,
 paragraphs:[string | {text}]}],teacher_opinion,selected_reference_ids?}.
Cite by [[REF:REF-001]] within narrative text; this tool maps to consecutive
numbers in FIRST-APPEARANCE order. It never invents a citation.
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse, json, re
from pathlib import Path

REF_TOKEN = re.compile(r'\[\[REF:(REF-[A-Za-z0-9_-]+)\]\]')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def compose(root, draft):
    root = Path(root).resolve()
    base = root / 'project-assets'
    project = read_json(base / 'project.json')
    registry = read_json(base / 'references.json')
    if project.get('schema_version') != 1 or registry.get('schema_version') != 1:
        raise ValueError('仅支持任务书共享资产契约 schema_version=1')
    pid = project.get('project_id')
    if registry.get('project_id') != pid or draft.get('project_id', pid) != pid:
        raise ValueError('项目 ID 不匹配，严禁串项目合并')
    refs = {r['id']: r for r in registry.get('items', [])}
    title = draft.get('title', '').strip()
    sections = draft.get('sections')
    opinion = draft.get('teacher_opinion', '').strip()
    if not title or not isinstance(sections, list) or len(sections) != 3:
        raise ValueError('正式正文固定三个主章（引言、研究现状、评述），参考文献为第四章。二级标题用 kind=subheading')
    for i, sec in enumerate(sections,1):
        if not re.match(r'^'+str(i)+r'\s+', (sec.get('heading') or '')):
            raise ValueError(f'主章标题须按 1/2/3 连续编号：第{i}章')
    if len(re.sub(r'\s+', '', opinion)) < 50:
        raise ValueError('指导教师评语拟稿须不少于 50 字（本端去空白含标点计数；校验端只算汉字/字母/数字，按最严口径留余量）')
    if any(h in opinion for h in ('本栏为拟稿','供教师审定拟稿','供指导教师审定','审定为准')) or re.search(r'审定.{0,2}为准',opinion):
        raise ValueError('指导教师评语禁止拟稿提示语/元话语尾巴（本栏为拟稿/供教师审定拟稿/供指导教师审定/审定为准，覆盖以教师最终审定为准、最终评价以指导教师审定为准等变体，含“审定结果为准”等插字变体）：正文以实质收束句（如"建议按计划进入毕业设计下一阶段工作。"）自然结束')
    all_ids, seen = [], set()
    structured = []
    narrative_chars = 0
    for sec in sections:
        heading = (sec.get('heading') or '').strip()
        if not heading or not isinstance(sec.get('paragraphs'), list):
            raise ValueError('每个章节必须有标题和 paragraphs 数组')
        blocks = []
        for block in sec['paragraphs']:
            if not isinstance(block, (str,dict)):
                raise ValueError('paragraphs 仅支持字符串或 {text,kind} 对象')
            kind='paragraph' if isinstance(block,str) else block.get('kind','paragraph')
            if kind not in ('paragraph','subheading'):
                raise ValueError('段落 kind 仅支持 paragraph/subheading')
            value = block if isinstance(block, str) else block.get('text', '')
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'空的正文段落: {heading}')
            if re.search(r'\[\d+(?:[,，\-–]\d+)*\]', REF_TOKEN.sub('', value)):
                raise ValueError('草稿中的方括号数字已被拦截：若是文内引用编号（如 [1]、[1,2]、[1-3]）必须改用 [[REF:REF-xxx]] 避免编号漂移；若确非引用（如归一化区间 [0,1]、样本编号），改用（0,1）等圆括号或去掉方括号，避免被误判为手填引用')
            if '[[' in REF_TOKEN.sub('', value) or ']]' in REF_TOKEN.sub('', value):
                raise ValueError('发现不合法或未闭合的参考文献标记，必须使用 [[REF:REF-001]]')
            for rid in REF_TOKEN.findall(value):
                if rid not in refs or refs[rid].get('verified') is not True or not refs[rid].get('checked_at'):
                    raise ValueError(f'{rid} 未存在/未核验，不能进入正式文书')
                if rid not in seen:
                    seen.add(rid); all_ids.append(rid)
            narrative_chars += len(re.sub(r'\s+', '', REF_TOKEN.sub('', value)))
            blocks.append({'text':value,'kind':kind} if kind=='subheading' else value)
        structured.append({'heading': heading, 'paragraphs': blocks, 'page_break_before': bool(sec.get('page_break_before', False))})
    if narrative_chars < 2500:
        raise ValueError(f'综述正文仅 {narrative_chars} 字符，低于官方 2500 字硬门槛')
    selected = draft.get('selected_reference_ids')
    if selected is not None and set(selected) != set(all_ids):
        raise ValueError('selected_reference_ids 与正文实际引用集合不匹配')
    if len(all_ids) < 8:
        raise ValueError('正式参考文献不足 8 篇；默认质量门槛，不得用虚构材料补足')
    number = {rid: i+1 for i, rid in enumerate(all_ids)}
    def localize(text):
        return REF_TOKEN.sub(lambda m: f'[{number[m.group(1)]}]', text)
    # bibliography ONLY from verified canonical registry, not model-generated HTML snippets
    bibliography = [{'number': number[rid], 'id': rid,
                     'citation': re.sub(r'^\s*\[\d+\]\s*', '', refs[rid]['citation']).strip(),
                     'source_url': refs[rid]['source_url']}
                    for rid in all_ids]
    info = dict(project.get('metadata') or {})
    info.update(draft.get('cover') or {})
    cover_whitelist = ['student_name','student_id','college','major','class_name','instructor_name','instructor_title']
    cover = {key: str(info.get(key) or '') for key in cover_whitelist}
    return {'project_id': pid, 'title': title, 'title_lines': draft.get('title_lines'),
            'cover': cover, 'sections': [{'heading': s['heading'],
             'paragraphs': [localize(p) if isinstance(p,str) else {'text':localize(p['text']),'kind':p['kind']} for p in s['paragraphs']], 'page_break_before': s['page_break_before']} for s in structured],
            'teacher_opinion': opinion, 'bibliography': bibliography,
            'selected_reference_ids': all_ids, 'narrative_chars': narrative_chars}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True); p.add_argument('--draft', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    result = compose(a.root, read_json(a.draft))
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f'READY: {a.out}; refs={len(result["bibliography"])}; chars={result["narrative_chars"]}')

if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, KeyError) as e: raise SystemExit('ERROR: '+str(e))
