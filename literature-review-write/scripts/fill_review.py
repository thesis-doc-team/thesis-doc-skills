#!/usr/bin/env python3
"""Fill only editable zones of the supplied *actual* official Word template.

NO Document() from scratch, NO new cover table, NO table regeneration.
For this specific official template use existing cover paragraphs and existing
single 2-row table. Fail closed if a different template structure is detected.
"""
import argparse, json, re
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER, WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from template_tools import require_official_template

REF = re.compile(r'\[(?:\d+)(?:[，,\-–]\d+)*\]')
FIELD_PARA = {14:'student_name', 16:'student_id',18:'college',20:'major',
              22:'class_name',24:'instructor_name',26:'instructor_title'}
LABELS = {12:'题',14:'学生姓名',16:'学',18:'学',20:'专',22:'班',24:'指导教师',26:'职'}

def clean_after_first(p, keep=1):
    for run in p.runs[keep:]:
        run._r.getparent().remove(run._r)

def font(run, size=10.5, chinese='宋体', west='Times New Roman', underline=False):
    run.font.size = Pt(size)
    run.font.name = west
    run.font.underline = underline
    rfonts = run._r.get_or_add_rPr().rFonts
    rfonts.set(qn('w:eastAsia'), chinese)
    rfonts.set(qn('w:ascii'), west)
    rfonts.set(qn('w:hAnsi'), west)
    run.font.italic = False
    return run

def split_title(title):
    title=title.strip()
    if len(title)<10: return [title, '']
    # Only suggest splitting; agent must inspect screenshot, may supply title_lines.
    weight=lambda c: 2 if ord(c)>127 else 1
    ideal=sum(weight(c) for c in title)/2
    checkpoints=[i for i in range(1,len(title)) if title[i-1] in '的与和及' or title[i] in ' 　']
    if not checkpoints:
        checkpoints=list(range(2,len(title)-1))
    at=min(checkpoints,key=lambda i: abs(sum(weight(c) for c in title[:i])-ideal))
    return [title[:at].strip(),title[at:].strip()]

def cover_field(p, value, title=False, second=False):
    if second:
        clean_after_first(p,0)
    else:
        clean_after_first(p,1) # preserve exact original label run
    pf=p.paragraph_format
    pf.tab_stops.clear_all()
    # Both title rows must use the SAME leading non-printing tab stop.
    # Otherwise the second row draws a leader from the page left edge.
    pf.tab_stops.add_tab_stop(Pt(163),WD_TAB_ALIGNMENT.LEFT,WD_TAB_LEADER.SPACES)
    if title:
        pf.tab_stops.add_tab_stop(Pt(286.5),WD_TAB_ALIGNMENT.CENTER,WD_TAB_LEADER.LINES)
    pf.tab_stops.add_tab_stop(Pt(410),WD_TAB_ALIGNMENT.LEFT,WD_TAB_LEADER.LINES)
    # The original label and placeholder paragraphs remain, only their fillable
    # runs are changed. Tab leaders give reliably equal-width underlines.
    p.add_run('\t\t')
    if value:
        font(p.add_run(value),size=14,underline=True)
    p.add_run('\t')

def format_text(p, text, body=True, heading=False):
    pf=p.paragraph_format
    pf.space_before=Pt(0)
    pf.space_after=Pt(0)
    pf.line_spacing=1.5
    if heading:
        p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        pf.first_line_indent=Pt(0)
        pf.keep_with_next=True  # avoid orphan headings at page bottoms
    else:
        p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.first_line_indent=Pt(21) # approximately 2 characters at 10.5pt
    cursor=0
    for m in REF.finditer(text) if body else []:
        if cursor<m.start():
            r=font(p.add_run(text[cursor:m.start()])); r.bold=heading
        r=font(p.add_run(m.group()), size=10.5)
        r.font.superscript=True
        cursor=m.end()
    if cursor<len(text):
        r=font(p.add_run(text[cursor:]));r.bold=heading

