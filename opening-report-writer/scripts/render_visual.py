#!/usr/bin/env python3
"""DOCX -> PDF + all PNG pages + objective pagination preflight.

This script DOES NOT certify visual PASS: an Agent must actually inspect EVERY PNG.
Render artifacts belong ONLY in the per-run owned .skill-tmp directory.
Requires LibreOffice (soffice) and PyMuPDF.
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from check_render import run as review_page_markers


def render(source: Path, outdir: Path, max_pages=None):
    try: import fitz
    except ImportError as exc: raise RuntimeError('需要 pip install PyMuPDF') from exc
    if shutil.which('soffice') is None: raise RuntimeError('缺少 soffice；不可声明完成视觉验收')
    source=source.resolve(); outdir=outdir.resolve()
    if not source.is_file(): raise FileNotFoundError(source)
    if outdir == source.parent or 'deliverables' in outdir.parts:
        raise ValueError('PNG/PDF 不允许写进 deliverables 成品目录')
    outdir.mkdir(parents=True,exist_ok=True)
    profile=outdir/'_lo-profile'
    cmd=['soffice',f'-env:UserInstallation={profile.as_uri()}', '--headless','--convert-to','pdf','--outdir',str(outdir),str(source)]
    r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=180)
    pdf=outdir/(source.stem+'.pdf')
    if r.returncode or not pdf.exists(): raise RuntimeError(f'LibreOffice 转换失败：{r.stdout} {r.stderr}')
    with fitz.open(pdf) as doc:
        page_rows=[]
        for i,page in enumerate(doc):
            image=outdir/f'page-{i+1}.png'
            page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(str(image))
            txt=page.get_text(sort=True)
            page_rows.append({'page':i+1,'image':str(image),'text_chars':len(txt), 'visual_inspection':'PENDING'})
        count=len(doc)
    markers=review_page_markers(pdf)
    warnings=list(markers['warnings'])
    if max_pages is not None and count>max_pages:
        warnings.append(f'超过用户当次授权的页数 {max_pages}（非默认上限）；不得靠改字体/页边距硬压页数')
    if not count: warnings.append('无可渲染页面')
    if count > 1 and page_rows[-1]['text_chars'] < 30:
        warnings.append('最后一页基本没有正文，疑似仅页码/边框的空白孤页；必须返工或如实报告')
    result={'status':'WARN' if warnings else 'PRECHECK_OK','page_count':count,
            'pages':page_rows,'warnings':warnings,'markers':markers['markers'],
            'visual_review':'PENDING：必须由 Agent 逐页打开 PNG 并记录结论；预检不等于视觉 PASS',
            'wps_tested':False}
    (outdir/'visual-precheck.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--file',required=True,type=Path)
    a.add_argument('--outdir',required=True,type=Path)
    a.add_argument('--max-pages',type=int,default=None,help='仅当用户事先给出页数上限时使用')
    q=a.parse_args()
    try:
        print(json.dumps(render(q.file,q.outdir,q.max_pages),ensure_ascii=False,indent=2))
    except Exception as exc:
        a.exit(2,f'ERROR: {exc}\n')
