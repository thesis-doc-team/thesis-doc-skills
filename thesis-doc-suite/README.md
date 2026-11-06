# Thesis Doc Suite Taru

**一个插件，六种毕业设计文书；一个项目，一套共享资产。**

Thesis Doc Suite（插件标识 `thesis-doc-suite`）是一套面向本科毕业论文（设计）全流程的 Claude Code 插件，当前版本官方模板锁定**塔里木大学**格式。它把六种常用毕业设计文书的生成能力整合为一个可安装、可复用的插件：每种文书一个独立 Skill，共享同一个项目资产包（技术事实、参考文献、进度计划），内置官方 Word 模板哈希锁定、文献真实性核验、逐页截图验证与安全清理机制。

> **适用范围与重要声明**
> - 适用于本科毕业论文（设计）各阶段文书的**准备与拟稿**。
> - 所有 Word 文书均为**供指导教师审定的拟稿**：不代签、不填签署日期、不写"优秀/良好"等等级、不编造指导会面、文献、数据与成果。**最终验收由用户和指导教师完成。**
> - 参考文献必须真实可核验；无法核实的条目会显式标注 `verified=false`，绝不冒充已核实文献。

---

## 目录

1. [各 Skill 的功能](#1-各-skill-的功能)
2. [Skill 之间的关系](#2-skill-之间的关系)
3. [系统整体架构](#3-系统整体架构)
4. [安装与加载](#4-安装与加载)
5. [环境依赖及准备](#5-环境依赖及准备)
6. [创建项目资产包](#6-创建项目资产包)
7. [准备技术资料](#7-准备技术资料)
8. [官方模板与范本配置](#8-官方模板与范本配置)
9. [每个 Skill 的调用方式与示例](#9-每个-skill-的调用方式与示例)
10. [标准工作流程](#10-标准工作流程)
11. [独立调用某个 Skill](#11-独立调用某个-skill)
12. [公共参考文献、计划及技术事实复用](#12-公共参考文献计划及技术事实复用)
13. [生成文件保存在哪里](#13-生成文件保存在哪里)
14. [版本管理、更新与维护](#14-版本管理更新与维护)
15. [查看错误与常见问题](#15-查看错误与常见问题)
16. [如何添加新的 Skill](#16-如何添加新的-skill)
17. [备份策略](#17-备份策略)
18. [文档索引](#18-文档索引)

---

## 1. 各 Skill 的功能

7 个业务 Skill（6 项毕业设计文书 + 1 个通用项目方案），1 个支持 Skill 管公共视觉素材，3 个管理 Skill 管项目与导航。每个 Skill 都能独立执行，只负责自己的产出，不越界生成其他文书。

| 命令 | 生成什么 | 必需输入 | 关键门槛 |
|---|---|---|---|
| `/thesis-doc-suite:project-technical-doc` | `<项目名>-技术文档.md` + `<项目名>_用户展示.html`（单文件离线网页）+ 执行汇报 | 项目源码或技术资料、项目根目录 | 无需 Word 模板；内容须有证据支撑 |
| `/thesis-doc-suite:thesis-taskbook-write` | `<课题简称>-毕业设计任务书-vN.docx` + 执行汇报 | 技术资料/技术 MD、官方任务书模板、课题题目、项目根目录 | ≥10 篇真实可核验参考文献 |
| `/thesis-doc-suite:opening-report-writer` | `<课题简称>-毕业设计开题报告-vN.docx` + 执行汇报 + 文献核验台账 | 项目技术文档、官方开题报告模板、项目根目录 | 正文汉字 ≥3000、≥10 篇核验文献 |
| `/thesis-doc-suite:literature-review-write` | `<课题简称>-文献综述-vN.docx` + 执行汇报 | 课题技术资料、官方文献综述模板、项目根目录 | 正文 ≥2500 字、默认 ≥8 篇独立真实文献 |
| `/thesis-doc-suite:thesis-guidance-record-write` | `<课题简称>-指导记录-vN.docx` + 执行汇报 | 真实项目技术资料、官方指导记录模板、项目根目录 | ≥8 次有真实依据的指导主题；时间/地点/方式/评价缺失一律留空 |
| `/thesis-doc-suite:thesis-midterm-check-write` | `<课题简称>-中期检查记录表-vN.docx` + 执行汇报 | 真实项目技术资料、官方中期检查模板、项目根目录 | 三个栏目各 ≥200 字；问题与整改逐条编号一一对应 |
| `/thesis-doc-suite:project-solution-write` | `<项目简称>-项目介绍与功能说明-vN.md` + `<项目简称>-项目介绍与功能说明-vN.html` + `<项目简称>-工程实施方案-vN.md` + 执行汇报 | 项目题目与功能树/功能清单、项目根目录 | 无需 Word 模板；技术路线重大歧义先澄清；两份 MD 边界严格分离；介绍 HTML 只读介绍 MD、单文件离线、统一视觉；介绍/实施均分章分批写入并 compose 后一次终检 |

另有 1 个支持 Skill（公共图片资料层，不生成文书、不负责在文书里插图）：

| 命令 | 作用 |
|---|---|
| `/thesis-doc-suite:technical-visual-assets` | 以正式技术 MD 为唯一事实源，离线生成正交技术图（可编辑 Mermaid/drawio、正交 SVG、原生 VSDX、300dpi PNG）与中英文图题，执行 A4/Word 版心门禁；用户实物照片经权利声明与本地验证后入库；不包含联网搜图 |

另有三个管理型 Skill（不生成文书、不修改业务 Skill 职责）：

| 命令 | 作用 |
|---|---|
| `/thesis-doc-suite:init-project` | 初始化项目资产包（project-assets/ 数据层 + deliverables/ 成品层骨架） |
| `/thesis-doc-suite:check-project` | 检查运行环境、插件完整性、模板哈希与项目资产状态，输出 PASS / WARN / BLOCK |
| `/thesis-doc-suite:help` | 展示可用命令、推荐工作流程与文档入口 |

每个 Skill 的详细说明见 [docs/skill-catalog.md](docs/skill-catalog.md)。

## 2. Skill 之间的关系

**共享资产复用 + 执行独立性**：

- 一个真实项目只有一份共享数据资产 `<PROJECT_ROOT>/project-assets/`。`project-technical-doc` 提炼的技术事实（`FACT-xxx`）可被任务书、开题报告直接复用；文献综述与开题报告共享参考文献库（`REF-xxx`）；中期检查与指导记录读取共享周计划与进展；`technical-visual-assets` 读取技术 MD 与 FACT，登记 VIS 视觉资产（`project-assets/visual-assets/` 子层）。
- 复用关系**不等于固定执行顺序**。只有确实必要的输入才是硬性前置（如任务书需要技术资料与官方模板）；缺少非必要资料时允许降级执行，并在执行汇报中说明影响。
- **禁止一个业务 Skill 跨越边界生成其他业务文书**。写任务书不会顺带产出开题报告；技术文档 Skill 不会自动编写任何 Word 表格。
- 各 Skill 对共享资产"先读后写"，更新已有条目必须给出证据与理由（`--replace --reason`），绝不静默覆盖其他 Skill 已确认的数据。

## 3. 系统整体架构

```
thesis-doc-suite/                 ← 一个 Claude Code 插件
├── .claude-plugin/plugin.json    ← 插件清单
├── skills/                       ← 六个业务 Skill + 一个支持 Skill + 三个管理型 Skill
│   ├── project-technical-doc/    ← 各自独立：SKILL.md + scripts/ + references/ + templates/ + assets/
│   ├── thesis-taskbook-write/
│   ├── opening-report-writer/
│   ├── literature-review-write/
│   ├── thesis-guidance-record-write/
│   ├── thesis-midterm-check-write/
│   ├── technical-visual-assets/  ← 公共图片资料层（VIS 视觉资产）
│   ├── init-project/  check-project/  help/
├── core/                         ← 公共基础设施（资产契约、引用规范、模板保护、质量规则）
├── scripts/                      ← 环境检查 / 插件校验 / 打包脚本
├── docs/                         ← 本套使用文档
├── site/                         ← 离线 HTML 介绍网站
├── examples/                     ← 脱敏合成示例项目
└── tests/                        ← 插件级一致性与隔离测试
```

- **一个插件**：`.claude-plugin/plugin.json` 注册，Claude Code 整体识别。
- **六个业务 Skill**：互相隔离，任何一个出问题不影响其他 Skill 使用；执行规则按需加载（SKILL.md 触发后才读取 references/），不预载全文。
- **公共基础设施（core/）**：项目资产协议、参考文献核验规范、模板哈希保护、共享写作规则（教师意见拟稿规范、实质性分页门禁、截图验证分析）。
- **项目资产包**：一个项目 = 数据（`project-assets/`）+ 成品（`deliverables/`）+ 运行区（`.skill-tmp/`）。项目数据永远保存在你的项目目录，**不写入插件安装目录**。

## 4. 安装与加载

**方式一：本地目录直接加载（开发/个人使用，推荐先用这个）**

```bash
claude --plugin-dir E:\Code\thesis-doc-skills\thesis-doc-suite
```

启动后即可在对话中使用 `/thesis-doc-suite:help` 查看全部命令。

**方式二：注册为本地 marketplace 后安装（长期使用）**

仓库根目录提供 `.claude-plugin/marketplace.json`。在 Claude Code 中执行：

```
/plugin marketplace add E:\Code\thesis-doc-skills
/plugin install thesis-doc-suite@thesis-doc-skills
```

更新插件后重新执行 `/plugin update thesis-doc-suite`（或重新加载）即可。

**方式三：ZIP 分发**

用打包脚本生成 ZIP（见 [docs/user-guide.md](docs/user-guide.md)）：

```bash
python E:\Code\thesis-doc-skills\thesis-doc-suite\scripts\package_plugin.py
```

ZIP 包含运行必需的全部资源（不含个人数据与临时文件）。收到 ZIP 的用户解压后，仍按方式一或方式二加载——ZIP 是分发载体，不是官方安装通道。

## 5. 环境依赖及准备

| 依赖 | 用途 | 必需性 |
|---|---|---|
| Python 3.10+ | 运行全部脚本 | **必需** |
| python-docx、lxml | 读写 Word DOCX | Word 文书必需 |
| PyMuPDF | DOCX 渲染为逐页截图 | Word 文书必需（逐页视觉验证） |
| markdown-it-py、beautifulsoup4 | 技术文档 HTML 派生 | 技术文档 Skill 必需 |
| LibreOffice 或 Word 兼容渲染器 | 逐页渲染截图验证 | Word 文书强烈建议；缺失时报"截图验证分析未完成" |
| WPS / Microsoft Word | 用户最终目视验收 | 可选（只有实际打开过才能写"WPS 已验证"） |

准备命令（Windows 优先，macOS/Linux 将 `python` 换成 `python3`）：

```bash
python -m pip install python-docx lxml PyMuPDF markdown-it-py beautifulsoup4
```

也可以按各 Skill 目录内 `requirements.txt` 安装。装好后运行环境检查：

```bash
python E:\Code\thesis-doc-skills\thesis-doc-suite\scripts\check_env.py
```

## 6. 创建项目资产包

为每个毕业设计项目创建**唯一**的资产包（一个项目 = 一个资产包，项目之间完全隔离）：

```
E:\thesis-work\my-project\          ← <PROJECT_ROOT>，由你指定
├── project-assets\                 ← 数据层：跨 Skill 共享（project/facts/references/schedule/progress/activity.jsonl）
├── deliverables\                   ← 成品层：technical-document\ taskbook\ opening-report\ literature-review\ guidance\ midterm\
└── .skill-tmp\                     ← 运行层：各 Skill 本轮运行区，结束自动清理
```

在 Claude Code 中执行 `/thesis-doc-suite:init-project`，按提示给出 `<PROJECT_ROOT>`、稳定 `project_id` 与项目名称即可。也可直接用命令行：

```bash
python E:\Code\thesis-doc-skills\thesis-doc-suite\core\asset-management\project_assets.py init --root "E:\thesis-work\my-project" --project-id "MY-THESIS-2026" --name "基于STM32的环境监测系统"
```

已存在的资产包**不会被覆盖**；`project_id` 不一致时会拒绝混用（防止串项目）。详细字段见 [docs/asset-management.md](docs/asset-management.md)。

## 7. 准备技术资料

各业务 Skill 的内容都来自**你的真实项目资料**，请把以下材料放进 `<PROJECT_ROOT>`（或任何你指定的目录，运行时告知 Skill 即可）：

- 项目技术手册、需求文档、设计稿、接口协议、硬件资料（MD/DOCX/PDF 均可）；
- 如有源码仓库/工程目录，可直接让 Skill 只读分析；
- 测试记录、实验数据（用于区分"已实现"与"实测通过"）；
- 已确认的个人信息（姓名/学号/学院/专业/班级/导师/职称）——**缺失字段一律留空，Skill 不会从范本继承他人信息**。

资料不完整时 Skill 会先完成可证实的部分，并在执行汇报里列出缺口，不会拿模板或范本编造内容。

## 8. 官方模板与范本配置

- 每个 Word 文书 Skill 都内置**官方空白模板的只读副本**（`skills/<skill>/assets/official-*-template.docx`）及其 `template-lock.json`（记录 SHA-256 与结构审计）。生成时**从副本填充，绝不修改官方原件**。
- 填充前后自动比对节属性、表格网格、合并关系、固定栏目与签名栏；哈希或结构不符会 FAIL 并停止，不会"强灌"。
- 内置的去标识化参考范本只用于学习写法与排版规律，**不是模板、不提供项目事实**；范本中的个人信息已被清除。
- 若学校发布**新版官方模板**：把它交给对应 Skill，Skill 会重新做只读结构审计、重建填写坐标并更新锁定文件——这个过程不修改你的模板原件。见 [docs/troubleshooting.md](docs/troubleshooting.md)。

## 9. 每个 Skill 的调用方式与示例

六个业务 Skill 与支持 Skill 均设为**仅显式调用**（普通聊天不会意外创建文档）。在 Claude Code 输入框中：

```
/thesis-doc-suite:project-technical-doc
```

```
/thesis-doc-suite:technical-visual-assets
```

```
/thesis-doc-suite:thesis-taskbook-write
```

```
/thesis-doc-suite:opening-report-writer
```

```
/thesis-doc-suite:literature-review-write
```

```
/thesis-doc-suite:thesis-guidance-record-write
```

```
/thesis-doc-suite:thesis-midterm-check-write
```

典型调用示例（在命令后补充你的情况，或调用后按 Skill 提示提供）：

```
/thesis-doc-suite:project-technical-doc 项目在 E:\thesis-work\my-project\source，项目名"基于STM32的环境监测系统"
/thesis-doc-suite:thesis-taskbook-write 项目根目录 E:\thesis-work\my-project，课题"基于STM32的环境监测系统"，起止日期 2099-03-01 至 2099-12-31
/thesis-doc-suite:thesis-midterm-check-write 项目根目录 E:\thesis-work\my-project，检查日期 2099-06-15
```

调用后 Skill 会按自己的标准流程执行（读取资产 → 锁定模板 → 生成 → 结构检查 → 逐页截图分析 → 归档 → 清理），最后交付成品与执行汇报。每个 Skill 内部脚本的命令行接口见对应 `skills/<name>/SKILL.md`。

## 10. 标准工作流程

推荐顺序（**非强制**——任何 Skill 都可独立调用，见下一节）：

```
准备环境（Python + 依赖 + 渲染器）
   → 加载插件（--plugin-dir 或 marketplace）
   → /thesis-doc-suite:init-project          创建资产包
   → 放入项目技术资料
   → /thesis-doc-suite:check-project         确认前置条件
   → /thesis-doc-suite:project-technical-doc 技术文档（提炼 FACT-xxx）
   → /thesis-doc-suite:technical-visual-assets 视觉素材（四类图，可选、按需）
   → /thesis-doc-suite:thesis-taskbook-write 任务书（建立 REF-xxx 与周计划基线）
   → /thesis-doc-suite:opening-report-writer 开题报告（复用事实/文献/计划）
   → /thesis-doc-suite:literature-review-write  文献综述（复用文献）
   → /thesis-doc-suite:thesis-guidance-record-write  指导记录（按真实阶段拟稿）
   → /thesis-doc-suite:thesis-midterm-check-write    中期检查（计划 vs 实际进展）
```

新手请按 [docs/quickstart.md](docs/quickstart.md) 的示例项目走一遍全流程。

## 11. 独立调用某个 Skill

任何时刻都可以只调用一个 Skill，条件是它的**必需输入**齐备（见第 1 节表格）：

- 只想写任务书？直接 `/thesis-doc-suite:thesis-taskbook-write`，提供技术资料与项目根目录即可；没有现成技术 MD 时 Skill 会从技术资料提取事实，不强制先做技术文档。
- 只想写中期检查？直接调用，共享计划缺失时会降级为"按当前资料拟稿 + 待确认清单"，并明确说明影响。
- 没有项目资产包？Skill 会提示先执行 `init`（或代为初始化并告知你）。

缺必需输入时 Skill 会明确报告缺口并停止，而不是编造内容。

## 12. 公共参考文献、计划及技术事实复用

同一项目只维护**一份**可信数据（`project-assets/`）：

- **技术事实 `FACT-xxx`**：每条含 `statement`（结论）+ `source`（文件/章节/行号出处）+ `status`（`implemented` 已实现 / `declared` 资料声明 / `unverified` 未核实 / `proposed` 设计拟议）。AI 推测**不得**记为已实现。
- **参考文献 `REF-xxx`**：稳定唯一 ID，含题名、作者、年份、来源、类型、URL/DOI、`verified` 核验状态与核验日期。优先知网、万方、维普、期刊/学位论文库、Crossref/DOI 等可核验来源；CSDN 等技术社区只能作为标注为网页的技术补充，不能冒充学术论文。同一篇文献跨文书复用，不重复检索。各文书正文的 `[1]` `[2]` 只是本次排版序号，与稳定 ID 通过映射关联。
- **周计划 `schedule.json`**：项目级唯一计划基线（`draft` 草拟 / `confirmed` 已确认），任务书、开题报告、中期检查共用；**计划不等于实际完成**，实际进展记入可选的 `progress.json`（`PROG-xxx`）。
- **更新规则**：先读后写；已有条目只有在提供证据和理由时才更新（`--replace --reason`），每次变更与成品登记都写入 `activity.jsonl` 审计流水；冲突无法自动合并时生成冲突报告，交你裁决。

```bash
python core\asset-management\project_assets.py status --root "E:\thesis-work\my-project"
python core\asset-management\project_assets.py merge  --root "E:\thesis-work\my-project" --kind references --input new-refs.json
```

## 13. 生成文件保存在哪里

全部产出集中在项目资产包内，**不散落在插件目录**：

| 内容 | 位置 |
|---|---|
| 技术文档 MD / HTML / 执行汇报 | `<PROJECT_ROOT>\deliverables\technical-document\` |
| 任务书 DOCX | `<PROJECT_ROOT>\deliverables\taskbook\` |
| 开题报告 DOCX / 执行汇报 / 文献核验台账 | `<PROJECT_ROOT>\deliverables\opening-report\` |
| 文献综述 DOCX | `<PROJECT_ROOT>\deliverables\literature-review\` |
| 指导记录 DOCX | `<PROJECT_ROOT>\deliverables\guidance\` |
| 中期检查记录表 DOCX | `<PROJECT_ROOT>\deliverables\midterm\` |
| 共享数据（事实/文献/计划/审计） | `<PROJECT_ROOT>\project-assets\` |
| 本轮中间文件（渲染截图、临时 JSON 等） | `<PROJECT_ROOT>\.skill-tmp\<skill-name>\<run-id>\`（结束清理，不进成品区） |

未指定交付路径时使用以上默认位置；也可以在调用时指定自定义交付路径。

## 14. 版本管理、更新与维护

- **成品版本（-vN）**：重新生成时创建 `-v2`、`-v3`…新文件，**永不覆盖、永不删除历史版本**。每个版本在验收后单独登记到 `activity.jsonl`（路径 + SHA-256 + 所用 REF-xxx），自然形成变更史。
- **数据版本**：事实/文献/计划的变更通过显式更新记录（含理由），与成品版本史互相印证。
- **插件更新**：更新插件目录后重新加载（`claude --plugin-dir` 重启会话，或 `/plugin update`）；各 Skill 内置模板的 SHA-256 锁会随版本记录在 `CHANGELOG.md`。
- **升级注意**：官方模板更新属于重大变更，须重新审计适配（见第 8 节）；共享资产 schema 升级会保持向后兼容或提供迁移说明（见 [docs/asset-management.md](docs/asset-management.md)）。

## 15. 查看错误与常见问题

每个 Skill 的**执行汇报**会如实列出：完成事项、实际执行的检查、WARN/FAIL 项、待你确认的信息。插件级问题先跑：

```bash
python scripts\check_env.py --root "E:\thesis-work\my-project" --skill thesis-taskbook-write
python scripts\verify_plugin.py
```

常见问题（Skill 没加载、模板哈希不符、文献核验失败、渲染器缺失、GBK 编码报错、清理失败、成品覆盖保护、project_id 冲突等）的**症状 → 原因 → 处理**见 [docs/troubleshooting.md](docs/troubleshooting.md)。

## 16. 如何添加新的 Skill

（`technical-visual-assets` 即按此流程扩展的支持 Skill。）后续计划扩展：论文正文生成、摘要与关键词、答辩 PPT 规划、指导教师评语、成果说明、更多学校模板。添加新 Skill 的步骤：

1. 在 `skills/` 下新建目录 `skills/<new-skill-name>/`，编写 `SKILL.md`（frontmatter 的 `name` **必须与目录名一致**，`description` 写清触发场景；文书生成类建议加 `disable-model-invocation: true` 防止误触发）。
2. **选择性**复用公共资产：需要共享事实/文献/计划时，以 `core/asset-management/project_assets.py` 为参考实现，制作本 Skill 的"协议兼容副本"（只改所有权常量与本 Skill 专用的 `compose` 装配逻辑）；不需要共享资产的 Skill 可以完全不用它。
3. 新文书类型在 `deliverables/` 下增加自己的子目录名（`doc-type`），模板放 `assets/` 并配 `template-lock.json` 哈希锁。
4. 在 `core/contracts/skill-catalog.json` 注册条目（命令、输入输出、前置条件），README、`docs/skill-catalog.md` 与介绍网站即可低成本同步。
5. 运行 `python scripts\verify_plugin.py` 与 `python tests\run_all.py` 确认无回归。

现有 Skill 不需要因新增 Skill 而重构。

## 17. 备份策略

| 对象 | 策略 |
|---|---|
| `project-assets/`（共享数据 + 审计流水） | **随项目备份**，是最有价值的数据；建议纳入 git 或云盘 |
| `deliverables/`（全部历史版本成品） | **随项目备份**，含每版 SHA-256 记录 |
| 你的原始技术资料 | **随项目备份**，Skill 只读不改 |
| 官方模板原件 | 插件内只读副本 + `template-lock.json` 哈希；你另存的原件自行保管 |
| 插件目录 `thesis-doc-suite/` | 可随时重装/重解压，无需备份；如自行改过 Skill 再考虑备份 |
| `.skill-tmp/` 运行区 | **无需备份**，临时文件用完即清理 |

## 18. 文档索引

| 文档 | 内容 |
|---|---|
| [docs/quickstart.md](docs/quickstart.md) | 以示例项目走完"从准备到首份文档"全过程 |
| [docs/user-guide.md](docs/user-guide.md) | 完整使用手册：每个 Skill 的详细用法与验收要点 |
| [docs/architecture.md](docs/architecture.md) | 系统架构与扩展机制 |
| [docs/asset-management.md](docs/asset-management.md) | 项目资产包结构、schema、读写与冲突规则 |
| [docs/skill-catalog.md](docs/skill-catalog.md) | 10 个 Skill 的逐一说明 |
| [docs/prerequisites.md](docs/prerequisites.md) | 前置条件清单（必需 / 可选） |
| [docs/troubleshooting.md](docs/troubleshooting.md) | 常见问题排查 |
| [docs/migration-report.md](docs/migration-report.md) | 迁移报告：6 个 Skill 的盘点、契约变体与逐文件差异记录 |
| [docs/test-report.md](docs/test-report.md) | 测试验证报告：PASS/WARN/FAIL/未测试 逐项如实记录 |
| `site/index.html` | 离线介绍网站（浏览器双击打开） |
| `CHANGELOG.md` | 版本变更记录 |
