#!/usr/bin/env python3
"""Shared heuristics for project-technical-doc content classification.

Used by:
  * scripts/gen_physical_modules.py  -> physical-modules.json
  * scripts/classify_content.py      -> content-index.json

Pure stdlib; never reads project source code and never writes the technical MD.
"""
from __future__ import annotations

import hashlib
import re

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
NUMBER_PREFIX = re.compile(r"^\s*\d+(?:\.\d+)*[\.、]?\s*")
BACKTICK = re.compile(r"`([^`]+)`")
PAREN = re.compile(r"[（(]\s*([^）)]+?)\s*[）)]")
LATIN = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9_+.-]{1,})(?![A-Za-z0-9_])")
SOURCE_FILE = re.compile(r"(?<![\w/\\])([A-Za-z0-9_.-]+\.(?:c|h|cpp|hpp|py|js|ino|java|kt))", re.I)
PIN = re.compile(r"(?<![A-Za-z0-9_])((?:I2C|SPI|USART|UART|ADC|GPIO|CAN|USB)\d?|P[ABCD]\d+)(?![A-Za-z0-9_])", re.I)
ABS_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|/)")

CATEGORIES = ("sensor", "actuator", "display", "input", "communication", "other")
CATEGORY_CN = {
    "sensor": "传感器模块",
    "actuator": "执行器模块",
    "display": "显示模块",
    "input": "交互输入模块",
    "communication": "通信模块",
    "other": "其他实物模块",
    "data-structure": "数据结构",
    "protocol": "通信协议",
    "interface-pin": "引脚与接口",
    "parameter-config": "参数与配置",
    "flow": "流程图",
    "architecture": "架构图",
    "test": "测试与结果",
    "specification": "规格与选型",
    "function": "功能与场景",
    "schedule": "任务与调度",
    "technology": "技术说明",
    "appendix": "附录与速查",
    "hardware-resource": "硬件资源与分配",
    "terminology": "术语与定义",
    "index": "索引与目录",
    "materials": "资料与参考",
    "excluded": "已排除章节",
    "module": "模块",
    "other-table": "其他数据表",
}

GENERIC_CODES = {
    "def", "struct", "typedef", "config", "handle", "data", "type", "types",
    "module", "modules", "sensor", "sensors", "module", "h", "c", "cpp", "hpp",
    "const", "void", "int", "float", "uint8", "uint16", "uint32", "bool",
    "true", "false", "null", "none", "and", "the", "for", "with",
    "i2c", "spi", "usart", "uart", "adc", "gpio", "can", "usb", "dma",
    "gpio", "tim", "rcc", "nvic", "hal",
}

KNOWN_CODES = (
    "STM32F103", "SIM900A", "SIM800", "SHT40", "SHT30", "DHT22", "DHT11",
    "BH1750", "ESP32", "RS485", "RS232", "OLED", "LCD", "GPS", "DTU",
    "Modbus", "LoRa", "Lora", "WiFi", "BLE", "NB-IoT",
    "D1", "4G", "5G",
)

PHYSICAL_KEYWORDS = {
    "sensor": ("传感器", "采集", "检测", "探头", "变送器", "温湿度", "粉尘", "火焰", "土壤", "水浸", "倾角", "气压", "氨气", "gps", "定位"),
    "actuator": ("执行器", "电机", "继电器", "蜂鸣器", "泵", "阀", "舵机", "风扇", "加热"),
    "display": ("oled", "lcd", "显示屏", "显示模块", "屏幕", "数码管"),
    "input": ("按键", "按钮", "触摸", "键盘", "开关", "旋钮"),
    "communication": ("4g", "5g", "gsm", "wifi", "wi-fi", "lora", "nb-iot", "dtu", "通信模块", "串口", "rs485", "rs232", "modbus", "蓝牙", "以太网", "can", "短信", "sim"),
}
SOFTWARE_WORDS = ("通信抽象层", "软件模块", "纯逻辑", "主程序", "模块间关系", "驱动框架", "协议栈", "抽象层",
                  "数据处理", "系统控制", "告警管理", "管理模块", "数据中枢", "主循环调度", "业务逻辑")
