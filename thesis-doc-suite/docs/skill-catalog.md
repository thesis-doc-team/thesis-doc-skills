# Skill 目录（Skill Catalog)

本页与 `core/contracts/skill-catalog.json`（结构化事实源）保持一致。插件共 10 个 Skill：6 个业务 Skill（生成文书）+ 1 个支持 Skill（公共图片资料层）+ 3 个管理型 Skill（初始化/检查/导航）。所有业务与支持 Skill 仅响应显式调用（`/thesis-doc-suite:<skill名>`），普通聊天不会触发文书生成。

---

## 一览表

| 命令 | 类型 | 版本 | 生成什么 | 交付目录 |
|---|---|---|---|---|
| `/thesis-doc-suite:project-technical-doc` | 业务 | 5.4.0 | 技术文档 MD + 用户展示 HTML + 实物模块清单 + 内容分类索引 + 执行汇报 | `deliverables/technical-document/` |
| `/thesis-doc-suite:thesis-taskbook-write` | 业务 | 1.2.2 | 任务书 DOCX + 执行汇报 | `deliverables/taskbook/` |
| `/thesis-doc-suite:opening-report-writer` | 业务 | 4.1.0 | 开题报告 DOCX + 执行汇报 + 文献核验台账 | `deliverables/opening-report/` |
| `/thesis-doc-suite:literature-review-write` | 业务 | 3.2.1 | 文献综述 DOCX + 执行汇报 | `deliverables/literature-review/` |
| `/thesis-doc-suite:thesis-guidance-record-write` | 业务 | 1.2.0 | 指导记录 DOCX + 执行汇报 | `deliverables/guidance/` |
| `/thesis-doc-suite:thesis-midterm-check-write` | 业务 | 1.3.2 | 中期检查记录表 DOCX + 执行汇报 | `deliverables/midterm/` |
| `/thesis-doc-suite:project-solution-write` | 业务 | 1.4.2 | 毕设选题探索 MD/DOCX/HTML（≤10个/批，功能≥5条、有场景、模块化、无PCB）+ 正式介绍 MD/HTML + 实施 MD + 执行汇报（信息混合输入、候选资产、写前冻结、分批写入） | `discovery/`、`projects/PROJECT-xxxx/`、`deliverables/project-introduction/`、`deliverables/implementation-plan/` |
| `/thesis-doc-suite:technical-visual-assets` | 支持 | 1.4.3 | 正交技术图（可编辑 Mermaid/drawio、正交 SVG、原生 VSDX、300dpi PNG）+ 中英文图题 + A4/Word 版心门禁 + 六类资源索引 | `project-assets/resource-catalog/`、`project-assets/visual-assets/` |
| `/thesis-doc-suite:init-project` | 管理 | 0.1.0 | 项目资产包骨架 | — |
| `/thesis-doc-suite:check-project` | 管理 | 0.1.0 | PASS/WARN/BLOCK 检查报告 | — |
| `/thesis-doc-suite:help` | 管理 | 0.1.0 | 命令导航与使用指导 | — |

---

## 业务 Skill 逐项说明

### project-technical-doc｜项目技术文档生成（v5.4.0）

- **定位**：只读理解真实项目资料/源码，产出有证据的 Markdown 技术文档，并派生单文件离线 HTML 用户展示网站。是共享技术事实（FACT-xxx）的主要提炼者。
- **生成**：`<项目名>-技术文档.md`、`<项目名>_用户展示.html`、`physical-modules.json`（实物模块清单）、`content-index.json`（表/图/模块分类与相似组）、`执行汇报.md`、（大型项目）`项目事实与证据台账.md`。
- **必需输入**：项目源码或技术资料（MD/DOCX/PDF 等）、项目根目录。
- **可选输入**：展示配置.json、已有 project-assets 事实库。
- **前置条件**：Python 3.10+；markdown-it-py、beautifulsoup4（HTML 派生）；无需官方 Word 模板。
- **图表门禁**：`diagram_qc.py` 检查 SVG 过宽、字号 <9px、节点/文字重叠、连线端点未接节点、marker 失效；节点数量本身不判失败，信息完整性优先。
- **场景**：把真实项目整理成可交付的技术说明文档和展示网页时。
- **边界**：不生成"已知问题与改进建议"等评审章节；不编写任何毕业设计 Word 表格。

