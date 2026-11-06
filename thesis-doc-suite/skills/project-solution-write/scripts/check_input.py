#!/usr/bin/env python3
"""Minimal project title/features gate for structured request JSON.

This is a fail-closed helper, not a semantic LLM requirement analyzer.
Use only after merging explicitly known current-turn/context/project-asset fields.
"""
import argparse
import json
from pathlib import Path

PLACEHOLDERS = {"", "待定", "未命名", "无", "暂无", "项目名", "项目名称", "新项目", "xxx", "...", "……", "待补充", "功能待补", "todo", "tbd"}
CHOICES = {"cost": "成本优先", "performance": "性能优先", "function": "功能优先", "balanced": "均衡方案"}


def meaningful(value):
    return isinstance(value, str) and value.strip().lower() not in PLACEHOLDERS


def has_requirements(value):
    if not isinstance(value, list):
        return False
    for row in value:
        if isinstance(row, str) and meaningful(row):
            return True
        if isinstance(row, dict) and (meaningful(row.get("name")) or meaningful(row.get("detail"))):
            return True
    return False


def check(data):
    if not isinstance(data, dict):
        raise ValueError("输入必须是 JSON 对象")
    missing = []
    if not meaningful(data.get("project_title")):
        missing.append("project_title")
    if not has_requirements(data.get("requirements")):
        missing.append("requirements")

    opt = data.get("optimization") or {}
    if not isinstance(opt, dict):
        opt = {}
    priority = opt.get("priority")
    has_priority = priority in CHOICES
    direct = bool(data.get("direct_generate", False))

    if missing:
        missing_words = []
        if "project_title" in missing:
            missing_words.append("项目题目")
        if "requirements" in missing:
            missing_words.append("具体功能清单")
        question = "请提供" + "和".join(missing_words) + "；功能直接用自己的话描述即可。"
        if not has_priority:
            question += " 设计侧重可同时选择：①成本优先 ②性能优先 ③功能优先 ④均衡方案。"
        return {"status": "NEEDS_INPUT", "missing": missing, "question": question,
                "generate_allowed": False, "priority": priority if has_priority else None}

    if not has_priority and not direct:
        return {"status": "NEEDS_PRIORITY", "missing": [],
                "question": "你希望这个项目优先考虑哪方面？①成本优先 ②性能优先 ③功能优先 ④均衡方案（无特别偏好可选④）。",
                "generate_allowed": False, "priority": None}
    return {"status": "READY", "missing": [], "question": "",
            "generate_allowed": True, "priority": priority if has_priority else "balanced",
            "priority_status": opt.get("status", "confirmed") if has_priority else "proposed",
            "note": "仍须由 Agent 判断功能是否存在会改变技术路线的重大歧义"}


def main():
    p=argparse.ArgumentParser(description="Gate project-solution-write intake fields")
    p.add_argument("--input", type=Path, help="从用户请求和已确认资产提取的 JSON 文件；缺省按空输入检查")
    p.add_argument("--json-out", type=Path, help="保存结果 JSON（可选）")
    args=p.parse_args()
    raw=json.loads(args.input.read_text(encoding="utf-8")) if args.input else {}
    result=check(raw)
    output=json.dumps(result,ensure_ascii=False,indent=2)
    print(output)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output+"\n",encoding="utf-8")
    return 0 if result["generate_allowed"] else 3


if __name__=="__main__":
    raise SystemExit(main())
