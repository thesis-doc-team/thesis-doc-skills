#!/usr/bin/env python3
"""原位填充官方任务书副本。只触及表内可填写单元格，不调整表格/行列/边框/页边距/附注。"""
import argparse
import json
import re
from datetime import date
from pathlib import Path
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from template_lock import verify as verify_template_lock


def font_set(run, size=10.5, bold=False):
    run.font.name = 'Times New Roman'
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), '宋体')
    run.font.size = Pt(size)
    run.bold = bold


def paragraph_style(p, *, centered=False, first_indent=False):
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.JUSTIFY
    fmt = p.paragraph_format
    fmt.left_indent = Pt(0)
    fmt.right_indent = Pt(0)
    fmt.first_line_indent = Pt(0 if centered else (21 if first_indent else 0))
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.line_spacing = 1.5
    # 防止源模板的显式 tabs 导致 WPS 中“看似居中实际偏移”
    ppr = p._p.pPr
    if ppr is not None:
        tabs = ppr.find(qn('w:tabs'))
        if tabs is not None:
            ppr.remove(tabs)


def set_value(cell, value, *, size=12):
    if not value:
        return  # 未提供个人信息：保留原官方空白内容
    if len(cell.paragraphs) != 1:
        # 官方题目单元格存在额外空段落；该区域属于可填写区域
        for p in cell.paragraphs[1:]:
            if p.text.strip():
                raise ValueError('目标单元格存在非空额外段落，拒绝覆盖')
            p._element.getparent().remove(p._element)
    p = cell.paragraphs[0]
    prior_run = next((r for r in p.runs if r.text.strip()), None)
    prior_bold = (prior_run.bold is True) if prior_run is not None else False
    prior_size = (prior_run.font.size.pt if prior_run and prior_run.font.size else size)
    if p.text.strip() and not ('年' in p.text and '月' in p.text and '周' in p.text):
        raise ValueError(f'目标单元格不是空白：{p.text[:30]}')
    p.clear()
    paragraph_style(p, centered=True)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    font_set(p.add_run(value), size=prior_size, bold=prior_bold)


def new_para_before(cell, before, content, *, indent=False):
    p = cell.add_paragraph()
    before._p.addprevious(p._p)
    paragraph_style(p, first_indent=indent)
    font_set(p.add_run(content))
    return p


def clean_empty_between(cell, start, end=None):
    paragraphs = list(cell.paragraphs)
    start_index = next(i for i, p in enumerate(paragraphs) if p._p is start._p) + 1
    end_index = next(i for i, p in enumerate(paragraphs) if p._p is end._p) if end is not None else len(paragraphs)
    for p in paragraphs[start_index:end_index]:
        if p.text.strip() == '':
            p._element.getparent().remove(p._element)


def find_head(cell, head):
    matches = [p for p in cell.paragraphs if p.text.replace(' ', '').startswith(head)]
    if len(matches) != 1:
        raise ValueError(f'官方模板缺少或重复栏目：{head}，匹配数量 {len(matches)}')
    return matches[0]


def valid_template(doc):
    if len(doc.tables) != 1 or len(doc.tables[0].rows) != 9 or len(doc.tables[0].columns) != 4:
        raise ValueError('模板并非已识别的官方任务书 9×4 主表；禁止套用硬编码行号')
    table = doc.tables[0]
    heads = [(5, '毕业论文（设计）内容：'), (6, '拟定工作进度：'),
             (6, '主要参考文献：'), (7, '任务下达人意见：'), (8, '任务接受人意见：')]
    for row, h in heads:
        find_head(table.rows[row].cells[0], h)
    return table


def date_text(data):
    keys = ('start_date', 'end_date', 'total_weeks')
    if not all(data.get(k) for k in keys):
        return ''
    a, b = date.fromisoformat(data['start_date']), date.fromisoformat(data['end_date'])
    if b <= a:
        raise ValueError('起止时间无效：结束时间早于或等于开始时间')
    return f'{a.year} 年 {a.month} 月 {a.day} 日——{b.year} 年 {b.month} 月 {b.day} 日（共 {data["total_weeks"]} 周）'


