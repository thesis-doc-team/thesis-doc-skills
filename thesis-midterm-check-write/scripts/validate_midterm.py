#!/usr/bin/env python3
"""Strict structural/template/content acceptance checks; no edits."""
import argparse
from pathlib import Path
import json
from zipfile import ZipFile
from lxml import etree
from docx import Document
from template_tools import DEFAULT_TEMPLATE,lock_check,count_content_chars,para_xml_props,unique_cells,sha256
from fill_midterm import FIELDS,paragraphs

PRESERVE_ZIP_PARTS=('word/styles.xml','word/settings.xml','word/fontTable.xml',
                    'word/numbering.xml','word/theme/theme1.xml')
def xml_equal(a,b):
    if a is None or b is None: return a is None and b is None
    return etree.tostring(a,method='c14n')==etree.tostring(b,method='c14n')

def validate(template,generated,data):
    original,lock=lock_check(template)
    new=Document(generated)
    problems=[]
    if len(new.tables)!=len(original.tables) or len(new.sections)!=len(original.sections):
        problems.append('表格数/节数被改变')
        return {'passed':False,'problems':problems}
    for k,(s1,s2) in enumerate(zip(original.sections,new.sections)):
        if not xml_equal(s1._sectPr,s2._sectPr): problems.append(f'节{k}页边距/纸张/页码/页眉设置被改变')
    if len(new.paragraphs)!=len(original.paragraphs):problems.append('表格外段落数量被改变')
    for i,(a,b) in enumerate(zip(original.paragraphs,new.paragraphs)):
        if para_xml_props(a)!=para_xml_props(b):problems.append(f'顶层段落{i}样式/行距被改变')
        if i!=2 or not data.get('inspection_date'):
            if a.text!=b.text:problems.append(f'顶层固定文字{i}被改变')
        elif not all(x in b.text for x in ('年','月','日')):
            problems.append('日期填写损坏原有年月日标签')
    a=original.tables[0]; b=new.tables[0]
    if not xml_equal(a._tbl.tblPr,b._tbl.tblPr) or not xml_equal(a._tbl.tblGrid,b._tbl.tblGrid):
        problems.append('表格样式/宽度/列网格被改变')
    if len(a.rows)!=len(b.rows):problems.append('表格行数被改变')
    allowed_rows={0:{1,3},1:{1},2:{0},3:{0},4:{0},5:({0} if data.get('college_opinion_authorized') else set())}
    for ri,(r1,r2) in enumerate(zip(a.rows,b.rows)):
        if not xml_equal(r1._tr.trPr,r2._tr.trPr):problems.append(f'第{ri}行行高/行属性被修改')
        u1,u2=unique_cells(r1),unique_cells(r2)
        if len(u1)!=len(u2):problems.append(f'第{ri}行合并关系发生变化');continue
        for ci,(c1,c2) in enumerate(zip(u1,u2)):
            if not xml_equal(c1._tc.tcPr,c2._tc.tcPr):problems.append(f'第{ri}行第{ci}个可见单元格属性被修改')
            if len(c1.paragraphs)!=len(c2.paragraphs):problems.append(f'第{ri}行第{ci}格段落数量被修改')
            for pi,(p1,p2) in enumerate(zip(c1.paragraphs,c2.paragraphs)):
                if para_xml_props(p1)!=para_xml_props(p2):problems.append(f'第{ri}行第{ci}格第{pi}段样式/段距改变')
                editable=(ri==0 and ci in (1,3)) or (ri==1 and ci==1) or (ri in (2,3,4) and ci==0 and pi>0 and not p1.text.strip()) or (ri==5 and ci==0 and pi>0 and not p1.text.strip() and data.get('college_opinion_authorized'))
                if not editable and p1.text!=p2.text:problems.append(f'固定文字遭到变更: 行{ri}格{ci}段{pi}')
    # Confirm all fixed teacher and college signatures/dates remain exactly intact.
    for ri,label in ((4,'指导教师签名'),(5,'负责人签名（盖章）')):
        p_orig=original.tables[0].cell(ri,0).paragraphs
        p_new=new.tables[0].cell(ri,0).paragraphs
        for i,p in enumerate(p_orig):
            if label in p.text and (p.text != p_new[i].text or p_orig[i+1].text != p_new[i+1].text):
                problems.append(f'{label}栏位及其日期被篡改')
    # Verify content equality and character counts; not only that a region is nonempty.
    t=b
    if t.cell(1,1).paragraphs[0].text != str(data.get('title','')).strip():problems.append('毕业设计题目与输入不一致')
    for key,col in (('student_name',1),('class_name',3)):
        if t.cell(0,col).text.strip()!=str(data.get(key,'')).strip():problems.append(f'{key} 缺失或与输入不一致')
    for field,row,maxn in FIELDS:
        try:
            want=paragraphs(data,field)
        except ValueError as e:
            problems.append(str(e));continue
        got=[p.text.strip() for p in t.cell(row,0).paragraphs[1:] if p.text.strip()]
        if row==4:got=[x for x in got if '指导教师签名' not in x and not ('年' in x and '月' in x and '日' in x)]
        if got!=want:problems.append(f'{field} 与输入文稿不一致或被改写')
        count=count_content_chars(want)
        if count<200:problems.append(f'{field} 仅 {count} 字，低于官方 200 字门槛')
    if data.get('teacher_opinion_is_draft') is not True:
        problems.append('指导教师意见必须仅以拟稿身份交付')
    if not data.get('college_opinion_authorized') and any(p.text.strip() for p in t.cell(5,0).paragraphs[1:10]):
        problems.append('未经授权填写了学院意见')
    with ZipFile(template) as z1, ZipFile(generated) as z2:
        for name in PRESERVE_ZIP_PARTS:
            if name in z1.namelist():
                if name not in z2.namelist() or z1.read(name)!=z2.read(name):
                    problems.append(f'Word 固有样式/配置包发生变化: {name}')
    report={'passed':not problems,'template_sha256':sha256(template),'output_sha256':sha256(generated),
            'sections':len(new.sections),'rows':len(b.rows),'paragraph_counts':{x:len(b.cell(r,0).paragraphs) for x,r,_ in FIELDS},
            'word_counts':{x:count_content_chars(paragraphs(data,x)) for x,_,_ in FIELDS},
            'problems':problems,'visual_qa':'REQUIRES_MANUAL_PAGE_BY_PAGE_REVIEW',
            'wps_qa':'NOT_CLAIMED_UNLESS_ACTUALLY_OPENED_IN_WPS'}
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--template',default=str(DEFAULT_TEMPLATE));p.add_argument('--file',required=True)
    p.add_argument('--data',required=True);p.add_argument('--report')
    args=p.parse_args()
    try:
        data=json.loads(Path(args.data).read_text(encoding='utf-8'))
        result=validate(args.template,args.file,data)
        out=json.dumps(result,ensure_ascii=False,indent=2)
        if args.report:Path(args.report).write_text(out+'\n',encoding='utf-8')
        print(out)
        if not result['passed']:raise SystemExit(2)
    except (OSError,ValueError,KeyError) as e:p.exit(2,f'ERROR: {e}\n')
