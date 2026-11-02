#!/usr/bin/env python3
"""Read-only measurements of de-identified review samples. Measures style, never imports sample claims."""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
from pathlib import Path
from collections import defaultdict,Counter
from docx import Document
import json,argparse,re

ROOT=Path(__file__).resolve().parent.parent
SAMPLES=ROOT/'assets/reference-samples'

def label_role(text):
    s=text.strip()
    if re.match(r'^1\s*(引言|研究背景)',s):return 'main-heading'
    if re.match(r'^2\s*国内外',s):return 'main-heading'
    if re.match(r'^3\s*(评述|设计)',s):return 'main-heading'
    if re.match(r'^4\s*参考文献',s) or s.startswith('参考文献'):return 'bibliography-heading'
    if re.match(r'^\[\s*\d+\s*\]',s):return 'bibliography-entry'
    if s.startswith('指导教师审阅意见'):return 'teacher-label'
    if s.startswith('该生'):return 'teacher-opinion'
    return 'body'

def audit(paths):
    result={'samples':[],'role_summary':{},'caveat':'统计仅是描述，不能覆盖学校官方模板；错误引用、文本事实与个人信息一律不得复用'}
    groups=defaultdict(list)
    for source in paths:
        d=Document(source)
        sample={'file':Path(source).name,'sections':len(d.sections),'tables':len(d.tables), 'section_headings':[]}
        blocks=[p for table in d.tables for row in table.rows for cell in row.cells for p in cell.paragraphs]
        for p in blocks:
            if not p.text.strip():continue
            role=label_role(p.text)
            first=p.paragraph_format.first_line_indent
            line=p.paragraph_format.line_spacing
            r=next((r for r in p.runs if r.text.strip()),None)
            rec={'indent_pt':round(first.pt,1) if first else None,'line_spacing':str(line),
                 'size_pt':round(r.font.size.pt,1) if r and r.font.size else None,
                 'western_font':r.font.name if r else None}
            groups[role].append(rec)
            if role=='main-heading':sample['section_headings'].append(p.text.strip()[:50])
        result['samples'].append(sample)
    for role,records in groups.items():
        result['role_summary'][role]={'paragraphs':len(records),'indent_pt':dict(Counter(str(r['indent_pt']) for r in records)),
           'line_spacing':dict(Counter(str(r['line_spacing']) for r in records)),
           'size_pt':dict(Counter(str(r['size_pt']) for r in records)),
           'western_font':dict(Counter(str(r['western_font']) for r in records))}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('files',nargs='*');p.add_argument('--report')
    a=p.parse_args();paths=a.files or sorted(SAMPLES.glob('sample-*.docx'))
    v=audit(paths);s=json.dumps(v,ensure_ascii=False,indent=2)
    if a.report:Path(a.report).write_text(s+'\n',encoding='utf8')
    print(s)
