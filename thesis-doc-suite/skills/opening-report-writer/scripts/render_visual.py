#!/usr/bin/env python3
"""DOCX -> PDF + all PNG pages + objective pagination preflight.

This script DOES NOT certify visual PASS: an Agent must actually inspect EVERY PNG.
Render artifacts belong ONLY in the per-run owned .skill-tmp directory.
DOCX->PDF 转换链依次探测 soffice -> Word COM -> WPS COM（可 --pdf 直通已转 PDF）；PNG/预检需 PyMuPDF。
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from check_render import run as review_page_markers


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


def render(source: Path, outdir: Path, max_pages=None, pdf_in=None):
    try: import fitz
    except ImportError as exc: raise RuntimeError('需要 pip install PyMuPDF') from exc
    source=source.resolve(); outdir=outdir.resolve()
    if not source.is_file(): raise FileNotFoundError(source)
    if outdir == source.parent or 'deliverables' in outdir.parts:
        raise ValueError('PNG/PDF 不允许写进 deliverables 成品目录')
    outdir.mkdir(parents=True,exist_ok=True)
    if pdf_in is not None:
        pdf=Path(pdf_in).resolve()
        if pdf.suffix.lower()!='.pdf' or not pdf.is_file(): raise ValueError('--pdf 需要已转换的 PDF 文件')
        converter='external-pdf'
    else:
        pdf,converter=_docx_to_pdf(source,outdir)
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
            'wps_tested':False,'converter':converter}
    (outdir/'visual-precheck.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--file',required=True,type=Path)
    a.add_argument('--outdir',required=True,type=Path)
    a.add_argument('--max-pages',type=int,default=None,help='仅当用户事先给出页数上限时使用')
    a.add_argument('--pdf',type=Path,default=None,help='直通外部已转换 PDF（跳过 DOCX->PDF 转换链）')
    q=a.parse_args()
    try:
        print(json.dumps(render(q.file,q.outdir,q.max_pages,q.pdf),ensure_ascii=False,indent=2))
    except Exception as exc:
        a.exit(2,f'ERROR: {exc}\n')
