#!/usr/bin/env python3
"""Static QA for the generated project-introduction HTML.

Checks the HTML as a visualization of the intro Markdown only:
- offline single file, no external scripts/fonts/images;
- no implementation-level leakage (GPIO/USART/DMA/CRC/code/secrets);
- feature cards match the Markdown feature headings;
- responsive scaffold and long-text safeguards;
- demo data explicitly marked as preview / not measured.

This is a static checker; it does not replace browser rendering or human review.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HARD_TERMS = (
    (r"\bGPIO\b", "GPIO"),
    (r"\bUSART\b", "USART"),
    (r"\bUART\b", "UART"),
    (r"\bI2C\b", "I2C"),
    (r"\bSPI\b", "SPI"),
    (r"\bDMA\b", "DMA"),
    (r"\bCRC(?:8|16|32)?\b", "CRC"),
    (r"\bADC\b", "ADC"),
    (r"\bPWM\b", "PWM"),
    (r"\bFlash\b", "Flash"),
    (r"\bEEPROM\b", "EEPROM"),
    (r"\bCubeMX\b", "CubeMX"),
    (r"\bAT\+", "AT 指令"),
    (r"寄存器", "寄存器"),
    (r"引脚", "引脚"),
    (r"波特率", "波特率"),
    (r"#include", "代码引用"),
    (r"\bP[ABC]\d{1,2}\b", "MCU 引脚名"),
    (r"接线图|电气接线|原理图", "接线/原理图"),
    (r"(?i)\b(?:api[_ -]?key|secret|password|passwd|token)\s*[:=]", "疑似凭据"),
    (r"付费|收费|售价|购买链接|下单", "商业措辞"),
)
SOFT_TERMS = (
    (r"\bMQTT\b", "MQTT"),
    (r"\bJSON\b", "JSON"),
    (r"\bAPI\b", "API"),
    (r"协议", "协议"),
    (r"端口", "端口"),
    (r"部署命令|部署步骤|docker|kubectl|systemctl|pip install|npm install|apt-get|sudo\b", "部署/命令"),
    (r"源码|代码", "代码"),
    (r"固件", "固件"),
    (r"工程实施方案", "工程实施方案"),
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style", "svg"):
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "svg") and self.skip:
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def clean_title(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_~]", "", text)
    return normalize(text)


def visible_text(html_text: str) -> str:
    parser = TextExtractor()
    parser.feed(html_text)
    return normalize("".join(parser.parts))


def extract_data(html_text: str) -> dict:
    match = re.search(
        r'<script[^>]*id="project-data"[^>]*>(.*?)</script>',
        html_text,
        re.S | re.I,
    )
    if not match:
        raise ValueError("未找到 <script id=\"project-data\"> 结构化数据块")
    return json.loads(match.group(1))


def md_feature_titles(md: str) -> list[str]:
    titles: list[str] = []
    in_features = False
    for line in md.replace("\r\n", "\n").split("\n"):
        if re.match(r"^##\s+", line):
            in_features = bool(re.search(r"功能说明|功能介绍|核心功能|功能模块", line))
            continue
        if in_features:
            match = re.match(r"^###\s+(.*)$", line)
            if match:
                title = re.sub(r"^\d+(?:\.\d+)*[.、]?\s*", "", match.group(1).strip())
                title = clean_title(title)
                if title:
                    titles.append(title)
    return titles


def count_tag(html_text: str, tag: str) -> int:
    return len(re.findall(rf"<{tag}\b", html_text, re.I))


def check(html_text: str, md_text: str) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    text = visible_text(html_text)

    # 1. Basic single-file scaffold
    if not re.match(r"^\s*<!doctype html>", html_text, re.I):
        errors.append("缺少 <!doctype html>")
    if not re.search(r"<html[^>]+lang=[\"']zh-CN[\"']", html_text, re.I):
        errors.append("缺少 lang=\"zh-CN\"")
    if not re.search(r"<meta[^>]+name=[\"']viewport[\"'][^>]+content=", html_text, re.I):
        errors.append("缺少 viewport 响应式声明")
    if count_tag(html_text, "style") != 1:
        errors.append("应只有一个内联 <style>，保持单文件")
    script_count = count_tag(html_text, "script")
    if script_count != 2:
        errors.append(f"应只有数据块 + 逻辑块两个 <script>，实际 {script_count} 个")

    # 2. Offline: no external resources
    external_patterns = (
        (r"<script[^>]+src\s*=", "外部 script"),
        (r"<link[^>]+href\s*=", "外部 link/字体"),
        (r"<img[^>]+src\s*=\s*[\"'](?:https?:)?//", "外部图片"),
        (r"@import", "CSS @import"),
        (r"url\(\s*[\"']?(?:https?:)?//", "CSS 远程 url()"),
        (r"<iframe\b|<object\b|<embed\b", "嵌入外部内容"),
    )
    for pattern, label in external_patterns:
        if re.search(pattern, html_text, re.I):
            errors.append(f"存在{label}，页面不是离线单文件")

    # 3. Safety
    if re.search(r"<[^>]+\son\w+\s*=", html_text, re.I):
        errors.append("存在内联事件处理器，需改为 addEventListener")
    if re.search(r"(?:href|src)\s*=\s*[\"']javascript:", html_text, re.I):
        errors.append("存在 javascript: 链接")
    if re.search(r"\binnerHTML\b|\bdocument\.write\b|\beval\s*\(", html_text):
        errors.append("存在 innerHTML/document.write/eval，用户文本必须用 textContent")
    if "<form" in html_text.lower():
        errors.append("静态介绍页不应包含表单")

    # 4. Implementation leakage
    for pattern, label in HARD_TERMS:
        if re.search(pattern, text, re.I):
            errors.append(f"页面出现实施层内容：{label}")
    for pattern, label in SOFT_TERMS:
        if re.search(pattern, text, re.I):
            warnings.append(f"页面出现可能偏技术的词：{label}（需人工确认是否越界）")

    # 5. Structure / responsive scaffold
    if len(re.findall(r"@media\s*\(", html_text)) < 2:
        errors.append("响应式断点不足（至少 2 个 @media）")
    for token in ("auto-fit", "max-width", "box-sizing", "overflow-wrap"):
        if token not in html_text:
            warnings.append(f"未发现 {token}，请人工检查长标题/多卡片布局")

    # 6. Structured data consistency
    try:
        data = extract_data(html_text)
    except (ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
        data = {}
    features = data.get("features") or []
    demo = (data.get("demo") or {}).get("items") or []
    md_titles = md_feature_titles(md_text)
    clean_md = clean_title(md_text)
    if md_titles:
        if len(features) != len(md_titles):
            warnings.append(f"HTML 功能数 {len(features)} 与 Markdown 功能小节数 {len(md_titles)} 不一致")
        for title in [f.get("title", "") for f in features]:
            if title and title not in clean_md:
                errors.append(f"HTML 出现 Markdown 中没有的功能：{title}")
    elif not features:
        warnings.append("Markdown 未识别到功能小节，HTML 也没有功能卡片")
    data_cards = len(re.findall(r"data-feature=", html_text))
    if data_cards != len(features):
        errors.append(f"功能卡片数 {data_cards} 与结构化数据 {len(features)} 不一致")
    for feature in features:
        if feature.get("title") and feature["title"] not in text:
            errors.append(f"功能卡片文字缺失：{feature['title']}")
    title = (data.get("project") or {}).get("title", "")
    if title:
        if title not in html_text:
            warnings.append("页面源码未直接出现完整项目题目")
    else:
        errors.append("结构化数据缺少 project.title")
    if demo:
        if "未实测" not in text and "示意数据" not in text:
            errors.append("存在场景示意数据，但页面未标注未实测/示意数据")
        if "验收场景" not in text and "场景" not in text:
            warnings.append("场景示意区缺少场景说明")
    if not features:
        warnings.append("页面没有功能卡片，需确认介绍 Markdown 是否缺少功能小节")

    status = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "features": len(features),
            "workflow": len(data.get("workflow") or []),
            "scenarios": len(data.get("scenarios") or []),
            "demo": len(demo),
            "md_feature_headings": len(md_titles),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查项目介绍 HTML 的内容边界与离线安全")
    parser.add_argument("--intro", type=Path, required=True, help="项目介绍 Markdown")
    parser.add_argument("--html", type=Path, required=True, help="生成的 HTML")
    parser.add_argument("--report", type=Path, help="可选 JSON 报告")
    args = parser.parse_args(argv)
    try:
        md_text = args.intro.read_text(encoding="utf-8-sig")
        html_text = args.html.read_text(encoding="utf-8-sig")
        report = check(html_text, md_text)
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": len(report["errors"]), "warnings": len(report["warnings"])}, ensure_ascii=False))
    for error in report["errors"]:
        print("ERROR:", error)
    for warning in report["warnings"]:
        print("WARN:", warning)
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())