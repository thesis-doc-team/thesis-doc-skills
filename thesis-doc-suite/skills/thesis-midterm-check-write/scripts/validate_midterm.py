#!/usr/bin/env python3
"""Gate v1.1: immutable official framework + mandatory narrative typography.

Checks the regression that v1.0 missed: no first-line indent, font mismatch,
unused blank-space spillover, fixed text/signatures changed.
"""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from template_tools import DEFAULT_TEMPLATE,lock_check,count_content_chars,unique_cells,sha256
from fill_midterm import FIELDS,paragraphs,issue_paragraphs,validate_issue_structure,indent_for,BODY_FONT_PT,BODY_FIRST_LINE_PT_BY_ROW

def xml_eq(a,b):
    if a is None or b is None:return a is None and b is None
    return etree.tostring(a,method='c14n')==etree.tostring(b,method='c14n')

def report_error(errors,message):
    errors.append(message)

def check_filled_body(original_cell,new_cell,parts,region,row,problems):
    op=original_cell.paragraphs; np=new_cell.paragraphs
    if not xml_eq(op[0]._p,np[0]._p):report_error(problems,f'{region} 官方栏目标题有变化')
    old_fixed=[p for p in op[1:] if p.text.strip()]
    new_fixed=[p for p in np[1:] if p.text.strip() and p.text.strip() not in parts]
    # Exact fixed original paragraphs are still present in same order, at the end.
    if len(new_fixed)!=len(old_fixed):
        report_error(problems,f'{region} 固定落款段落数改变')
    else:
        for i,(x,y) in enumerate(zip(old_fixed,new_fixed)):
            if not xml_eq(x._p,y._p):report_error(problems,f'{region} 固定落款第{i}段变化')
    actual=np[1:1+len(parts)]
    if [p.text for p in actual]!=parts:
        report_error(problems,f'{region} 正文顺序或内容不一致')
    if len(np)!=1+len(parts)+len(old_fixed):
        report_error(problems,f'{region} 未清理多余占位空段或擅自增加段落：{len(np)}')
    for index,p in enumerate(actual):
        txt=parts[index]
        expected=Pt(indent_for(txt,row))
        if p.paragraph_format.first_line_indent!=expected:
            report_error(problems,f'{region} 正文第{index+1}段首行缩进错误，应为 {expected.pt}pt')
        if p.paragraph_format.line_spacing!=1.5:
            report_error(problems,f'{region} 正文第{index+1}段行距不是原模板1.5倍')
        # Paragraph styles/spacing other than editable firstLine must be untouched.
        pa=op[1+index]
        if pa.style.name!=p.style.name or pa.paragraph_format.space_before!=p.paragraph_format.space_before or pa.paragraph_format.space_after!=p.paragraph_format.space_after or pa.alignment!=p.alignment:
            report_error(problems,f'{region} 正文第{index+1}段其余格式被改变')
        for rid,r in enumerate(p.runs):
            if r.font.size!=Pt(BODY_FONT_PT):report_error(problems,f'{region} 正文第{index+1}段字体大小不是12pt')
            fonts=r._element.rPr.rFonts if r._element.rPr is not None else None
            if fonts is None or fonts.get(qn('w:eastAsia'))!='宋体' or fonts.get(qn('w:ascii'))!='Times New Roman':
                report_error(problems,f'{region} 第{index+1}段第{rid}个run中西文字体错误')

