#!/usr/bin/env python3
"""Fill ONLY editable text slots of the verbatim university midterm DOCX.

Fails closed when template SHA mismatches the reviewed, bundled official copy.
No paragraphs, tables, borders, section or signature contents are removed.
"""
import argparse
from datetime import date
from io import BytesIO
from zipfile import ZipFile
import json
from pathlib import Path
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from template_tools import DEFAULT_TEMPLATE, lock_check, count_content_chars

FIELDS = [('progress_paragraphs',2,11), ('issues_paragraphs',3,10),
          ('teacher_opinion_paragraphs',4,10)]

def paragraphs(data,key):
    value = data.get(key)
    if isinstance(value,str):
        value = [s.strip() for s in value.splitlines() if s.strip()]
    if not isinstance(value,list) or not value or not all(isinstance(s,str) and s.strip() for s in value):
        raise ValueError(f'{key} 须为非空段落数组或多行文本')
    return [s.strip() for s in value]

def append_content(p, text):
    if p.text.strip():
        raise ValueError('尝试写入非空的官方固定段落，已拒绝')
    r=p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(12)
    rpr=r._element.get_or_add_rPr()
    rfonts=rpr.rFonts
    if rfonts is None:
        rfonts=OxmlElement('w:rFonts')
        rpr.insert(0,rfonts)
    rfonts.set(qn('w:eastAsia'),'宋体')

def fill_blank_cell(cell, text):
    if cell.text.strip():
        raise ValueError('个人信息目标单元格已有文字；禁止覆盖学校固定栏目')
    append_content(cell.paragraphs[0],text)

def write_body(cell, parts, indices):
    available=[cell.paragraphs[i] for i in indices if i < len(cell.paragraphs)]
    if len(parts) > len(available):
        raise ValueError(f'模板仅允许在 {len(available)} 个已有空白段落中填入内容；不能新增段落改变结构')
    for p, s in zip(available,parts):
        append_content(p,s)

def fill_docx(template, data, output):
    doc, lock = lock_check(template)
    if not isinstance(data,dict) or not data.get('title'):
        raise ValueError('必须提供本项目课题题目，不能从样本继承')
    if data.get('teacher_opinion_is_draft') is not True:
        raise ValueError('教师意见必须声明“拟稿待指导教师审核”，禁止伪装已批准')
    if data.get('college_opinion_paragraphs') and data.get('college_opinion_authorized') is not True:
        raise ValueError('学院意见未经明确授权不得预填')
    parsed={}
    for field,row,maxn in FIELDS:
        vals=paragraphs(data,field)
        if count_content_chars(vals) < 200:
            raise ValueError(f'{field} 不足 200 字（不计标点空白），实际 {count_content_chars(vals)} 字')
        if len(vals)>maxn:
            raise ValueError(f'{field} 段落数超出官方已有空白位置 {maxn}')
        parsed[field]=vals
    t=doc.tables[0]
    for field, col in [('student_name',1),('class_name',3)]:
        if data.get(field):
            fill_blank_cell(t.cell(0,col),str(data[field]).strip())
    fill_blank_cell(t.cell(1,1),str(data['title']).strip())
    if data.get('inspection_date'):
        raw=str(data['inspection_date'])
        try:
            dt=date.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError('inspection_date 必须为真实的 YYYY-MM-DD，禁止套用旧范本日期') from exc
        p=doc.paragraphs[2]
        if '年' not in p.text or '月' not in p.text or '日' not in p.text or len(p.runs)<2:
            raise ValueError('模板日期占位结构不符')
        # Modify only the date placeholder run; title/labels/spacing/style untouched.
        p.runs[-1].text=f' {dt.year}年  {dt.month}月  {dt.day}日'
    for field,row,_ in FIELDS:
        cell=t.cell(row,0)
        candidates=[i for i,p in enumerate(cell.paragraphs) if i>0 and not p.text.strip()]
        if row==4:
            # Restrict blanks before the teacher's signature/date; both remain verbatim.
            sig=next(i for i,p in enumerate(cell.paragraphs) if '指导教师签名' in p.text)
            candidates=[i for i in candidates if i<sig]
        write_body(cell,parsed[field],candidates)
    if data.get('college_opinion_paragraphs'):
        parts=paragraphs(data,'college_opinion_paragraphs')
        cell=t.cell(5,0)
        sig=next(i for i,p in enumerate(cell.paragraphs) if '负责人签名' in p.text)
        candidates=[i for i,p in enumerate(cell.paragraphs) if i>0 and i<sig and not p.text.strip()]
        write_body(cell,parts,candidates)
    target=Path(output)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.resolve() == Path(template).resolve():
        raise ValueError('禁止覆盖官方模板原件')
    # Preserve every original OOXML package part BYTE-FOR-BYTE except word/document.xml.
    # python-docx's serializer may otherwise rewrite styles/settings XML even when the
    # writer never edited them; this zip-level substitution avoids that drift entirely.
    buffer=BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    final=BytesIO()
    with ZipFile(template,'r') as base, ZipFile(buffer,'r') as edited, ZipFile(final,'w') as dest:
        for meta in base.infolist():
            data=edited.read(meta.filename) if meta.filename=='word/document.xml' else base.read(meta.filename)
            dest.writestr(meta,data)
    target.write_bytes(final.getvalue())
    print(f'CREATED: {target} (template sha256={lock["sha256"]})')

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--template',default=str(DEFAULT_TEMPLATE))
    a.add_argument('--data',required=True)
    a.add_argument('--out',required=True)
    args=a.parse_args()
    try:
        fill_docx(args.template,json.loads(Path(args.data).read_text(encoding='utf-8')),args.out)
    except (ValueError, OSError, KeyError,IndexError) as e:
        a.exit(2,f'ERROR: {e}\n')
