#!/usr/bin/env python3
"""Generate physical-modules.json v1 from the approved technical Markdown.

Two document styles are supported:

1. One physical module per H3 section (e.g. ``6.1 D1 粉尘检测模块``).
2. A functional H3 section containing sub-module bullets (e.g.
   ``6.1 环境监测模块`` with ``- 粉尘采集子模块：...``), plus dependency
   mentions such as ``依赖：...蜂鸣器模块``.

Software sections (数据处理 / 系统控制 / uart_comm / Warn / main / lower_snake_case)
are excluded.  The output is validated with check_physical_modules.py before
the command exits 0.

Usage:
  python scripts/gen_physical_modules.py <technical.md> [--out physical-modules.json]
                                         [--md-out physical-modules.md] [--report gen-report.json]
"""
from __future__ import annotations

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(_sys.stderr, "reconfigure"):
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
import re
from pathlib import Path

import content_rules as rules
from check_physical_modules import section_ranges

SKILL_NAME = "project-technical-doc"
PAREN = re.compile(r"[（(][^）)]*[）)]")
SUB_LINE = re.compile(
    r"^\s*[-*]\s*(?:\*\*)?([^：:*\n]{2,40}?(?:子模块|模块))(?:\*\*)?\s*[：:]\s*(.+?)\s*$",
    re.M)
DEP_LINE = re.compile(r"^\s*[-*]\s*(?:\*\*)?依赖(?:\*\*)?\s*[：:]\s*(.+?)\s*$", re.M)


def _main_title(title):
    text = PAREN.sub("", rules.strip_number(title)).strip()
    return text or title


def _short_name(label):
    text = re.sub(r"(?:采集)?子模块$", "", label.strip())
    return text.strip(" -—:：") or label.strip()


def _code_near(line, keyword, after=15, before=5):
    pos = line.find(keyword)
    if pos < 0:
        return None
    best_after = best_before = None
    for code in rules.KNOWN_CODES:
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(code) + r"(?=[A-Za-z_]|[^A-Za-z0-9_]|$)"
        for m in re.finditer(pattern, line, re.I):
            delta = m.start() - pos
            if 0 <= delta <= after:
                if best_after is None or delta < best_after[0]:
                    best_after = (delta, code)
            elif -before <= delta < 0:
                if best_before is None or -delta < best_before[0]:
                    best_before = (-delta, code)
    return (best_after or best_before)[1] if (best_after or best_before) else None

def _alias_code(label, detail, doc_text):
    # Hardware words win over interface words: 粉尘+D1, not 粉尘+UART.
    for keyword in ("粉尘", "温湿度", "火焰", "土壤", "4G", "短信", "显示",
                    "OLED", "按键", "蜂鸣器"):
        if keyword in label:
            for line in doc_text.splitlines():
                if keyword in line:
                    code = _code_near(line, keyword)
                    if code:
                        return code
            return keyword
    known = rules.known_code(label + " " + detail)
    if known:
        return known
    return rules.best_code_token(label)


def _module(code, name, hardware, category, section, section_line,
            source_files=None, pins=None, note=None):
    mod = {
        "code": code, "name": name, "hardware": hardware,
        "category": category, "section": section, "section_line": section_line,
    }
    if source_files:
        mod["source_files"] = source_files
    if pins:
        mod["pins"] = "/".join(pins)
    if note and note != hardware:
        mod["note"] = note
    return mod


def _submodules(section_title, line_no, body, doc_text):
    out, seen = [], set()
    for m in SUB_LINE.finditer(body):
        label, detail = m.group(1).strip(), m.group(2).strip().rstrip("；;")
        if label in ("子模块", "模块") or len(detail) < 2:
            continue
        code = _alias_code(label, detail, doc_text)
        category = rules.classify_physical(label, detail) or "other"
        name = _short_name(label)
        if not re.search(r"(?:模块|传感器|显示|按键|蜂鸣器)$", name):
            name += "模块"
        if "粉尘" in label:
            hardware = f"D1 粉尘传感器：{detail}"
        elif "温湿度" in label:
            hardware = f"SHT40 温湿度传感器：{detail}"
        elif "火焰" in label:
            hardware = f"火焰传感器：{detail}"
        elif "土壤" in label:
            hardware = f"土壤湿度传感器：{detail}"
        elif code and any(ch.isascii() for ch in code):
            hardware = f"{code} {label}：{detail}"
        else:
            hardware = f"{label}：{detail}"
        if code.casefold() in seen:
            continue
        seen.add(code.casefold())
        out.append(_module(code, name, hardware, category, section_title,
                           line_no, rules.extract_source_files(detail),
                           rules.extract_pins(detail), rules.first_sentence(detail, 100)))
    return out


