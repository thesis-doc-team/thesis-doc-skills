---
name: pptx-format-audit
version: 0.1.0
argument-hint: "[文件.pptx]"
description: 只读解析 PPTX 的完整格式：幻灯片尺寸、主题字体与配色、母版/版式/占位符继承链、每个形状的位置尺寸、文本框边距与自动调整、实际生效的字体/字号/颜色/行距/段距/项目符号、表格与图片信息。当用户说"看看这个 PPT 的格式""字号字体是多少""为什么模板改了没生效""对照母版检查版式"时使用。
---

# pptx-format-audit｜PPTX 格式全景解析

## 目标

把一份 `.pptx` 的格式信息**一次读全**，输出结构化 JSON，供规范比对、模板排查或格式迁移使用：

- **direct**：run 上直接写的格式（作者显式设置的）。
- **effective**：把 `presentation.defaultTextStyle`、母版 `txStyles`、母版/版式占位符 `lstStyle`、形状 `lstStyle`、段落 `defRPr` 与 run 直接格式依次合并后的**实际生效值**。
- **主题字体**：`+mj-lt` / `+mn-ea` 等占位会解析出 `font_*_resolved` 的真实字体名。
- **结构快照**：母版、版式、占位符、幻灯片、表格、图片（显示尺寸/像素尺寸/哈希）、备注。

只读，不修改原文件、不写项目资产、不联网；仅依赖 Python 标准库。

## 执行步骤

1. **确认输入**：用户给出 `.pptx` 路径；若只给目录，先定位唯一 `.pptx`，多个则让用户确认。
2. **运行脚本**：

   ```bash
   python scripts/inspect_pptx.py "<文件.pptx>" --json "<输出.json>"
   ```

   省略 `--json` 时直接打印到 stdout。退出码 `0` 成功，`2` 文件不存在/不是有效 PPTX。

3. **解读结果**（按用户问题裁剪，不要整份倾倒）：

   | JSON 路径 | 含义 |
   | --- | --- |
   | `presentation.slide_size_cm` | 幻灯片尺寸（判断 16:9 / 4:3） |
   | `presentation.default_text_style` | 全局默认文字样式（继承链最底层） |
   | `theme.fonts` / `theme.colors` | 主题 major/minor 字体与配色 |
   | `masters[].text_styles` | 母版 `titleStyle` / `bodyStyle` / `otherStyle` |
   | `layouts[]` | 版式名称、类型、母版归属、占位符位置 |
   | `slides[].shapes[]` | 形状类型、占位符、解析后的位置尺寸 |
   | `shapes[].text_body.paragraphs[].runs[].effective` | 实际字体、字号、颜色、行距等 |
   | `shapes[].table` | 表格列宽、行高、单元格文本与格式 |
   | `shapes[].picture` | 图片显示尺寸、像素尺寸、哈希 |

4. **回答口径**：
   - 用户问"设置是多少"→ 报 `direct`；问"实际显示是多少"→ 报 `effective`，并说明继承来源（全局默认/母版/版式/占位符）。
   - 主题字体不要只报 `+mn-ea`，要给出 `font_*_resolved` 的真实字体名。
   - 占位符位置可能来自版式或母版，脚本已合并；若 `position_cm` 为空说明三级都没设置。
   - 行距 `{percent: 150.0}` 表示 150%，`{pt: 18.0}` 表示固定磅值。
   - 数字保留脚本给出的精度，不要二次换算。

5. **异常处理**：
   - `ERROR: 不是有效的 PPTX/ZIP 包` → 文件可能损坏或被加密，先让用户用 PowerPoint 另存一份。
   - `warnings` 非空 → 如实转述缺失部件（如版式/母版/图片目标缺失），不要猜测。

## 约束

- 不修改、不"顺手修复"原文件；需要修改时另起任务。
- 不虚构 JSON 中不存在的属性；字段缺失表示"未显式设置"，不等同于"没有格式"。
- 大文档 JSON 可能较大，写入 `--json` 文件后按需读取，避免整份打印。
