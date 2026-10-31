# 快速入门（Quick Start）

本教程以一个**虚构脱敏示例项目**为主线，带你从零开始走完"准备环境 → 生成第一份文档"的全过程。

> 示例项目："基于 STM32 的环境监测系统"。
> 文中所有姓名、学号、日期、文献、URL 均为**纯合成数据**（日期用 2099 年、URL 用 `example.invalid`、姓名用"示例学生"），仅演示流程，**不得当作真实文献、事实或个人信息使用**。

全程约 8 步。完成后你会得到：一份项目技术文档（MD + 离线 HTML）和一份毕业设计任务书 DOCX。

---

## 第 1 步：准备环境

需要：Python 3.10+、Claude Code。

```bash
# Windows（macOS/Linux 用 python3）
python -m pip install python-docx lxml PyMuPDF markdown-it-py beautifulsoup4
```

Word 文书的逐页截图验证还需要 LibreOffice（或本机 Word/WPS 对应的命令行渲染方式）。装好后自检：

```bash
python E:\Code\thesis-doc-skills\thesis-doc-suite\scripts\check_env.py
```

预期输出摘要（末尾类似）：

```
PASS  python 3.12.x
PASS  python-docx / lxml / PyMuPDF / markdown-it-py / beautifulsoup4
WARN  LibreOffice 未检测到（Word 文书逐页截图验证将受限，可继续但需人工核对排版）
```

`WARN` 不阻止继续；出现 `BLOCK` 时按提示处理（见 [troubleshooting.md](troubleshooting.md)）。

## 第 2 步：加载插件

```bash
claude --plugin-dir E:\Code\thesis-doc-skills\thesis-doc-suite
```

进入 Claude Code 后输入 `/thesis-doc-suite:help`。如果能看到命令列表，说明插件加载成功。

> 另外两种加载方式（marketplace / ZIP 解压）见 [README.md 第 4 节](../README.md#4-安装与加载)。

## 第 3 步：初始化项目资产包

准备一个项目目录（示例用 `E:\thesis-work\env-monitor`）存放资料与产出，然后在 Claude Code 中执行：

```
/thesis-doc-suite:init-project 项目根目录 E:\thesis-work\env-monitor，project-id ENV-MONITOR-2099，项目名称"基于STM32的环境监测系统"
```

等价命令行（二选一即可）：

```bash
python E:\Code\thesis-doc-skills\thesis-doc-suite\core\asset-management\project_assets.py init --root "E:\thesis-work\env-monitor" --project-id "ENV-MONITOR-2099" --name "基于STM32的环境监测系统"
```

预期输出：`CREATED: E:\thesis-work\env-monitor\project-assets`。此时资产包里有空的 `project.json`、`facts.json`、`references.json`、`schedule.json`、`activity.jsonl` 和 `deliverables\` 骨架。

## 第 4 步：放入技术资料

把项目的真实材料拷入项目目录，例如：

```
E:\thesis-work\env-monitor\
├── source\                  ← STM32 工程源码（如有）
├── docs\技术手册.md          ← 项目技术资料（示例：描述功能、器件、通信方案）
└── project-assets\          ← 第 3 步生成
```

本教程假设你有一份 `docs\技术手册.md`，描述：STM32F103 主控、温湿度/粉尘传感器、OLED 显示、4G 模块经 MQTT 上报、超阈值蜂鸣告警等（合成示例）。**资料里没写的功能，Skill 不会替你发明。**

## 第 5 步：检查前置条件

```
/thesis-doc-suite:check-project 项目根目录 E:\thesis-work\env-monitor，接下来要执行 project-technical-doc
```

预期输出摘要：

```
PASS  Python 3.12.x 及所需依赖
PASS  插件结构完整，9 个 Skill 可加载
PASS  项目资产包已初始化（project_id=ENV-MONITOR-2099）
WARN  project-assets 中暂无技术事实（首次运行正常，由本 Skill 提炼入库）
```

只有 `PASS/WARN` 即可继续；`BLOCK` 表示关键条件不足，按提示补齐。

## 第 6 步：生成技术文档（第一份产出）

```
/thesis-doc-suite:project-technical-doc 项目资料在 E:\thesis-work\env-monitor\docs\技术手册.md 与 source\，项目根目录 E:\thesis-work\env-monitor
```

Skill 会：只读理解项目 → 建立证据台账 → 写完整 Markdown 技术文档 → 派生单文件离线 HTML → 检查一致性 → 归档并登记资产。

预期产出（`E:\thesis-work\env-monitor\deliverables\technical-document\`）：

```
基于STM32的环境监测系统-技术文档.md
基于STM32的环境监测系统_用户展示.html     ← 双击即可离线浏览
执行汇报.md                              ← 生成路径、检查结果、待确认事项
```

同时，从资料核实的技术事实以 `FACT-xxx` 写入 `project-assets\facts.json`（含出处与状态），供后续文书复用。

**验收**：打开 HTML 看整体效果，对照 MD 抽查几处技术细节；执行汇报里标注"待确认"的内容需要你核实。

## 第 7 步：生成毕业设计任务书（第二份产出，复用共享资产）

```
/thesis-doc-suite:thesis-taskbook-write 项目根目录 E:\thesis-work\env-monitor，课题"基于STM32的环境监测系统"，起止日期 2099-03-01 至 2099-12-31
```

Skill 会：读取共享资产（复用 FACT-xxx，不再重查）→ 检索并核验 ≥10 篇真实参考文献（登记为 REF-xxx）→ 建立周计划基线（schedule.json）→ 在官方模板副本的可填区域填写 → 结构比对 + 逐页截图分析 → 交付并清理运行区。

预期产出（`deliverables\taskbook\`）：

```
基于STM32的环境监测系统-毕业设计任务书-v1.docx
```

**验收**：用 WPS/Word 打开成品——这是**给指导教师审定的拟稿**：导师意见栏是拟稿正文，签名与日期保持空白；核对课题名称、任务条目、周次安排；参考文献应全部可追溯（执行汇报列出使用的 REF-xxx 与核验状态）。

## 第 8 步：查看运行记录（可选）

```bash
python E:\Code\thesis-doc-skills\thesis-doc-suite\core\asset-management\project_assets.py status --root "E:\thesis-work\env-monitor"
```

预期输出为 JSON 摘要：项目 ID、文献数（含已核验数）、事实数、周计划状态。每次成品交付都在 `project-assets\activity.jsonl` 留下记录（路径、SHA-256、引用的 REF-xxx）。

---

## 接下来做什么

- 按第 10 节的推荐顺序继续生成开题报告、文献综述、指导记录、中期检查——它们都会**复用同一套资产**，不需要重复录入信息。
- 想深入某个 Skill：见 [user-guide.md](user-guide.md) 与 [skill-catalog.md](skill-catalog.md)。
- 遇到报错：见 [troubleshooting.md](troubleshooting.md)。
- 想理解"一个项目 = 一个资产包"的细节：见 [asset-management.md](asset-management.md)。

> 提醒：本教程中的项目、文献、人员信息全部为合成示例。你的真实项目请使用真实资料；Skill 对无法核实的内容一律标注"待确认"，绝不编造。
