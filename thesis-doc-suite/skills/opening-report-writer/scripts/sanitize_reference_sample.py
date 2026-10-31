#!/usr/bin/env python3
"""Create a style-preserving, privacy-scrubbed *reference sample* DOCX.

NEVER writes to the official template, and never packages the original personal-data source.
This utility is for maintainers to refresh example assets from a user-authorized sample.
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

COVER = {
    '题目': '基于嵌入式平台的智能交互终端系统设计与实现',
    '学生姓名': '（已匿名）',
    '学号': '（已匿名）',
    '学院': '（已匿名）',
    '专业': '（已匿名）',
    '班级': '（已匿名）',
    '指导教师': '（已匿名）',
    '职称': '（已匿名）',
    '起止时间': '（以实际任务书为准）',
}
# These are exemplar topic terms, NOT sources for any new project.
GENERALIZE = [
    (r'基于\s*树莓派\s*4\s*的\s*智能交互镜(?:的)?系统设计与实现', '基于嵌入式平台的智能交互终端系统设计与实现'),
    (r'Raspberry\s*Pi\s*4\s*Model\s*B', '通用嵌入式开发板'),
    (r'树莓派\s*4\s*B?', '嵌入式开发板'),
    (r'树莓派', '嵌入式平台'),
    (r'ReSpeaker\s*4-Mic', '通用麦克风阵列'),
    (r'ReSpeaker', '通用麦克风阵列'),
    (r'智能交互镜', '智能交互终端'),
    (r'智能魔镜', '智能终端'),
]
EXPECTED_COVER = ('学生姓名', '学号', '学院', '专业', '班级', '指导教师', '职称')

def replace_across_runs(p, pattern: str, subst: str) -> None:
    """Replace spans even if a Word phrase crosses multiple runs; preserve run properties elsewhere."""
    rs = list(p.runs)
    if not rs: return
    full = ''.join(r.text for r in rs)
    matches = list(re.finditer(pattern, full, re.I))
    if not matches: return
    for m in reversed(matches):
        s, e = m.span()
        offsets, pos = [], 0
        for r in rs:
            offsets.append((pos, pos+len(r.text)))
            pos += len(r.text)
        idxs = [i for i, (start, end) in enumerate(offsets) if start < e and end > s]
        if not idxs: continue
        first, last = idxs[0], idxs[-1]
        fstart, _ = offsets[first]
        _, lend = offsets[last]
        pre = rs[first].text[:s-fstart]
        post = rs[last].text[e-offsets[last][0]:]
        if first == last:
            rs[first].text = pre + subst + post
        else:
            rs[first].text = pre + subst
            for j in range(first+1,last): rs[j].text = ''
            rs[last].text = post

def replace_label_value(p, value):
    label_run = p.runs[0] if p.runs else p.add_run()
    label = label_run.text.split('：')[0] + '：'
    label_run.text = label
    for r in list(p.runs)[1:]: r.text = ''
    r = p.add_run('  ' + value)
    r.underline = True

def redact(source: Path, destination: Path) -> None:
    src = Document(source)
    # De-identify all cover values, retaining the fixed cover labels.
    for i, p in enumerate(src.paragraphs):
        plain = p.text.strip()
        if plain.startswith('题') and '目：' in plain:
            replace_label_value(p, COVER['题目'])
            if i+1 < len(src.paragraphs):
                # Original title is broken across two lines. Clear remaining identifying phrase.
                q = src.paragraphs[i+1]
                for r in q.runs: r.text = ''
        for field, replacement in COVER.items():
            if field == '题目': continue
            pattern = re.sub(r'\s+',r'\\s*',field)
            if plain.replace(' ','').startswith(field+'：'):
                replace_label_value(p, replacement)
                break
    body_cell=src.tables[0].cell(0,0)
    for p in body_cell.paragraphs:
        # Preserve reference bibliography titles faithfully; they are NOT approved for reuse.
        for pattern, sub in GENERALIZE:
            replace_across_runs(p,pattern,sub)
    # A visible usage warning in the sample itself: not part of official template.
    first=body_cell.paragraphs[0]
    notice=first.insert_paragraph_before('【脱敏写作范本｜非官方模板｜只学习写法和结构；文献、数字、项目事实必须按新课题重新核验，禁止直接复制。】')
    notice.alignment=WD_ALIGN_PARAGRAPH.LEFT
    notice.paragraph_format.space_after=Pt(8)
    for r in notice.runs:
        r.bold=True
        r.font.size=Pt(10.5)
    src.core_properties.author = '匿名写作示例'
    src.core_properties.last_modified_by = 'opening-report-writer'
    src.core_properties.title = '毕业设计开题报告脱敏参考范本（非官方模板）'
    src.core_properties.subject = '仅供语言组织与层次分析；不能作为技术事实或文献来源'
    src.core_properties.keywords = 'deidentified, example, nonofficial'
    destination.parent.mkdir(parents=True,exist_ok=True)
    src.save(destination)
    verify(destination)

def verify(path: Path) -> None:
    from zipfile import ZipFile
    doc=Document(path)
    plain='\n'.join([p.text for p in doc.paragraphs]+[p.text for t in doc.tables for row in t.rows for cell in row.cells for p in cell.paragraphs])
    assert '【脱敏写作范本' in plain
    for key in EXPECTED_COVER:
        rows = [p.text.replace(' ','') for p in doc.paragraphs if p.text.replace(' ','').startswith(key+'：')]
        assert rows and '（已匿名）' in rows[0], f'cover not anonymized: {key}'
    assert not re.search(r'(?<!\d)(?:1[3-9]\d{9}|\d{17}[\dXx])(?!\d)',plain), 'phone or ID pattern remains'
    assert not re.search(r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}',plain), 'email remains'
    assert re.search(r'1\s*课题来源|1\s*课题研究立项依据',plain)
    assert '7 参考文献' in plain or '7 主要参考文献' in plain
    assert len(doc.tables)==1 and len(doc.tables[0].rows)==2
    with ZipFile(path) as z:
        xml='\n'.join(z.read(n).decode('utf-8','ignore') for n in z.namelist() if n.endswith(('.xml','.rels')))
        assert doc.core_properties.author == '匿名写作示例'
        assert doc.core_properties.last_modified_by == 'opening-report-writer'
        assert '基于树莓派4的智能交互镜' not in xml
    print('OK: sanitized example; cover IDs redacted, meta scrubbed, structure preserved')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('source',type=Path)
    ap.add_argument('target',type=Path)
    a=ap.parse_args()
    redact(a.source,a.target)
if __name__=='__main__':main()