SOFTWARE_CODE = re.compile(r"^(?:main|warn)$", re.I)
SOFTWARE_UNDERSCORE = re.compile(r"^[a-z][a-z0-9]*_[a-z0-9_]+$")


def strip_number(text):
    return NUMBER_PREFIX.sub("", str(text)).strip()


def heading_marks(lines):
    marks = []
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if m:
            marks.append((i, len(m.group(1)), m.group(2).strip()))
    return marks


def nearest_heading(marks, line_index):
    h2 = h3 = h4 = None
    for idx, level, title in marks:
        if idx > line_index:
            break
        if level == 2:
            h2 = title
            h3 = h4 = None
        elif level == 3:
            h3 = title
            h4 = None
        elif level == 4:
            h4 = title
    return h2, h3, h4


def module_sections(lines):
    """H3 sections under a '模块详解' H2; None if the chapter is absent."""
    marks = heading_marks(lines)
    start = None
    for idx, (line_idx, level, title) in enumerate(marks):
        if level == 2 and "模块详解" in title:
            start = idx
            break
    if start is None:
        return None
    sections = []
    for line_idx, level, title in marks[start + 1:]:
        if level <= 2:
            break
        if level == 3:
            sections.append((line_idx + 1, title))
    return sections


def section_body(lines, start_line, next_heading_line=None):
    start = max(0, start_line - 1)
    end = len(lines) if next_heading_line is None else max(start, next_heading_line - 1)
    return "\n".join(lines[start:end])


def best_code_token(text):
    """Pick a stable module/protocol token from a title; fall back to Chinese."""
    raw = strip_number(text)
    main = PAREN.sub(" ", raw)
    known = known_code(main) or known_code(raw)
    if known:
        return known
    candidates = LATIN.findall(main)
    if not candidates:
        for token in PAREN.findall(raw):
            candidates.extend(LATIN.findall(token))
    cleaned = []
    for token in candidates:
        token = token.strip("`()（）[]【】 ,.;:：，。")
        if not token or token.casefold() in GENERIC_CODES:
            continue
        score = 0
        if any(ch.isdigit() for ch in token):
            score += 3
        if token.isupper() and len(token) >= 2:
            score += 2
        if token[0].isupper():
            score += 1
        cleaned.append((score, len(token), token))
    if cleaned:
        cleaned.sort(key=lambda x: (-x[0], -x[1]))
        return cleaned[0][2]
    # Chinese fallback: the main title without parenthetical explanations.
    zh = re.sub(r"[`（）()【】\[\]，。；：,.;:]", " ", main)
    zh = re.sub(r"\s+", " ", zh).strip()
    for word in zh.split(" "):
        if len(word) >= 2 and any("一" <= ch <= "鿿" for ch in word):
            return word
    return zh[:12] or "模块"

def known_code(text):
    """Longest known product/protocol code present at a token/CamelCase prefix."""
    hits = []
    for code in KNOWN_CODES:
        # Allow LoraRemoteData / UartComm / SHT40_DataTypeDef, but not D10 for D1.
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(code) + r"(?=[A-Za-z_]|[^A-Za-z0-9_]|$)"
        if re.search(pattern, text, re.I):
            hits.append(code)
    if not hits:
        return None
    hits.sort(key=len, reverse=True)
    return hits[0]


def module_code_from_text(text):
    """Module/protocol code used for grouping tables (SHT40 / RS485 / Modbus / D1)."""
    known = known_code(text)
    if known:
        return known
    token = best_code_token(text)
    if token and token.casefold() not in GENERIC_CODES:
        # LoraRemoteData_t -> LoraRemoteData; UartComm_ConfigTypeDef -> UartComm
        head = re.split(r"[_\-]", token)[0]
        if len(head) >= 2 and head.casefold() not in GENERIC_CODES:
            return head
        return token
    return None