### thesis-taskbook-write｜毕业设计任务书（v1.2.2）

- **定位**：在官方空白任务书 DOCX 允许填写区原位填充，保留全部固定栏目/表格/签名结构；参考文献经真实检索核验。
- **生成**：`<课题简称>-毕业设计任务书-vN.docx`、执行汇报。
- **必需输入**：技术资料或技术 MD、官方任务书 DOCX 模板（内置只读副本）、课题题目、项目根目录。
- **可选输入**：院系/班级/姓名/学号/导师/职称、起止日期、已核验参考文献、已填任务书范本。
- **前置条件**：Python 3.10+（python-docx、lxml、PyMuPDF）；LibreOffice 或 Word 兼容渲染器（逐页截图）；≥10 篇真实可核验参考文献；官方模板 template-lock.json 哈希匹配。
- **场景**：开题前提交学校格式的毕业设计任务书。
- **边界**：不生成开题报告/论文/HTML；下达人意见为拟稿，签名日期空白。

### opening-report-writer｜毕业设计开题报告（v4.1.0）

- **定位**：在官方空白开题报告 DOCX 允许填写区编写七项完整内容（立项依据、研究现状、任务与可行性、重点问题、工作条件、进度计划、参考文献）。
- **生成**：`<课题简称>-毕业设计开题报告-vN.docx`、执行汇报-vN.md、文献核验台账-vN.md。
- **必需输入**：项目技术文档（上游技术 MD 优先）、官方开题报告 DOCX 模板（内置只读副本）、项目根目录。
- **可选输入**：已核验参考文献（复用 REF-xxx）、共享周计划、封面个人信息。
- **前置条件**：Python 3.10+（python-docx、lxml、PyMuPDF）；LibreOffice 或 Word 兼容渲染器；≥10 篇真实可核验参考文献；正文汉字 ≥3000（不含文献与封面）。
- **场景**：开题答辩前撰写并排版开题报告。
- **边界**：不得把尚未完成的研究工作写成已完成；不生成技术文档/任务书/中期检查/论文/HTML。

### literature-review-write｜文献综述（v3.2.1）

- **定位**：在学校官方 DOCX 文献综述模板原位编写综述正文（真实 Word 上标引文、参考文献、指导教师意见拟稿），按研究问题组织文献比较与评述。
- **生成**：`<课题简称>-文献综述-vN.docx`、执行汇报。
- **必需输入**：当前课题技术资料、官方文献综述 DOCX 模板（内置只读副本）、项目根目录。
- **可选输入**：已核验文献（复用 REF-xxx）、文献综述范本、封面个人信息。
- **前置条件**：Python 3.10+（python-docx、lxml、PyMuPDF）；LibreOffice 或 Word 兼容渲染器；正文 ≥2500 字；默认 ≥8 篇独立真实文献（服从学校要求）。
- **场景**：提交毕业设计文献综述、或为开题报告积累文献基础。
- **边界**：不堆砌技术介绍、不生成任务书/开题报告/中期检查；不把简单标题罗列当综述。

### thesis-guidance-record-write｜毕业论文（设计）指导记录（v1.2.0）

- **定位**：按真实项目技术阶段拟稿不少于 8 次指导记录，问题与修改意见一一编号配对，自动复制官方 13 行记录表，评价与签名栏保持空白。
- **生成**：`<课题简称>-指导记录-vN.docx`、执行汇报。
- **必需输入**：真实项目技术资料、官方指导记录 DOCX 模板（内置只读副本）、项目根目录。
- **可选输入**：真实指导时间/地点/方式（缺失一律留空）、已填范本、共享计划与进展。
- **前置条件**：Python 3.10+（python-docx、lxml、PyMuPDF）；LibreOffice 或 Word 兼容渲染器；≥8 个有真实依据的指导主题。
- **场景**：整理指导记录表供审核打印。产出为待审核拟稿/打印底稿，不代替实际指导与手写签字。
- **边界**：不虚构指导会议/教师意见/完成日期/签名；官方表无参考文献栏，不擅自添加。

