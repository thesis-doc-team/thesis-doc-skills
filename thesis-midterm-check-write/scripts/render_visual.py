#!/usr/bin/env python3
"""Render each page and run automatic *prechecks* before human/Agent visual QA.

PDF/PNG remain in the owned .skill-tmp run directory. Do not confuse automatic
prechecks with visually inspected PASS results.
Requires LibreOffice and PyMuPDF (`fitz`) available in the execution environment.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import fitz

FIXED=['塔里木大学毕业论文（设计）中期检查记录表','附件6','指导教师签名',
       '负责人签名（盖章）','学院意见','完成进度','存在的问题及整改措施','指导教师意见',
       '毕业论文（设计）题','学生姓名','班级','年','月','日']

def page_substantive_chars(raw):
    for s in FIXED:raw=raw.replace(s,'')
    raw=re.sub(r'（[^）]*不少于200字[^）]*）','',raw)
    return len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',raw))

def render_and_precheck(source,output_dir,max_pages=3):
    source=Path(source).resolve();out=Path(output_dir).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    out.mkdir(parents=True,exist_ok=True)
    profile=out/'_libreoffice_profile'
    # Isolated office instance; keeps user UI/config untouched.
    command=['soffice',f'-env:UserInstallation={profile.as_uri()}',
             '--headless','--convert-to','pdf','--outdir',str(out),str(source)]
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=120)
    pdf=out/(source.stem+'.pdf')
    if result.returncode!=0 or not pdf.exists():
        raise RuntimeError(f'无法渲染文档：{result.stdout} {result.stderr}')
    doc=fitz.open(pdf)
    pages=[]
    for index,p in enumerate(doc):
        png=out/f'page-{index+1}.png'
        p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(png)
        text=p.get_text()
        pages.append({'page':index+1,'png':str(png),'chars':len(text),
                      'substantive_chars':page_substantive_chars(text),
                      'visually_inspected':False})
    problems=[]
    if doc.page_count>max_pages:
        problems.append(f'超出官方空白模板的 {max_pages} 页基准：实际 {doc.page_count} 页。应先精简重复内容，不可动学校字号/页边距/行距。')
    if doc.page_count and pages[-1]['substantive_chars']<50:
        problems.append('最后一页几乎没有有效正文，疑似孤立签名/学院意见落款页。')
    if doc.page_count==0:problems.append('PDF页数为0')
    report={'auto_precheck_passed':not problems,'page_count':doc.page_count,
            'pages':pages,'problems':problems,
            'human_visual_review':'PENDING — Agent/审稿人必须逐张打开全部 PNG 并标记结论，未审不得宣布正式PASS',
            'wps_tested':False}
    (out/'visual-precheck.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--file',required=True);a.add_argument('--outdir',required=True)
    a.add_argument('--max-pages',type=int,default=3)
    args=a.parse_args()
    try:
        report=render_and_precheck(args.file,args.outdir,args.max_pages)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if not report['auto_precheck_passed']:raise SystemExit(2)
    except Exception as e:
        a.exit(2,f'ERROR: {e}\n')
