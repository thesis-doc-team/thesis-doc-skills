#!/usr/bin/env python3
"""Fill original guidance record DOCX by cloning original *row groups*; never redraw tables.
The only changed content is in designated original blanks: cover identity fields and
7 cells per 13-row record. All other text and row/cell geometry remains unchanged.
This tool drafts records: the school requires genuine teacher review/manual signing.
"""
import argparse, json, hashlib, re
from pathlib import Path
from copy import deepcopy
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

HERE=Path(__file__).resolve().parents[1]
LOCK=HERE/'assets'/'template-lock.json'


def verify_source(src):
    lock=json.loads(LOCK.read_text(encoding='utf-8'))
    found=hashlib.sha256(Path(src).read_bytes()).hexdigest()
    if found!=lock['sha256']:
        raise ValueError('模板 SHA256 与内置官方模板不符：禁止用旧单元格坐标填新版；请重新审计适配')
    return lock


def set_blank(cell, text):
    """Replace only a blank editable cell, retaining its original pPr/tcPr."""
    if not text: return
    if cell.text.strip(): raise ValueError('目标字段已包含官方文字，拒绝覆盖')
    p=cell.paragraphs[0]
    for r in p.runs: r.text=''
    run=p.add_run(str(text).strip())
    run.font.name='Times New Roman'
    run.font.size=Pt(11)
    rPr=run._r.get_or_add_rPr()
    rf=rPr.rFonts
    if rf is not None: rf.set(qn('w:eastAsia'),'宋体')


def fill_cover(doc, data):
    labels={13:'title',15:'student_name',17:'student_id',19:'college',21:'major',23:'class_name',25:'advisor_name',27:'advisor_title'}
    for para_no,key in labels.items():
        value=data.get(key)
        if not value: continue
        p=doc.paragraphs[para_no]
        if '：' not in p.text: raise ValueError(f'封面字段 {key} 定位不再匹配')
        # Tail whitespace in label paragraph is a designated blank, not a fixed label.
        target=p.runs[-1]
        if target.text.strip() and not target.text.isspace() and '：' not in target.text:
            raise ValueError(f'封面 {key} 最后一个 run 已有内容，拒绝覆盖')
        target.text=re.sub(r'\s+$','',target.text) + '  '+str(value).strip()


def fill_issue_cell(cell, pairs):
    if not (1 <= len(pairs) <= 4): raise ValueError('每条记录应为 1~4 组问题与建议')
    content=['指导教师指出存在问题：']
    content.extend(f'{i}. {pair["problem"].strip()}' for i,pair in enumerate(pairs,1))
    content.append('指导教师提出修改意见：')
    content.extend(f'{i}. {pair["action"].strip()}' for i,pair in enumerate(pairs,1))
    original=cell.paragraphs
    # The editable cell in official template contains 5 placeholder paragraphs (first group)
    # or 2 blank paragraphs (second group); add only within the original editable cell.
    for p in original:
        p.clear()  # preserves w:pPr, including paragraph first-line indent
    while len(cell.paragraphs) < len(content):
        clone=deepcopy(original[-1]._p)
        cell._tc.append(clone)
    for i,txt in enumerate(content):
        p=cell.paragraphs[i]
        p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        if p.paragraph_format.first_line_indent is None:
            p.paragraph_format.first_line_indent=Pt(21)
        # Paragraph style applies ONLY in editable body, not fixed framework.
        p.paragraph_format.space_before=Pt(0)
        p.paragraph_format.space_after=Pt(0)
        p.paragraph_format.line_spacing=1.1
        run=p.add_run(txt)
        run.font.name='Times New Roman'
        run.font.size=Pt(10.5)
        run.bold=txt.startswith('指导教师')
        rf=run._r.get_or_add_rPr().rFonts
        if rf is not None:rf.set(qn('w:eastAsia'),'宋体')
    # Preserve remaining paragraphs but empty; removing them would alter more of the form.


def fill_one(table, base, data, record):
    if record.get('status')!='draft':raise ValueError('记录必须标注 status=draft，不能冒充真实指导记录')
    pairs=record.get('issue_pairs',[])
    if not pairs or any(not x.get('problem') or not x.get('action') for x in pairs):
        raise ValueError('每个问题必须有独立的可执行整改建议')
    person=data.get('student_name','')
    set_blank(table.cell(base,2),person)
    set_blank(table.cell(base,5),data.get('student_id'))
    # Actual grade/major of this person; no copy from example.
    grade=data.get('grade','')
    major=data.get('major','')
    set_blank(table.cell(base,10), ' '.join(x for x in [major,grade] if x))
    set_blank(table.cell(base+1,2),data['title'])
    # Only use dates/places with explicit provenance; never fabricate meetings.
    if record.get('date'):
        if not record.get('date_verified'): raise ValueError('指导日期未确认，不得填写')
        set_blank(table.cell(base+2,3),record['date'])
    if record.get('location'):
        if not record.get('location_verified'):raise ValueError('指导地点未确认，不得填写')
        set_blank(table.cell(base+2,9),record['location'])
    # Method and three evaluation rows intentionally remain unselected; must be marked
    # by the actual teacher per school instructions.
    fill_issue_cell(table.cell(base+5,1), pairs)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--template',required=True);ap.add_argument('--data',required=True);ap.add_argument('--out',required=True)
    args=ap.parse_args()
    verify_source(args.template)
    src=Path(args.template).resolve(); dst=Path(args.out).resolve()
    if src==dst:raise ValueError('输出不得覆盖官方模板原件')
    data=json.loads(Path(args.data).read_text(encoding='utf-8'))
    records=data.get('records',[])
    if not isinstance(records,list) or len(records)<8:
        raise ValueError('官方说明及项目约定：默认至少8次，未满足则不得出正式交付稿')
    if len(records)>60:raise ValueError('单个文档超过60次，需另行评审排版容量')
    if not data.get('title'):raise ValueError('必须提供当前真实项目题目')
    doc=Document(src)
    if len(doc.tables)!=2 or len(doc.tables[1].rows)!=26:
        raise ValueError('官方表格形态变化，禁止硬编码填充')
    fill_cover(doc,data)
    tbl=doc.tables[1]
    source_rows=[deepcopy(row._tr) for row in tbl.rows[0:13]]
    for _ in range(len(records)-2):
        for row in source_rows:
            tbl._tbl.append(deepcopy(row))
    if len(tbl.rows)!=len(records)*13:raise ValueError('记录表复制失败')
    for i,record in enumerate(records):
        fill_one(tbl,13*i,data,record)
    doc.core_properties.title='毕业论文（设计）指导记录（待教师核实稿）'
    doc.core_properties.subject='依据技术文档生成的指导记录待审核草稿；非真实指导事实证明'
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():raise ValueError('成品路径已存在，必须新建版本，不得覆盖历史成品')
    doc.save(dst)
    print(f'CREATED: {dst} | records={len(records)} | official={src.name}')

if __name__=='__main__':main()
