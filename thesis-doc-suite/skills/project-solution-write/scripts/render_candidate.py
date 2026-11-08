#!/usr/bin/env python3
"""候选项目单一事实源 JSON -> MD / DOCX / HTML。只写名称、概述、功能。"""
from __future__ import annotations
import argparse
import html
import json
import re
from pathlib import Path

HTML_TEMPLATE = Path(__file__).resolve().parents[1] / 'templates' / 'topic-candidate.html'
FORBIDDEN = re.compile(r'推荐理由|适合人群|难度评分|硬件引脚|GPIO|工程实施交付说明|后续改进建议|收费说明|开发步骤|技术选型比较', re.I)


def validate(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError('候选项目必须为 JSON 对象')
    title = data.get('title')
    overview = data.get('overview')
    features = data.get('features')
    if not isinstance(title, str) or not 4 <= len(title.strip()) <= 120:
        raise ValueError('title 不能为空，长度为 4-120 字符')
    if not isinstance(overview, str) or not 15 <= len(overview.strip()) <= 1500:
        raise ValueError('overview 须说明项目用途与工作概念')
    if not isinstance(features, list) or not 2 <= len(features) <= 15:
        raise ValueError('features 必须含 2-15 个核心功能')
    for field, value in [('title',title),('overview',overview)]:
        if re.search(r'<\s*(?:script|iframe|object|style)|```|\{\{',value,re.I):
            raise ValueError(f'{field} 包含不允许的 HTML/代码标记')
    if '\n' in title or '\r' in title:
        raise ValueError('项目标题不能换行')
    clean = []
    seen = set()
    for item in features:
        if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not isinstance(item.get('description'), str):
            raise ValueError('每个功能必须包含 name 和 description 字符串')
        name, desc = item['name'].strip(), item['description'].strip()
        if not name or len(desc) < 6:
            raise ValueError('功能标题不能为空，功能描述应具体而非只有名称')
        if '\n' in name or '\r' in name or re.search(r'<\s*(?:script|iframe|object|style)|```|\{\{|(?m:^\s*#{1,6}\s)',desc,re.I):
            raise ValueError('功能名称或描述含不允许的标记')
        if name in seen:
            raise ValueError('同一项目不能有重复功能名')
        seen.add(name)
        clean.append({'name': name, 'description': desc})
    # Do not over-reject a project title containing a technical noun; reject forbidden sections by explicit keyed fields.
    extra = set(data) - {'title', 'overview', 'features', 'signature', 'constraints', 'tags'}
    if extra:
        raise ValueError('候选内容只能有名称、概述和核心功能，发现无关字段: ' + str(sorted(extra)))
    if FORBIDDEN.search(overview) or any(FORBIDDEN.search(i['description']) for i in clean):
        raise ValueError('推荐阶段禁止写实施/销售/评分/建议类内容')
    return {'title': title.strip(), 'overview': overview.strip(), 'features': clean}


def make_markdown(data: dict) -> str:
    d = validate(data)
    lines = [f"# {d['title']}", '', '## 项目概述', '', d['overview'], '', '## 核心功能', '']
    lines += [f"### {f['name']}\n\n{f['description']}\n" for f in d['features']]
    return '\n'.join(lines).rstrip() + '\n'


def make_html(data: dict) -> str:
    d = validate(data)
    path = HTML_TEMPLATE
    template = path.read_text(encoding='utf-8')
    tiles = []
    for i, f in enumerate(d['features'], 1):
        tiles.append(f'<article class="feature"><span class="feature-n">{i:02d}</span><h3>{html.escape(f["name"])}</h3><p>{html.escape(f["description"])}</p></article>')
    replacements = {
        '{{TITLE}}': html.escape(d['title']),
        '{{OVERVIEW}}': html.escape(d['overview']),
        '{{FEATURES}}': '\n'.join(tiles),
        '{{FEATURE_COUNT}}': str(len(d['features'])),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def make_docx(data: dict, out: Path) -> None:
    """按 C 版杂志编辑风格生成候选项目概览 DOCX。

    版式规格来自用户确认的 `方案C_杂志编辑版.docx`：A4、Noto Serif/Sans、
    暖橙与奶油底、2 列概述条、3 列功能表、底部橙色页脚。支持 3–15 条功能
    与长短不一的标题/概述/描述；功能行 cantSplit，内容多时自然分页。
    """
    d = validate(data)
    try:
        from docx import Document
        from docx.shared import Cm, Pt, RGBColor, Twips
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
    except ImportError as e:
        raise RuntimeError('DOCX 生成需要 python-docx，请安装 requirements.txt 中的依赖') from e

    SERIF = 'Noto Serif CJK SC'
    SANS = 'Noto Sans CJK SC'
    ACCENT = 'B15A36'
    ACCENT_2 = 'BA754D'
    BAR = 'BC754D'
    CREAM = 'FAF6F0'
    INK = '23302E'
    SECTION_INK = '25342D'
    LABEL = '8D4E30'
    BODY = '354541'
    FEATURE_TITLE = '293C37'
    FEATURE_DESC = '56635F'
    RULE = 'E4DAD0'
    FOOTER_MUTED = '64748B'

    def set_run(run, font_name, size_pt, color_hex, bold=False):
        run.font.name = font_name
        run.font.size = Pt(size_pt)
        run.font.bold = bold
        run.font.italic = False
        run.font.color.rgb = RGBColor.from_string(color_hex)
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = OxmlElement('w:rFonts')
            rPr.append(rFonts)
        for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
            rFonts.set(qn(attr), font_name)

    def set_para(p, before=0, after=0, line=1.25, align=None, keep_next=False):
        pf = p.paragraph_format
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.line_spacing = line
        if align is not None:
            pf.alignment = align
        pf.keep_with_next = keep_next

    def shade(cell, fill):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = tcPr.find(qn('w:shd'))
        if shd is None:
            shd = OxmlElement('w:shd')
            tcPr.append(shd)
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), fill)

    def cell_margins(cell, top, start, bottom, end):
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = tcPr.find(qn('w:tcMar'))
        if tcMar is not None:
            tcPr.remove(tcMar)
        tcMar = OxmlElement('w:tcMar')
        for tag, value in (('top', top), ('start', start), ('bottom', bottom), ('end', end)):
            el = OxmlElement('w:' + tag)
            el.set(qn('w:w'), str(value))
            el.set(qn('w:type'), 'dxa')
            tcMar.append(el)
        tcPr.append(tcMar)

    def bottom_rule(cell, color, size):
        tcPr = cell._tc.get_or_add_tcPr()
        old = tcPr.find(qn('w:tcBorders'))
        if old is not None:
            tcPr.remove(old)
        borders = OxmlElement('w:tcBorders')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), str(size))
        bottom.set(qn('w:space'), '0')
        bottom.set(qn('w:color'), color)
        borders.append(bottom)
        tcPr.append(borders)

    def no_table_borders(table):
        tblPr = table._tbl.tblPr
        old = tblPr.find(qn('w:tblBorders'))
        if old is not None:
            tblPr.remove(old)
        borders = OxmlElement('w:tblBorders')
        for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            el = OxmlElement('w:' + side)
            el.set(qn('w:val'), 'nil')
            borders.append(el)
        look = tblPr.find(qn('w:tblLook'))
        if look is not None:
            look.addprevious(borders)
        else:
            tblPr.append(borders)

    def fixed_layout(table):
        tblPr = table._tbl.tblPr
        old = tblPr.find(qn('w:tblLayout'))
        if old is not None:
            tblPr.remove(old)
        layout = OxmlElement('w:tblLayout')
        layout.set(qn('w:type'), 'fixed')
        look = tblPr.find(qn('w:tblLook'))
        if look is not None:
            look.addprevious(layout)
        else:
            tblPr.append(layout)

    def cant_split(row):
        trPr = row._tr.get_or_add_trPr()
        if trPr.find(qn('w:cantSplit')) is None:
            trPr.append(OxmlElement('w:cantSplit'))

    def top_rule(p, color, size):
        pPr = p._p.get_or_add_pPr()
        pBdr = pPr.find(qn('w:pBdr'))
        if pBdr is None:
            pBdr = OxmlElement('w:pBdr')
            pPr.append(pBdr)
        top = OxmlElement('w:top')
        top.set(qn('w:val'), 'single')
        top.set(qn('w:sz'), str(size))
        top.set(qn('w:space'), '0')
        top.set(qn('w:color'), color)
        pBdr.append(top)

    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(2.0), Cm(1.5)
    section.left_margin, section.right_margin = Cm(2.0), Cm(1.9)
    section.header_distance, section.footer_distance = Cm(0.7), Cm(0.8)
    sectPr = section._sectPr
    old_grid = sectPr.find(qn('w:docGrid'))
    if old_grid is not None:
        sectPr.remove(old_grid)
    grid = OxmlElement('w:docGrid')
    grid.set(qn('w:linePitch'), '360')
    sectPr.append(grid)

    normal = doc.styles['Normal']
    normal.font.name = SANS
    normal.font.size = Pt(10)
    normal.font.color.rgb = RGBColor.from_string(BODY)
    normal_rPr = normal.element.get_or_add_rPr()
    normal_fonts = normal_rPr.find(qn('w:rFonts'))
    if normal_fonts is None:
        normal_fonts = OxmlElement('w:rFonts')
        normal_rPr.append(normal_fonts)
    for attr in ('w:ascii', 'w:hAnsi', 'w:eastAsia', 'w:cs'):
        normal_fonts.set(qn(attr), SANS)

    # 顶部小标 + 项目名称
    p = doc.add_paragraph()
    set_para(p, 0, 7, 1.25, keep_next=True)
    set_run(p.add_run('P R O J E C T    O V E R V I E W'), SANS, 8.5, ACCENT, True)

    p = doc.add_paragraph()
    set_para(p, 0, 13, 1.36, keep_next=True)
    set_run(p.add_run(d['title']), SERIF, 21, INK, True)

    # 项目概述：左侧暖橙竖条 + 右侧奶油底
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    fixed_layout(table)
    no_table_borders(table)
    widths = (227, 9468)
    for i, w in enumerate(widths):
        table.columns[i].width = Twips(w)
    left, right = table.rows[0].cells
    left.width, right.width = Twips(widths[0]), Twips(widths[1])
    shade(left, BAR)
    shade(right, CREAM)
    cell_margins(left, 0, 0, 0, 0)
    cell_margins(right, 180, 245, 205, 230)
    set_para(left.paragraphs[0], 0, 0, 1.2)

    label_p = right.paragraphs[0]
    set_para(label_p, 0, 6, 1.1)
    set_run(label_p.add_run('项目概述'), SANS, 10.5, LABEL, True)
    body_p = right.add_paragraph()
    set_para(body_p, 0, 0, 1.558)
    set_run(body_p.add_run(d['overview']), SANS, 10, BODY, False)

    # 章节标题
    p = doc.add_paragraph()
    set_para(p, 15, 10, 1.25, keep_next=True)
    set_run(p.add_run('核心功能'), SERIF, 13, SECTION_INK, True)

    # 三列功能表：编号 / 功能名 / 功能描述
    features = d['features']
    table = doc.add_table(rows=len(features), cols=3)
    table.autofit = False
    fixed_layout(table)
    no_table_borders(table)
    widths = (907, 2098, 6690)
    for i, w in enumerate(widths):
        table.columns[i].width = Twips(w)
    for ri, feature in enumerate(features):
        row = table.rows[ri]
        cant_split(row)
        for ci, w in enumerate(widths):
            cell = row.cells[ci]
            cell.width = Twips(w)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            cell_margins(cell, 200, 70, 190, 65)
            bottom_rule(cell, RULE, 5)
        num_p = row.cells[0].paragraphs[0]
        set_para(num_p, 0, 0, 1.2)
        set_run(num_p.add_run(f'{ri + 1:02d}'), SERIF, 12, ACCENT_2, True)
        title_p = row.cells[1].paragraphs[0]
        set_para(title_p, 0, 0, 1.2)
        set_run(title_p.add_run(feature['name']), SANS, 10, FEATURE_TITLE, True)
        desc_p = row.cells[2].paragraphs[0]
        set_para(desc_p, 0, 0, 1.5)
        set_run(desc_p.add_run(feature['description']), SANS, 9.5, FEATURE_DESC, False)

    # 页脚：橙色上分隔线 + 右对齐小字
    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    set_para(fp, 0, 0, 1.0, align=WD_ALIGN_PARAGRAPH.RIGHT)
    top_rule(fp, ACCENT_2, 6)
    set_run(fp.add_run('PROJECT OVERVIEW'), SANS, 7.5, ACCENT_2, True)
    set_run(fp.add_run('   · 项目概览'), SANS, 7.5, FOOTER_MUTED, False)

    doc.core_properties.title = d['title']
    doc.core_properties.subject = '项目名称、概述与核心功能'
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)