def fill(template, data, out):
    doc,lock=require_official_template(template)
    if len(doc.sections)!=2 or len(doc.tables)!=1 or len(doc.tables[0].rows)!=2 or len(doc.tables[0].columns)!=1:
        raise ValueError('官方模板结构与此 Skill 映射不符；拒绝重建或强制写入')
    if len(doc.paragraphs)<27 or not all(doc.paragraphs[i].text.startswith(label)
                                         for i,label in LABELS.items()):
        raise ValueError('封面字段位置改变，需更新只填位置映射；不得猜测写入')
    table=doc.tables[0]
    fixed_instruction=table.cell(0,0).paragraphs[0].text
    teacher_label=table.cell(1,0).paragraphs[0].text
    if '2500' not in fixed_instruction or '指导教师审阅意见' not in teacher_label:
        raise ValueError('官方正文说明或教师审阅区标签不同；不擅自更改固定框架')
    lines=data.get('title_lines') or split_title(data['title'])
    if not isinstance(lines,list) or len(lines)!=2 or ''.join(x.replace(' ','') for x in lines)!=data['title'].replace(' ',''):
        raise ValueError('title_lines 必须是与课题题目一致的两个字符串（不省略字符）')
    cover_field(doc.paragraphs[12],lines[0],title=True)
    cover_field(doc.paragraphs[13],lines[1],title=True,second=True)
    for idx,key in FIELD_PARA.items():
        cover_field(doc.paragraphs[idx],str(data.get('cover',{}).get(key,'') or ''))
    # Body cell: preserve official instruction para; clear only blank fill space.
    body=table.cell(0,0)
    if any(p.text.strip() for p in body.paragraphs[1:]):
        raise ValueError('官方正文填充区不是空白；避免误删已有正文')
    for p in body.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    for sec in data['sections']:
        p=body.add_paragraph()
        format_text(p,sec['heading'],heading=True)
        if sec.get('page_break_before'):
            # Word/LO may ignore keep-next or pageBreakBefore inside a long split table row.
            # Use an explicit page-break run in this *fillable* paragraph.
            from docx.enum.text import WD_BREAK
            first_r = p.runs[0]._r
            br = p.add_run()
            br.add_break(WD_BREAK.PAGE)
            p._p.remove(br._r)
            first_r.addprevious(br._r)
        for content in sec['paragraphs']:
            kind = content.get('kind','paragraph') if isinstance(content,dict) else 'paragraph'
            value = content['text'] if isinstance(content,dict) else content
            p=body.add_paragraph();format_text(p,value,heading=(kind=='subheading'))
    p=body.add_paragraph();format_text(p,'4 参考文献',heading=True)
    for item in data['bibliography']:
        p=body.add_paragraph()
        # Bibliography numbers MUST be baseline, not superscript.
        format_text(p, f'[{item["number"]}] {item["citation"]}',body=False)
        p.paragraph_format.first_line_indent=Pt(0)
        p.paragraph_format.left_indent=Pt(0)
    # Teacher review: only replace empty placeholders before signature/date.
    cell=table.cell(1,0)
    pars=cell.paragraphs
    signatures=[p for p in pars if '指导教师（签字）' in p.text]
    if len(signatures)!=1 or not any('年' in p.text and '月' in p.text and '日' in p.text for p in pars):
        raise ValueError('教师签字日期未定位，不得修改教师审阅区框架')
    sign=signatures[0]
    for p in pars[1:pars.index(sign)]:
        if p.text.strip(): raise ValueError('教师意见空白区已有内容，禁止覆盖')
        p._p.getparent().remove(p._p)
    from docx.oxml import OxmlElement
    from docx.text.paragraph import Paragraph
    new=OxmlElement('w:p')
    sign._p.addprevious(new)
    p=Paragraph(new,cell)
    format_text(p,data['teacher_opinion'],body=False)
    # Do not set 'teacher signed / approved' metadata or insert a fake signature.
    out=Path(out)
    if out.resolve()==Path(template).resolve():
        raise ValueError('拒绝覆盖官方模板原件')
    if out.exists():
        raise ValueError('最终成品文件已存在：请分配新 vN 版本名，禁止覆盖旧成品')
    out.parent.mkdir(parents=True,exist_ok=True)
    doc.save(out)
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--template',required=True);ap.add_argument('--data',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    try:
        path=fill(a.template,json.loads(Path(a.data).read_text(encoding='utf-8')),a.out)
        print(f'FILLED: {path}')
    except (ValueError,KeyError,OSError) as e:raise SystemExit('ERROR: '+str(e))
