#!/usr/bin/env python3
"""Static checks for an evidence-grounded Markdown technical document.

Only checks form, not factual validity. No third-party packages needed.
Usage: python scripts/check_markdown.py document.md
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')
import json
import re
import sys
from collections import Counter
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LINK = re.compile(r"\[[^\]]+\]\(#([^)]+)\)")
NUM_H2 = re.compile(r"^(\d+)\.\s+(.+)$")
NUM_H3 = re.compile(r"^(\d+)\.(\d+)\s+(.+)$")
PLACEHOLDERS = re.compile(r"【(?:项目名称|核心技术一|核心技术二|请填写|待填|真实背景|实际资料路径)[^】]*】")

# The technical document must not include stand-alone critique/roadmap sections.
# Operational error-handling belongs within the relevant implementation chapter.
FORBIDDEN_SECTION = re.compile(
    r"(?:已知问题|存在的问题|问题与(?:改进|优化|建议)|问题分析与改进|不足与(?:改进|优化)|"
    r"改进建议|改进方向|优化建议|优化方向|风险与对策|风险分析|风险评估|"
    r"未来展望|技术展望|后续规划|后续计划|升级建议|升级计划|技术演进|未来工作|发展规划)"
)



def slug(text):
    # Approximation of common GitHub Markdown heading slugs.
    text = re.sub(r"<[^>]*>", "", text).lower().strip()
    text = re.sub(r"[`*_~]", "", text)
    text = "".join(c for c in text if c.isalnum() or c in " -_")
    return re.sub(r"\s+", "-", text)


def check(path):
    doc = Path(path).read_text(encoding="utf-8-sig")
    lines = doc.splitlines()
    error, warning = [], []
    headings, links, code_blocks = [], [], []
    used_slugs = Counter()
    seen_tables = 0
    fence = None
    start = None
    code = []
    in_frontmatter = bool(lines and lines[0].strip() == "---")
    frontmatter_end = False
    for number, line in enumerate(lines, 1):
        if in_frontmatter and not frontmatter_end:
            if number > 1 and line.strip() == "---":
                frontmatter_end = True
            continue
        m = re.match(r"^\s*(`{3,}|~{3,})([^`]*)$", line)
        if m:
            token = m.group(1)
            if fence is None:
                fence = token
                start = number
                lang = m.group(2).strip().split(None, 1)[0].lower() if m.group(2).strip() else ""
                code = []
            elif token[0] == fence[0] and len(token) >= len(fence):
                code_blocks.append((start, lang, "\n".join(code)))
                fence, start = None, None
            else:
                code.append(line)
            continue
        if fence is not None:
            code.append(line)
            continue
        h = HEADING.match(line)
        if h:
            level, title = len(h.group(1)), h.group(2)
            if level >= 2 and FORBIDDEN_SECTION.search(title):
                error.append(f"第 {number} 行：检测到越界章节：{title}")
            headings.append((number, level, title))
            base = slug(title)
            used_slugs[base] += 1
            effective = base if used_slugs[base] == 1 else f"{base}-{used_slugs[base]-1}"
            headings[-1] += (effective,)
        links.extend((number, x) for x in LINK.findall(line))
        if line.startswith("|") and re.match(r"^\|[\s:|-]+\|\s*$", line):
            seen_tables += 1
        if PLACEHOLDERS.search(line):
            warning.append(f"第 {number} 行：可能残留模板占位符")
    if fence is not None:
        error.append(f"第 {start} 行：代码围栏未闭合")
    for start, lang, block in code_blocks:
        if lang == "json":
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                error.append(f"第 {start} 行：JSON 示例不能解析：{exc.msg} (行 {exc.lineno})")
    titles = {h[3] for h in headings}
    for number, anchor in links:
        if anchor not in titles:
            warning.append(f"第 {number} 行：内部锚点 #{anchor} 未找到匹配标题")
    h1s = [h for h in headings if h[1] == 1]
    if len(h1s) != 1:
        warning.append(f"H1 标题数量为 {len(h1s)}，建议恰好 1 个")
    last_h2 = 0
    h2_ids = []
    for number, level, title, _ in headings:
        if level == 2 and title != "目录":
            m = NUM_H2.match(title)
            if not m:
                warning.append(f"第 {number} 行：H2 未采用数字章编号：{title}")
                continue
            idx = int(m.group(1))
            h2_ids.append(idx)
            if idx != last_h2 + 1:
                warning.append(f"第 {number} 行：章节编号 {idx} 不连续（前一章 {last_h2}）")
            last_h2 = idx
        if level == 3:
            m = NUM_H3.match(title)
            if not m:
                warning.append(f"第 {number} 行：H3 未采用 x.y 编号：{title}")
            elif int(m.group(1)) != last_h2:
                warning.append(f"第 {number} 行：小节 {title} 与当前章 {last_h2} 不一致")
    if not h2_ids:
        warning.append("未检测到编号主章节")
    # Mandatory diagrams: HTML is derived from this MD — an MD without Mermaid
    # sources yields an HTML without figures/SVG at all.  Hard gate (ERROR),
    # so publish.py refuses to enter the HTML stage until diagrams exist.
    mermaid_starts = [start for start, lang, _ in code_blocks if lang == "mermaid"]
    if not mermaid_starts:
        error.append("MD 未包含任何 Mermaid 图：架构与关键流程必须以 ```mermaid 图表达（强制），无图 MD 不得进入 HTML 阶段")
    h2_marks = [(number, title) for number, level, title, _ in headings if level == 2 and title != "目录"]
    def chapter_of(line_no):
        current = None
        for mark_no, mark_title in h2_marks:
            if mark_no <= line_no:
                current = mark_title
            else:
                break
        return current
    per_chapter = Counter(chapter_of(s) for s in mermaid_starts)
    for mark_no, mark_title in h2_marks:
        if re.search(r"总体架构|关键流程", mark_title) and not per_chapter[mark_title]:
            error.append(f"第 {mark_no} 行：章节「{mark_title}」必须包含至少 1 幅 Mermaid 图（强制），文字描述不能替代图")
    print(f"FILE  {path}")
    print(f"STATS 行数={len(lines)} H1={len(h1s)} H2={sum(h[1]==2 for h in headings)} "
          f"H3={sum(h[1]==3 for h in headings)} 代码块={len(code_blocks)} "
          f"Mermaid={sum(lang=='mermaid' for _,lang,_ in code_blocks)} "
          f"JSON={sum(lang=='json' for _,lang,_ in code_blocks)} 表格≈{seen_tables}")
    print(f"RESULT ERROR={len(error)} WARNING={len(warning)}")
    for issue in error:
        print("ERROR  " + issue)
    for issue in warning:
        print("WARN   " + issue)
    print("NOTE   事实真实性、语义矛盾及 Mermaid 可渲染性仍须人工复核。")
    return 1 if error else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_markdown.py <document.md>", file=sys.stderr)
        sys.exit(2)
    try:
        sys.exit(check(sys.argv[1]))
    except (OSError, UnicodeError) as exc:
        print(f"ERROR  无法读取文件：{exc}", file=sys.stderr)
        sys.exit(2)
