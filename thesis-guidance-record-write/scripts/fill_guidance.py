#!/usr/bin/env python3
"""Fill original guidance record DOCX by cloning original *row groups*; never redraw tables.
The only changed content is in designated original blanks: cover identity fields and
7 cells per 13-row record. All other text and row/cell geometry remains unchanged.
This tool drafts records: the school requires genuine teacher review/manual signing.
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import argparse, json, hashlib, re
from pathlib import Path
from copy import deepcopy
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement

HERE=Path(__file__).resolve().parents[1]
LOCK=HERE/'assets'/'template-lock.json'

# 指导内容格：官方固定行高 5312twip=265.6pt（hRule=exact），正文超出不会被撑高，
# 而是被裁切并压盖下一行（真实事故截图）。10.5pt/1.1 行距实测约合 18~19 行，硬预算取 17 行。
# 估算偏保守：全角 2 单元/半角 1 单元，首行 54 单元（21pt 缩进）、续行 60 单元。
CONTENT_LINES_BUDGET = 17
CONTENT_FIRST_UNITS = 54
CONTENT_LINE_UNITS = 60
ITEM_CHARS_SOFT = 90


def estimate_cell_lines(texts):
    """估算指导内容格渲染行数（固定行高下的防裁切硬预算）。"""
    lines = 0
    for text in texts:
        units = sum(2 if ord(ch) >= 128 else 1 for ch in str(text))
        lines += 1 if units <= CONTENT_FIRST_UNITS else 1 + -(-(units - CONTENT_FIRST_UNITS) // CONTENT_LINE_UNITS)
    return lines


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
    rPr.get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')


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
    estimated=estimate_cell_lines(content)
    if estimated>CONTENT_LINES_BUDGET:
        raise ValueError(
            f'指导内容超出单元格行预算（估算 {estimated} 行 > 上限 {CONTENT_LINES_BUDGET} 行）：'
            '官方该行行高固定，超出会被裁切并压盖下一行。指导记录是概括性文书——每条问题/意见 '
            '1~2 句（约 30~80 字），写对象与修改/验证方向即可，不写寄存器、引脚、时钟分频、'
            '波特率数值、逐条指令序列等实现细节（细节属于技术文档）；必要时减少条目或压缩措辞')
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
        run._r.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),'宋体')
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
    # 表尾 1pt 防空白页尾段：官方文档以表格收尾，末行恰达版心底线时 Word 必在表后挂一个段落
    # 标记并溢到新页——空白原件实测 5 页第 5 页、真实成品 11 页第 11 页整页空白。追加不可见
    # （行高 exact 1pt + 段落标记 1pt）空段让必居行落回末页：11 页→10 页，官方可见内容零改动。
    # 这是版面修复而非内容增写；validate_guidance 只放行这一种额外段落。
    guard=doc.add_paragraph()
    guard.paragraph_format.space_before=Pt(0)
    guard.paragraph_format.space_after=Pt(0)
    guard.paragraph_format.line_spacing=Pt(1)
    _pPr=guard._p.get_or_add_pPr()
    _rPr=OxmlElement('w:rPr')
    for _tag in ('w:sz','w:szCs'):
        _e=OxmlElement(_tag);_e.set(qn('w:val'),'2');_rPr.append(_e)
    _pPr.append(_rPr)
    doc.core_properties.title='毕业论文（设计）指导记录（待教师核实稿）'
    doc.core_properties.subject='依据技术文档生成的指导记录待审核草稿；非真实指导事实证明'
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():raise ValueError('成品路径已存在，必须新建版本，不得覆盖历史成品')
    doc.save(dst)
    print(f'CREATED: {dst} | records={len(records)} | official={src.name}')

if __name__=='__main__':main()
