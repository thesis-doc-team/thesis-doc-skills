#!/usr/bin/env python3
"""Render actual pages + automated red flags. Manual visual inspection is mandatory and distinct.

Requires LibreOffice (soffice) and PyMuPDF (fitz). Writes files only inside the
user-specified, per-run owned workdir. Never asserts WPS/Word was tested.
"""
import argparse,json,re,subprocess
from pathlib import Path
import fitz

FIXED=('塔里木大学','毕业论文（设计）文献综述','附件3','指导教师（签字）','年    月    日')

def render(source,outdir):
    source=Path(source).resolve();outdir=Path(outdir).resolve()
    if not source.is_file():raise ValueError('不存在待渲染 DOCX')
    outdir.mkdir(parents=True,exist_ok=True)
    profile=outdir/'lo_profile'
    cmd=['soffice',f'-env:UserInstallation={profile.as_uri()}',
         '--headless','--convert-to','pdf','--outdir',str(outdir),str(source)]
    cp=subprocess.run(cmd,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=180)
    pdf=outdir/(source.stem+'.pdf')
    if cp.returncode or not pdf.is_file():raise RuntimeError('DOCX 转 PDF 失败: '+cp.stdout+' '+cp.stderr)
    pages=[];issues=[]
    with fitz.open(pdf) as d:
        if not d.page_count:issues.append('PDF页数为0')
        for i,page in enumerate(d):
            image=outdir/f'page-{i+1}.png'
            page.get_pixmap(matrix=fitz.Matrix(1.65,1.65),alpha=False).save(image)
            raw=page.get_text()
            meaningful=raw
            for f in FIXED:meaningful=meaningful.replace(f,'')
            count=len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',meaningful))
            if 'Error! Reference source not found' in raw:issues.append(f'第{i+1}页含失效引用提示')
            pages.append({'page':i+1,'png':str(image),'content_chars_approx':count,
             'visual_review':'PENDING — 需实际打开并逐页确认'})
    if pages and pages[-1]['content_chars_approx']<30:
        issues.append('末页有效文字极少，疑似孤立落款或空白页，需要人工确认')
    output={'engine':'LibreOffice + PyMuPDF','pdf_path':str(pdf),'page_count':len(pages),
            'pages':pages,'automatic_warnings':issues,'fully_visually_inspected':False,
            'word_tested':False,'wps_tested':False,
            'status':'AWAITING_MANUAL_PAGE_INSPECTION' if not issues else 'WARNING_REVIEW_REQUIRED'}
    (outdir/'visual-precheck.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--outdir',required=True)
    a=p.parse_args()
    try:res=render(a.file,a.outdir);print(json.dumps(res,ensure_ascii=False,indent=2))
    except Exception as exc:raise SystemExit('ERROR: '+str(exc))
