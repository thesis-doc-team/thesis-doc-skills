#!/usr/bin/env python3
"""Render all DOCX pages to PNG for review, producing *precheck* not WPS approval.

Keeps all output within caller-designated owned workdir. Page count is informative
only: do NOT compress text to match blank template pagination.
"""
import argparse,json,re,subprocess
from pathlib import Path
import fitz

def run(source,output_dir):
    source=Path(source).resolve();out=Path(output_dir).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    out.mkdir(parents=True,exist_ok=True)
    pdf=out/(source.stem+'.pdf')
    profile=out/'_lo-profile'
    cmd=['soffice',f'-env:UserInstallation={profile.as_uri()}',
         '--headless','--convert-to','pdf','--outdir',str(out),str(source)]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
    if proc.returncode!=0 or not pdf.exists():raise RuntimeError(f'渲染失败：{proc.stdout} {proc.stderr}')
    pages=[]
    with fitz.open(pdf) as doc:
        for i,p in enumerate(doc):
            pic=out/f'page-{i+1}.png'
            p.get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False).save(pic)
            pages.append({'page':i+1,'png':str(pic),'extracted_chars':len(p.get_text()),
                          'visually_inspected':False,'conclusion':'PENDING'})
    warnings=[]
    if pages and pages[-1]['extracted_chars']<80:warnings.append('最后一页内容很少：请视觉检查是否孤立签名或异常空白；这不是自动删改内容的许可')
    result={'pages':pages,'page_count':len(pages),'warnings':warnings,'requires_each_page_review':True,
            'render_engine':'LibreOffice','wps_tested':False,
            'visual_approved':False,'no_fixed_page_limit':True}
    (out/'visual-precheck.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--file',required=True);a.add_argument('--outdir',required=True)
    args=a.parse_args();print(json.dumps(run(args.file,args.outdir),ensure_ascii=False,indent=2))
