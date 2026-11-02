#!/usr/bin/env python3
"""Read-only fingerprint of official literature-review DOCX. Never modifies it."""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse, hashlib, json
from pathlib import Path
from docx import Document

def inspect(path):
    d=Document(path)
    return {'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'sections':len(d.sections), 'tables':len(d.tables),
            'rows_each_table':[len(t.rows) for t in d.tables],
            'cols_each_table':[len(t.columns) for t in d.tables],
            'paragraphs_outside_tables':len(d.paragraphs),
            'page_layouts':[{'width_emu':s.page_width,'height_emu':s.page_height,
                             'left_margin_emu':s.left_margin,'right_margin_emu':s.right_margin,
                             'top_margin_emu':s.top_margin,'bottom_margin_emu':s.bottom_margin}
                             for s in d.sections],
            'cover_labels':[p.text.split('：')[0] for p in d.paragraphs if '：' in p.text][:8],
            'instruction': d.tables[0].cell(0,0).paragraphs[0].text if d.tables else None,
            'review_label': d.tables[0].cell(1,0).paragraphs[0].text if d.tables and len(d.tables[0].rows)>1 else None}
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('template'); ap.add_argument('--json')
    a=ap.parse_args(); result=inspect(a.template)
    s=json.dumps(result,indent=2,ensure_ascii=False)
    if a.json: Path(a.json).write_text(s+'\n',encoding='utf8')
    print(s)
