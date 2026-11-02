#!/usr/bin/env python3
"""Render all DOCX pages and flag split-session signs without ever changing margins/rows.
DOCX->PDF 依次探测 soffice -> Word COM -> WPS COM（可 --pdf 直通已转 PDF）。"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse, json, os, re, subprocess
from pathlib import Path
import fitz

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


def render(docx, outdir, pdf_in=None):
    src=Path(docx).resolve();out=Path(outdir).resolve();out.mkdir(parents=True,exist_ok=True)
    if pdf_in is not None:
        pdf=Path(pdf_in).resolve()
        if pdf.suffix.lower()!='.pdf' or not pdf.is_file(): raise ValueError('--pdf 需要已转换的 PDF 文件')
        converter='external-pdf'
    else:
        pdf,converter=_docx_to_pdf(src,out)
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
            'template_layout_changed':False,'wps_tested':False,'converter':converter}
    (out/'render-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--outdir',required=True);p.add_argument('--pdf',default=None,help='直通外部已转换 PDF（跳过转换链）')
    a=p.parse_args();r=render(a.file,a.outdir,a.pdf)
    print('RENDERED',r['page_count'],'pages; warnings',len(r['warnings']))
    for w in r['warnings']:print('WARN:',w)