def _dependencies(section_title, line_no, body, section_titles):
    out = []
    m = DEP_LINE.search(body)
    if not m:
        return out
    for token in re.split(r"[、；;，,]", m.group(1)):
        token = re.sub(r"[（(][^）)]*[）)]", "", token).strip(" 。；;，,")
        if not token:
            continue
        code = rules.known_code(token)
        for keyword in ("蜂鸣器", "按键", "OLED", "显示屏", "传感器"):
            if keyword in token and not code:
                code = keyword
        if not code:
            continue
        # Already has its own H3 section? Do not duplicate it under 告警依赖.
        if any(code.casefold() in title.casefold() for title in section_titles):
            continue
        category = rules.classify_physical(token, token) or "other"
        name = token.replace("模块", "").strip() or token
        if not re.search(r"(?:模块|传感器|显示|按键|蜂鸣器)$", name):
            name += "模块"
        out.append(_module(code, name, token, category, section_title, line_no,
                           rules.extract_source_files(token),
                           rules.extract_pins(token), ""))
    return out


def _parent_module(section_title, line_no, body):
    main = _main_title(section_title)
    code = rules.best_code_token(section_title)
    category = rules.classify_physical(section_title, body)
    if category is None:
        return None
    sentence = rules.first_sentence(body, 140)
    raw_title = rules.strip_number(section_title)
    hardware = f"{raw_title}（{sentence}）" if sentence else raw_title
    name = main
    if code and name.casefold().startswith(code.casefold()):
        name = name[len(code):].strip(" -—:：")
    if not name or name == "模块":
        name = main
    return _module(code, name, hardware, category, section_title, line_no,
                   rules.extract_source_files(body), rules.extract_pins(body),
                   "")


def generate(md_path, out_path, md_out=None, report_path=None):
    md = Path(md_path).expanduser().resolve()
    text = md.read_text("utf-8-sig")
    lines = text.splitlines()
    ranges = section_ranges(lines)
    modules, excluded, warnings = [], [], []
    if ranges is None:
        modules = []
    else:
        section_titles = [title for _, title, _ in ranges]
        seen = {}
        for line_no, title, body in ranges:
            if rules.is_software_section(title, body):
                excluded.append({"line": line_no, "title": title, "reason": "软件模块/抽象层"})
                # 告警管理模块虽为软件功能章，但依赖真实蜂鸣器；单独提取实物依赖。
                for mod in _dependencies(title, line_no, body, section_titles):
                    key = mod["code"].casefold()
                    if key not in seen:
                        seen[key] = True
                        modules.append(mod)
                continue
            subs = _submodules(title, line_no, body, text)
            if subs:
                for mod in subs:
                    key = mod["code"].casefold()
                    if key in seen:
                        excluded.append({"line": line_no, "title": mod["code"], "reason": "重复 code"})
                        continue
                    seen[key] = True
                    modules.append(mod)
            else:
                mod = _parent_module(title, line_no, body)
                if mod is None:
                    excluded.append({"line": line_no, "title": title, "reason": "未发现实物形态证据"})
                    continue
                key = mod["code"].casefold()
                if key in seen:
                    excluded.append({"line": line_no, "title": mod["code"], "reason": "重复 code"})
                    continue
                seen[key] = True
                modules.append(mod)
    data = {"schema_version": 1, "generated_by": SKILL_NAME, "modules": modules}
    out = Path(out_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    if md_out:
        lines_out = ["# 实物模块清单", "",
                     "> 由 `gen_physical_modules.py` 从技术文档「模块详解」章提取；只含实物形态模块。", "",
                     "| code | 名称 | 实物/器件 | 类别 | 引脚/接口 | 源文件 | 说明 |",
                     "|---|---|---|---|---|---|---|"]
        for m in modules:
            lines_out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                m["code"], m["name"], m["hardware"], m.get("category", ""),
                m.get("pins", ""), ", ".join(m.get("source_files", [])), m.get("note", "")))
        Path(md_out).write_text("\n".join(lines_out) + "\n", "utf-8")
    from check_physical_modules import check as check_manifest
    report = check_manifest(md, out)
    if report_path:
        payload = {
            "status": report["status"], "markdown": str(md), "manifest": str(out),
            "modules": len(modules), "excluded": excluded,
            "warnings": warnings + report.get("warnings", []),
            "errors": report.get("errors", []),
        }
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return {"status": report["status"], "manifest": str(out),
            "modules": len(modules), "excluded": excluded,
            "warnings": warnings + report.get("warnings", []),
            "errors": report.get("errors", [])}


def main():
    ap = argparse.ArgumentParser(description="从技术文档「模块详解」章生成 physical-modules.json v1")
    ap.add_argument("markdown")
    ap.add_argument("--out", dest="out", default=None)
    ap.add_argument("--md-out", dest="md_out", default=None)
    ap.add_argument("--report", dest="report", default=None)
    args = ap.parse_args()
    md = Path(args.markdown).expanduser()
    out = Path(args.out) if args.out else md.parent / "physical-modules.json"
    try:
        result = generate(md, out, args.md_out, args.report)
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in ("PASS", "WARN") else 1


if __name__ == "__main__":
    raise SystemExit(main())