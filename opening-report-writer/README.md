# opening-report-writer — 官方模板保护型开题报告写作 Skill

> 唯一用途：**根据当前项目技术文档，编写符合塔里木大学官方空白模板的毕业论文（设计）开题报告 Word 文件**。不承担技术文档、HTML 网站或毕业论文全文编写。

## 与你的 `project-technical-doc` Skill 的关系

```text
project-technical-doc（已提供的上游 Skill）
    └── 当前项目-技术文档.md
                ↓
     opening-report-writer（本 Skill）
       ├── 读取项目事实与阶段目标
       ├── 检索并核实学术参考文献
       ├── 编写开题报告七部分
       ├── 从内置官方 DOCX 原件的副本填报
       └── 自动检查 + 全页渲染检查
                ↓
     项目-毕业设计开题报告.docx
     执行汇报.md
     文献核验台账.md
     （交付目录仅此 3 项，其余过程文件交付前删除）
```

两者**单向衔接，不相互修改**。上游不会被迫改为本 Skill 风格，本 Skill 不强制接收上游 HTML。只需要本次技术文档，也可以独立运行本 Skill。

## 安装

解压后把完整 `opening-report-skill/` 文件夹放在：

- Claude Code 项目级：`<项目根目录>/.claude/skills/opening-report-skill/`
- Codex 项目级：`<项目根目录>/.agents/skills/opening-report-skill/`

随后在 Agent 中调用 `opening-report-writer`（其内部 `SKILL.md` 的 name 即为此名称），提供本次项目技术文档即可。

**运行环境：** Python 3.10+；`lxml`（通常已随 `python-docx` 安装）。可运行 `python -m pip install -r requirements.txt`。可使用 Word、WPS 或 LibreOffice 渲染 DOCX 做全页视觉校验。若有 OpenAI DOCX Skill 环境，可调用其 `render_docx.py`；若要使用可选的 PDF 孤立签字预警脚本，可额外安装 `PyMuPDF`。

## 一段直接可复制的调用语

```text
使用 opening-report-writer Skill。
当前消息给你的是我的项目技术文档，你只负责撰写毕业设计开题报告。
必须使用 Skill 内置的塔里木大学官方 DOCX 模板原件的副本填写，
不得改变官方模板固定文字、页边距、表格、签字栏、字体与行距。
请按七项学校要求完整编写；参考文献不少于10项，优先知网、万方、维普、
正式学术论文网站、出版社/标准官网，CSDN可用于辅助工程参考但不是核心来源。
逐条核实来源；正文引文使用 Word 真上标，参考文献只编号一次，正文和文献均1.5倍行距，
参考文献段落左对齐+悬挂缩进（禁止两端对齐拉伸空隙）。
阶段进度使用“第X周--第Y周”。
生成 Word 后运行结构检查，逐页渲染目视复核，再提交 DOCX、执行汇报和文献核验台账；
其它中间文件（过程 JSON、检查报告、渲染图、检索日志等）交付前全部清理，交付目录只留这 3 项。
验收由我决定。不要更改上游技术文档或源码。
```

## 目录

```text
opening-report-skill/
├── SKILL.md                               主执行规范
├── README.md                              安装与使用说明
├── VERSION.md                             版本记录
├── requirements.txt                       脚本运行依赖
├── assets/
│   ├── official-opening-report-template.docx   用户官方模板二进制原件
│   └── template.sha256                         官方原件哈希
├── references/
│   ├── official-template-invariants.md     模板 OOXML 逆向及不可变约束
│   ├── content-writing-guide.md           技术文档→开题报告写作路径
│   ├── literature-policy.md               真实学术文献检索与引用规范
│   ├── report-json-contract.md            结构化内容输入说明
│   ├── quality-gates.md                   自动+视觉验收门禁
│   ├── reproduction-method.md             逆向复现方法与四层模型
│   ├── integration-contract.md            与上游 Skill 合并接口
│   └── shared-project-assets-contract.md  项目级共享资产协议 v1（跨 Skill）
├── templates/
│   ├── execution-report.md                交付汇报样板
│   └── evidence-register.md               来源事实台账样板
├── examples/
│   └── report-input.example.json          仅字段结构，无虚构可用文献
├── scripts/
│   ├── inspect_template.py                 模板结构只读分析
│   ├── build_report.py                     从官方副本填报成 Word
│   ├── check_report.py                     模板/引文/行距/字数检查
│   ├── check_render.py                     PDF 分页签名孤立预警
│   └── project_assets.py                   共享资产读写/运行目录/record-use
└── tests/
    ├── test_pipeline.py                   构建与静态检查回归测试
    ├── test_guards.py                     门禁回归测试
    └── test_project_assets.py             共享资产命令烟测
```

## 关键边界

- 这是“**开题报告写作**”Skill；技术文档依赖上游输入，不负责生产它。
- 官方模板原件永远不允许被覆盖；校验文件可据此追踪是否被修改。输出仅填充封面和正文留白区。
- 官方说明规定七项内容，**并未预设正文七个字面章题**；Skill 为方便复现提供默认统一章题，不冒充官方规定。
- 引用必须实查真实论文；不得为了凑够条目而伪造；生成程序不能替代学术核验。
- **一个项目一个资产包** `<PROJECT_ROOT>/`：`project-assets/`（数据）+ `deliverables/`（成品）+ `.skill-tmp/`（运行区），按项目分类、整包可迁移；成品带版本号（-v1、-v2…），重生成不覆盖历史版本。
- **本轮交付只保留 3 项**（开题报告 DOCX、执行汇报.md、文献核验台账.md，均带 -vN）；过程文件统一放 `.skill-tmp/opening-report-writer/<run-id>/`，交付前整体删除，不留检索脚本/日志、下载 PDF、渲染图或中间 JSON。
- **一个项目一个共享数据资产库** `<PROJECT_ROOT>/project-assets/`（与任务书/技术文档 Skill 共用）：参考文献与周计划先读后写按 REF-xxx/稳定阶段 ID 复用，交付后 record-use 登记；共享资产、用户原始资料与官方模板原件永不删除。
- 参考文献段落左对齐+悬挂缩进，禁止两端对齐拉伸空隙；该属性由生成器写入并被终检强制校验。
- 机器校验不代替**打开 Word 后逐页视觉检查**；发现孤立签名不得擅自修改模板的教师意见栏。
- **最终验收人是用户**，Agent 负责执行、核查和诚实汇报。
