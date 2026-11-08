#!/usr/bin/env python3
"""毕设/课程设计选题质量静态检查（standard library only）。

本脚本独立于 render_candidate.validate，专用于检查候选项目是否符合毕设选题的
功能数量、场景具体性、模块化偏好、无假大空与无 PCB/数模电路等约束。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 候选 level 规则（按 purpose 决定；毕设/课程设计 ≥7，具体数量由题目发散决定）
FEATURE_RANGES = {
    "graduation_capstone": (7, 15),  # 毕业设计
    "course_project": (7, 15),       # 课程设计
    "competition": (5, 15),          # 竞赛
    "default": (3, 15),              # 个人练手/未声明用途
}

# 禁止在候选中出现的“假大空”或暗示需手绘电路的措辞
FORBIDDEN_PATTERNS = [
    (re.compile(r"自绘\s*PCB|自制电路|手工焊接|自行设计电路|数模混合电路|自研芯片|FPGA\s*自研"), "禁止要求用户自绘 PCB / 设计电路"),
    (re.compile(r"大规模部署|全自动生产线|城市级|完全覆盖|首创|世界一流"), "禁止假大空/无工程依据的修饰"),
    (re.compile(r"云计算集群|大(?:数据|规模)\s*集群|分布式集群"), "禁止依赖超出毕设规模的服务器集群"),
]

# 场景具体性：概述/功能描述中至少出现一个场景锚词
SCENE_ANCHORS = (
    r"温室|大棚|化工厂|路边|校园|宿舍|教室|实验室|办公|仓库|物流|停车场|家居|厨房|卧室|浴室|养老|医院|诊所|药店|超市|便利店|餐厅|后厨|农田|鱼塘|养殖|蜂场|果园|茶园|"
    r"变电站|机房|展厅|博物馆|图书馆|公交站|地铁站|电梯|井道|楼道|走廊|阳台|花房|宠物|猫|狗|水产|水族|鱼缸|草坪|"
    r"安装在|部署在|放置在|固定在|用于|面向|服务|帮助|协助|供\s*\S+使用"
)
SCENE_RE = re.compile(SCENE_ANCHORS)

# 功能描述必须有具体行为动词（不是只有“监测”“管理”“控制”三选一）
ACTION_RE = re.compile(r"(采集|显示|报警|提醒|通知|发送|接收|记录|保存|切换|计算|分析|控制|驱动|播放|识别|检测|判断|定位|跟踪|追踪|上传|下载|同步|打印|扫描|加热|制冷|加湿|除湿|开关|调速|调光|计费|计数|对时|校准)")

VAGUE_FEATURES = re.compile(r"^\s*(智能监测|智慧管理|数据分析|云平台|物联网方案|综合管控|全面感知)\s*$")

# 题目过窄/过宽：过窄到单一作物/病害/算法，过宽到“智慧城市”式口号
TOO_SPECIFIC_TITLE = re.compile(
    r"(番茄|黄瓜|苹果|柑橘|小麦|水稻|玉米|草莓|葡萄|茶叶|烟叶).*(病|虫|叶|果|斑)|"
    r"基于\s*(?:YOLO|CNN|ResNet|Transformer|BERT|GPT)\S*",
    re.I,
)
TOO_BROAD_TITLE = re.compile(r"智慧城市|智慧农业|万物互联|全行业|综合管理平台|智慧平台|全自动生产线", re.I)

# 功能发散覆盖：至少覆盖 4 类，避免 7 条功能全是“采集 X”
FUNCTION_CATEGORIES = {
    "采集/监测": ("采集", "检测", "测量", "读取", "采样", "传感", "识别", "定位", "跟踪"),
    "显示/交互": ("显示", "屏幕", "页面", "按键", "触摸", "语音", "提示", "界面"),
    "告警/提醒": ("报警", "告警", "提醒", "通知", "蜂鸣", "静音"),
    "通信/远程": ("无线", "通信", "上传", "远程", "网络", "发送", "接收", "蓝牙", "wifi", "4g", "同步"),
    "配置/存储": ("配置", "设置", "保存", "存储", "记录", "参数", "阈值", "校准", "标定"),
    "异常/自检": ("异常", "故障", "自检", "断线", "超时", "超载", "无效"),
    "统计/数据": ("统计", "分析", "报表", "查询", "历史", "趋势", "计数", "估算"),
}


def check_text_has_scene(text: str) -> bool:
    return bool(SCENE_RE.search(text or ""))


def check_features_have_action(features: list[dict]) -> bool:
    for feature in features:
        desc = feature.get("description", "") or feature.get("name", "")
        if ACTION_RE.search(desc):
            return True
    return False


def has_vague_only(features: list[dict]) -> list[str]:
    vague: list[str] = []
    for feature in features:
        name = feature.get("name", "")
        if VAGUE_FEATURES.match(str(name).strip()):
            vague.append(name)
    return vague


def check_title_generality(title: str) -> list[str]:
    """题目应泛化到“应用场景 + 核心能力”，不要窄到单一作物/病害/算法，也不要宽成口号。"""
    warnings: list[str] = []
    title = title or ""
    if TOO_SPECIFIC_TITLE.search(title):
        warnings.append("题目可能过窄：绑定了单一作物/病害/算法；建议向上泛化到“场景+核心能力”，把具体对象放到功能里")
    if TOO_BROAD_TITLE.search(title):
        warnings.append("题目可能过宽/假大空：建议收窄到一个具体场景与可验证能力")
    if len(title.strip()) > 45:
        warnings.append("题目偏长：建议压缩到“应用场景 + 核心能力”")
    return warnings


def covered_categories(features: list[dict]) -> list[str]:
    covered: list[str] = []
    for name, keys in FUNCTION_CATEGORIES.items():
        text = " ".join(str(f.get("name", "")) + " " + str(f.get("description", "")) for f in features).lower()
        if any(key.lower() in text for key in keys):
            covered.append(name)
    return covered


def check_candidate(data: dict, purpose: str = "default") -> dict:
    """检查单个候选项目的毕设选题质量。"""
    errors: list[str] = []
    warnings: list[str] = []
    low, high = FEATURE_RANGES.get(purpose, (3, 15))
    features = data.get("features", [])
    title = data.get("title", "")
    overview = data.get("overview", "")
    n = len(features)
    if n < low:
        errors.append(f"功能数量不足：{n} 条（\"{purpose}\" 至少需要 {low} 条核心功能）")
    if n > high:
        errors.append(f"功能数量超出上限：{n} 条（最多 {high} 条）")
    if overview and not check_text_has_scene(overview):
        warnings.append("概述未出现具体服务场所/用户类型；建议加入\"温室/宿舍/仓库/…\"等场景锚词")
    if not check_features_have_action(features):
        warnings.append("功能描述中未发现具体行为动词（如采集、显示、报警、控制…）；建议每条功能写清楚触发→操作→可观察闭环")
    warnings.extend(check_title_generality(title))
    categories = covered_categories(features)
    if n >= 7 and len(categories) < 4:
        warnings.append(f"功能类别覆盖不足：仅 {len(categories)} 类（{', '.join(categories) or '无'}）；建议从采集/显示/告警/通信/配置/异常/统计至少覆盖 4 类，按题目发散而非重复同类功能")
    vague = has_vague_only(features)
    if vague:
        errors.append(f"存在空洞功能名（只写标签、不说做什么）：{', '.join(vague[:5])}")
    full = title + " " + overview + " " + " ".join(f.get("description", "") for f in features)
    for regex, label in FORBIDDEN_PATTERNS:
        if regex.search(full):
            errors.append(label)
    return {"errors": errors, "warnings": warnings}


def check_batch(projects: list[dict], purpose: str = "default") -> dict:
    """检查整批候选项目的选题质量。"""
    results: list[dict] = []
    all_errors = 0
    all_warnings = 0
    for i, proj in enumerate(projects):
        r = check_candidate(proj, purpose)
        title = proj.get("title", f"候选 #{i + 1}")
        r["title"] = title
        results.append(r)
        all_errors += len(r["errors"])
        all_warnings += len(r["warnings"])
    status = "FAIL" if all_errors else ("WARN" if all_warnings else "PASS")
    return {
        "status": status,
        "purpose": purpose,
        "projects": len(projects),
        "errors": all_errors,
        "warnings": all_warnings,
        "results": results,
    }


def check_profile(profile: dict) -> dict:
    """检查 profile.json 不包含预算/周期字段。"""
    errors: list[str] = []
    for key in ("budget", "timeframe", "budget_limit", "deadline", "completion_date"):
        if key in profile:
            errors.append(f"profile 不应包含 '{key}' 字段，请通过 constraints 表达功能/规模边界")
    return {"errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="毕设/课程设计候选选题质量检查")
    parser.add_argument("--candidate-file", type=Path, help="单个候选 project.json")
    parser.add_argument("--batch-file", type=Path, help="整批候选 JSON")
    parser.add_argument("--profile-file", type=Path, help="discovery/profile.json")
    parser.add_argument("--purpose", default="default", choices=("graduation_capstone", "course_project", "competition", "default"),
                        help="项目用途类型")
    parser.add_argument("--report", type=Path, help="JSON 报告")
    args = parser.parse_args(argv)
    if not any((args.candidate_file, args.batch_file, args.profile_file)):
        parser.error("至少需要一个检查目标")
    results: dict = {}
    errors = 0
    warnings = 0
    try:
        if args.batch_file:
            data = json.loads(args.batch_file.read_text(encoding="utf-8"))
            projects = data.get("projects", []) if isinstance(data, dict) else data
            r = check_batch(projects, args.purpose)
            results["batch"] = r
            errors += r["errors"]
            warnings += r["warnings"]
        if args.candidate_file:
            data = json.loads(args.candidate_file.read_text(encoding="utf-8"))
            r = check_candidate(data, args.purpose)
            results["candidate"] = r
            errors += len(r["errors"])
            warnings += len(r["warnings"])
        if args.profile_file:
            data = json.loads(args.profile_file.read_text(encoding="utf-8"))
            known = data.get("known", data)
            r = check_profile(known)
            results["profile"] = r
            errors += len(r["errors"])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    report = {"status": status, "errors": errors, "warnings": warnings, **results}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "errors": errors, "warnings": warnings}, ensure_ascii=False))
    for result in (results.get("batch", {}).get("results") or [results.get("candidate")] if results.get("candidate") else []):
        for error in result.get("errors") or []:
            print(f"ERROR: [{result.get('title','')}] {error}")
        for warning in result.get("warnings") or []:
            print(f"WARN: [{result.get('title','')}] {warning}")
    for error in results.get("profile", {}).get("errors") or []:
        print(f"ERROR: [profile] {error}")
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())