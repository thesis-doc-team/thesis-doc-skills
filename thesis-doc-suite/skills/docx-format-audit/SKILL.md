---
name: docx-format-audit
version: 0.1.0
argument-hint: "[文件.docx]"
description: 只读解析 DOCX 的完整格式：文档默认值、样式继承链、实际生效的字体/字号/行距/缩进/对齐/颜色、页面设置、页眉页脚、表格、编号、图片尺寸与哈希。当用户说"看看这个 Word 的格式""字号行距是多少""对照模板检查格式""为什么显示的和设置的不一样"时使用。
---

# docx-format-audit｜DOCX 格式全景解析

## 目标

把一份 `.docx` 的格式信息**一次读全**，输出结构化 JSON，供后续规范比对、问题定位或迁移使用：

- **direct**：元素上直接写的格式（作者显式设置的）。
- **style_chain**：段落/字符样式从根到叶的继承链（`basedOn`）。
- **effective**：把文档默认值、样式链、主题字体与直接格式合并后的**实际生效值**。
- **page / headers_footers / tables / numbering / images**：页面、页眉页脚、表格、编号与图片的完整快照。

只读，不修改原文件、不写项目资产、不联网；仅依赖 Python 标准库。

## 执行步骤

1. **确认输入**：用户给出 `.docx` 路径；若只给了目录，先定位唯一 `.docx`，多个则让用户确认。
2. **运行脚本**：

   ```bash
   python scripts/inspect_docx.py "<文件.docx>" --json "<输出.json>"
   ```

   省略 `--json` 时直接打印到 stdout。退出码 `0` 成功，`2` 文件不存在/不是有效 DOCX。

3. **解读结果**（按用户问题裁剪，不要整份倾倒）：

   | JSON 路径 | 含义 |
   | --- | --- |
   | `document_defaults` | 文档级默认段落/字符格式 |
   | `theme.fonts` | 主题的 major/minor 字体（`+mj-lt`/`+mn-ea` 的真实来源） |
   | `styles` | 所有样式定义及其 `based_on` |
   | `sections[]` | 纸张、方向、页边距、分栏、页眉页脚引用 |
   | `paragraphs[].effective` | 该段实际字号、行距、缩进、对齐等 |
   | `paragraphs[].runs[].effective` | 每个 run 实际字体（西文/中文）、加粗、颜色等 |
   | `tables[]` | 表格列宽、行高、合并单元格、单元格内段落格式 |
   | `numbering` | 多级编号定义与实例 |
   | `images[]` | 图片显示尺寸（cm）、像素尺寸、文件哈希 |

4. **回答口径**：
   - 用户问"设置是多少"→ 报 `direct`；问"实际显示是多少"→ 报 `effective`，并说明来自哪条样式链。
   - 主题字体不要只报 `+mn-ea`，要结合 `theme.fonts` 给出真实字体名（`font_*_resolved`）。
   - 中文字体看 `font_east_asia` / `font_east_asia_resolved`，不要拿西文字体代替。
   - 行距区分 `rule=auto`（倍数）与 `rule=exact|atLeast`（磅值）。
   - 数字保留脚本给出的精度，不要二次换算。

5. **异常处理**：
   - `ERROR: 不是有效的 DOCX/ZIP 包` → 文件可能损坏或被加密，先让用户用 Word 另存一份。
   - `warnings` 非空 → 如实转述缺失部件，不要猜测内容。

## 约束

- 不修改、不"顺手修复"原文件；需要修改时另起任务。
- 不虚构 JSON 中不存在的属性；字段缺失表示"未显式设置"，不等同于"没有格式"。
- 大文档 JSON 可能较大，写入 `--json` 文件后按需读取，避免整份打印。