def classify_physical(title, body):
    text = (title + "\n" + body).casefold()
    if any(word in text for word in SOFTWARE_WORDS):
        return None
    for category in ("display", "input", "actuator", "communication", "sensor"):
        if any(word in text for word in PHYSICAL_KEYWORDS[category]):
            return category
    # A section literally named "xx模块" with no software marker is treated as
    # physical only when a device/interface noun is present.
    if any(word in text for word in ("模块", "器件", "外设", "接口")) and not any(
            word in text for word in ("软件", "逻辑", "算法", "数据结构")):
        return "other"
    return None


def is_software_section(title, body):
    code = best_code_token(title)
    if SOFTWARE_CODE.match(code) or SOFTWARE_UNDERSCORE.match(code):
        return True
    return any(word in (title + body) for word in SOFTWARE_WORDS)


def extract_source_files(body):
    out = []
    for name in SOURCE_FILE.findall(body):
        if name not in out:
            out.append(name)
    return out


def extract_pins(body):
    out = []
    for pin in PIN.findall(body):
        pin = pin.upper()
        if pin not in out:
            out.append(pin)
    return out


def first_sentence(body, limit=120):
    for line in body.splitlines():
        text = line.strip()
        if not text or text.startswith(("#", "```", "|", ">", "-", "*")):
            continue
        text = re.sub(r"[`*_]", "", text)
        # Split at Chinese sentence enders immediately, but only split an
        # English period when followed by whitespace (so 0.96 is not cut).
        parts = re.split(r"(?<=[。！？!?])\s*|(?<=\.)\s+", text, maxsplit=1)
        sentence = parts[0].strip()
        if sentence:
            return sentence[:limit]
    return ""


TABLE_RULES = {
    # Content signals in the header/caption dominate the chapter heading.
    # Weight: header 3, caption/title 2 (title is caption when present).
    "data-structure": {
        "header": ("字段", "成员", "变量", "偏移", "长度", "返回码", "状态码",
                   "错误码", "枚举"),
        "title": ("数据结构", "结构体", "datatype", "typedef", "字段", "枚举",
                  "返回码", "状态码", "错误码"),
    },
    "protocol": {
        "header": ("帧", "字节", "命令", "功能码", "寄存器", "地址", "校验", "crc",
                   "返回码", "错误码", "指令", "应答", "解析用途"),
        "title": ("协议", "帧", "命令", "寄存器", "modbus", "crc", "at指令",
                  "at 指令", "校验", "指令"),
    },
    "interface-pin": {
        "header": ("引脚", "接口", "端口", "外设", "复用", "器件", "地址", "通道"),
        "title": ("引脚", "接口", "资源分配", "外设", "端口", "i2c", "spi",
                  "uart", "usart", "器件地址"),
    },
    "parameter-config": {
        "header": ("参数", "默认值", "阈值", "配置", "取值", "范围", "取值范围",
                   "模拟量", "表达式", "单位"),
        "title": ("参数", "阈值", "配置", "默认值", "注入机制", "标定", "常量",
                  "取值范围"),
    },
    "hardware-resource": {
        "header": ("中断", "优先级", "缓冲区", "dma", "定时器", "通道", "资源",
                   "分配", "大小", "用途"),
        "title": ("资源", "中断", "优先级", "dma", "定时器", "通道", "缓冲区"),
    },
    "architecture": {
        "header": ("层级", "层次", "组成", "职责", "模块", "子系统"),
        "title": ("架构", "框架", "层次", "分层", "组成", "子系统", "模块划分"),
    },
    "flow": {
        "header": ("状态", "转移", "动作", "异常", "恢复", "步骤", "条件", "分支"),
        "title": ("流程", "状态机", "步骤", "转移", "恢复", "异常处理"),
    },
    "test": {
        "header": ("测试项", "用例", "操作", "预期结果", "结果", "编号"),
        "title": ("测试", "用例", "结果"),
    },
    "terminology": {
        "header": ("术语", "缩写", "英文", "定义"),
        "title": ("术语", "缩写", "定义", "名词"),
    },
    "index": {
        "header": ("索引", "编号", "页码", "章节", "目录"),
        "title": ("索引", "目录", "编号"),
    },
    "materials": {
        "header": ("资料", "文档", "标准", "手册", "参考", "来源"),
        "title": ("资料", "参考", "文档", "标准", "手册"),
    },
    "function": {
        "header": ("功能", "实现模块", "关键手段", "状态", "角色", "职责",
                   "场景", "环节", "行为"),
        "title": ("功能", "场景", "角色", "映射"),
    },
    "specification": {
        "header": ("项目", "规格", "方案", "评估", "结论", "部件"),
        "title": ("规格", "选型", "外围电路"),
    },
    "schedule": {
        "header": ("任务", "周期", "职责"),
        "title": ("调度", "周期"),
    },
    "technology": {
        "header": ("技术", "实现", "要点"),
        "title": ("技术", "解析", "采集技术"),
    },
    "appendix": {
        "header": (),
        "title": ("附录", "速查", "模板"),
    },
}
TABLE_PRIORITY = [
    "excluded", "data-structure", "protocol", "parameter-config", "hardware-resource",
    "interface-pin", "architecture", "flow", "test", "terminology", "index",
    "materials", "appendix", "function", "specification", "schedule", "technology",
]


