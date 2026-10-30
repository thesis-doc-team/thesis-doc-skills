#!/usr/bin/env python3
import argparse,json,statistics
from collections import Counter
from pathlib import Path
from docx import Document
p=argparse.ArgumentParser();p.add_argument('files',nargs='+');p.add_argument('--report');a=p.parse_args()
result=[]
for f in a.files:
 d=Document(f);counts=Counter();sizes=Counter();indents=Counter();paragraphs=0
 for table in d.tables[1:]:
  for row in table.rows:
   for cell in row._tr.tc_lst:
    from docx.table import _Cell
    c=_Cell(cell,table)
    for para in c.paragraphs:
     if not para.text.strip():continue
     paragraphs+=1
     if para.paragraph_format.first_line_indent is not None:
      indents[round(para.paragraph_format.first_line_indent.pt,1)]+=1
     for run in para.runs:
      if run.text.strip():
       counts[run.font.name or '(inherited)']+=1
       sizes[run.font.size.pt if run.font.size else '(inherited)']+=1
 result.append({'name':Path(f).name,'record_blocks_13rows':len(d.tables[1].rows)//13 if len(d.tables)>1 else None,
                'paragraphs':paragraphs,'fonts':counts.most_common(8),'font_sizes':sizes.most_common(8),
                'first_line_indents_pt':indents.most_common(8)})
print(json.dumps(result,ensure_ascii=False,indent=2,default=str))
if a.report:Path(a.report).write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
