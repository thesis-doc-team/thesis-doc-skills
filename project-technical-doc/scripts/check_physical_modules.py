#!/usr/bin/env python3
"""Validate physical-modules.json against the generated technical Markdown (contract v1).

The manifest must sit next to the technical document with the fixed name
physical-modules.json (no version suffix). It lists only physically embodied
modules (sensors, actuators, displays, inputs, communication radios...) so the
user can map hardware photos to the 「模块详解」chapter sections.  v5.3 accepts
an individual code in the section body (or elsewhere in the document with an
explicit `section` mapping), because functional sections like 「环境监测模块」
may contain D1/SHT40/火焰/土壤 sub-modules.

Usage: python scripts/check_physical_modules.py <document.md> [--json <manifest>] [--report <path>]
Exit codes: 0 PASS/WARN (warnings are non-blocking), 1 FAIL, 2 unreadable input.
"""

import sys as _sys
if hasattr(_sys.stdout,'reconfigure'):_sys.stdout.reconfigure(encoding='utf-8',errors='replace')
if hasattr(_sys.stderr,'reconfigure'):_sys.stderr.reconfigure(encoding='utf-8',errors='replace')

import argparse
import json
import re
import sys
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
CATEGORIES = ('sensor', 'actuator', 'display', 'input', 'communication', 'other')
# 软件模块命名启发式（只警告不阻断；"不要一巴掌打死"）：全小写下划线名、main、Warn
SOFTWARE_NAME = re.compile(r'^(?:main|warn)$', re.I)
SOFTWARE_UNDERSCORE = re.compile(r'^[a-z][a-z0-9]*_[a-z0-9_]+$')
ABS_PATH = re.compile(r'^(?:[A-Za-z]:[\\/]|/)')


def module_sections(lines):
    """「模块详解」章内的 H3 小节 [(行号, 标题)]；文档无该章返回 None。"""
    marks = [(i, len(m.group(1)), m.group(2)) for i, line in enumerate(lines, 1)
             if (m := HEADING.match(line))]
    start = next((idx for idx, (_, level, title) in enumerate(marks)
                  if level == 2 and '模块详解' in title), None)
    if start is None:
        return None
    sections = []
    for line_no, level, title in marks[start + 1:]:
        if level <= 2:
            break
        if level == 3:
            sections.append((line_no, title))
    return sections


def code_pattern(code):
    """词边界匹配：D1 不得命中 D10 / MD1，OLED 不得命中 OLEDX。"""
    return re.compile(r'(?<![A-Za-z0-9_])' + re.escape(code) + r'(?![A-Za-z0-9_])', re.I)


def section_ranges(lines):
    """[(line_no, title, body)] for H3 sections under 模块详解."""
    marks = [(i + 1, len(m.group(1)), m.group(2).strip())
             for i, line in enumerate(lines) if (m := HEADING.match(line))]
    start = next((idx for idx, (_, level, title) in enumerate(marks)
                  if level == 2 and '模块详解' in title), None)
    if start is None:
        return None
    ranges = []
    for pos in range(start + 1, len(marks)):
        line_no, level, title = marks[pos]
        if level <= 2:
            break
        if level != 3:
            continue
        end = len(lines) + 1
        for next_no, next_level, _ in marks[pos + 1:]:
            if next_level <= 3:
                end = next_no
                break
        body = "\n".join(lines[line_no:end - 1])
        ranges.append((line_no, title, body))
    return ranges


