#!/usr/bin/env python3
"""Make a literature-review rendering plan from the *same* project-assets registry as taskbook.

Draft input (JSON): {project_id,title,title_lines?,cover?,sections:[{heading,
 paragraphs:[string | {text}]}],teacher_opinion,selected_reference_ids?}.
Cite by [[REF:REF-001]] within narrative text; this tool maps to consecutive
numbers in FIRST-APPEARANCE order. It never invents a citation.
"""
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
    if not title or not isinstance(sections, list) or len(sections) < 3:
        raise ValueError('须给出真实题目和 sections（引言、研究现状、评述）')
    if len(re.sub(r'\s+', '', opinion)) < 50:
        raise ValueError('指导教师评语拟稿须不少于 50 字')
    all_ids, seen = [], set()
    structured = []
    narrative_chars = 0
    for sec in sections:
        heading = (sec.get('heading') or '').strip()
        if not heading or not isinstance(sec.get('paragraphs'), list):
            raise ValueError('每个章节必须有标题和 paragraphs 数组')
        blocks = []
        for block in sec['paragraphs']:
            value = block if isinstance(block, str) else block.get('text', '')
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'空的正文段落: {heading}')
            if '[[' in REF_TOKEN.sub('', value) or ']]' in REF_TOKEN.sub('', value):
                raise ValueError('发现不合法或未闭合的参考文献标记，必须使用 [[REF:REF-001]]')
            for rid in REF_TOKEN.findall(value):
                if rid not in refs or refs[rid].get('verified') is not True or not refs[rid].get('checked_at'):
                    raise ValueError(f'{rid} 未存在/未核验，不能进入正式文书')
                if rid not in seen:
                    seen.add(rid); all_ids.append(rid)
            narrative_chars += len(re.sub(r'\s+', '', REF_TOKEN.sub('', value)))
            blocks.append(value)
        structured.append({'heading': heading, 'paragraphs': blocks, 'page_break_before': bool(sec.get('page_break_before', False))})
    if narrative_chars < 2500:
        raise ValueError(f'综述正文仅 {narrative_chars} 字符，低于官方 2500 字硬门槛')
    selected = draft.get('selected_reference_ids')
    if selected is not None and set(selected) != set(all_ids):
        raise ValueError('selected_reference_ids 与正文实际引用集合不匹配')
    if len(all_ids) < 8:
        raise ValueError('论文来源不足 8 篇；该门槛是本 Skill 审慎默认值，可根据学校明确要求修改规则，不能凑假文献')
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
             'paragraphs': [localize(p) for p in s['paragraphs']], 'page_break_before': s['page_break_before']} for s in structured],
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
