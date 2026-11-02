#!/usr/bin/env python3
"""Read-only DOCX sample style statistics. Samples never become official templates."""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from docx import Document


def stat(files):
    data={}
    for path in files:
        d=Document(path)
        paragraphs=[p for t in d.tables for row in t.rows[:1] for c in row.cells[:1] for p in c.paragraphs]
        groups={x:[] for x in ('heading1','heading2','body','reference')}
        for p in paragraphs:
            tx=p.text.strip()
            if not tx: continue
            k=('reference' if re.match(r'^\[\d+\]',tx) else
                'heading2' if re.match(r'^\d+\.\d+\s',tx) else
                'heading1' if re.match(r'^[1-7]\s+[^\d]',tx) else 'body')
            pf=p.paragraph_format
            ind='unspecified' if pf.first_line_indent is None else f'{pf.first_line_indent.pt:.1f}pt'
            ls='unspecified' if pf.line_spacing is None else str(pf.line_spacing)
            groups[k].append((ind,ls,len(tx)))
        data[path.name]={k:{'count':len(v),'first_line_indent':dict(Counter(x[0] for x in v)),
                            'line_spacing':dict(Counter(x[1] for x in v)),
                            'mean_character_count':round(sum(x[2] for x in v)/len(v),1) if v else 0}
                         for k,v in groups.items()}
    return {'disclaimer':'仅记录已填样本的观测值，不覆盖官方空白模板及写作规范；不认定样本中事实为真实。','samples':data}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('files',nargs='+',type=Path)
    p.add_argument('--report',type=Path)
    a=p.parse_args()
    r=stat(a.files)
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False,indent=2))
