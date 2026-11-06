"""Regression tests for batched Markdown composition.

Covers: intro/impl composition, missing/duplicate H1, empty parts, single-batch
warning, code-fence heading handling, atomic output, and the SKILL batch rule.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "scripts" / "compose_markdown.py"


class TestComposeMarkdown(unittest.TestCase):
    def run_compose(self, parts, kind="introduction", title="示例项目", min_parts=4):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            parts_dir = tmp / "parts"
            parts_dir.mkdir()
            for name, text in parts.items():
                (parts_dir / name).write_text(text, encoding="utf-8")
            out = tmp / "draft.md"
            report_path = tmp / "report.json"
            env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            cp = subprocess.run(
                [
                    sys.executable,
                    str(COMPOSE),
                    "--parts-dir",
                    str(parts_dir),
                    "--out",
                    str(out),
                    "--kind",
                    kind,
                    "--title",
                    title,
                    "--min-parts",
                    str(min_parts),
                    "--report",
                    str(report_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
            )
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
            text = out.read_text(encoding="utf-8") if out.exists() else ""
            leftovers = list(tmp.glob(".*.tmp"))
            return cp, report, text, leftovers

    def test_compose_introduction_parts_in_order(self):
        parts = {
            "00-meta.md": "# 示例项目｜项目介绍与功能说明\n\n> 版本：V1.0\n",
            "01-overview.md": "## 1. 项目概述\n\n示例项目用于验证分批组装。\n",
            "02-scenarios.md": "## 2. 应用场景与系统目标\n\n### 2.1 典型场景\n\n- 场景一\n",
            "03-features.md": "## 3. 功能说明\n\n### 3.1 采集\n\n采集数据并显示。\n",
            "04-system-workflow.md": "## 4. 系统组成概览\n\n| 组成部分 | 作用 |\n|---|---|\n| 采集 | 获取数据 |\n\n## 5. 使用与交互流程\n\n### 5.1 首次使用\n\n1. 上电\n",
        }
        cp, report, text, leftovers = self.run_compose(parts)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["parts"], 5)
        self.assertIn("# 示例项目｜项目介绍与功能说明", text)
        self.assertIn("## 3. 功能说明", text)
        self.assertLess(text.index("## 1. 项目概述"), text.index("## 2. 应用场景与系统目标"))
        self.assertLess(text.index("## 2. 应用场景与系统目标"), text.index("## 3. 功能说明"))
        self.assertLess(text.index("## 3. 功能说明"), text.index("## 4. 系统组成概览"))
        self.assertEqual(leftovers, [])

    def test_compose_implementation_parts(self):
        parts = {
            "00-meta.md": "# 示例项目｜工程实施方案\n\n> 版本：V1.0\n",
            "01-scope.md": "## 1. 项目范围与设计基线\n\n范围说明。\n",
            "02-architecture.md": "## 2. 系统架构与数据流\n\n架构说明。\n",
            "03-functions.md": "## 3. 核心功能实现\n\n实现说明。\n",
            "04-stages.md": "## 4. 分阶段开发实施步骤\n\n阶段说明。\n",
            "05-tests.md": "## 5. 测试验收与排障\n\n验收说明。\n",
        }
        cp, report, text, _ = self.run_compose(parts, kind="implementation", title="示例项目")
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["parts"], 6)

    def test_missing_h1_fails(self):
        cp, report, text, _ = self.run_compose({"01-a.md": "## 1. 项目概述\n\n内容。\n"}, min_parts=1)
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any("一级标题" in error for error in report["errors"]), report["errors"])
        self.assertEqual(text, "")

    def test_duplicate_h1_fails(self):
        parts = {
            "00-a.md": "# 项目 A｜项目介绍与功能说明\n\n## 1. 项目概述\n\n内容。\n",
            "01-b.md": "# 项目 B｜项目介绍与功能说明\n\n## 2. 功能说明\n\n内容。\n",
        }
        cp, report, _, _ = self.run_compose(parts, min_parts=1)
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any("一级标题" in error for error in report["errors"]), report["errors"])

    def test_single_batch_warns(self):
        parts = {
            "00-all.md": "# 示例项目｜项目介绍与功能说明\n\n## 1. 项目概述\n\n内容。\n\n## 2. 功能说明\n\n内容。\n\n## 3. 使用与交互流程\n\n内容。\n"
        }
        cp, report, _, _ = self.run_compose(parts, min_parts=4)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual(report["status"], "WARN")
        self.assertTrue(any("只收到 1 个批次" in warning for warning in report["warnings"]), report["warnings"])

    def test_empty_part_fails(self):
        parts = {
            "00-meta.md": "",
            "01-overview.md": "# 示例项目｜项目介绍与功能说明\n\n## 1. 项目概述\n\n内容。\n",
        }
        cp, report, _, _ = self.run_compose(parts, min_parts=1)
        self.assertEqual(cp.returncode, 2)
        self.assertTrue(any("为空" in error for error in report["errors"]), report["errors"])

    def test_code_fence_heading_ignored(self):
        parts = {
            "00-meta.md": "# 示例项目｜工程实施方案\n",
            "01-code.md": "## 1. 项目范围与设计基线\n\n```c\n# not a heading\n```\n",
        }
        cp, report, _, _ = self.run_compose(parts, kind="generic", min_parts=2)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual(report["h1"], ["示例项目｜工程实施方案"])
        self.assertEqual(report["h2_count"], 1)

    def test_skill_batch_rule_present(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("分批写入", skill)
        self.assertIn("compose_markdown.py", skill)
        self.assertTrue((ROOT / "references" / "batch-writing.md").is_file())


if __name__ == "__main__":
    unittest.main()