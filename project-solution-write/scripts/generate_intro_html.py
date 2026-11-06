#!/usr/bin/env python3
"""Generate a single-file project-introduction HTML from the intro Markdown.

The HTML is a visualization of 《项目介绍与功能说明》 only. It never reads the
implementation plan and never invents functions or measurements. Standard
library only; no external fonts, icons, scripts or images are emitted.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = SKILL_ROOT / "templates" / "project-introduction.html"

TONE = ("blue", "mint", "warm", "violet")
SYMBOLS = ("▦", "◉", "♬", "↗", "◇", "▤", "⚙", "◈")

ICONS = {
    "scale": '<path d="M12 3v18M4 7h16M6 7l-3 6h6L6 7Zm12 0-3 6h6l-3-6ZM7 21h10"/>',
    "layers": '<path d="m12 2 9 5-9 5-9-5 9-5Zm-9 10 9 5 9-5M3 17l9 5 9-5"/>',
    "monitor": '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4M7 9h10M7 12h6"/>',
    "bell": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4"/>',
    "radio": '<path d="M12 19v-7M8 19h8M7 13a7 7 0 0 1 10 0M4 10a11 11 0 0 1 16 0M12 5h.01"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>',
    "activity": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "cpu": '<rect x="7" y="7" width="10" height="10" rx="2"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    "cloud": '<path d="M17.5 19a4.5 4.5 0 0 0 .5-8.97A6 6 0 0 0 6.2 10.5 4 4 0 0 0 7 19h10.5Z"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3Z"/><path d="m9 12 2 2 4-5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "spark": '<path d="m12 3 2.2 6.8L21 12l-6.8 2.2L12 21l-2.2-6.8L3 12l6.8-2.2L12 3Z"/>',
    "box": '<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>',
}


@dataclass
class Block:
    kind: str
    level: int = 0
    text: str = ""
    items: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    lang: str = ""


def parse_markdown(text: str) -> list[Block]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[Block] = []
    para: list[str] = []
    i, n = 0, len(lines)

    def flush_para() -> None:
        nonlocal para
        if para:
            joined = " ".join(x.strip() for x in para if x.strip())
            if joined:
                blocks.append(Block("para", text=joined))
            para = []

    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            flush_para()
            i += 1
            continue
        if stripped.startswith("```"):
            flush_para()
            lang = stripped[3:].strip()
            i += 1
            code: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            if i < n:
                i += 1
            blocks.append(Block("code", text="\n".join(code), lang=lang))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            blocks.append(Block("heading", level=len(m.group(1)), text=m.group(2).strip()))
            i += 1
            continue
        if stripped.startswith(">"):
            flush_para()
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].lstrip())
                i += 1
            blocks.append(Block("quote", text="\n".join(quote)))
            continue
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            flush_para()
            rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                if re.match(r"^\|[\s:|-]+\|$", row):
                    i += 1
                    continue
                rows.append([c.strip() for c in row.strip("|").split("|")])
                i += 1
            if rows:
                blocks.append(Block("table", rows=rows))
            continue
        m = re.match(r"^\s*[-*+]\s+(.*)$", line)
        if m:
            flush_para()
            items: list[str] = []
            while i < n:
                mm = re.match(r"^\s*[-*+]\s+(.*)$", lines[i])
                if mm:
                    items.append(mm.group(1).strip())
                    i += 1
                    continue
                if lines[i].strip() and not re.match(
                    r"^\s*(?:#{1,6}\s|\d+[.)]\s|>|\||```|---\s*$)", lines[i]
                ):
                    if items:
                        items[-1] += " " + lines[i].strip()
                    i += 1
                    continue
                break
            blocks.append(Block("ul", items=items))
            continue
        m = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if m:
            flush_para()
            items = []
            while i < n:
                mm = re.match(r"^\s*\d+[.)]\s+(.*)$", lines[i])
                if mm:
                    items.append(mm.group(1).strip())
                    i += 1
                    continue
                if lines[i].strip() and not re.match(
                    r"^\s*(?:#{1,6}\s|[-*+]\s|>|\||```|---\s*$)", lines[i]
                ):
                    if items:
                        items[-1] += " " + lines[i].strip()
                    i += 1
                    continue
                break
            blocks.append(Block("ol", items=items))
            continue
        if stripped in ("---", "***", "___"):
            flush_para()
            i += 1
            continue
        para.append(line)
        i += 1
    flush_para()
    return blocks


def strip_md(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_~]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clip(text: str, limit: int) -> str:
    text = strip_md(text)
    if len(text) <= limit:
        return text
    cut = max((text.rfind(p, 0, limit) for p in "。！？；"), default=-1)
    if cut >= max(6, limit // 2):
        return text[: cut + 1]
    cut = max((text.rfind(p, 0, limit) for p in "，、"), default=-1)
    if cut >= max(6, limit // 2):
        return text[:cut] + "…"
    return text[:limit].rstrip() + "…"


def short_label(text: str, limit: int = 18) -> str:
    text = strip_md(text)
    for sep in ("：", ":", "，", "。", "；", "、", "（", "("):
        idx = text.find(sep)
        if 0 < idx <= limit:
            text = text[:idx]
            break
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text.strip()


def heading_text(block: Block) -> str:
    return strip_md(block.text)


def strip_numbering(text: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*[.、]?\s*", "", text).strip()


def find_heading(blocks: list[Block], level: int, keywords: tuple[str, ...]) -> int:
    for i, block in enumerate(blocks):
        if block.kind == "heading" and block.level == level:
            title = heading_text(block)
            if any(k in title for k in keywords):
                return i
    return -1


def section_blocks(blocks: list[Block], index: int) -> list[Block]:
    if index < 0:
        return []
    level = blocks[index].level
    out: list[Block] = []
    for block in blocks[index + 1 :]:
        if block.kind == "heading" and block.level <= level:
            break
        out.append(block)
    return out


def sub_sections(blocks: list[Block]) -> list[dict]:
    out: list[dict] = []
    current: dict | None = None
    for block in blocks:
        if block.kind == "heading" and block.level == 3:
            current = {"title": strip_numbering(heading_text(block)), "blocks": []}
            out.append(current)
        elif current is not None:
            current["blocks"].append(block)
    return out


def first_para(blocks: list[Block]) -> str:
    for block in blocks:
        if block.kind == "para" and block.text.strip():
            return strip_md(block.text)
    return ""


def feature_text(blocks: list[Block]) -> str:
    """取功能说明的首段；若首段以冒号收尾或很短，则补上紧随其后的公式/清单。"""
    first_index = -1
    text = ""
    for i, block in enumerate(blocks):
        if block.kind == "para" and block.text.strip():
            first_index = i
            text = strip_md(block.text)
            break
    if not text:
        return ""
    if text.endswith(("：", ":")) or len(text) < 50:
        extras: list[str] = []
        for block in blocks[first_index + 1 : first_index + 4]:
            if block.kind == "quote" and block.text.strip():
                extras.append(strip_md(block.text))
            elif block.kind in ("ul", "ol"):
                extras.extend(strip_md(x) for x in block.items[:3] if x.strip())
            elif block.kind == "table":
                for row in block.rows[1:4]:
                    if row and strip_md(row[0]):
                        extras.append(strip_md(row[0]))
        if extras:
            cleaned = [x.rstrip("；;，,。 ") for x in extras if x.strip()]
            if cleaned:
                text = text + " " + "；".join(cleaned[:4])
    return text


def first_table(blocks: list[Block]) -> list[list[str]]:
    for block in blocks:
        if block.kind == "table" and len(block.rows) >= 2:
            return block.rows
    return []


def list_items(blocks: list[Block], kind: str | None = None) -> list[str]:
    out: list[str] = []
    for block in blocks:
        if block.kind in ("ul", "ol") and (kind is None or block.kind == kind):
            out.extend(strip_md(x) for x in block.items if x.strip())
    return out


def match_icon(text: str) -> str | None:
    rules = (
        ("scale", ("称重", "重量", "计量", "秤", "load cell")),
        ("layers", ("数量", "库存", "估算", "计数", "统计")),
        ("monitor", ("显示", "屏幕", "页面", "界面", "oled", "看板")),
        ("bell", ("报警", "告警", "缺货", "提醒", "蜂鸣")),
        ("radio", ("无线", "通信", "网络", "远程", "上传", "lora", "wifi", "4g")),
        ("database", ("配置", "保存", "数据", "管理", "存储", "记录")),
        ("shield", ("安全", "权限", "认证", "防护")),
        ("clock", ("时间", "定时", "调度", "周期")),
        ("cloud", ("云", "平台", "服务", "后台")),
        ("cpu", ("控制", "主控", "处理", "计算", "芯片", "mcu")),
        ("activity", ("传感", "采集", "监测", "检测", "感知")),
    )
    low = text.lower()
    for name, keys in rules:
        if any(k in low for k in keys):
            return name
    return None


def icon_for(title: str, description: str = "") -> str:
    # 标题优先，描述只作兜底，避免“无线通信”的描述里出现“重量”而被误判为称重。
    return match_icon(title) or match_icon(title + " " + description) or "layers"


def icon_svg(name: str) -> str:
    body = ICONS.get(name, ICONS["layers"])
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{body}</svg>"
    )


def split_title(title: str) -> tuple[str, str, str, str]:
    title = strip_md(title).split("｜")[0].split("|")[0].strip()
    lead, rest = "", title
    if "的" in title:
        idx = title.rfind("的")
        lead, rest = title[: idx + 1], title[idx + 1 :].strip()
    tail = ""
    if rest.endswith("系统") and len(rest) > 2:
        tail, rest = "系统", rest[:-2]
    if not rest:
        rest, lead = title, ""
    return title, lead, rest, tail


def infer_category(title: str, features: list[dict], system: list[str]) -> str:
    text = (title + " " + " ".join(f["title"] + " " + f["description"] for f in features) + " " + " ".join(system)).lower()
    if any(k in text for k in ("仓储", "库存", "货架", "货位", "仓库")):
        return "EMBEDDED · SMART STORAGE"
    if any(k in text for k in ("环境", "监测", "传感", "温湿度", "粉尘", "水质", "气象")):
        return "EMBEDDED · ENVIRONMENT"
    if any(k in text for k in ("镜", "语音", "交互", "显示", "屏", "助手")):
        return "SMART INTERACTION · UI"
    if any(k in text for k in ("机器人", "机械臂", "小车", "运动控制", "舵机")):
        return "ROBOTICS · CONTROL"
    if any(k in text for k in ("web", "软件", "平台", "前端", "后端", "管理系统")):
        return "SOFTWARE · SYSTEM"
    return "PROJECT · SOLUTION"


def extract_features(blocks: list[Block]) -> list[dict]:
    idx = find_heading(blocks, 2, ("功能说明", "功能介绍", "核心功能", "功能模块"))
    if idx < 0:
        return []
    sec = section_blocks(blocks, idx)
    items: list[dict] = []
    for sub in sub_sections(sec):
        desc = feature_text(sub["blocks"])
        if not desc:
            listed = list_items(sub["blocks"])
            desc = listed[0] if listed else ""
        if not desc:
            rows = first_table(sub["blocks"])
            if len(rows) > 1 and len(rows[1]) > 1:
                desc = strip_md(rows[1][1])
        if sub["title"] and desc:
            items.append({"title": sub["title"], "description": clip(desc, 170)})
    if not items:
        rows = first_table(sec)
        for row in rows[1:]:
            if len(row) >= 2 and strip_md(row[0]):
                items.append({"title": strip_md(row[0]), "description": clip(row[1], 150)})
    if not items:
        for li in list_items(sec):
            if li:
                items.append({"title": short_label(li), "description": clip(li, 150)})
    if not items:
        for p in [b for b in sec if b.kind == "para"]:
            text = strip_md(p.text)
            if text:
                items.append({"title": short_label(text), "description": clip(text, 150)})
    for i, item in enumerate(items):
        item["id"] = f"F{i + 1:02d}"
        item["icon"] = icon_for(item["title"], item["description"])
        item["tone"] = TONE[i % len(TONE)]
    return items


def extract_scenarios(blocks: list[Block]) -> tuple[list[dict], str]:
    idx = find_heading(blocks, 2, ("应用场景", "系统目标", "功能范围"))
    if idx < 0:
        return [], ""
    sec = section_blocks(blocks, idx)
    sub = find_heading(sec, 3, ("典型场景", "应用场景", "使用场景"))
    if sub >= 0:
        target = section_blocks(sec, sub)
    else:
        # 没有“典型场景”子标题时，只取二级章节直属内容；
        # 不能把“系统目标”等三级小节的内容误当成应用场景。
        target = []
        for block in sec:
            if block.kind == "heading" and block.level == 3:
                break
            target.append(block)
    intro = first_para(target)
    items: list[dict] = []
    for li in list_items(target):
        items.append({"title": short_label(li, 20), "description": clip(li, 160)})
    if not items:
        rows = first_table(target)
        for row in rows[1:]:
            if len(row) >= 2 and strip_md(row[0]):
                items.append({"title": strip_md(row[0]), "description": clip(row[1], 160)})
    for i, item in enumerate(items):
        item["symbol"] = SYMBOLS[i % len(SYMBOLS)]
        item["tone"] = TONE[i % len(TONE)]
    return items, intro


def extract_workflow(blocks: list[Block]) -> tuple[list[dict], str]:
    idx = find_heading(blocks, 2, ("使用与交互", "使用流程", "交互流程", "运行流程", "使用方式"))
    if idx < 0:
        return [], ""
    sec = section_blocks(blocks, idx)
    sub = find_heading(sec, 3, ("首次使用", "日常使用", "使用流程", "操作流程"))
    target = section_blocks(sec, sub) if sub >= 0 else sec
    intro = first_para(target)
    raw = list_items(target, "ol") or list_items(target, "ul")
    if not raw:
        rows = first_table(target)
        for row in rows[1:]:
            if len(row) >= 2 and strip_md(row[0]):
                raw.append(strip_md(row[0]) + "：" + strip_md(row[1]))
    if not raw:
        for block in target:
            if block.kind == "code" and block.lang == "mermaid":
                labels: list[str] = []
                for line in block.text.splitlines():
                    for label in re.findall(r"\[([^\]]+)\]", line):
                        label = strip_md(label)
                        if label and label not in labels:
                            labels.append(label)
                raw = labels[:10]
                break
    items: list[dict] = []
    for item in raw:
        if item:
            items.append({"title": short_label(item, 18), "description": clip(item, 80)})
    return items, intro


def extract_system(blocks: list[Block]) -> tuple[list[str], str]:
    idx = find_heading(blocks, 2, ("系统组成", "组成概览"))
    if idx < 0:
        return [], ""
    sec = section_blocks(blocks, idx)
    intro = first_para(sec)
    items: list[str] = []
    rows = first_table(sec)
    for row in rows[1:]:
        if row and strip_md(row[0]):
            items.append(strip_md(row[0]))
    if not items:
        items = list_items(sec)
    if not items and intro:
        for part in re.split(r"[、，；;]", intro):
            part = part.strip()
            if 2 <= len(part) <= 20:
                items.append(part)
    seen: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen[:10], intro


def extract_demo(blocks: list[Block]) -> tuple[list[dict], str]:
    idx = find_heading(blocks, 2, ("功能展示", "验收场景", "展示场景", "演示场景"))
    if idx < 0:
        return [], ""
    sec = section_blocks(blocks, idx)
    intro = first_para(sec)
    rows = first_table(sec)
    if len(rows) < 2:
        return [], intro
    header = [strip_md(c) for c in rows[0]]

    def col(*keys: str) -> int:
        for i, cell in enumerate(header):
            if any(k in cell for k in keys):
                return i
        return -1

    ci = col("编号", "ID", "序号")
    cs = col("场景", "项目")
    co = col("操作", "步骤")
    ce = col("预期", "结果")
    ct = col("状态", "结论")
    for name, value in (("ci", ci), ("cs", cs), ("co", co), ("ce", ce), ("ct", ct)):
        if value < 0:
            if name == "ci":
                ci = 0
            elif name == "cs":
                cs = 1
            elif name == "co":
                co = 2
            elif name == "ce":
                ce = 3
            else:
                ct = 4
    items: list[dict] = []
    for row in rows[1:]:
        def cell(index: int) -> str:
            return strip_md(row[index]) if 0 <= index < len(row) else ""

        title, op, expected, status = cell(cs), cell(co), cell(ce), cell(ct) or "预期，待实测"
        if not title and not expected:
            continue
        items.append(
            {
                "label": (cell(ci) + " " + title).strip(),
                "title": title or cell(ci) or "场景",
                "value": cell(ci) or f"{len(items) + 1:02d}",
                "unit": "场景",
                "operation": clip(op, 120) or "按项目介绍中的操作说明执行。",
                "expected": clip(expected, 160) or "以项目介绍中的验收描述为准。",
                "status": status,
                "alert": any(k in title for k in ("报警", "缺货", "异常", "故障", "失败", "告警")),
                "progress": 62,
            }
        )
    return items, intro


def build_data(blocks: list[Block], source_name: str) -> dict:
    title = ""
    for block in blocks:
        if block.kind == "heading" and block.level == 1:
            title = strip_md(block.text).split("｜")[0].split("|")[0].strip()
            break
    if not title:
        raise ValueError("未找到一级项目标题（# 项目名称｜项目介绍与功能说明）")

    meta = "\n".join(b.text for b in blocks if b.kind == "quote")
    version = ""
    match = re.search(r"版本[：:]\s*([^\n]+)", meta)
    if match:
        version = match.group(1).strip()
    status = ""
    match = re.search(r"文档状态[：:]\s*([^\n]+)", meta)
    if match:
        status = match.group(1).strip()

    overview_idx = find_heading(blocks, 2, ("项目概述", "项目简介", "项目定位", "项目介绍"))
    overview = first_para(section_blocks(blocks, overview_idx)) if overview_idx >= 0 else ""
    features = extract_features(blocks)
    scenarios, scenarios_intro = extract_scenarios(blocks)
    workflow, workflow_intro = extract_workflow(blocks)
    system_items, system_intro = extract_system(blocks)
    demo_items, demo_intro = extract_demo(blocks)

    full_title, lead, accent, tail = split_title(title)
    category = infer_category(title, features, system_items)
    if not overview:
        overview = f"本页面依据《项目介绍与功能说明》整理，介绍 {accent or full_title} 的目标、功能、使用方式与边界。"
    overview = clip(overview, 160)

    tags = [short_label(f["title"], 12) for f in features[:3]]
    if not tags:
        tags = [category, version or "项目介绍"]

    summary = [
        {
            "symbol": SYMBOLS[i % len(SYMBOLS)],
            "value": short_label(f["title"], 12),
            "note": clip(f["description"], 30),
        }
        for i, f in enumerate(features[:4])
    ]
    if not summary:
        summary = [
            {
                "symbol": SYMBOLS[i % len(SYMBOLS)],
                "value": short_label(s["title"], 12),
                "note": clip(s["description"], 30),
            }
            for i, s in enumerate(scenarios[:4])
        ]

    short_brand = re.sub(r"(系统|平台|装置)$", "", accent or full_title).strip()
    brand_limit = 10 if re.search(r"[A-Za-z]", short_brand) else 6
    if len(short_brand) > brand_limit:
        short_brand = short_brand[:brand_limit].rstrip()

    showcase_tiles: list[dict] = []
    showcase_kind = (
        "slots"
        if any(k in title for k in ("仓储", "库存", "货架", "货位")) and len(features) >= 3
        else "metrics"
    )
    for i, f in enumerate(features[:4]):
        showcase_tiles.append(
            {
                "label": short_label(f["title"], 12),
                "badge": "功能",
                "value": f"{i + 1:02d}",
                "unit": "模块",
                "meta": clip(f["description"], 34),
                "icon": f["icon"],
                "tone": f["tone"],
                "art": showcase_kind == "slots",
            }
        )
    if not showcase_tiles:
        for i, item in enumerate(demo_items[:4]):
            showcase_tiles.append(
                {
                    "label": short_label(item["title"], 12),
                    "badge": "场景",
                    "value": item["value"],
                    "unit": "",
                    "meta": clip(item["expected"], 34),
                    "icon": "layers",
                    "tone": TONE[i % len(TONE)],
                    "art": False,
                }
            )
    callouts: list[dict] = []
    alert_feature = next(
        (f for f in features if any(k in f["title"] + f["description"] for k in ("报警", "告警", "缺货", "提醒", "异常"))),
        None,
    )
    net_feature = next(
        (f for f in features if any(k in f["title"] + f["description"] for k in ("无线", "远程", "通信", "网络", "上传"))),
        None,
    )
    if alert_feature:
        callouts.append({"text": short_label(alert_feature["title"], 10), "tone": "alert", "icon": "!"})
    if net_feature:
        callouts.append({"text": short_label(net_feature["title"], 10), "tone": "ok", "icon": "↗"})

    data = {
        "schema_version": 1,
        "project": {
            "title": full_title,
            "short_title": short_brand,
            "category": category,
            "version": version,
            "status": status,
            "source": source_name,
        },
        "overview": {"intro": overview},
        "tags": tags,
        "summary": summary,
        "features": features,
        "featuresIntro": "围绕用户已确认的功能清单，逐项说明触发方式、可见行为与使用边界。",
        "workflow": workflow,
        "workflowIntro": clip(workflow_intro, 120) or "项目的主要使用流程可以分为以下几个环节。",
        "scenarios": scenarios,
        "scenariosIntro": clip(scenarios_intro, 140) or "围绕项目描述的使用场景展开。",
        "system": {
            "items": system_items,
            "intro": clip(system_intro, 120) or "由主要功能模块与协作环节构成。",
        },
        "showcase": {
            "kind": showcase_kind,
            "title": "功能概览" if features else "项目概览",
            "badge": "概念展示",
            "bottom": f"{len(features)} 个核心功能" if features else "项目介绍",
            "tiles": showcase_tiles,
            "callouts": callouts,
        },
        "demo": {
            "title": "验收场景，提前看见",
            "intro": clip(demo_intro, 150) or "以下为项目介绍中的验收场景与预期结果，尚未实机测试。",
            "note": "验收场景 · 预期结果 · 未实测",
            "items": demo_items,
        },
    }
    data["page_title"] = f"{full_title} · 项目介绍"
    data["page_description"] = clip(overview, 120)
    data["header_note"] = f"项目介绍 · {version}" if version else "项目介绍 · 可视化展示"
    data["footer_note"] = "内容依据《项目介绍与功能说明》 · 页面示意不代表实机测试结果"
    return data


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def render_hero(data: dict) -> str:
    project = data["project"]
    _, lead, accent, tail = split_title(project["title"])
    if lead:
        title_html = (
            f'<span class="title-lead">{esc(lead)}</span><br>'
            f'<span class="title-accent">{esc(accent)}</span>{esc(tail)}'
        )
    else:
        title_html = f'<span class="title-accent">{esc(accent)}</span>{esc(tail)}'
    tags = "".join(f"<span>{esc(t)}</span>" for t in (data.get("tags") or [project["category"]])[:3])
    actions = []
    if data["features"]:
        actions.append('<a class="btn btn-primary" href="#features">了解核心功能 <span aria-hidden="true">↗</span></a>')
    else:
        actions.append('<a class="btn btn-primary" href="#overview">查看项目概览 <span aria-hidden="true">↗</span></a>')
    if data["demo"]["items"]:
        actions.append('<a class="btn btn-plain" href="#showcase">查看场景示意 <span aria-hidden="true">→</span></a>')
    elif data["scenarios"]:
        actions.append('<a class="btn btn-plain" href="#scenes">查看应用场景 <span aria-hidden="true">→</span></a>')
    showcase = render_showcase(data)
    grid_class = "hero-grid" if showcase else "hero-grid single"
    return f'''<section id="overview" class="hero"><div class="wrapper {grid_class}">
        <div class="hero-copy rise">
          <span class="eyebrow"><span class="dot"></span><span>{esc(project["category"])}</span></span>
          <h1>{title_html}</h1>
          <p class="lead">{esc(data["overview"]["intro"])}</p>
          <div class="hero-actions">{"".join(actions)}</div>
          <div id="hero-tags" class="hero-badges" aria-label="项目关键词">{tags}</div>
        </div>
        {showcase}
      </div></section>'''


def render_showcase(data: dict) -> str:
    showcase = data["showcase"]
    if not showcase["tiles"]:
        return ""
    tiles = []
    for tile in showcase["tiles"]:
        if tile.get("art"):
            art = '<span class="metric-art" aria-hidden="true"></span>'
        else:
            art = f'<span class="metric-icon">{icon_svg(tile.get("icon", "layers"))}</span>'
        tiles.append(
            f'''<div class="metric-tile tone-{esc(tile["tone"])}">
            <div class="metric-head"><span>{esc(tile["label"])}</span><span class="metric-badge">{esc(tile["badge"])}</span></div>
            <div class="metric-center">{art}<div class="metric-num">{esc(tile["value"])}<span>{esc(tile["unit"])}</span></div></div>
            <div class="metric-meta">{esc(tile["meta"])}</div>
            <div class="metric-bar" aria-hidden="true"><i></i></div>
          </div>'''
        )
    callouts = []
    for callout in showcase["callouts"]:
        cls = "float-label alert" if callout["tone"] == "alert" else "float-label upload"
        icon_cls = "bubble-icon" if callout["tone"] == "alert" else "bubble-icon green"
        callouts.append(
            f'<div class="{cls}"><span class="{icon_cls}">{esc(callout["icon"])}</span> {esc(callout["text"])}</div>'
        )
    count_cls = f" count-{len(tiles)}" if len(tiles) == 3 else ""
    return f'''<div class="showcase rise" aria-label="项目概念图">
          <span class="deco one"></span><span class="deco two"></span>
          <div class="dashboard">
            <div class="dash-top"><strong>{esc(showcase["title"])}</strong><span class="dash-pulse">{esc(showcase["badge"])}</span></div>
            <div class="metric-grid{count_cls}">{"".join(tiles)}</div>
            <div class="dash-bottom"><span>PROJECT · CONCEPT VIEW</span><b>{esc(showcase["bottom"])}</b></div>
          </div>
          {"".join(callouts)}
        </div>'''


def render_summary(data: dict) -> str:
    if not data["summary"]:
        return ""
    cards = "".join(
        f'<article class="summary rise"><span class="symbol">{esc(x["symbol"])}</span>'
        f'<strong>{esc(x["value"])}</strong><p>{esc(x["note"])}</p></article>'
        for x in data["summary"]
    )
    return f'<section aria-label="项目特点"><div class="wrapper summary-grid">{cards}</div></section>'


def render_features(data: dict) -> str:
    if not data["features"]:
        return ""
    cards = []
    for feature in data["features"]:
        cards.append(
            f'''<article class="feature-card tone-{esc(feature["tone"])} rise" data-feature="{esc(feature["id"])}">
            <div class="feature-icon">{icon_svg(feature["icon"])}</div>
            <h3>{esc(feature["title"])}</h3>
            <p>{esc(feature["description"])}</p>
            <span class="num-id">{esc(feature["id"][1:])}</span>
          </article>'''
        )
    return f'''<section class="section-bg" id="features"><div class="wrapper">
        <div class="section-head rise"><p class="section-kicker">FUNCTIONS / 功能模块</p><h2 class="section-title">核心功能，一目了然</h2><p class="section-desc">{esc(data["featuresIntro"])}</p></div>
        <div class="feature-grid">{"".join(cards)}</div>
      </div></section>'''


def render_workflow(data: dict) -> str:
    if not data["workflow"]:
        return ""
    n = len(data["workflow"])
    arrows = n <= 5
    cls = "flow-layout flow-arrows" if arrows else "flow-layout"
    style = f' style="--flow-cols:{n}"' if arrows else ""
    steps = "".join(
        f'<article class="flow-step rise"><div class="step-i">{i + 1:02d}</div>'
        f'<h3>{esc(step["title"])}</h3><p>{esc(step["description"])}</p></article>'
        for i, step in enumerate(data["workflow"])
    )
    return f'''<section id="workflow"><div class="wrapper">
        <div class="section-head rise"><p class="section-kicker">WORKFLOW / 使用流程</p><h2 class="section-title">项目如何运转</h2><p class="section-desc">{esc(data["workflowIntro"])}</p></div>
        <div class="{cls}"{style}>{steps}</div>
      </div></section>'''


def render_demo(data: dict) -> str:
    items = data["demo"]["items"]
    if not items:
        return ""
    first = items[0]
    buttons = "".join(
        f'<button type="button" data-demo-index="{i}" aria-pressed="{"true" if i == 0 else "false"}">{esc(item["label"])}</button>'
        for i, item in enumerate(items)
    )
    state_cls = "scene-state alert" if first["alert"] else "scene-state"
    return f'''<section id="showcase"><div class="wrapper demo-panel rise">
        <div class="demo-info">
          <p class="section-kicker">SCENARIO / 场景示意</p>
          <h2 class="section-title">{esc(data["demo"]["title"])}</h2>
          <p>{esc(data["demo"]["intro"])}</p>
          <span class="demo-note">{esc(data["demo"]["note"])}</span>
          <div class="selector" role="group" aria-label="选择演示场景" id="demo-selector">{buttons}</div>
        </div>
        <div class="demo-screen" role="status" aria-live="polite">
          <div class="screen-top"><span>SCENARIO VIEW</span><strong id="demo-title">{esc(first["title"])}</strong></div>
          <div class="screen-value"><big><span id="demo-value">{esc(first["value"])}</span><small id="demo-unit">{esc(first["unit"])}</small></big><span id="demo-state" class="{state_cls}">{esc(first["status"])}</span></div>
          <div class="screen-sub"><span><b>操作：</b><span id="demo-operation">{esc(first["operation"])}</span></span><span><b>预期：</b><span id="demo-expected">{esc(first["expected"])}</span></span></div>
          <div class="screen-meter" aria-hidden="true"><span id="demo-meter-bar"></span></div>
        </div>
      </div></section>'''


def render_scenarios(data: dict) -> str:
    if not data["scenarios"]:
        return ""
    cards = "".join(
        f'<article class="scenario-card tone-{esc(item["tone"])} rise"><h3>{esc(item["title"])}</h3>'
        f'<p>{esc(item["description"])}</p><span class="scenario-illustration" aria-hidden="true">{esc(item["symbol"])}</span></article>'
        for item in data["scenarios"]
    )
    return f'''<section id="scenes"><div class="wrapper">
        <div class="section-head rise"><p class="section-kicker">APPLICATION / 应用场景</p><h2 class="section-title">适用于这些场景</h2><p class="section-desc">{esc(data["scenariosIntro"])}</p></div>
        <div class="scenario-grid count-{len(data["scenarios"])}">{cards}</div>
      </div></section>'''


def render_system(data: dict) -> str:
    if not data["system"]["items"]:
        return ""
    chips = "".join(f"<span>{esc(item)}</span>" for item in data["system"]["items"])
    return f'''<section id="composition"><div class="wrapper system-bar rise"><div><h3>系统组成概览</h3><p>{esc(data["system"]["intro"])}</p></div><div class="system-chips">{chips}</div></div></section>'''


def render_nav(data: dict) -> str:
    links = ['<a href="#overview">项目概览</a>']
    if data["features"]:
        links.append('<a href="#features">功能模块</a>')
    if data["workflow"]:
        links.append('<a href="#workflow">使用流程</a>')
    if data["scenarios"]:
        links.append('<a href="#scenes">应用场景</a>')
    return "".join(links)


def safe_json(data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def render_page(data: dict, template: str) -> str:
    replacements = {
        "{{PAGE_TITLE}}": esc(data["page_title"]),
        "{{PAGE_DESCRIPTION}}": esc(data["page_description"]),
        "{{BRAND}}": esc(data["project"]["short_title"]),
        "{{NAV_ITEMS}}": render_nav(data),
        "{{HEADER_NOTE}}": esc(data["header_note"]),
        "{{HERO_SECTION}}": render_hero(data),
        "{{SUMMARY_SECTION}}": render_summary(data),
        "{{FEATURES_SECTION}}": render_features(data),
        "{{WORKFLOW_SECTION}}": render_workflow(data),
        "{{SHOWCASE_SECTION}}": render_demo(data),
        "{{SCENARIOS_SECTION}}": render_scenarios(data),
        "{{SYSTEM_SECTION}}": render_system(data),
        "{{FOOTER_TITLE}}": esc(data["project"]["title"]),
        "{{FOOTER_NOTE}}": esc(data["footer_note"]),
        "{{PROJECT_DATA_JSON}}": safe_json(data),
    }
    output = template
    for key, value in replacements.items():
        output = output.replace(key, value)
    if "{{" in output:
        leftover = sorted(set(re.findall(r"\{\{[^}]+\}\}", output)))
        raise ValueError("模板占位符未替换：" + ", ".join(leftover))
    return output


def write_atomic(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从《项目介绍与功能说明》Markdown 生成单文件 HTML")
    parser.add_argument("--intro", type=Path, required=True, help="项目介绍 Markdown")
    parser.add_argument("--out", type=Path, help="输出 HTML；默认与 intro 同名 .html")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="HTML 模板")
    parser.add_argument("--data-out", type=Path, help="可选：输出结构化数据 JSON")
    args = parser.parse_args(argv)
    try:
        intro_text = args.intro.read_text(encoding="utf-8-sig")
        template = args.template.read_text(encoding="utf-8")
        blocks = parse_markdown(intro_text)
        data = build_data(blocks, args.intro.name)
        output = render_page(data, template)
        out = args.out or args.intro.with_suffix(".html")
        write_atomic(out, output)
        if args.data_out:
            write_atomic(args.data_out, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        warnings = []
        if not data["features"]:
            warnings.append("未找到功能小节，功能卡片区将隐藏")
        if not data["workflow"]:
            warnings.append("未找到使用流程，流程区将隐藏")
        if not data["scenarios"]:
            warnings.append("未找到应用场景，场景区将隐藏")
        if not data["system"]["items"]:
            warnings.append("未找到系统组成，组成区将隐藏")
        if not data["demo"]["items"]:
            warnings.append("未找到验收场景表，场景示意区将隐藏")
        print(
            json.dumps(
                {
                    "status": "WARN" if warnings else "PASS",
                    "out": str(out),
                    "features": len(data["features"]),
                    "workflow": len(data["workflow"]),
                    "scenarios": len(data["scenarios"]),
                    "demo": len(data["demo"]["items"]),
                    "warnings": warnings,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())