def render(data: dict, folder: Path, stem: str = '项目概览') -> list[str]:
    d = validate(data)
    folder.mkdir(parents=True, exist_ok=True)
    targets = [folder / (stem + ext) for ext in ('.md', '.docx', '.html')]
    if any(t.exists() for t in targets):
        raise FileExistsError('版本文件已存在，拒绝覆盖')
    try:
        targets[0].write_text(make_markdown(d), encoding='utf-8')
        make_docx(d, targets[1])
        targets[2].write_text(make_html(d), encoding='utf-8')
        verify_triplet(targets)
    except Exception:
        for t in targets:
            t.unlink(missing_ok=True)
        raise
    return [str(t) for t in targets]


def verify_triplet(targets: list[Path]) -> None:
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET
    md = targets[0].read_text('utf-8')
    ht = targets[2].read_text('utf-8')
    if 'http://cdn' in ht.lower() or '<script src=' in ht.lower() or '{{' in ht:
        raise ValueError('HTML 必须离线且模板变量全部替换')
    with ZipFile(targets[1]) as z:
        docxml = z.read('word/document.xml')
        root = ET.fromstring(docxml)
        texts = [e.text or '' for e in root.iter() if e.tag.endswith('}t')]
        flat = ''.join(texts)
    for line in md.splitlines():
        # each description/title should survive in both other outputs
        val = re.sub(r'^#{1,3}\s*', '', line).strip()
        if len(val) > 4 and val not in flat:
            raise ValueError('DOCX 文本不一致: ' + val[:35])
        if len(val) > 4 and html.escape(val) not in ht:
            raise ValueError('HTML 文本不一致: ' + val[:35])


def main():
    ap = argparse.ArgumentParser(description='独立生成候选项目 MD DOCX HTML')
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--out-dir', type=Path, required=True)
    args = ap.parse_args()
    info = json.loads(args.input.read_text('utf-8'))
    print(json.dumps({'files': render(info, args.out_dir)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
