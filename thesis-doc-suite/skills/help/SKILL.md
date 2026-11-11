---
name: help
version: 0.1.0
argument-hint: "[想了解的命令或问题]"
description: Thesis Doc Suite 插件使用导航：展示十三个可用命令、推荐工作流程、文档与网站入口，并按用户当前进度给出下一步建议。当用户问"怎么用""有哪些命令""help""我该先做什么"或需要了解插件能力总览时使用。
---

# help｜Thesis Doc Suite 使用导航

## 可用命令一览

| 命令 | 作用 |
|---|---|
| `/thesis-doc-suite:init-project` | 初始化项目资产包（一个项目 = 数据 + 成品 + 运行区） |
| `/thesis-doc-suite:check-project` | 检查环境、模板、资产是否齐备（PASS/WARN/BLOCK） |
| `/thesis-doc-suite:project-technical-doc` | 从真实项目资料/源码生成技术文档 MD + 离线展示 HTML |
| `/thesis-doc-suite:technical-visual-assets` | 建立四类真实可追溯视觉资产（框架/架构/流程图 + 核心模块实物图，VIS-xxx） |
| `/thesis-doc-suite:docx-format-audit` | 只读导出 DOCX 全景格式（样式链、有效字体/字号/行距、页面、表格、图片） |
| `/thesis-doc-suite:pptx-format-audit` | 只读导出 PPTX 全景格式（母版/版式继承、主题字体、形状与文本有效格式） |
| `/thesis-doc-suite:thesis-taskbook-write` | 生成毕业设计任务书 DOCX（官方模板原位填写） |
| `/thesis-doc-suite:opening-report-writer` | 生成开题报告 DOCX（七项内容） |
| `/thesis-doc-suite:literature-review-write` | 生成文献综述 DOCX（真实引文与评述） |
| `/thesis-doc-suite:thesis-guidance-record-write` | 生成指导记录 DOCX（≥8 次，问题—整改配对） |
| `/thesis-doc-suite:thesis-midterm-check-write` | 生成中期检查记录表 DOCX（三栏各 ≥200 字） |
| `/thesis-doc-suite:help` | 本导航 |

## 推荐工作流程（非强制顺序）

1. **准备环境**：Python 3.10+、pip 依赖、LibreOffice（渲染截图）→ 详见 `docs/prerequisites.md`。
2. **加载插件**：`claude --plugin-dir <插件目录>` 或经本地 marketplace 安装。
3. **初始化项目**：`/thesis-doc-suite:init-project`（每项目一次）。
4. **导入技术资料**：把源码/技术手册放入项目目录或记住其路径。
5. **检查前置条件**：`/thesis-doc-suite:check-project`。
6. **选择 Skill 生成**：推荐先 `project-technical-doc`（提炼共享技术事实），再按需生成各文书；**也可以直接生成任何一种文书**。
7. **查看成品与汇报**：成品在 `<PROJECT_ROOT>/deliverables/<文书类型>/`（`-vN` 版本永不覆盖）；执行汇报列出检查结果与待确认事项。

## 常见起点

- "我想给项目写技术文档" → `/thesis-doc-suite:project-technical-doc`
- "技术文档要配真实的框架图/模块实物图" → `/thesis-doc-suite:technical-visual-assets`（需已有技术 MD 与 FACT）
- "要交任务书/开题/综述/中期/指导记录" → 对应文书命令
- "看看这个 Word/PPT 的实际字体字号行距" → `/thesis-doc-suite:docx-format-audit` 或 `/thesis-doc-suite:pptx-format-audit`
- "不知道资料齐不齐" → `/thesis-doc-suite:check-project`
- "两个项目会不会串数据" → 不会；每个项目独立资产包，`project_id` 不一致时拒绝合并（见 `docs/asset-management.md`）

## 文档与网站入口

- `README.md`：插件总览与安装
- `docs/quickstart.md`：示例项目全程入门
- `docs/user-guide.md`：逐 Skill 使用手册
- `docs/troubleshooting.md`：问题排查
- `site/index.html`：离线介绍网站（双击打开）

根据用户提出的具体问题，给出上述对应入口的简短说明即可，不要整份朗读文档。
