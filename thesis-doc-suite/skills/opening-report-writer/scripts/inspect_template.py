#!/usr/bin/env python3
"""Read-only inspect of the embedded official DOCX template (never rewrite it)."""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile
from lxml import etree

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'assets'/'official-opening-report-template.docx'
EXPECTED=(ROOT/'assets'/'template.sha256').read_text(encoding='utf8').strip()
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
sha=hashlib.sha256(SRC.read_bytes()).hexdigest()
with ZipFile(SRC) as z:
    root=etree.fromstring(z.read('word/document.xml'))
    sections=root.xpath('./w:body/w:sectPr',namespaces=N)
    tables=root.xpath('./w:body/w:tbl',namespaces=N)
    table=tables[0]
    rows=table.xpath('./w:tr',namespaces=N)
    paragraph_count=[len(x.xpath('./w:tc/w:p',namespaces=N)) for x in rows]
    props=sections[0]
    pg=props.xpath('./w:pgSz',namespaces=N)[0]
    margins=props.xpath('./w:pgMar',namespaces=N)[0]
    get=lambda element,key: element.get('{'+N['w']+'}'+key)
    fixed=[''.join(p.xpath('.//w:t/text()',namespaces=N)) for p in root.xpath('./w:body/w:p',namespaces=N)]
    info={
        'sha256':sha,'sha256_matches_user_official_asset':sha==EXPECTED,
        'page_size_twips':{'width':get(pg,'w'),'height':get(pg,'h')},
        'margins_twips':{k:get(margins,k) for k in ('top','bottom','left','right')},
        'section_count':len(sections),'table_count':len(tables),
        'table_rows':len(rows),'table_columns':len(rows[0].xpath('./w:tc',namespaces=N)),
        'cell_paragraph_counts':paragraph_count,
        'frontmatter_static_text':[t.strip() for t in fixed if t.strip()],
        'student_signature_present':bool(root.xpath('.//w:t[contains(text(),"学生签名")]',namespaces=N)),
        'teacher_opinion_present':bool(root.xpath('.//w:t[contains(text(),"指导教师审阅意见")]',namespaces=N))
    }
print(json.dumps(info,ensure_ascii=False,indent=2))
if sha!=EXPECTED:raise SystemExit(1)
