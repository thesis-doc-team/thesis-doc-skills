#!/usr/bin/env python3
"""Read-only empirical style audit of anonymized taskbook examples; not a template mutator."""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
from docx import Document

def audit(paths):
    records=[];samples=[]
    for path in paths:
        d=Document(path)
        if len(d.tables)!=1 or len(d.tables[0].rows)!=9:raise ValueError(f'范本结构不是 9 行主表: {path}')
        t=d.tables[0];refs=0;schedule=0
        for row,role in ((5,'内容'),(6,'进度'),(7,'下达人意见')):
            started=False
            for p in t.cell(row,0).paragraphs[1:]:
                text=p.text.strip()
                if not text:continue
                if role=='进度' and '主要参考文献' in text:break
                if role=='下达人意见' and '签名' in text:break
                if role=='进度' and re.match(r'第\s*\d+',text):schedule+=1
                if role=='进度' and not re.match(r'第\s*\d+',text):continue
                f=p.paragraph_format.first_line_indent
                runs=[r for r in p.runs if r.text.strip()]
                records.append({'sample':path.name,'role':role,'first_line_indent_pt':round(f.pt,2) if f is not None else None,
                                'line_spacing':p.paragraph_format.line_spacing,
                                'size_pt':next((r.font.size.pt for r in runs if r.font.size is not None),None),
                                'font':next((r.font.name for r in runs if r.font.name),None)})
        in_refs=False
        for p in t.cell(6,0).paragraphs:
            if '主要参考文献' in p.text:in_refs=True;continue
            if in_refs and p.text.strip():refs+=1
        samples.append({'file':path.name,'content_paragraphs':len([p for p in t.cell(5,0).paragraphs[1:] if p.text.strip()]),
                        'schedule_paragraphs':schedule,'reference_entries':refs,
                        'issuer_opinion_present':any(p.text.strip() and '签名' not in p.text and '年' not in p.text for p in t.cell(7,0).paragraphs[1:])})
    grouped=defaultdict(list)
    for r in records:grouped[r['role']].append(r)
    summary={}
    for k,rs in grouped.items():
        summary[k]={'count':len(rs),**{name:dict(Counter(str(row[field]) for row in rs)) for name,field in [('indent_pt','first_line_indent_pt'),('line_spacing','line_spacing'),('size_pt','size_pt'),('font','font')]}}
    return {'sample_count':len(samples),'samples':samples,'roles':summary,
            'decision_rule':'仅统计匿名范本，官方模板的固定边框、字体要求优先；差异不按简单平均改变原模板；样本引用均为无效示意，不得作为真实文献。'}

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('samples',nargs='+',type=Path);a.add_argument('--report',type=Path)
    args=a.parse_args()
    d=audit(args.samples)
    s=json.dumps(d,ensure_ascii=False,indent=2)
    if args.report:args.report.write_text(s+'\n',encoding='utf8')
    print(s)