def check(markdown, manifest=None):
    md = Path(markdown)
    js = Path(manifest) if manifest else md.parent / 'physical-modules.json'
    errors, warnings = [], []
    report = {'status': 'FAIL', 'markdown': str(md), 'manifest': str(js),
              'modules': 0, 'errors': errors, 'warnings': warnings}
    if not js.is_file():
        errors.append(f'缺少实物模块清单 {js.name}：必须与 {md.name} 同级交付、定名不加版本号（项目无实物模块也要写 modules: []，字段不得省略）')
        return report
    try:
        data = json.loads(js.read_text('utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f'{js.name} 无法解析：{exc}')
        return report
    if not isinstance(data, dict):
        errors.append(f'{js.name} 顶层必须是 JSON 对象')
        return report
    if data.get('schema_version') != 1:
        errors.append(f"schema_version 必须为 1（当前 {data.get('schema_version')!r}）")
    if data.get('generated_by') != 'project-technical-doc':
        errors.append(f"generated_by 必须为 project-technical-doc（当前 {data.get('generated_by')!r}）")
    modules = data.get('modules')
    if not isinstance(modules, list):
        errors.append('modules 必须是数组（无实物模块时写 []，字段不得省略）')
        return report
    report['modules'] = len(modules)

    lines = md.read_text('utf-8-sig').splitlines()
    sections = module_sections(lines)
    ranges = section_ranges(lines) or []
    if sections is None:
        if modules:
            errors.append('未找到「模块详解」章：code 必须与正文该章的小节标题/正文一致，否则无法把照片对应到章节')
        sections = []
    seen, matched = {}, []
    for index, mod in enumerate(modules, 1):
        if not isinstance(mod, dict):
            errors.append(f'第 {index} 条必须是 JSON 对象')
            continue
        label = f'第 {index} 条'
        for key in ('code', 'name', 'hardware'):
            value = mod.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f'{label}缺少必填字段 {key}（非空字符串）')
        code = mod.get('code')
        if not isinstance(code, str) or not code.strip():
            continue
        code = code.strip()
        label = f'模块 {code}'
        if code.casefold() in seen:
            errors.append(f'{label}的 code 与前面条目重复：全文件唯一')
        seen[code.casefold()] = True
        if 'category' in mod and mod.get('category') not in CATEGORIES:
            warnings.append(f"{label}的 category={mod.get('category')!r} 不在建议集合 {' / '.join(CATEGORIES)} 内（建议值，不阻断）")
        if SOFTWARE_NAME.match(code) or SOFTWARE_UNDERSCORE.match(code):
            warnings.append(f'{label} 名称形似软件模块（全小写下划线 / main / warn）：请人工确认其具备实物形态；通信抽象层、纯逻辑、主程序不得列入')
        src = mod.get('source_files')
        if 'source_files' in mod:
            if not isinstance(src, list):
                errors.append(f'{label}的 source_files 必须是文件名数组')
                src = []
            for name in src:
                if not isinstance(name, str) or not name.strip():
                    errors.append(f'{label}的 source_files 只能包含非空文件名')
                elif '/' in name or '\\' in name:
                    errors.append(f'{label}的 source_files 只写裸文件名（不写目录/路径）：{name}')
        for key in ('pins', 'note'):
            if key in mod and not isinstance(mod.get(key), str):
                errors.append(f'{label}的 {key} 必须是字符串')
        for key in ('name', 'hardware', 'pins', 'note'):
            value = mod.get(key)
            if not isinstance(value, str):
                continue
            lowered = value.lower()
            if 'data:' in lowered or ';base64,' in lowered:
                errors.append(f'{label}的 {key} 含内嵌图片/base64：只给元数据，不输出图片')
            elif ABS_PATH.match(value.strip()):
                errors.append(f'{label}的 {key} 含绝对路径：只给元数据，不写路径引用')
        pattern = code_pattern(code)
        declared_section = mod.get('section')
        if 'section' in mod:
            if not isinstance(declared_section, str) or not declared_section.strip():
                errors.append(f'{label}的 section 必须是非空字符串')
            elif ranges and not any(pattern.search(title) or declared_section.strip() in title
                                    for _, title, _ in ranges):
                errors.append(f'{label}的 section={declared_section!r} 不在「模块详解」小节中')
        hit = next(((line_no, title) for line_no, title in sections if pattern.search(title)), None)
        if hit is None:
            # v5.3: allow an individual hardware code inside a functional
            # section body (e.g. 6.1 环境监测模块 contains D1/SHT40/火焰/土壤).
            body_hit = None
            for line_no, title, body in ranges:
                if declared_section and declared_section.strip() not in title:
                    continue
                if pattern.search(body):
                    body_hit = (line_no, title)
                    break
            if body_hit is None and declared_section:
                # The code may be documented elsewhere in the technical MD
                # (e.g. 4.2 传感器选型表 says D1, while 6.1 says 粉尘子模块).
                # Accept whole-document evidence only when the author declares
                # the module section for photo mapping.
                if pattern.search("\n".join(lines)):
                    section_line = next((no for no, title, _ in ranges
                                         if declared_section.strip() in title), None)
                    if section_line is not None:
                        body_hit = (section_line, declared_section)
                        warnings.append(f'{label} 的 code 仅出现在正文其他位置，已按 section={declared_section!r} 映射；请人工确认')
            if body_hit is None:
                errors.append(f'{label}未在技术文档正文中找到：code 必须与「模块详解」小节标题/正文或文档其他位置一致（如 6.1 D1 粉尘检测模块），否则下游无法把照片对应到章节')
            else:
                matched.append(body_hit[0])
        else:
            matched.append(hit[0])
    if matched != sorted(matched):
        errors.append('modules 未按正文出现顺序排列：请按「模块详解」小节在正文中的先后重排（同一小节并列多个模块不违规）')
    report['status'] = 'FAIL' if errors else ('WARN' if warnings else 'PASS')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown', help='生成的技术文档 MD')
    parser.add_argument('--json', dest='manifest', default=None,
                        help='清单路径，默认取 MD 同级的 physical-modules.json')
    parser.add_argument('--report', default=None, help='另存 JSON 报告路径')
    args = parser.parse_args()
    try:
        result = check(args.markdown, args.manifest)
    except (OSError, UnicodeError) as exc:
        parser.exit(2, f'ERROR: 无法读取文件：{exc}\n')
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(out + '\n', encoding='utf-8')
    print(out)
    sys.exit(0 if result['status'] in ('PASS', 'WARN') else 1)


if __name__ == '__main__':
    main()