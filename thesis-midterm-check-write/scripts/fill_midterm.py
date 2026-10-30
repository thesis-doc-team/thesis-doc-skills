#!/usr/bin/env python3
"""Fill the *official original* midterm DOCX with paragraph formatting.

Only content-placeholders can be edited/reduced. Official fixed text, labels,
page setup, tables, signatures, original template bytes and ZIP parts are locked.
Release v1.3: supports strictly numbered, one-to-one issue -> corrective action
pairs; rejects narrative-only problem sections. Original official framework remains locked.
"""
import argparse
from datetime import date
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import json
import re
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from template_tools import DEFAULT_TEMPLATE,lock_check,count_content_chars

FIELDS=[('progress_paragraphs',2,11),('issues_paragraphs',3,10),('teacher_opinion_paragraphs',4,10)]
# The source official blank has 1.5-line spacing and 12pt main text.
# Set exactly 2 x 12pt for NEW narrative paragraphs, not for fixed headers/signatures.
BODY_FIRST_LINE_PT_BY_ROW={2:12,3:24,4:24,5:24}
BODY_FONT_PT=12
ZERO_INDENT_LABELS=('存在问题：','存在的问题：','整改措施：','下一步计划：')

def paragraphs(data,key):
    value=data.get(key)
    if isinstance(value,str):
        value=[s.strip() for s in value.splitlines() if s.strip()]
    if not isinstance(value,list) or not value or not all(isinstance(s,str) and s.strip() for s in value):
        raise ValueError(f'{key} 须为非空段落数组或多行文本')
    return [s.strip() for s in value]

ISSUE_HEADING_OPTIONS=('存在问题：','存在的问题：')
REMEDY_HEADING='整改措施：'
NUMBERED_ITEM=re.compile(r'^（([1-9][0-9]*)）\s*(.+)$')
MAX_ISSUE_PAIRS=4  # 官方问题格仅有10个可写段落：2标签 + 2×4条
MIN_ISSUE_TEXT_CHARS=18

def issue_paragraphs(data):
    """Canonical 2–4 numbered problems and 1:1 remedial actions.

    Preferred: issue_pairs=[{problem,action,verification?(optional)}].
    Backward compatible: issues_paragraphs, provided it already follows format.
    """
    if data.get('issue_pairs') is not None:
        pairs=data['issue_pairs']
        if not isinstance(pairs,list) or not 2<=len(pairs)<=MAX_ISSUE_PAIRS:
            raise ValueError('issue_pairs 必须为2至4条问题/措施对象（原模板空间限制）')
        issues=[]; actions=[]
        for n,pair in enumerate(pairs,1):
            if not isinstance(pair,dict):
                raise ValueError(f'第{n}条问题/措施必须是对象')
            problem=pair.get('problem')
            action=pair.get('action')
            check=pair.get('verification','')
            if not isinstance(problem,str) or not problem.strip() or not isinstance(action,str) or not action.strip():
                raise ValueError(f'第{n}条必须包含非空 problem 和 action')
            if check and not isinstance(check,str):raise ValueError('verification 必须是文本')
            issues.append(f'（{n}）{problem.strip()}')
            acts=action.strip()
            if check and check.strip() and check.strip() not in acts:
                ver=check.strip()
                if ver.startswith('通过'):ver=ver[2:]
                acts=acts.rstrip('。；;')+'，通过'+ver
                if not acts.endswith('。'):acts+='。'
            actions.append(f'（{n}）{acts}')
        canonical=['存在问题：',*issues,'整改措施：',*actions]
        if data.get('issues_paragraphs') is not None and paragraphs(data,'issues_paragraphs')!=canonical:
            raise ValueError('issue_pairs 与 issues_paragraphs 不一致，拒绝自动猜测哪一份生效')
        result=canonical
    else:
        result=paragraphs(data,'issues_paragraphs')
    validate_issue_structure(result)
    return result

def validate_issue_structure(parts):
    """Hard gate: headings, one paragraph per numbered point, same 1..N identifiers."""
    if not isinstance(parts,list) or len(parts)<6 or len(parts)>10 or (len(parts)-2)%2:
        raise ValueError('问题整改须为2~4条：存在问题： + N条（1）… + 整改措施： + N条（1）…')
    n=(len(parts)-2)//2
    if parts[0] not in ISSUE_HEADING_OPTIONS or parts[n+1]!=REMEDY_HEADING:
        raise ValueError('问题整改须使用独立小标题“存在问题：”“整改措施：”，顺序不可颠倒')
    for i in range(1,n+1):
        a=NUMBERED_ITEM.fullmatch(parts[i]); b=NUMBERED_ITEM.fullmatch(parts[n+1+i])
        if a is None or b is None or int(a.group(1))!=i or int(b.group(1))!=i:
            raise ValueError(f'问题与整改措施第{i}项编号不一致；须各自独立成段，以（{i}）开头')
        for label,m in [('问题',a),('整改',b)]:
            if len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',m.group(2)))<MIN_ISSUE_TEXT_CHARS:
                raise ValueError(f'第{i}项{label}内容太空泛，至少{MIN_ISSUE_TEXT_CHARS}有效字符')
    return {'issue_count':n,'remedy_count':n,'paired_numbering':list(range(1,n+1))}

def is_label(text,row):
    # Different role styles are reverse-measured from the 4 uploaded samples.
    # Issue/remediation labels remain flush; sections in progress are 12pt.
    return row in (3,5) and text.strip() in ZERO_INDENT_LABELS