### thesis-midterm-check-write｜毕业设计中期检查记录表（v1.3.2）

- **定位**：在官方中期检查记录表 DOCX 允许填写区写入完成进度、问题与整改（逐条编号一一对应）和指导教师意见拟稿，三栏各 ≥200 字。
- **生成**：`<课题简称>-中期检查记录表-vN.docx`、执行汇报-vN。
- **必需输入**：真实项目技术资料、官方中期检查 DOCX 模板（内置只读副本）、项目根目录。
- **可选输入**：共享周计划 schedule.json、进展快照 progress.json、检查日期、班级/姓名。
- **前置条件**：Python 3.10+（python-docx、lxml、PyMuPDF）；LibreOffice 或 Word 兼容渲染器；计划与实际进度的真实证据。
- **场景**：中期检查节点提交进度与问题整改记录表。
- **边界**：不把计划写成已完成成果、不凭空编造工作成果；学院意见默认空白；不生成其他文书。

---

## 支持 Skill 逐项说明

### project-solution-write｜毕设选题探索、候选推荐与正式方案（v1.4.2）

- **定位**：专业/技术/题目信息可混合输入，默认直接进入毕设/课程设计选题推荐；无题目也能从专业/技术出发推荐，每轮最多 10 个独立候选；正式确认题目与功能后进入原严格方案流程。**只做选题候选与方案文档，不执行开发**。
- **探索阶段**：每个候选独立生成 `项目概览.md`、`项目概览.docx`、`项目概览.html`（只含名称、概述、核心功能简述）；维护 `discovery/catalog.json`、`profile.json`、`rejected-projects.json`、`history.jsonl`，稳定 `PROJECT-xxxx` ID，candidate/interested/rejected/confirmed 状态与不可覆盖版本；拒绝默认不重推，用户明确恢复沿用旧 ID。
- **正式阶段**：题目+功能硬门禁、成本/性能/功能/均衡选择、写前设计冻结、分批写入与一次终检、介绍 MD/HTML + 实施 MD 边界保持不变；候选不生成完整实施方案。
- **HTML 可视化**：`templates/project-introduction.html` + `scripts/generate_intro_html.py` 以介绍 MD 为唯一内容源生成单文件、离线、响应式介绍页；`scripts/validate_intro_html.py` 检查离线、安全、内容边界、功能一致性与场景“未实测”标注。
- **生成**：探索阶段 `项目概览.md/docx/html`（每批≤10个，每个候选独立三文件）；正式阶段 `<项目简称>-项目介绍与功能说明-vN.md/.html` 与 `<项目简称>-工程实施方案-vN.md`。
- **必需输入**：专业/技术关键词/项目想法（至少一项）；项目根目录；正式阶段需题目+具体功能。
- **可选输入**：功能树/清单（正式阶段必需，探索期可后补）、既有技术资料/源码、已确认约束与选型、已核验文献（REF-xxx）。
- **前置条件**：Python 3.10+（正式方案仅标准库；候选 DOCX 需 `python-docx>=1.1,<2`）；无需官方 Word 模板；静态检查后须人工逐章审阅；候选 DOCX/HTML 需实际渲染抽查，未逐候选浏览器验收需如实说明。
- **场景**：只有专业/技术/想法时先做候选；用户确认题目与功能后生成正式方案；需要候选或正式文档时使用。
- **边界**：候选只写名称/概述/功能，不写推荐理由、评分、选型、成本比较、开发计划；正式阶段不臆造实测、不擅增功能、不写交付/收费/改进建议；已有实现的技术文档/HTML 展示交 `project-technical-doc`。

