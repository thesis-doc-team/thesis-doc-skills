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
    d = validate(data)
    try:
        from docx import Document
        from docx.shared import Cm, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
    except ImportError as e:
        raise RuntimeError('DOCX 生成需要 python-docx，请安装 requirements.txt 中的依赖') from e
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin, sec.bottom_margin = Cm(2.1), Cm(2.1)
    sec.left_margin, sec.right_margin = Cm(2.4), Cm(2.4)
    style = doc.styles['Normal']
    style.font.name = 'Microsoft YaHei'
    style.font.size = Pt(10.5)
    style.font.color.rgb = RGBColor(49, 65, 91)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.3
    for name, sz in [('Title', 19), ('Heading 1', 13), ('Heading 2', 11)]:
        s = doc.styles[name]
        s.font.name = 'Microsoft YaHei'
        s.font.size = Pt(sz)
        s.font.color.rgb = RGBColor(39, 75, 158)
        s.font.bold = True
        s.paragraph_format.space_before = Pt(13)
        s.paragraph_format.space_after = Pt(6)
    p = doc.add_paragraph(style='Title')
    p.add_run(d['title'])
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    doc.add_heading('项目概述', level=1)
    doc.add_paragraph(d['overview'])
    doc.add_heading('核心功能', level=1)
    for i, f in enumerate(d['features'], 1):
        p = doc.add_paragraph()
        p.paragraph_format.keep_together = True
        p.paragraph_format.space_before = Pt(7)
        r = p.add_run(f'{i:02d}  {f["name"]}')
        r.bold = True
        r.font.color.rgb = RGBColor(37, 80, 174)
        desc = doc.add_paragraph(f['description'])
        desc.paragraph_format.keep_together = True
        desc.paragraph_format.left_indent = Cm(0.65)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run('项目概览')
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
