#!/usr/bin/env python3
"""Read-only template inspection; emits JSON outside official DOCX."""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse
from pathlib import Path
import json
from template_tools import DEFAULT_TEMPLATE, lock_check, sha256, unique_cells

def inspect(template):
    d,lock=lock_check(template)
    s=d.sections[0]
    t=d.tables[0]
    data={'template_sha256':sha256(template),'size_cm':[round(s.page_width.cm,3),round(s.page_height.cm,3)],
          'margins_cm':{x:round(getattr(s,x).cm,3) for x in ('top_margin','bottom_margin','left_margin','right_margin')},
          'tables':len(d.tables),'table_grid_columns':len(t.columns),'rows':len(t.rows),
          'document_paragraphs':[p.text for p in d.paragraphs],
          'cells':[],'template_lock':lock['sha256']}
    for i,row in enumerate(t.rows):
        data['cells'].append({'row':i,'unique_cells':[{'text_head':c.text[:85],
                      'paragraphs':len(c.paragraphs), 'blank_paragraphs':sum(not p.text.strip() for p in c.paragraphs)} for c in unique_cells(row)]})
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('template',nargs='?',default=str(DEFAULT_TEMPLATE))
    p.add_argument('--json',dest='outfile')
    a=p.parse_args()
    try:
        data=inspect(a.template)
        output=json.dumps(data,ensure_ascii=False,indent=2)
        if a.outfile:
            Path(a.outfile).write_text(output+'\n',encoding='utf-8')
        else:print(output)
    except (ValueError,OSError) as e:
        p.exit(2,f'ERROR: {e}\n')