def indent_for(text,row):
    return 0 if is_label(text,row) else BODY_FIRST_LINE_PT_BY_ROW.get(row,24)

def set_rfonts(run, east_asia='宋体', ascii_font='Times New Roman'):
    run.font.name=ascii_font
    run.font.size=Pt(BODY_FONT_PT)
    rp=run._element.get_or_add_rPr()
    rf=rp.rFonts
    if rf is None:
        rf=OxmlElement('w:rFonts'); rp.insert(0,rf)
    for attribute,value in [('ascii',ascii_font),('hAnsi',ascii_font),('eastAsia',east_asia)]:
        rf.set(qn('w:'+attribute),value)

def append_content(p, text, body_row=None):
    if p.text.strip():
        raise ValueError('尝试写入非空的官方固定段落，已拒绝')
    # Office blank-space placeholders have 1.5 line spacing. Preserve it.
    if body_row is not None:
        p.paragraph_format.first_line_indent=Pt(indent_for(text,body_row))
    run=p.add_run(text)
    set_rfonts(run)

def fill_blank_cell(cell,text):
    if cell.text.strip():
        raise ValueError('个人信息目标单元格已有文字；禁止覆盖学校固定栏目')
    append_content(cell.paragraphs[0],text)

def write_body(cell,parts,indices,row):
    slots=[cell.paragraphs[i] for i in indices if i<len(cell.paragraphs)]
    if len(parts)>len(slots):
        raise ValueError(f'有 {len(parts)} 个正文段落，官方仅提供 {len(slots)} 个可填写占位；禁止扩展固定表格结构')
    for para,content in zip(slots,parts):
        append_content(para,content,body_row=row)
    # The numerous remaining blank lines are *fillable writing-space placeholders*
    # (NOT official labels or structural rows). Remove unused placeholders ONLY
    # inside filled regions to prevent unnecessary page 4/5 and orphan signatures.
    for para in slots[len(parts):]:
        assert not para.text.strip()
        para._element.getparent().remove(para._element)

def fill_docx(template,data,output):
    doc,lock=lock_check(template)
    if not isinstance(data,dict) or not data.get('title'):
        raise ValueError('必须提供本项目题目，禁止继承范本课题')
    if data.get('teacher_opinion_is_draft') is not True:
        raise ValueError('教师意见仅为拟稿，必须显式标注待教师审核')
    if data.get('college_opinion_paragraphs') and data.get('college_opinion_authorized') is not True:
        raise ValueError('学院意见未经授权禁止预填')
    parsed={}
    for field,_,maxn in FIELDS:
        parts=issue_paragraphs(data) if field=='issues_paragraphs' else paragraphs(data,field)
        count=count_content_chars(parts)
        if count<200:raise ValueError(f'{field} 不足200字：{count}')
        if len(parts)>maxn:raise ValueError(f'{field} 超出原占位段落数量：{maxn}')
        parsed[field]=parts
    tab=doc.tables[0]
    for field,col in [('student_name',1),('class_name',3)]:
        if data.get(field):fill_blank_cell(tab.cell(0,col),str(data[field]).strip())
    fill_blank_cell(tab.cell(1,1),str(data['title']).strip())
    if data.get('inspection_date'):
        try:dt=date.fromisoformat(str(data['inspection_date']))
        except ValueError as exc:raise ValueError('inspection_date 只接受真实 YYYY-MM-DD') from exc
        pp=doc.paragraphs[2]
        if not all(s in pp.text for s in ('年','月','日')):raise ValueError('官方日期占位不同，停止写入')
        pp.runs[-1].text=f' {dt.year}年  {dt.month}月  {dt.day}日'
    for field,row,_ in FIELDS:
        cell=tab.cell(row,0)
        all_p=cell.paragraphs
        sign_index=next((i for i,p in enumerate(all_p) if '指导教师签名' in p.text),len(all_p)) if row==4 else len(all_p)
        indices=[i for i,p in enumerate(all_p) if 0<i<sign_index and not p.text.strip()]
        write_body(cell,parsed[field],indices,row)
    if data.get('college_opinion_paragraphs'):
        cell=tab.cell(5,0)
        all_p=cell.paragraphs
        sig=next(i for i,p in enumerate(all_p) if '负责人签名' in p.text)
        parts=paragraphs(data,'college_opinion_paragraphs')
        write_body(cell,parts,[i for i,p in enumerate(all_p) if i>0 and i<sig and not p.text.strip()],5)
    out=Path(output)
    if out.resolve()==Path(template).resolve():raise ValueError('不能覆盖官方模板')
    if out.exists():raise ValueError(f'输出文件已存在：{out}（必须使用 -vN 新版本，禁止覆盖历史文件）')
    out.parent.mkdir(parents=True,exist_ok=True)
    buf=BytesIO();doc.save(buf);buf.seek(0)
    final=BytesIO()
    with ZipFile(template,'r') as base,ZipFile(buf,'r') as edited,ZipFile(final,'w') as target:
        for meta in base.infolist():
            target.writestr(meta,edited.read(meta.filename) if meta.filename=='word/document.xml' else base.read(meta.filename))
    out.write_bytes(final.getvalue())
    print(f'CREATED: {out} (official SHA256={lock["sha256"]})')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--template',default=str(DEFAULT_TEMPLATE))
    p.add_argument('--data',required=True)
    p.add_argument('--out',required=True)
    a=p.parse_args()
    try:fill_docx(a.template,json.loads(Path(a.data).read_text(encoding='utf8')),a.out)
    except (ValueError,OSError,KeyError,IndexError) as e:p.exit(2,f'ERROR: {e}\n')
