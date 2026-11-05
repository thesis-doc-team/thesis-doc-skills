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
    pages=[];issues=[];problems=[]
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
            kind=blank_page_kind(page)
            if kind=='blank':
                problems.append(f'第{i+1}页为空白页（整页无正文，仅页码/页眉/页脚亦算）：成品不得出现空白页。先与官方空白原件同渲染器对照定性：原件同位置亦空白→模板固有，如实报告用户；原件无空白→内容/占位挤出，只动可填正文收口重排后复验（不删事实、不改官方框架、不缩字号行距）')
            elif kind=='near_blank':
                issues.append(f'第{i+1}页正文不足10字且几乎无表格/图形：疑似近空白页，必须目视确认')
            pages.append({'page':i+1,'png':str(image),'content_chars_approx':count,'blank_check':kind or 'ok',
             'visual_review':'PENDING — 需实际打开并逐页确认'})
    if pages and pages[-1]['content_chars_approx']<30:
        issues.append('末页有效文字极少，疑似孤立落款或空白页，需要人工确认')
    output={'engine':converter+' + PyMuPDF','pdf_path':str(pdf),'page_count':len(pages),
            'pages':pages,'problems':problems,'auto_precheck_passed':not problems,
            'automatic_warnings':issues,'fully_visually_inspected':False,
            'word_tested':False,'wps_tested':False,
            'status':'FAIL_PRECHECK' if problems else ('AWAITING_MANUAL_PAGE_INSPECTION' if not issues else 'WARNING_REVIEW_REQUIRED')}
    (outdir/'visual-precheck.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--outdir',required=True);p.add_argument('--pdf',default=None,help='直通外部已转换 PDF（跳过转换链）')
    a=p.parse_args()
    try:
        res=render(a.file,a.outdir,a.pdf);print(json.dumps(res,ensure_ascii=False,indent=2))
        if res['problems']:raise SystemExit(2)
    except Exception as exc:raise SystemExit('ERROR: '+str(exc))
