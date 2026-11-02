#!/usr/bin/env python3
"""Render each page and run automatic *prechecks* before human/Agent visual QA.

PDF/PNG remain in the owned .skill-tmp run directory. Do not confuse automatic
prechecks with visually inspected PASS results.
DOCX->PDF 依次探测 soffice -> Word COM -> WPS COM（可 --pdf 直通已转 PDF）；PNG/预检需 PyMuPDF (`fitz`)。
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
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

def _com_to_pdf(src, pdf, prog_id, label):
    import base64, shutil
    ps = shutil.which('powershell') or shutil.which('pwsh')
    if not ps:
        return False, f'{label}:环境无 PowerShell，无法走 COM 转换'
    s = str(src).replace("'", "''")
    d = str(pdf).replace("'", "''")
    script = ("$ErrorActionPreference='Stop';"
              f"try{{$app=New-Object -ComObject {prog_id};$app.Visible=$false;"
              f"$doc=$app.Documents.Open('{s}',$false,$true);"
              f"$doc.ExportAsFixedFormat('{d}',17);$doc.Close($false);$app.Quit();'CONVERTED'}}"
              f"catch{{Write-Output ('FAILED: '+$_.Exception.Message);exit 1}}")
    enc = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    try:
        r = subprocess.run([ps, '-NoProfile', '-NonInteractive', '-EncodedCommand', enc],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                           encoding='utf-8', errors='replace', timeout=300)
        if r.returncode == 0 and pdf.is_file():
            return True, ''
        return False, f'{label} COM 转换失败：{r.stdout} {r.stderr}'
    except Exception as e:
        return False, f'{label} COM 调用异常：{e}'


def _docx_to_pdf(source, outdir):
    """DOCX->PDF: soffice -> Word COM -> WPS COM probe chain; honest failure points to --pdf passthrough."""
    import shutil
    src = Path(source).resolve()
    out = Path(outdir).resolve()
    pdf = out / (src.stem + '.pdf')
    errors = []
    soffice = shutil.which('soffice')
    if soffice:
        profile = out / '_lo-profile'
        cmd = [soffice, f'-env:UserInstallation={profile.as_uri()}',
               '--headless', '--convert-to', 'pdf', '--outdir', str(out), str(src)]
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding='utf-8', errors='replace', timeout=180)
            if r.returncode == 0 and pdf.is_file():
                return pdf, 'soffice'
            errors.append(f'soffice 转换失败：{r.stdout} {r.stderr}')
        except Exception as e:
            errors.append(f'soffice 调用异常：{e}')
    else:
        errors.append('未安装 LibreOffice(soffice)')
    for prog_id, label in (('Word.Application', 'MS Word'), ('KWPS.Application', 'WPS')):
        ok, err = _com_to_pdf(src, pdf, prog_id, label)
        if ok:
            return pdf, label + ' COM'
        errors.append(err)
    raise RuntimeError('DOCX->PDF 转换链全部失败（soffice->Word COM->WPS COM）：'
                       + '；'.join(x for x in errors if x)
                       + '。可改用 --pdf 直通已转换的 PDF 再继续 PNG/预检（不得谎报无法截图或跳过验收）')


def render_and_precheck(source,output_dir,max_pages=3,pdf_in=None):
    source=Path(source).resolve();out=Path(output_dir).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    out.mkdir(parents=True,exist_ok=True)
    if pdf_in is not None:
        pdf=Path(pdf_in).resolve()
        if pdf.suffix.lower()!='.pdf' or not pdf.is_file(): raise ValueError('--pdf 需要已转换的 PDF 文件')
        converter='external-pdf'
    else:
        pdf,converter=_docx_to_pdf(source,out)
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
            'wps_tested':False,'converter':converter}
    (out/'visual-precheck.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--file',required=True);a.add_argument('--outdir',required=True)
    a.add_argument('--max-pages',type=int,default=3)
    a.add_argument('--pdf',default=None,help='直通外部已转换 PDF（跳过转换链）')
    args=a.parse_args()
    try:
        report=render_and_precheck(args.file,args.outdir,args.max_pages,args.pdf)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if not report['auto_precheck_passed']:raise SystemExit(2)
    except Exception as e:
        a.exit(2,f'ERROR: {e}\n')
