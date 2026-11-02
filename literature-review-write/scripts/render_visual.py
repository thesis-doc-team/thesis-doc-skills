#!/usr/bin/env python3
"""Render actual pages + automated red flags. Manual visual inspection is mandatory and distinct.

DOCX->PDF 依次探测 soffice -> Word COM -> WPS COM（可 --pdf 直通）；PNG 需 PyMuPDF (fitz). Writes files only inside the
user-specified, per-run owned workdir. Never asserts WPS/Word was tested.
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse,json,re,subprocess
from pathlib import Path
import fitz

FIXED=('塔里木大学','毕业论文（设计）文献综述','附件3','指导教师（签字）','年    月    日')

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


def render(source,outdir,pdf_in=None):
    source=Path(source).resolve();outdir=Path(outdir).resolve()
    if not source.is_file():raise ValueError('不存在待渲染 DOCX')
    outdir.mkdir(parents=True,exist_ok=True)
    if pdf_in is not None:
        pdf=Path(pdf_in).resolve()
        if pdf.suffix.lower()!='.pdf' or not pdf.is_file(): raise ValueError('--pdf 需要已转换的 PDF 文件')
        converter='external-pdf'
    else:
        pdf,converter=_docx_to_pdf(source,outdir)
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
    output={'engine':converter+' + PyMuPDF','pdf_path':str(pdf),'page_count':len(pages),
            'pages':pages,'automatic_warnings':issues,'fully_visually_inspected':False,
            'word_tested':False,'wps_tested':False,
            'status':'AWAITING_MANUAL_PAGE_INSPECTION' if not issues else 'WARNING_REVIEW_REQUIRED'}
    (outdir/'visual-precheck.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--outdir',required=True);p.add_argument('--pdf',default=None,help='直通外部已转换 PDF（跳过转换链）')
    a=p.parse_args()
    try:res=render(a.file,a.outdir,a.pdf);print(json.dumps(res,ensure_ascii=False,indent=2))
    except Exception as exc:raise SystemExit('ERROR: '+str(exc))
