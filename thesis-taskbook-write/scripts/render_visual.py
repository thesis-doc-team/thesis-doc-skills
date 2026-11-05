#!/usr/bin/env python3
"""Render all DOCX pages to PNG for review, producing *precheck* not WPS approval.

Keeps all output within caller-designated owned workdir. Page count is informative
only: do NOT compress text to match blank template pagination.
DOCX->PDF 依次探测 soffice -> Word COM -> WPS COM（可 --pdf 直通已转 PDF）。
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse,json,re,subprocess
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


def run(source,output_dir,pdf_in=None):
    source=Path(source).resolve();out=Path(output_dir).resolve()
    if not source.is_file():raise FileNotFoundError(source)
    out.mkdir(parents=True,exist_ok=True)
    if pdf_in is not None:
        pdf=Path(pdf_in).resolve()
        if pdf.suffix.lower()!='.pdf' or not pdf.is_file(): raise ValueError('--pdf 需要已转换的 PDF 文件')
        converter='external-pdf'
    else:
        pdf,converter=_docx_to_pdf(source,out)
    pages=[];problems=[];warnings=[]
    with fitz.open(pdf) as doc:
        for i,p in enumerate(doc):
            pic=out/f'page-{i+1}.png'
            p.get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False).save(pic)
            kind=blank_page_kind(p)
            if kind=='blank':
                problems.append(f'第{i+1}页为空白页（整页无正文，仅页码/页眉/页脚亦算）：成品不得出现空白页。先与官方空白原件同渲染器对照定性：原件同位置亦空白→模板固有，如实报告用户；原件无空白→内容/占位挤出，只动可填正文收口重排后复验（不删事实、不改官方框架、不缩字号行距）')
            elif kind=='near_blank':
                warnings.append(f'第{i+1}页正文不足10字且几乎无表格/图形：疑似近空白页，必须目视确认')
            pages.append({'page':i+1,'png':str(pic),'extracted_chars':len(p.get_text()),
                          'blank_check':kind or 'ok',
                          'visually_inspected':False,'conclusion':'PENDING'})
    if pages and pages[-1]['extracted_chars']<80:warnings.append('最后一页内容很少：请视觉检查是否孤立签名或异常空白；这不是自动删改内容的许可')
    result={'pages':pages,'page_count':len(pages),'problems':problems,'auto_precheck_passed':not problems,
            'warnings':warnings,'requires_each_page_review':True,
            'render_engine':converter,'wps_tested':False,
            'visual_approved':False,'no_fixed_page_limit':True}
    (out/'visual-precheck.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--file',required=True);a.add_argument('--outdir',required=True);a.add_argument('--pdf',default=None,help='直通外部已转换 PDF（跳过转换链）')
    args=a.parse_args();res=run(args.file,args.outdir,args.pdf);print(json.dumps(res,ensure_ascii=False,indent=2))
    if res['problems']:raise SystemExit(2)
