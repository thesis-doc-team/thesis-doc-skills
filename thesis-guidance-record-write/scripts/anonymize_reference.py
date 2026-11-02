#!/usr/bin/env python3
"""Offline import helper. Explicit identifiers become generic strings, metadata is scrubbed.
Source sample is used only for style study, never as a factual source for another project.
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import re,sys
from pathlib import Path
from docx import Document

def clean_text(s):
    pairs=[
        (r'夏\s*骏\s*豪','某同学'),(r'崔\s*帅\s*杰','某同学'),(r'陈\s*军','某教师'),
        (r'504122\d{4}','XXXXXXXXXX'),(r'信息楼\s*[A-Z]?\s*\d+','校内实验室'),
        (r'物联网工程\s*2021\s*级\s*1\s*班','某专业某年级某班'),
        (r'物联网工程\s*2021\s*级','某专业某年级'),
        (r'信息工程学院','某学院'),(r'物联网工程','某专业'),
        (r'基于\s*4G\s*通信驱动的多功能井盖设计与实现','某智能监测终端设计与实现'),
        (r'井盖','监测设备'),
        (r'基于\s*4G\s*通信驱动的多功能监测设备设计','某智能监测终端设计'),
        (r'20\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日','20XX年X月X日'),
        (r'2021\s*级','某年级'),
    ]
    for a,b in pairs:s=re.sub(a,b,s)
    return s

def all_paras(doc):
    seen=set()
    for p in doc.paragraphs:
        if p._p not in seen:yield p;seen.add(p._p)
    for tbl in doc.tables:
        for r in tbl.rows:
            for tc in r._tr.tc_lst:
                from docx.table import _Cell
                for p in _Cell(tc,tbl).paragraphs:
                    if p._p not in seen:yield p;seen.add(p._p)

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: anonymize_reference.py original.docx anonymized.docx')
    src=Path(sys.argv[1]);dst=Path(sys.argv[2]);d=Document(src)
    for p in all_paras(d):
        old=p.text;new=clean_text(old)
        if old!=new:
            if p.runs:
                p.runs[0].text=new
                for x in p.runs[1:]: x.text=''
            else:p.add_run(new)
    cp=d.core_properties
    cp.author='';cp.last_modified_by='';cp.keywords='';cp.comments='';cp.category='';cp.identifier=''
    cp.title='去标识化指导记录参考样本（写作/段落示例，非官方模板）'
    cp.subject='人物、学号、日期、地点、题目已模糊化；不得移用技术事实和教师评价'
    dst.parent.mkdir(parents=True,exist_ok=True)
    d.save(dst)
    print('CREATED:',dst)