### technical-visual-assets｜正交工程绘图、原生 VSDX 与视觉资产（v1.4.3）

- **定位**：用户指定正式技术 MD 为唯一事实源，离线提取/绘制正交（横平竖直）技术图；生成原生 VSDX（Visio 打开状态如实标注）、中英文图题、A4/Word 版心与实际渲染门禁；Visio 式 SVG + 可编辑 drawio；六类资源目录；**不包含任何联网搜图功能**。**只做素材与登记，不负责在文书里插图**（插图由下游 Skill 自行决定）。
- **生成**：`project-assets/resource-catalog/` 与 `project-assets/visual-assets/`——MD 驱动的六类资源索引与图表源、仅从 MD 提取的模块实物照片上传清单、用户照片经本地验证后的 RES/VIS 候选记录、可编辑 Mermaid/drawio、正交 SVG、原生 VSDX、300dpi PNG、A4 布局审计结果、中英文图题元数据（`.figure.json`）。
- **必需输入**：同项目根目录与稳定 project_id、本项目正式技术 Markdown。
- **可选输入**：用户上传的模块照片与权利声明、官方 A4 DOCX 模板（Word 适配阶段必需）、同项目派生 FACT 用于正式 VIS 审核。
- **前置条件**：Python 3.10+（仅标准库，禁止自动装包）；无需联网搜图、不自动安装工具；300dpi PNG 导出需本机 Chrome/Edge（无浏览器时保留 SVG）；VSDX 生成不需要 Visio，Visio 实际打开验证需本机 Visio/WPS 并如实标注。
- **场景**：依据唯一正式技术 MD 生成可编辑工程图、原始数据表格、用户实物图需求清单；按官方模板验收 A4 版式后由文书 Skill 复用。
- **边界**：技术事实只来自上游 MD 与 FACT；不修改上游 MD 与业务 Skill；用户照片需权利声明并经本地验证后入库；不恢复联网搜图。

---

## 管理型 Skill 逐项说明

### init-project｜初始化项目资产包（v0.1.0）

- **定位**：在用户指定的项目根目录创建 `project-assets/`（数据层）与 `deliverables/`（成品层）骨架；一个项目一个资产包，已存在不覆盖、project_id 不一致拒绝混用。
- **输入**：项目根目录、稳定 project_id、项目名称；可选人员元信息。
- **前置条件**：Python 3.10+（仅标准库）。
- **场景**：为新毕业设计项目使用本插件的第一步。

### check-project｜前置条件与资产检查（v0.1.0）

- **定位**：检查运行环境、插件完整性、模板哈希与项目资产状态，按 **PASS / WARN / BLOCK** 三类输出结论。BLOCK 仅用于确实阻止当前操作的关键缺失，不把所有缺项都判为 BLOCK。
- **输入**：可选项目根目录、目标 Skill 名称。
- **前置条件**：Python 3.10+（仅标准库）。
- **场景**：生成文书前确认资料齐备；排查 Skill 无法执行的原因。

### help｜使用导航（v0.1.0）

- **定位**：展示全部可用命令、推荐工作流程与文档入口（README、docs/、site/），按当前进度给出下一步建议。
- **输入**：可选具体问题或场景描述。
- **场景**：忘记命令、不知道先做什么、想了解某个 Skill 能干什么。

---

## Skill 之间的关系（速览）

- **共享资产复用**：技术文档提炼 FACT → 任务书/开题报告复用；文献综述与开题报告共享 REF；中期检查/指导记录读取计划与进展；technical-visual-assets 读取技术 MD 与 FACT 登记 VIS 视觉资产（`project-assets/visual-assets/` 子层）。
- **执行独立性**：任何 Skill 可单独调用；复用关系不构成固定执行顺序；缺非必要资料降级执行并声明影响。
- **边界**：业务 Skill 不越界生成其他业务文书；管理型 Skill 不修改业务 Skill 职责。
- 详见 [architecture.md](architecture.md) 与 `core/contracts/skill-boundaries.md`。
