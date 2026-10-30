#!/usr/bin/env python3
"""Render all DOCX pages and flag split-session signs without ever changing margins/rows."""
import argparse, json, os, re, subprocess
from pathlib import Path
import fitz

def render(docx, outdir):
    src=Path(docx).resolve();out=Path(outdir).resolve();out.mkdir(parents=True,exist_ok=True)
    profile=out/'_lo_profile'
    cmd=['soffice',f'-env:UserInstallation={profile.as_uri()}',
         '--headless','--convert-to','pdf','--outdir',str(out),str(src)]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
    pdf=out/f'{src.stem}.pdf'
    if proc.returncode or not pdf.exists():raise RuntimeError(proc.stdout+' '+proc.stderr)
    doc=fitz.open(pdf);pages=[];warnings=[]
    for i,page in enumerate(doc):
        filename=out/f'page-{i+1}.png'
        page.get_pixmap(matrix=fitz.Matrix(1.65,1.65),alpha=False).save(filename)
        content=page.get_text(sort=True)
        substantive=len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',content))
        if substantive<20:warnings.append(f'第{i+1}页有效文字过少，检查是否空白/孤页')
        if i>1 and re.search(r'^\s*指导教师（签字）',content):
            warnings.append(f'第{i+1}页以签字栏开始，疑似官方固定行高导致跨页（未改表格）')
        if i>1 and re.search(r'指导内容\s*$',content.strip()):
            warnings.append(f'第{i+1}页在新记录指导内容标题处结束，下一页继续；属跨页风险')
        pages.append({'page':i+1,'image':str(filename),'substantive_chars':substantive,
                      'visually_inspected':False,'verdict':'PENDING'})
    report={'page_count':len(doc),'pages':pages,'warnings':warnings,
            'visual_review':'PENDING: 必须逐张检查全部 PNG 的缺字、遮挡、边框与跨页；页数无上限，不按空白页数压缩。',
            'template_layout_changed':False,'wps_tested':False}
    (out/'render-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--outdir',required=True)
    a=p.parse_args();r=render(a.file,a.outdir)
    print('RENDERED',r['page_count'],'pages; warnings',len(r['warnings']))
    for w in r['warnings']:print('WARN:',w)
