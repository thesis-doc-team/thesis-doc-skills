#!/usr/bin/env python3
"""Render all DOCX pages and flag split-session signs without ever changing margins/rows.
DOCX->PDF 依次探测 soffice -> Word COM -> WPS COM（可 --pdf 直通已转 PDF）。"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse, json, os, re, subprocess
from pathlib import Path
import fitz

def page_ink_ratio(page):
    """非白像素占比（72dpi，1/7 抽样；任一通道<245 计非白）。空白页≈0。"""
    pix=page.get_pixmap(alpha=False)
    s,n=pix.samples,pix.n
    total=nonwhite=0
    for j in range(0,len(s)-n,n*7):
        total+=1
        if s[j]<245 or s[j+1]<245 or s[j+2]<245:nonwhite+=1
    return nonwhite/max(total,1)

def blank_page_kind(page):
    """任意页空白页判定（用户硬性要求：Word 成品任何位置不得出现空白页）。返回 None/'blank'/'near_blank'。
    正文文字只计页眉/页脚带（上下 72pt）以外的文本块；纯页码行不计。'blank'=无正文且几乎无着墨
    （无表格/图形）；'near_blank'=正文<10 字且着墨<1%，须目视确认。表格框线着墨使空白填写页不被误判。"""
    ph=page.rect.height
    lines=[b[4] for b in page.get_text('blocks') if b[3]>72 and b[1]<ph-72]
    core=re.sub(r'\s','',''.join(lines))
    if re.fullmatch(r'[\-–—－_/\.0-9]*',core):core=''
    ink=page_ink_ratio(page)
    if not core and ink<0.003:return 'blank'
    if len(core)<10 and ink<0.01:return 'near_blank'
    return None

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
    doc=fitz.open(pdf);pages=[];warnings=[];problems=[]
    for i,page in enumerate(doc):
        filename=out/f'page-{i+1}.png'
        page.get_pixmap(matrix=fitz.Matrix(1.65,1.65),alpha=False).save(filename)
        content=page.get_text(sort=True)
        substantive=len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',content))
        kind=blank_page_kind(page)
        if kind=='blank':
            problems.append(f'第{i+1}页为空白页（整页无正文，仅页码/页眉/页脚亦算）：fill_guidance.py 已内置表尾 1pt 防空白页尾段；仍出现时先与官方空白原件同渲染器对照定性（原件同位置亦空白→模板固有如实报告；否则内容/占位挤出，回到可填正文收口重排后复验）')
        elif kind=='near_blank' or substantive<20:
            warnings.append(f'第{i+1}页有效文字过少（{kind or "内容偏少"}），检查是否空白/孤页')
        if i>1 and re.search(r'^\s*指导教师（签字）',content):
            warnings.append(f'第{i+1}页以签字栏开始，疑似官方固定行高导致跨页（未改表格）')
        if i>1 and re.search(r'指导内容\s*$',content.strip()):
            warnings.append(f'第{i+1}页在新记录指导内容标题处结束，下一页继续；属跨页风险')
        pages.append({'page':i+1,'image':str(filename),'substantive_chars':substantive,
                      'blank_check':kind or 'ok','visually_inspected':False,'verdict':'PENDING'})
    report={'page_count':len(doc),'pages':pages,'problems':problems,'auto_precheck_passed':not problems,'warnings':warnings,
            'visual_review':'PENDING: 必须逐张检查全部 PNG 的缺字、遮挡、边框与跨页；页数无上限，但任何位置的空白页都不得存在。',
            'template_layout_changed':False,'wps_tested':False,'converter':converter}
    (out/'render-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--outdir',required=True);p.add_argument('--pdf',default=None,help='直通外部已转换 PDF（跳过转换链）')
    a=p.parse_args();r=render(a.file,a.outdir,a.pdf)
    print('RENDERED',r['page_count'],'pages; problems',len(r['problems']),'; warnings',len(r['warnings']))
    for x in r['problems']:print('FAIL:',x)
    for w in r['warnings']:print('WARN:',w)
    if r['problems']:raise SystemExit(2)