def validate(template,generated,data):
    original,lock=lock_check(template)
    new=Document(generated)
    problems=[]
    if len(new.tables)!=len(original.tables) or len(new.sections)!=len(original.sections):
        return {'passed':False,'problems':['原表格数量或节数改变']}
    for i,(a,b) in enumerate(zip(original.sections,new.sections)):
        if not xml_eq(a._sectPr,b._sectPr):report_error(problems,f'第{i}节页面设置/页眉页脚改变')
    if len(original.paragraphs)!=len(new.paragraphs):report_error(problems,'外部段落数量改变')
    for i,(a,b) in enumerate(zip(original.paragraphs,new.paragraphs)):
        if i==2 and data.get('inspection_date'):
            if a._p.pPr is not None and not xml_eq(a._p.pPr,b._p.pPr):report_error(problems,'顶部日期段格式变更')
        elif not xml_eq(a._p,b._p):report_error(problems,f'外部固定段落第{i}项修改')
    ot=original.tables[0];nt=new.tables[0]
    if not xml_eq(ot._tbl.tblPr,nt._tbl.tblPr) or not xml_eq(ot._tbl.tblGrid,nt._tbl.tblGrid):
        report_error(problems,'表格宽度/边框/网格被改')
    if len(ot.rows)!=len(nt.rows):report_error(problems,'表格行数改变')
    for ri,(ra,rb) in enumerate(zip(ot.rows,nt.rows)):
        if not xml_eq(ra._tr.trPr,rb._tr.trPr):report_error(problems,f'第{ri}行行属性改变')
        cells_a=unique_cells(ra);cells_b=unique_cells(rb)
        if len(cells_a)!=len(cells_b):report_error(problems,f'第{ri}行合并格数改变');continue
        for ci,(ca,cb) in enumerate(zip(cells_a,cells_b)):
            if not xml_eq(ca._tc.tcPr,cb._tc.tcPr):report_error(problems,f'第{ri}行第{ci}列单元格属性改变')
            if ri in (2,3,4) and ci==0:continue
            if ri==5 and ci==0 and data.get('college_opinion_authorized'):continue
            if ri==0 and ci in (1,3):
                if ca.paragraphs[0].paragraph_format.first_line_indent!=cb.paragraphs[0].paragraph_format.first_line_indent:
                    report_error(problems,f'表头信息第{ci}格缩进改变')
                continue
            if ri==1 and ci==1:continue
            if not xml_eq(ca._tc,cb._tc):report_error(problems,f'禁止修改固定区域第{ri}行第{ci}格')
    for k,row,_ in FIELDS:
        try:
            parts=issue_paragraphs(data) if k=='issues_paragraphs' else paragraphs(data,k)
            if count_content_chars(parts)<200:report_error(problems,f'{k}不足200字')
            check_filled_body(ot.cell(row,0),nt.cell(row,0),parts,k,row,problems)
        except (KeyError,ValueError,IndexError) as exc:report_error(problems,str(exc))
    if nt.cell(1,1).text.strip()!=str(data.get('title','')).strip():report_error(problems,'课题题目不符合输入')
    for key,col in [('student_name',1),('class_name',3)]:
        if nt.cell(0,col).text.strip()!=str(data.get(key,'')).strip():report_error(problems,f'{key} 填写不符合输入')
    if data.get('teacher_opinion_is_draft') is not True:report_error(problems,'未声明教师意见拟稿')
    tparts=data.get('teacher_opinion_paragraphs') or []
    if isinstance(tparts,str):tparts=[tparts]
    if any(('本栏为拟稿' in str(p) or '供教师审定拟稿' in str(p)) for p in tparts):
        report_error(problems,'教师意见正文含拟稿提示语（本栏为拟稿/供教师审定拟稿），应以收束句自然结束')
    if not data.get('college_opinion_authorized') and not xml_eq(ot.cell(5,0)._tc,nt.cell(5,0)._tc):
        report_error(problems,'学院意见未经授权发生更改')
    with ZipFile(template) as a,ZipFile(generated) as b:
        if a.namelist()!=b.namelist():report_error(problems,'DOCX压缩包内文件清单变动')
        for name in a.namelist():
            if name!='word/document.xml' and name in b.namelist() and a.read(name)!=b.read(name):
                report_error(problems,f'模板静态内容发生更改：{name}')
    return {'passed':not problems,'problems':problems,'template_sha256':sha256(template),
            'output_sha256':sha256(generated), 'rows':len(nt.rows),
            'paragraph_counts':{k:len(nt.cell(row,0).paragraphs) for k,row,_ in FIELDS}, 'formatting':{
                'first_line_indent_pt_by_row':BODY_FIRST_LINE_PT_BY_ROW,
                'line_spacing':1.5,'font_pt':BODY_FONT_PT,
                'chinese_font':'宋体','ascii_font':'Times New Roman'},
            'word_counts':{k:count_content_chars(issue_paragraphs(data) if k=='issues_paragraphs' else paragraphs(data,k)) for k,_,_ in FIELDS},
            'issue_pairing':validate_issue_structure(issue_paragraphs(data)),
            'visual_qa':'PENDING: render_visual.py + human/agent each-page inspection'}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--template',default=str(DEFAULT_TEMPLATE))
    ap.add_argument('--file',required=True)
    ap.add_argument('--data',required=True)
    ap.add_argument('--report')
    args=ap.parse_args()
    try:
        d=json.loads(Path(args.data).read_text(encoding='utf-8'))
        res=validate(args.template,args.file,d)
        out=json.dumps(res,ensure_ascii=False,indent=2)
        if args.report:Path(args.report).write_text(out+'\n',encoding='utf-8')
        print(out)
        if not res['passed']:raise SystemExit(2)
    except (OSError,ValueError,KeyError) as exc:ap.exit(2,f'ERROR: {exc}\n')
