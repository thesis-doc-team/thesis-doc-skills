#!/usr/bin/env python3
"""Read-only reverse audit of filled midterm DOCX paragraph formatting.
Do not copy project text/names, only measure role, indent, font and spacing.
"""
import argparse
import json
from collections import Counter,defaultdict
from pathlib import Path
from docx import Document

def scan(paths):
    records=[]
    for path in paths:
        doc=Document(path)
        if not doc.tables or len(doc.tables[0].rows)<5:
            raise ValueError(f'缺少中期检查表结构：{path}')
        for row,role in [(2,'完成进度'),(3,'问题与整改'),(4,'教师意见')]:
            ps=doc.tables[0].cell(row,0).paragraphs
            signature=next((i for i,p in enumerate(ps) if '指导教师签名' in p.text),len(ps))
            for p in ps[1:signature]:
                txt=p.text.strip()
                if not txt:continue
                first=p.paragraph_format.first_line_indent
                runs=[r for r in p.runs if r.text.strip()]
                font=next((r.font.name for r in runs if r.font.name),None)
                size=next((r.font.size.pt for r in runs if r.font.size),None)
                label=(txt.endswith(('方面','方面：','问题：','措施：','计划：')) and len(txt)<=18)
                records.append({'role':role,'kind':'label' if label else 'body',
                                'indent_pt':round(first.pt,2) if first is not None else None,
                                'font':font,'size_pt':size,
                                'line_spacing':p.paragraph_format.line_spacing})
    groups=defaultdict(list)
    for rec in records:groups[rec['role']+'/'+rec['kind']].append(rec)
    def group_report(rs):
        return {'paragraphs':len(rs),'indent_pt_distribution':dict(Counter(str(x['indent_pt']) for x in rs)),
                'font_distribution':dict(Counter(str(x['font']) for x in rs)),
                'size_distribution':dict(Counter(str(x['size_pt']) for x in rs)),
                'line_spacing_distribution':dict(Counter(str(x['line_spacing']) for x in rs))}
    return {'samples':len(paths),'roles':{key:group_report(x) for key,x in groups.items()},
            'policy':'只统计格式属性，不复制范本真实人物/技术事实；官方模板和学校规则优先，冲突在报告中保留，不用统计多数篡改固定栏目'}

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('samples',nargs='+')
    a.add_argument('--report')
    ar=a.parse_args()
    res=scan([Path(s) for s in ar.samples]);txt=json.dumps(res,ensure_ascii=False,indent=2)
    if ar.report:Path(ar.report).write_text(txt+'\n',encoding='utf8')
    print(txt)
