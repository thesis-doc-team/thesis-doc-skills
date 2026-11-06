#!/usr/bin/env python3
"""A4/Word-content-box measurement and static layout checks, stdlib only.

This does not claim to replace page rendering in Word/WPS. It deliberately
returns NEEDS_VISUAL_REVIEW unless a PDF/page screenshot has been inspected.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
WP='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
NS={'w':W,'wp':WP}
TWIP_PER_MM=1440/25.4
EMU_PER_MM=36000
DEFAULT_A4=(210.0,297.0)


def mm_twips(v):return round(v*TWIP_PER_MM,2)
def twips_mm(v):return round(v/TWIP_PER_MM,2)
def attr(el,key,default=None):
    return default if el is None else el.attrib.get('{'+W+'}'+key,default)


def read_doc(path):
    path=Path(path)
    if not path.is_file() or path.suffix.lower()!='.docx':
        raise ValueError('需要真实 DOCX 模板/成品，不接受未知文件格式')
    with ZipFile(path) as z:
        if 'word/document.xml' not in z.namelist():raise ValueError('DOCX 没有 document.xml')
        payload=z.read('word/document.xml')
    if len(payload)>20_000_000:raise ValueError('document.xml 过大')
    return ET.fromstring(payload)


def get_sections(root):
    rows=[]
    for index, sect in enumerate(root.findall('.//w:sectPr',NS),1):
        pg=sect.find('./w:pgSz',NS);mar=sect.find('./w:pgMar',NS)
        if pg is None or mar is None:continue
        wide=int(attr(pg,'w','11906'));high=int(attr(pg,'h','16838'))
        left=int(attr(mar,'left','1440'));right=int(attr(mar,'right','1440'))
        top=int(attr(mar,'top','1440'));bottom=int(attr(mar,'bottom','1440'))
        header=int(attr(mar,'header','708'));footer=int(attr(mar,'footer','708'))
        width, height=twips_mm(wide),twips_mm(high)
        innerw=twips_mm(wide-left-right)
        innerh=twips_mm(high-top-bottom)
        a4=any(abs(width-x)<1.2 and abs(height-y)<1.2 for x,y in [DEFAULT_A4,tuple(reversed(DEFAULT_A4))])
        rows.append({'index':index,'page_mm':[width,height],'is_a4':a4,
                     'margins_mm':{'left':twips_mm(left),'right':twips_mm(right),
                                   'top':twips_mm(top),'bottom':twips_mm(bottom),
                                   'header':twips_mm(header),'footer':twips_mm(footer)},
                     'content_width_mm':innerw,'content_height_mm':innerh,
                     'figure_max_width_mm':max(5,round(innerw-2,1)),
                     'figure_max_height_mm':max(5,round(min(innerh-18,innerh*0.82),1)),
                     'table_max_width_mm':innerw,
                     'min_figure_text_pt':9.0,
                     'caption_reserved_height_mm':12.0})
    if not rows:raise ValueError('模板未提供可核验的 sectPr 页面/页边距，拒绝假设标准页边距')
    return rows


def inspect_template(path):
    sections=get_sections(read_doc(path))
    return {'status':'PROFILED','template':str(Path(path)),'sections':sections,
            'notice':'对多节/横竖混排文档，插入前需定位所在节；本检查不修改官方模板。'}


def fit_figure(width_mm,height_mm,section,source_min_text_pt=None):
    if width_mm<=0 or height_mm<=0:raise ValueError('图像宽高必须为正数')
    wlim=section['figure_max_width_mm'];hlim=section['figure_max_height_mm']
    scale=min(wlim/width_mm,hlim/height_mm,1.0)
    w=round(width_mm*scale,2);h=round(height_mm*scale,2)
    effective=(round(source_min_text_pt*scale,2) if source_min_text_pt is not None else None)
    reasons=[]
    if effective is not None and effective<section['min_figure_text_pt']:
        reasons.append('缩放后图中文字小于9pt；必须重排/拆图，不能强行压缩')
    if width_mm>0 and height_mm>0 and min(w,h)<25:
        reasons.append('图像物理尺寸过小，建议重新布局')
    return {'status':'NEEDS_RELAYOUT' if reasons else 'PLANNED_NEEDS_PAGE_RENDER',
            'original_mm':[width_mm,height_mm], 'suggested_width_mm':w,
            'suggested_height_mm':h,'scale':round(scale,5),
            'effective_text_pt':effective,'issues':reasons,
            'note':'必须使用 Word/WPS 实际渲染逐页检查；此结果只是几何预检。'}


def audit_docx(path):
    root=read_doc(path);sections=get_sections(root)
    # Conservative: if multiple sections exist, all figures/tables require per-section attribution.
    sec=sections[0]; problems=[];pictures=[]; tables=[]
    for i,extent in enumerate(root.findall('.//wp:extent',NS),1):
        width=round(int(extent.get('cx','0'))/EMU_PER_MM,2)
        height=round(int(extent.get('cy','0'))/EMU_PER_MM,2)
        floating=False
        # relationship to wp:anchor requires ancestor tracking
        for anchor in root.findall('.//wp:anchor',NS):
            if extent in anchor.findall('.//wp:extent',NS):floating=True
        issue=[]
        if width>sec['content_width_mm']+0.5:issue.append('图片宽度超出版心')
        if height>sec['content_height_mm']+0.5:issue.append('图片高度超出正文高度')
        if width<=0 or height<=0:issue.append('图片尺寸无效')
        if floating:issue.append('浮动环绕对象需检测与文本碰撞；优先改为嵌入型')
        pictures.append({'index':i,'size_mm':[width,height],'floating':floating,'issues':issue})
        problems.extend([f'图片{i}: {x}' for x in issue])
    for i,tbl in enumerate(root.findall('.//w:tbl',NS),1):
        grid=tbl.findall('./w:tblGrid/w:gridCol',NS)
        values=[int(attr(el,'w','0')) for el in grid]
        gridw=twips_mm(sum(values))
        if not values or gridw==0:
            total_w=tbl.find('./w:tblPr/w:tblW',NS)
            if total_w is not None and attr(total_w,'type')=='dxa':
                gridw=twips_mm(int(attr(total_w,'w','0')))
        issue=[]
        if gridw>sec['content_width_mm']+0.5:issue.append('表格网格宽度超出版心')
        if gridw==0:issue.append('无法确定实际表格宽度；需 Word/WPS 实际渲染')
        cells=[len(r.findall('./w:tc',NS)) for r in tbl.findall('./w:tr',NS)]
        tables.append({'index':i,'width_mm':gridw,'max_cells_in_row':max(cells or [0]),'issues':issue})
        problems.extend([f'表{i}: {x}' for x in issue])
    if len(sections)>1:problems.append('含多个节，需按真实图片/表格所在节分别计算版心')
    if any(not x['is_a4'] for x in sections):problems.append('至少一个节不是A4纸张')
    return {'status':'BLOCK_STATIC_ISSUES' if problems else 'STATIC_CHECK_PASS_NEEDS_VISUAL_REVIEW',
            'page_sections':sections,'figures':pictures,'tables':tables,
            'issues':problems,'required_next':'在真实 Word/WPS 中渲染全部相关页，人工检查断页、重叠、字体与图题，不得仅凭XML合格批准。'}


def main():
    ap=argparse.ArgumentParser(description='A4 官方 Word 版心测量/静态溢出审计，不改原文件')
    sub=ap.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('profile');a.add_argument('--template',required=True)
    b=sub.add_parser('audit');b.add_argument('--docx',required=True)
    c=sub.add_parser('fit-figure');c.add_argument('--template',required=True)
    c.add_argument('--width-mm',type=float,required=True);c.add_argument('--height-mm',type=float,required=True)
    c.add_argument('--text-pt',type=float);c.add_argument('--section',type=int,default=1)
    args=ap.parse_args()
    try:
        if args.cmd=='profile':r=inspect_template(args.template)
        elif args.cmd=='audit':r=audit_docx(args.docx)
        else:
            sec=inspect_template(args.template)['sections'][args.section-1]
            r=fit_figure(args.width_mm,args.height_mm,sec,args.text_pt)
        print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['status'] not in ('BLOCK_STATIC_ISSUES','NEEDS_RELAYOUT') else 2
    except (OSError,ValueError,IndexError,ET.ParseError) as e:
        print(json.dumps({'status':'BLOCK','error':str(e)},ensure_ascii=False));return 2
if __name__=='__main__':raise SystemExit(main())