def classify_table(headers, title, caption=""):
    """Classify by table header/caption content, not by the chapter name.

    Header hits dominate (3 points each); the caption/title is a 2-point signal.
    The caller should pass the table's own caption (表 X-Y ...) as ``caption``
    and the nearest heading as ``title``.  A chapter heading alone cannot force
    a table into test/appendix when its headers say parameter/data-structure.
    """
    header_text = " ".join(str(h) for h in headers).casefold()
    title_text = (str(caption or "") + " " + str(title or "")).casefold()
    if any(word in title_text for word in ("已知问题", "改进建议", "风险与对策",
                                          "未来展望", "后续规划")):
        return "excluded"
    scores = {}
    for category, rule in TABLE_RULES.items():
        score = 0
        for word in rule["header"]:
            if word.casefold() in header_text:
                score += 3
        for word in rule["title"]:
            if word.casefold() in title_text:
                score += 2
        scores[category] = score
    best = max(scores.values()) if scores else 0
    if best == 0:
        return "other-table"
    for category in TABLE_PRIORITY:
        if scores.get(category, 0) == best:
            return category
    return "other-table"

def classify_diagram(content, title):
    title_l = title.casefold()
    if any(word in title_l for word in ("架构", "框架", "层次", "分层", "组成")):
        return "architecture"
    if re.search(r"^\s*(?:graph|flowchart)\s+(?:LR|RL|TB|TD|BT)\s*$", content, re.M) and "subgraph" in content:
        return "architecture"
    if "-->" in content or "--" in content or "{}" in content:
        return "flow"
    return "other"


def extract_keywords(text, limit=8):
    words = []
    for token in LATIN.findall(text):
        token = token.strip("`()（）[]【】 ,.;:：，。")
        if token and token.casefold() not in GENERIC_CODES and token not in words:
            words.append(token)
    for term in ("数据结构", "通信协议", "引脚", "接口", "参数", "阈值", "配置",
                 "流程", "架构", "模块", "测试", "结果", "帧", "命令", "寄存器", "校验"):
        if term in text and term not in words:
            words.append(term)
    return words[:limit]


def stable_group_id(title):
    return "GRP-" + hashlib.sha1(title.encode("utf-8")).hexdigest()[:8].upper()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()