#!/usr/bin/env python3
"""Compose batched Markdown parts into one draft (stdlib only).

The agent writes one section/group per batch file under a parts directory, then
this script concatenates them in filename order. It never rewrites content or
invents sections; it only checks structure, reports warnings, and writes the
composed draft atomically.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

INTRO_REQUIRED = (
    ("项目概述", ("项目概述", "项目简介", "项目定位", "项目介绍")),
    ("功能说明", ("功能说明", "功能介绍", "核心功能", "功能模块")),
    ("使用流程", ("使用与交互", "使用流程", "交互流程", "运行流程", "使用方式")),
)
IMPL_REQUIRED = (
    ("范围/设计基线", ("范围", "需求", "设计基线", "项目目标")),
    ("架构", ("架构", "系统拓扑", "系统组成")),
    ("实现", ("实现", "设计", "模块")),
    ("实施步骤", ("实施步骤", "开发步骤", "实施阶段", "分阶段开发")),
    ("验收", ("验收", "测试")),
)


def headings(text: str) -> list[tuple[int, str]]:
    """Collect Markdown headings outside fenced code blocks."""
    out: list[tuple[int, str]] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            out.append((len(match.group(1)), match.group(2).strip()))
    return out


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按文件名顺序组装分批 Markdown 草稿")
    parser.add_argument("--parts-dir", type=Path, required=True, help="批次目录（*.md）")
    parser.add_argument("--out", type=Path, required=True, help="组装后的草稿路径")
    parser.add_argument("--kind", choices=("introduction", "implementation", "generic"), default="generic")
    parser.add_argument("--title", default="", help="可选：项目题目，用于核对 H1")
    parser.add_argument("--min-parts", type=int, default=4, help="建议的最少批次数（默认 4）")
    parser.add_argument("--report", type=Path, help="可选：JSON 报告")
    args = parser.parse_args(argv)

    errors: list[str] = []
    warnings: list[str] = []
    parts = sorted(
        (p for p in args.parts_dir.glob("*.md") if p.is_file()),
        key=lambda p: p.name.lower(),
    ) if args.parts_dir.is_dir() else []
    texts: list[tuple[Path, str]] = []
    for part in parts:
        try:
            text = part.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            errors.append(f"{part.name} 不是有效 UTF-8")
            continue
        text = text.strip("\n")
        if not text.strip():
            errors.append(f"{part.name} 为空")
            continue
        texts.append((part, text))

    if not texts:
        errors.append("没有可用的 Markdown 批次")
    output = "\n\n".join(text for _, text in texts).strip() + "\n" if texts else ""
    hs = headings(output)
    h1 = [text for level, text in hs if level == 1]
    h2 = [text for level, text in hs if level == 2]
    if len(h1) != 1:
        errors.append(f"组装结果应恰好有一个一级标题，实际 {len(h1)} 个")
    if not h2:
        errors.append("组装结果缺少二级章节标题")
    if h1 and args.title and normalize(args.title) not in normalize(h1[0]):
        warnings.append(f"一级标题未包含项目题目：{args.title}")
    if len(texts) < max(1, args.min_parts):
        warnings.append(f"只收到 {len(texts)} 个批次（建议至少 {args.min_parts} 批，避免一次性整篇生成）")

    required = INTRO_REQUIRED if args.kind == "introduction" else IMPL_REQUIRED if args.kind == "implementation" else ()
    for label, keys in required:
        if not any(any(key in heading for key in keys) for heading in h2):
            warnings.append(f"未找到“{label}”二级章节，需确认是否适用")
    if args.kind == "introduction" and len(h2) < 3:
        warnings.append("介绍草稿二级章节少于 3 个，需确认介绍是否完整")
    if args.kind == "implementation" and len(h2) < 5:
        warnings.append("实施草稿二级章节少于 5 个，需确认实施方案是否完整")

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    if not errors and output:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.out.with_name(f".{args.out.name}.tmp")
        tmp.write_text(output, encoding="utf-8", newline="\n")
        tmp.replace(args.out)

    report = {
        "status": status,
        "out": str(args.out),
        "kind": args.kind,
        "parts": len(texts),
        "h1": h1,
        "h2_count": len(h2),
        "warnings": warnings,
        "errors": errors,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "out": str(args.out), "parts": len(texts), "h2": len(h2)}, ensure_ascii=False))
    for warning in warnings:
        print("WARN:", warning)
    for error in errors:
        print("ERROR:", error)
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())