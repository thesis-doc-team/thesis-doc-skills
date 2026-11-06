"""Regression tests for the project-introduction HTML generator and validator.

Covers:
- three project types with different feature counts (3 / 6 / 10);
- missing optional sections hiding instead of inventing;
- long titles/descriptions and dynamic card counts;
- XSS-safe text handling;
- single-file/offline scaffold;
- validator rejection of external resources, implementation leakage, inline
  handlers and missing "not measured" labels.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "generate_intro_html.py"
VAL = ROOT / "scripts" / "validate_intro_html.py"


def make_md(title, features, workflow=None, scenarios=None, system=None, demo=None, overview=None):
    lines = [
        f"# {title}｜项目介绍与功能说明",
        "",
        "> 版本：V1.0",
        "> 文档状态：拟实施方案",
        "",
        "## 1. 项目概述",
        overview or f"本系统围绕 {title} 的核心场景展开，提供必要的采集、处理与展示能力。",
        "",
        "## 2. 应用场景与系统目标",
        "",
    ]
    if scenarios:
        lines.append("### 2.1 典型场景")
        lines.extend(f"- {item}" for item in scenarios)
        lines.append("")
    lines.extend(["### 2.2 系统目标", "1. 完成用户确认的主要功能。", ""])
    lines.extend(["## 3. 功能说明", ""])
    for index, (name, description) in enumerate(features, 1):
        lines.extend([f"### 3.{index} {name}", description, ""])
    lines.extend(["## 4. 系统组成概览", ""])
    if system:
        lines.extend(["| 组成部分 | 作用 |", "|---|---|"])
        lines.extend(f"| {item} | 承担相应职责 |" for item in system)
        lines.append("")
    lines.extend(["## 5. 使用与交互流程", ""])
    if workflow:
        lines.append("### 5.1 首次使用")
        lines.extend(f"{index}. {item}" for index, item in enumerate(workflow, 1))
        lines.append("")
    lines.extend(["## 6. 使用条件与运行边界", "1. 按现场条件使用，未标定前不宣称精度。", ""])
    lines.extend(["## 7. 功能展示与验收场景", ""])
    if demo:
        lines.extend(["| 编号 | 场景 | 操作 | 预期可观察结果 | 状态 |", "|---|---|---|---|---|"])
        for index, (scene, operation, expected) in enumerate(demo, 1):
            lines.append(f"| S{index:02d} | {scene} | {operation} | {expected} | 预期，待实测 |")
        lines.append("")
    return "\n".join(lines)


ENV_MD = make_md(
    "温室环境监测节点",
    [
        ("温湿度采集", "周期采集空气温度与湿度，并在本地屏幕上显示。"),
        ("光照监测", "采集光照强度，用于判断是否需要遮阳。"),
        ("无线通信", "周期上传环境数据到远程页面，网络异常时本地仍可显示。"),
    ],
    workflow=["安装传感器", "接通电源", "配置无线网络"],
    scenarios=["温室大棚的日常环境巡检", "实验室环境记录"],
    system=["传感器", "主控处理", "本地显示", "无线通信"],
    demo=[
        ("温湿度采集", "改变环境温度", "屏幕数值随之变化"),
        ("断网运行", "关闭无线网络", "本地显示与采集不中断"),
    ],
)

MIRROR_MD = make_md(
    "智能交互镜",
    [
        ("语音唤醒", "通过语音唤醒镜面助手。"),
        ("日程显示", "在镜面显示当天日程。"),
        ("天气信息", "显示本地天气与温度。"),
        ("音乐播放", "通过语音控制音乐播放。"),
        ("镜面显示", "在镜面上叠加时间、天气与提示。"),
        ("手机同步", "与手机端同步日程和偏好设置。"),
    ],
    workflow=["上电启动", "连接网络", "语音唤醒", "查看信息", "手机同步"],
    scenarios=["家庭玄关的日程与天气查看", "卧室的语音助手场景"],
    system=["麦克风", "主控处理", "镜面显示", "无线同步"],
    demo=[
        ("语音唤醒", "说出唤醒词", "镜面显示助手已唤醒"),
        ("日程查看", "询问今日日程", "镜面显示日程摘要"),
    ],
)

ROBOT_MD = make_md(
    "基于多传感器融合的智能巡检机器人系统",
    [(f"巡检功能{i}", f"完成第 {i} 项巡检任务，采集现场状态并上报。") for i in range(1, 11)],
    workflow=["部署机器人", "建立地图", "设置巡检点", "启动巡检", "回传数据", "异常复核"],
    scenarios=["园区夜间巡检", "机房设备巡检", "仓库通道巡检"],
    system=["移动底盘", "传感器", "主控", "无线", "云平台", "充电桩"],
    demo=[
        ("启动巡检", "下发巡检任务", "机器人按路线移动"),
        ("障碍物", "在路线中放置障碍", "机器人减速或绕行"),
        ("低电量", "模拟电量不足", "返回充电桩"),
    ],
)

MINIMAL_MD = make_md(
    "最小演示项目",
    [("唯一功能", "只做一件事：采集并显示一个状态。")],
    overview="这是一个只保留必要功能的最小项目。",
)

XSS_MD = make_md(
    "安全测试项目",
    [
        ('功能<script>alert(1)</script>', '描述中包含 "><img src=x onerror=alert(1)> 与 javascript:alert(1)。'),
    ],
    workflow=["打开页面"],
    scenarios=["正常场景"],
    system=["组件"],
    demo=[("正常场景", "点击", "页面显示正常")],
)

LONG_MD = make_md(
    "这是一个用于验证超长标题和超长描述在页面中能够正常换行而不会产生横向溢出的项目名称",
    [
        ("超长功能标题用于检查卡片在窄屏和多列布局下的换行表现", "这是一段很长的功能描述。" * 20),
    ],
    workflow=["第一步操作说明很长，需要在卡片内正常换行显示。" * 3],
    scenarios=["这是一个很长的应用场景描述，需要在卡片内正常换行显示，不能溢出容器。" * 2],
    system=["一个很长的系统组成名称用于检查标签换行"],
    demo=[("长场景标题", "长操作说明" * 5, "长预期结果" * 8)],
)


class TestHtmlGeneration(unittest.TestCase):
    def run_generator(self, md_text):
        tmp = Path(tempfile.mkdtemp())
        intro = tmp / "intro.md"
        intro.write_text(md_text, encoding="utf-8")
        out = tmp / "intro.html"
        data = tmp / "data.json"
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        cp = subprocess.run(
            [sys.executable, str(GEN), "--intro", str(intro), "--out", str(out), "--data-out", str(data)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        html = out.read_text(encoding="utf-8") if out.exists() else ""
        payload = json.loads(data.read_text(encoding="utf-8")) if data.exists() else {}
        return cp, intro, out, html, payload

    def run_validator(self, intro, html_path):
        report = html_path.parent / "qa.json"
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        cp = subprocess.run(
            [sys.executable, str(VAL), "--intro", str(intro), "--html", str(html_path), "--report", str(report)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        payload = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
        return cp, payload

    def test_environment_project_generates_and_validates(self):
        cp, intro, out, html, data = self.run_generator(ENV_MD)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual(len(data["features"]), 3)
        self.assertEqual(len(data["workflow"]), 3)
        self.assertEqual(len(data["scenarios"]), 2)
        self.assertEqual(len(data["demo"]["items"]), 2)
        self.assertIn("温湿度采集", html)
        self.assertIn("无线通信", html)
        vcp, report = self.run_validator(intro, out)
        self.assertEqual(vcp.returncode, 0, vcp.stdout + vcp.stderr)
        self.assertEqual(report["status"], "PASS")

    def test_smart_mirror_project(self):
        cp, intro, out, html, data = self.run_generator(MIRROR_MD)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual(len(data["features"]), 6)
        self.assertEqual(len(data["workflow"]), 5)
        self.assertEqual(html.count("data-feature="), 6)
        vcp, report = self.run_validator(intro, out)
        self.assertEqual(vcp.returncode, 0, vcp.stdout + vcp.stderr)
        self.assertEqual(report["status"], "PASS")

    def test_robot_project_ten_features_and_long_title(self):
        cp, intro, out, html, data = self.run_generator(ROBOT_MD)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual(len(data["features"]), 10)
        self.assertEqual(len(data["workflow"]), 6)
        self.assertEqual(html.count("data-feature="), 10)
        self.assertIn("智能巡检机器人", html)
        vcp, report = self.run_validator(intro, out)
        self.assertEqual(vcp.returncode, 0, vcp.stdout + vcp.stderr)
        self.assertEqual(report["status"], "PASS")

    def test_minimal_project_hides_missing_sections(self):
        cp, intro, out, html, data = self.run_generator(MINIMAL_MD)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual(len(data["features"]), 1)
        self.assertEqual(data["workflow"], [])
        self.assertEqual(data["scenarios"], [])
        self.assertEqual(data["system"]["items"], [])
        self.assertEqual(data["demo"]["items"], [])
        for section_id in ('id="workflow"', 'id="scenes"', 'id="composition"', 'id="showcase"'):
            self.assertNotIn(section_id, html)
        self.assertIn("唯一功能", html)
        self.assertIn("WARN", cp.stdout)
        vcp, report = self.run_validator(intro, out)
        self.assertEqual(vcp.returncode, 0, vcp.stdout + vcp.stderr)

    def test_dynamic_feature_counts(self):
        counts = []
        for md in (ENV_MD, MIRROR_MD, ROBOT_MD):
            cp, _, _, html, data = self.run_generator(md)
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            counts.append(html.count("data-feature="))
            self.assertEqual(counts[-1], len(data["features"]))
        self.assertEqual(counts, [3, 6, 10])

    def test_xss_text_is_escaped(self):
        cp, intro, out, html, data = self.run_generator(XSS_MD)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn("onerror=alert(1)", html)
        self.assertIn("alert(1)", html)
        self.assertIn("&quot;&gt;", html)
        self.assertIn("安全测试项目", html)
        vcp, report = self.run_validator(intro, out)
        self.assertEqual(vcp.returncode, 0, vcp.stdout + vcp.stderr)

    def test_long_text_css_safeguards(self):
        cp, intro, out, html, data = self.run_generator(LONG_MD)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertIn("overflow-wrap:anywhere", html)
        match = re.search(r"\.title-accent\{([^}]*)\}", html)
        self.assertIsNotNone(match)
        self.assertNotIn("white-space:nowrap", match.group(1))
        self.assertIn("超长功能标题", html)
        vcp, report = self.run_validator(intro, out)
        self.assertEqual(vcp.returncode, 0, vcp.stdout + vcp.stderr)

    def test_single_file_offline_scaffold(self):
        cp, _, _, html, _ = self.run_generator(ENV_MD)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("<link", html.lower())
        self.assertNotIn("<img", html.lower())
        self.assertNotIn("@import", html)
        self.assertEqual(len(re.findall(r"<script\b", html, re.I)), 2)
        self.assertIn('name="viewport"', html)
        self.assertGreaterEqual(len(re.findall(r"@media\s*\(", html)), 2)
        self.assertNotIn("{{", html)

    def test_demo_is_marked_not_measured(self):
        cp, _, _, html, data = self.run_generator(ENV_MD)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertIn("未实测", data["demo"]["note"])
        self.assertIn("未实测", html)
        self.assertIn("验收场景", html)

    def test_validator_rejects_external_script(self):
        _, intro, out, html, _ = self.run_generator(ENV_MD)
        bad = out.parent / "bad_external.html"
        bad.write_text(html.replace("</body>", '<script src="https://example.com/x.js"></script></body>'), encoding="utf-8")
        cp, report = self.run_validator(intro, bad)
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any("外部 script" in error for error in report["errors"]), report["errors"])

    def test_validator_rejects_implementation_leak(self):
        _, intro, out, html, _ = self.run_generator(ENV_MD)
        bad = out.parent / "bad_leak.html"
        bad.write_text(html.replace("温湿度采集", "GPIO 引脚"), encoding="utf-8")
        cp, report = self.run_validator(intro, bad)
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any("GPIO" in error or "引脚" in error for error in report["errors"]), report["errors"])

    def test_validator_rejects_inline_handler(self):
        _, intro, out, html, _ = self.run_generator(ENV_MD)
        bad = out.parent / "bad_inline.html"
        bad.write_text(html.replace("</body>", '<button onclick="alert(1)">x</button></body>'), encoding="utf-8")
        cp, report = self.run_validator(intro, bad)
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any("内联事件" in error for error in report["errors"]), report["errors"])

    def test_validator_rejects_missing_demo_label(self):
        _, intro, out, html, _ = self.run_generator(ENV_MD)
        bad = out.parent / "bad_demo.html"
        bad.write_text(html.replace("未实测", "已完成"), encoding="utf-8")
        cp, report = self.run_validator(intro, bad)
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any("未实测" in error or "示意" in error for error in report["errors"]), report["errors"])


    def test_skill_references_html_pipeline(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("4.5", skill)
        self.assertIn("generate_intro_html.py", skill)
        self.assertIn("validate_intro_html.py", skill)
        for relative in (
            "templates/project-introduction.html",
            "references/html-visualization-rules.md",
            "references/html-content-mapping.md",
            "references/html-quality-check.md",
            "assets/reference-samples/project-introduction-reference.html",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_generic_template_has_no_example_business_data(self):
        template = (ROOT / "templates" / "project-introduction.html").read_text(encoding="utf-8")
        for forbidden in ("四个货位", "货位状态概览", "60.0 kg", "24 件", "低库存状态提示", "智能仓储"):
            self.assertNotIn(forbidden, template)


if __name__ == "__main__":
    unittest.main()