def validate_input(data):
    for key in ['title', 'thesis_content', 'schedule', 'references', 'issuer_opinion']:
        if not data.get(key):
            raise ValueError(f'缺少必要输入：{key}')
    if len(data['references']) < 10:
        raise ValueError('主要参考文献少于 10 条，不能作为合规任务书生成')
    if len(re.sub(r'\s+', '', data['issuer_opinion'])) < 50:
        raise ValueError('任务下达人意见不足 50 字')
    for r in data['references']:
        if not isinstance(r, dict) or not all(r.get(k) for k in ('citation', 'source_url', 'source_type')):
            raise ValueError('每条参考文献必须有 citation/source_url/source_type 证据字段')
        if r.get('verified') is not True:
            raise ValueError('存在尚未核验的参考文献；先核验再将 verified 设为 true')
    intervals = sorted((int(s['from_week']), int(s['to_week'])) for s in data['schedule'])
    if any(a > b for a, b in intervals):
        raise ValueError('工作进度出现起始周大于结束周')
    if 'total_weeks' in data:
        expected = list(range(1, int(data['total_weeks']) + 1))
        actual = [x for a,b in intervals for x in range(a,b+1)]
        if actual != expected:
            raise ValueError('进度周次不连续、重复或与总周数不符')


def write(data, template, output):
    validate_input(data)
    template, output = Path(template), Path(output)
    verify_template_lock(template)
    if output.exists():
        raise ValueError(f"交付文件已存在，拒绝覆盖历史成品：{output}；请使用新的 -vN 版本名")
    if template.resolve() == output.resolve():
        raise ValueError("禁止覆盖官方模板原件")
    document = Document(template)
    t = valid_template(document)
    for row, col, key in [(0, 1, 'college'), (0, 3, 'class_name'),
                          (1, 1, 'student_name'), (1, 3, 'student_id'),
                          (4, 1, 'instructor_name'), (4, 3, 'instructor_title')]:
        set_value(t.cell(row, col), data.get(key, ''))
    set_value(t.cell(2, 1), data['title'])
    set_value(t.cell(3, 1), date_text(data))
    # 写论文设计内容：保留官方栏目标题，其余空白占位段落可以重排
    content_cell = t.cell(5, 0)
    content_head = find_head(content_cell, '毕业论文（设计）内容：')
    clean_empty_between(content_cell, content_head)
    for item in data['thesis_content']:
        if not str(item).strip():
            continue
        p = content_cell.add_paragraph()
        paragraph_style(p, first_indent=True)
        font_set(p.add_run(str(item).strip()))
    # 官方“拟定工作进度”和“主要参考文献”同在 row6 合并单元格内
    mixed = t.cell(6, 0)
    sched_head, ref_head = find_head(mixed, '拟定工作进度：'), find_head(mixed, '主要参考文献：')
    clean_empty_between(mixed, sched_head, ref_head)
    clean_empty_between(mixed, ref_head)
    for item in data['schedule']:
        a, b = int(item['from_week']), int(item['to_week'])
        range_word = f'第 {a} 周' if a == b else f'第 {a}—{b} 周'
        new_para_before(mixed, ref_head, f'{range_word}：{item["task"].strip()}')
    for i, r in enumerate(data['references'], 1):
        raw = re.sub(r'^\s*\[\d+\]\s*', '', r['citation'].strip())
        p = mixed.add_paragraph()
        paragraph_style(p)
        font_set(p.add_run(f'[{i}] {raw}'))
    issuer = t.cell(7, 0)
    ih = find_head(issuer, '任务下达人意见：')
    sig = find_head(issuer, '任务下达人签名')
    clean_empty_between(issuer, ih, sig)
    new_para_before(issuer, sig, data['issuer_opinion'].strip(), indent=True)
    receiver = t.cell(8, 0)
    if data.get('receiver_opinion'):
        rh, rs = find_head(receiver, '任务接受人意见：'), find_head(receiver, '任务接收人签名')
        clean_empty_between(receiver, rh, rs)
        new_para_before(receiver, rs, data['receiver_opinion'].strip(), indent=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    if template.resolve() == output.resolve():
        raise ValueError('禁止覆盖官方模板原件；请指定不同 --out 路径')
    document.save(output)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--template', type=Path, required=True)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    src = json.loads(a.data.read_text(encoding='utf-8'))
    write(src, a.template, a.out)
    print(f'OK: {a.out}')


if __name__ == '__main__':
    main()
