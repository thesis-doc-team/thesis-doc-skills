#!/usr/bin/env python3
"""Optional PDF preflight: find signatures/teacher opinion split across pages.

Requires PyMuPDF. This is only a helper; all pages still need human visual QA.
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse
import json
import re
import sys
from pathlib import Path

def run(path):
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError('未安装 PyMuPDF，无法做自动分页预警；必须人工逐页检查。') from exc
    document=fitz.open(path)
    markers={'学生签名':[], '指导教师审阅意见':[], '指导教师签名':[]}
    titles=[]
    texts=[]
    for i,page in enumerate(document):
        s=page.get_text(sort=True)
        texts.append(s)
        for key in markers:
            if key in s: markers[key].append(i+1)
        for line in s.splitlines():
            line=line.strip()
            if re.match(r'^[1-7]\s*[^0-9\s]',line):
                titles.append({'page':i+1,'heading':line[:70]})
    warnings=[]
    if (markers['指导教师审阅意见'] and markers['指导教师签名']
            and markers['指导教师审阅意见'][-1] != markers['指导教师签名'][-1]):
        warnings.append('教师审阅意见与教师签字出现在不同页面：签名可能孤立，必须检查并调整正文分页。')
    if texts:
        last=texts[-1].strip()
        # Low-ink final page often signals a detached signature block.
        if '指导教师签名' in last and len(re.sub(r'\s','',last))<50:
            warnings.append('末页基本只有教师签名与日期：属于孤立签字页，不能直接交付。')
    if not all(markers[k] for k in markers):
        warnings.append('有签名/意见锚点没有出现在 PDF 文本中；需目视检查是否被字体或分页影响。')
    return {'pages':len(document),'markers':markers,'titles':titles,
            'warnings':warnings,'status':'WARN' if warnings else 'PRECHECK_OK',
            'note':'该工具不检查字体替代、裁切、表格边框；仍需人工逐页目视。'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pdf',type=Path)
    p.add_argument('--output-report',type=Path)
    args=p.parse_args()
    try:
        result=run(args.pdf)
        if args.output_report:args.output_report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        sys.exit(1 if result['status']=='WARN' else 0)
    except Exception as exc:
        print('WARN: '+str(exc),file=sys.stderr);sys.exit(2)
if __name__=='__main__':main()
