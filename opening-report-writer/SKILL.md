---
name: opening-report-writer
# Trigger: 根据用户本次提供的技术文档，编写“塔里木大学毕业论文（设计）开题报告”。
# Outputs: 正式 Word + 执行汇报 + 文献核验台账；不制作技术文档、网页、论文正文或答辩 PPT。
# v2: 交付目录只保留最终成果（过程文件写入运行目录并在交付前删除）；参考文献左对齐排版并进入终检。
# v3: 接入项目级共享资产 project-assets（一个项目一个数据资产库，REF-xxx/周计划/FACT-xxx 先读后写、record-use 留痕、安全清理）。
description: 以用户本次提供的项目技术文档为唯一项目事实基础，结合可核查的学术论文、学位论文、标准与必要的官方技术资料，按内置塔里木大学官方开题报告 DOCX 空白模板编写七项必需内容；在不改动官方模板原件、封面/填写说明/正文提示/表格/签名意见/页码等固定内容和版式的前提下，仅填充授权空白区域。正文五号宋体、英文 Times New Roman、1.5 倍行距；正文引文必须是 Word 真正上标，文献编号只出现一次；参考文献段落显式左对齐+悬挂缩进，禁止两端对齐拉伸空隙。生成后通过自动结构校验、逐页渲染校验，交付 DOCX、执行汇报与文献核验台账三项，其余中间文件交付前一律清理，由用户最终验收。兼容上游 project-technical-doc 产出的 Markdown，但不调用其生成流程、不产出 Markdown 技术文档或 HTML。接入 <PROJECT_ROOT>/project-assets/ 项目级共享资产：参考文献与周计划先读后写复用，交付后 record-use 留痕。
---

# opening-report-writer v3｜基于技术文档编写开题报告

## 0. 技能定位与绝对边界

本 Skill 的唯一主任务是：**读取用户在当前任务中给出的技术文档 → 提炼开题报告论证 → 真实检索并核对参考文献 → 将内容填入官方 Word 模板副本 → 全面校验并交付。**

**禁止**：修改项目源码、补写/改写技术文档、输出或运行技术文档 Skill 的 HTML 生成链路、编写毕业论文全文、课程设计报告、可行性报告或答辩 PPT、替用户填写指导教师评语或签名、修改学校官方模板原件。不能把旧的项目案例（例如某 Linux 设备监控系统）作为新项目技术事实来源。

上游 `project-technical-doc` 与本 Skill 的接口：其**最终 Markdown 技术文档**可以作为本 Skill 的输入；本 Skill 从该技术文档提取技术事实，再单独完成开题报告，**绝不自动重写上游文件**。如用户同时要求两类成果，由外部调度明确按“技术文档 → 开题报告”顺序运行；两个 Skill 分别验收。

## 1. 项目级共享资产（project-assets）：一个项目一个数据资产库，强制先读后写

本 Skill 与 `thesis-taskbook-write`（任务书）、`project-technical-doc`（技术文档）以及后续论文/答辩 Skill **同属一套文书系统**：一个真实项目只有一份共享数据资产 `<PROJECT_ROOT>/project-assets/`，由多个 Skill 共同维护。**任务书生成时已核验的参考文献与已排定的周计划，本 Skill 直接按稳定 ID 复用，不再重新检索、不另编一套**，杜绝“任务书一份文献/计划、开题报告又一份”的货不对板。完整契约见 `references/shared-project-assets-contract.md`；命令用本 Skill 自带的 `scripts/project_assets.py`（协议兼容副本，所有权常量已归属本 Skill）。

### 1.1 存储位置与红线

- 唯一持久化根目录：`<PROJECT_ROOT>/project-assets/`，含 `project.json`（项目标识、用户确认的稳定元信息）、`references.json`（REF-xxx 文献库）、`schedule.json`（周计划基线）、`facts.json`（FACT-xxx 项目事实）、`activity.jsonl`（审计流水）。
- **绝不能**把 `project-assets/` 放在 `.claude/skills/`、`.agents/skills/` 或本 Skill 安装目录内；**禁止**向本 Skill 的 `assets/` 保存项目论文或项目事实（Skill 升级会丢资料）。共享资产、用户原始资料、官方模板原件、最终交付**永不删除**。
- `project_id` 唯一且持久：读到的 store 与本次任务 project_id 不一致时**立即停止合并**，防止串项目。store 不存在时才允许 `init`，并向用户说明已新建。

### 1.2 稳定 ID 与正文编号

- 文献长期身份是 `REF-xxx`；正文 `[1]`…`[N]` 只按**本份文书**首次引用顺序临时生成，绝不把 `[1]` 当长期 ID，也不沿用上一份文书里的编号。
- 技术事实是 `FACT-xxx`，`status ∈ implemented/declared/unverified/proposed`；周计划阶段用稳定 stage ID。跨文书关联**只通过稳定 ID**。
- 事实状态不因文体改变：开题报告的“拟实现/预计验证”只是表达方式，不得把共享库中 `declared/proposed` 的事实改写成 `implemented`。

### 1.3 固定执行顺序（每次运行必走）

1. **识别项目**：确定 `<PROJECT_ROOT>` 与 `project_id`，`python scripts/project_assets.py status --root <PROJECT_ROOT>` 读取现有资产基线。
2. **先读后写**：优先复用已 verified 且相关的 REF-xxx 与周计划基线；仅补充**缺失且有证据**的条目（`merge --kind references|facts|schedule`），不重新创作已存在且仍适用的资产。
3. **只经稳定 ID 关联**；确需变更已有条目时，必须有依据并显式覆盖（`--replace --reason`），并在执行汇报写明影响的下游文书。**禁止默默覆盖**其他 Skill 已审定的计划、已验证文献、用户原始资料与官方模板；**禁止为了复用而生造**文献或事实。
4. **本份文书独立验收**：文献相关性、引用支持范围、模板与各项门禁照常执行；资产库有内容 ≠ 可跳过本轮检查。
5. **使用记录（强制）**：交付后 `record-use --file <成品.docx> --doc-type opening-report --ref-ids REF-xxx,…`，登记实际采用的 REF ID、成品路径与 sha256。
6. **安全清理**：过程文件只写自己的 `<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/`（由 `workdir` 命令创建，带所有权标记）；报告完成后 `cleanup --run-id` 只删本 Skill 自己的运行目录，**不得**删除其他 Skill 的 `.skill-tmp`、共享资产、用户资料、官方模板与最终交付。

### 1.4 各资产在本 Skill 中的用法

| 资产 | 用法 |
|---|---|
| references.json | **优先复用** verified 的 REF-xxx；缺口才检索补充，新核实条目 `merge` 入库（verified=true 必须附真实 checked_at）。只在导出文书时按本校格式排版，不改共享条目内容 |
| schedule.json | 进度计划**以共享周计划基线为准**：措辞可按开题文体详略调整，**周次、顺序、日期不得暗改**；基线是 draft 就照实标“暂定”，绝不把 draft 说成 confirmed；确属项目级变更须 `--replace --reason` 并报告影响 |
| facts.json | 复用既有 FACT-xxx；本轮从技术文档新提炼的事实按证据等级映射入库：VERIFIED→implemented、DECLARED/EXAMPLE→declared、DESIGN/PLANNED→proposed、UNKNOWN→unverified，source 必须带文件+章节定位 |
| project.json / activity.jsonl | metadata 只存用户确认的稳定字段（不存密码）；merge/record-use 自动留审计痕，不手改 |

```bash
# 命令速查（compose 是任务书专用装配命令，本 Skill 不使用）
python scripts/project_assets.py status  --root <PROJECT_ROOT>
python scripts/project_assets.py workdir --root <PROJECT_ROOT>            # 建本轮运行目录 .skill-tmp/opening-report-writer/<run-id>/
python scripts/project_assets.py merge   --root <PROJECT_ROOT> --kind references --input <run目录>/new-references.json
python scripts/project_assets.py merge   --root <PROJECT_ROOT> --kind schedule   --input <run目录>/schedule-proposal.json
python scripts/project_assets.py record-use --root <PROJECT_ROOT> --file <成品.docx> --doc-type opening-report --ref-ids REF-001,REF-002
python scripts/project_assets.py cleanup --root <PROJECT_ROOT> --run-id <run-id>
```

### 1.5 项目资产包（bundle）布局与版本意识

一个项目 = 一个**资产包目录**（按项目分类，插件化后项目间互不串扰，整包可拷贝/归档/迁移）：

```text
<PROJECT_ROOT>/                        # 项目资产包根；--root 就指向这里
├── project-assets/                    # 共享数据资产（多 Skill 共写，见 1.1）
├── deliverables/                      # 成品集中区，按文书类型分目录
│   ├── taskbook/……任务书-v1.docx
│   └── opening-report/……开题报告-v1.docx
└── .skill-tmp/<skill-name>/<run-id>/  # 各 Skill 运行目录（自动清理）
```

- **成品集中**：本 Skill 的最终文书交付到 `<PROJECT_ROOT>/deliverables/opening-report/`，不散落其他 output 目录；查一个项目的全部产出只看这一个包。
- **版本意识**：项目内容变更或调用 Skill 重新生成时，产出 `-v2`、`-v3`…**新文件绝不覆盖历史版本**；每个版本单独 `record-use` 登记（路径 + sha256），`activity.jsonl` 自然形成变更史。数据层（计划/事实/文献）变更走 `--replace --reason`，与成品版本史互相印证。
- 历史版本属于持久成果，**不在清理范围**；清理只针对 `.skill-tmp` 运行目录。

## 2. 官方模板是最高格式依据，不得修改

- 官方原件：`assets/official-opening-report-template.docx`，来自用户指定的《02_塔里木大学毕业论文（设计）开题报告.docx》。**只读、不可覆盖或重新排版**。
- 模板 SHA256：`assets/template.sha256`。每次运行前必须校验；不一致立即 FAIL。
- **只允许**在生成的副本中填充封面字段和正文第一行表格的空白书写区域；为适配篇幅，书写区域内的冗余空白占位段落可用于填充或清除。该操作是对可填写区域进行填报，不是更改学校的固定格式。
- **绝不能改**：页尺寸、页边距、节、页眉页脚、页码、学校名称、封面字段名称、教务处制、附件标识、填写说明原文、正文说明文字、表格边框/行列结构、学生签名/日期、指导教师审阅意见/签名/日期，也不能私自更换整体模板。
- 用户缺少姓名、学号、导师、时间等信息时：**保留官方空格/下划线，不借用历史范本中的人物信息**。
- 若用户说“模板格式不能改”，优先保持官方原件的结构；若可读性改善与原件冲突，**以原件为准**，在汇报中说明，不暗改。
- 样本开题报告只用于理解写作层次与论文论证方式；与官方模板发生冲突时不采用样本的设置。详情见 `references/official-template-invariants.md`。

## 3. 输入与唯一项目事实来源

| 本次用户给的资料 | 可做的工作 | 不可擅自断言 |
|---|---|---|
| 技术文档 MD/DOCX/PDF/说明书 | 提取课题定位、问题背景、功能、架构、关键技术、测试计划和工程条件 | “源码已验证”“功能经过真实测量” |
| 技术文档 + 源码（明确授权只读） | 用源码辅助核对技术事实与模块状态 | 未执行的测试“通过” |
| 技术文档 + 项目测试报告 | 将真实实测与拟达到目标区分 | 用目标值替代实测值 |
| 上游 technical-doc Skill 最终 MD | 直接作为当前项目事实输入，提炼开题报告内容 | 倒写、修改上游 MD/HTML |

根据输入建立简短证据台账（可临时文件），按 **VERIFIED（直接可见的实施/测试证据）／DECLARED（资料声明）／DESIGN（已有方案）／PLANNED（本次开题拟完成）／UNKNOWN（不足）** 标记。开题报告属于“准备做什么、为什么可行、如何验证”的文体：即使源码已有部分实现，仍使用适宜的研究任务、设计路线、预计验证表达，不能把现有结果虚构成已经完成的毕业设计结论。

**不得**从旧范本、旧聊天项目、生成器示例、一般行业常识推断本项目的具体型号、参数、功能、数据表、算法指标、测试结论。

## 4. 官方要求与通用章节预设

学校官方填写说明**要求七项内容，不规定正文七章的具体字面标题**。为了批量复现一致的写作格式，本 Skill 设置可复用章节预设（非学校新增规定）：

1. `1 课题研究立项依据` → 建议 `1.1 课题背景`、`1.2 研究目的和意义`。
2. `2 国内外研究现状及分析` → 国内/国外可以分小节，需对文献进行比较评述，非网页资料堆砌。
3. `3 课题任务要求及实现预期目标的可行性分析` → 任务、预期目标、技术/环境/实施可行性。
4. `4 重点研究的问题及解决思路` → 重点问题、原因与可实现的解决路径。
5. `5 完成课题所需工作条件及解决办法` → 开发条件、软硬件环境、测试条件与获取方式。
6. `6 工作方案及进度计划` → 技术路线、阶段任务、验收节点、周次计划。
7. `7 主要参考文献` → 可核查的来源不少于 10 篇，全文引文与文末一一对应。

上述一级标题**默认锁定一致，不随项目任意改名**。如果用户交来的当前学校正式指南明确规定不同字面章题，或用户明确授权调整，则以正式要求为准，并在 JSON 中设置 `allow_custom_heading_titles=true`。二级标题可根据项目特点增减，但不得漏掉官方七项内容；尤其不能把“工作条件”和“工作方案”混为一章而漏写。**第一章二级标题固定首选“课题背景”，不回退到旧版“课题来源”。**

正文不少于 3000 个汉字（实际按模板的字数要求核对），建议围绕研究动机、现状评述、研究任务、关键技术与验证方案形成完整论证。字数不靠无意义重复凑数。参考文献、封面、学校说明不计入正文 3000 字自动核查。写作参考 `references/content-writing-guide.md`。

## 5. 学术参考文献：必须实际检索、逐条核实

阅读 `references/literature-policy.md` 并严格执行：

- 优先：**CNKI 中国知网、万方、维普、学校图书馆数据库**内可核验的论文/学位论文；国际的 IEEE Xplore、ACM Digital Library、SpringerLink、ScienceDirect、期刊官网及 DOI 出版页；适用的正式标准/RFC 与官方技术文档亦可引用。
- **CSDN 可以作为软件实现、工具操作的辅助技术参考**，但其内容不能代替学术领域的研究现状论证；仅在有明确作者、标题、访问 URL、可核对正文时引用，原则上不超过 2 篇，优先于博客引用其原始论文或官方文档。
- Google Scholar、百度学术等可用于**发现文献**，引用时应追溯到论文出版社、学位论文库、DOI 注册页或原始可核对条目；不能把搜索摘要当作已读全文。
- 每一项必须在当前任务核查**真实作者、题名、年份、出版载体、卷期页码（如有）、DOI/稳定 URL**，并登记来源与核查日。不能臆造论文、凭空填 ISBN/DOI、以“看似学术”代替实际存在。
- 引用的**支持范围**应与正文句子对应；只确认存在但未读到摘要/结论，不得写具体研究结果。不能虚构引用中的性能提升数字、市场规模或结论。
- 不少于 10 项，原则上**至少 7 项**为期刊论文、会议论文、学位论文、书籍、标准或官方技术文档，网络博客最多 2 项。
- 可借鉴 GB/T 7714 著录顺序，若当前学校给出更明确的格式则以学校规定为准。URL/DOI 不应因为篇幅被自动截断；网址太长需检查换行布局。

**正文引用是 Word 真正上标**：生成输入必须用 `[[cite:1]]`、`[[cite:1-3]]`、`[[cite:1,3]]` 标记，构建器将其转换成上标 `[1]`；**文末条目是基线 `[1]`，只出现一次编号**。禁止手工写裸 `[1]` 再让 Word 自动列表二次编号。**参考文献也采用 1.5 倍行距**，与正文一致。**参考文献段落必须显式左对齐 + 悬挂缩进，禁止两端对齐**：含长 URL 的外文条目在两端对齐下会被 Word 拉伸出行内大空隙（"OASIS.　MQTT　Version…"式排版事故）；该属性由构建器写入、`check_report.py` 终检强制校验，并列入逐页目视清单。不要拿前一版文献清单直接复用，除非本次逐条核实并确与新课题有关。

## 6. 一次性执行流程（Agent 必须完成）

### A｜读取模板与本次技术文档

0. **接入共享资产（第 1 章）**：确定 `<PROJECT_ROOT>` 与 `project_id`，运行 `project_assets.py status` 读取 REF-xxx、周计划与 FACT-xxx 基线并记录；project_id 不一致立即停止，store 不存在才按第 1 章处置。
1. 读 `references/official-template-invariants.md`，检查 `assets/template.sha256`；若当前任务用户另给官方模板，应由用户显式授权更换内置原件，不能默默覆盖。
2. 从本次技术文档提炼“课题—背景—任务—架构/技术路线—关键问题—开发条件—测试与预期目标”。
3. 建立证据矩阵：每一重要功能、技术和指标必须能反向定位到用户资料；未知内容谨慎表述。
4. 对不影响写作的缺失信息（姓名、日期）保留官方空白，不反复追问；只有决定性课题边界/技术事实冲突才向用户提出单个必要问题。

### B｜独立做文献检索与研究现状

- **先复用共享文献库（第 1 章）**：从 `references.json` 选取已 verified 且与本课题相关的 REF-xxx 覆盖研究现状论点，缺口才补检；新核实条目在交付前 `merge` 入库（稳定 REF-xxx，verified=true 附 checked_at）。
- 先根据课题类型生成中文与英文检索式；按 `references/literature-policy.md` 的分层目录检索，核对真实来源。
- 建立内部候选文献与“正文论点映射”表；按**正文首次引用顺序**编排最终参考文献编号。
- 不能联网/找不到 10 篇核实资料时：不得为凑够条目编造；说明门禁尚未通过，列出已核查项及需要补足的范围，**不得声称提交版 PASS**。

### C｜撰写完整七章开题正文

- 先完成**内容草稿**，可在 Agent 内部采用结构化 JSON；这不是给用户另写一篇 Markdown 技术文档。
- 首章避免“本系统已成功验证”一类开题时态错误；目标用拟实现/预计验证，已有实现作为基础事实而非最终结论。
- 研究现状必须组织国内外技术路线、已知研究进展与本课题区别，每个具体外部研究判断应有真实参考来源。
- 关键问题必须是本项目实际需要解决的工程难点，方案与本次技术文档契合，不扩展为大而空的未来规划。
- 进度计划采用 `第1周--第2周：任务`；**不用 `～`、`~`、长破折号代替 `--`**。各任务与正式起止时间要一致，没有任务书时标“暂定”，不要擅定毕业答辩日期。周计划**以共享 schedule.json 基线为准（第 1 章）**：可调整措辞详略，不得暗改周次/顺序/日期；基线缺失时可提出 draft 候选并 `merge`，不得声称为已确认。
- 教师审阅意见和签字区一律保持空白，交指导教师填写。

### D｜将文本整理成结构化 `报告内容.json`

阅读 `references/report-json-contract.md`：封面字段、7 节 blocks、文末至少 10 项已核查文献。项目事实与真实来源均由 Agent 填入；`references/` 里的范本及示例**不提供任何新项目事实**。周计划与技术事实**从共享资产读取（第 1 章）**：进度计划按 schedule.json 基线措辞化，事实口吻与 facts.json 的 status 保持一致（declared/proposed 只写“拟/预计”）；本轮新提炼事实按第 1 章映射 `merge` 入库。**该 JSON 是过程中间层，写入本轮运行目录 `<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/报告内容.json`**（目录由 `project_assets.py workdir` 创建），不得散落在交付目录顶层。

### E｜必须从官方模板副本生成 DOCX

```bash
python scripts/build_report.py "<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/报告内容.json" \
  --output "<PROJECT_ROOT>/deliverables/opening-report/<项目名>-毕业设计开题报告-vN.docx"
```

该工具用 OOXML **仅修改 `word/document.xml` 中封面空白填写位与正文留白区**（参考文献段落同时写入左对齐+悬挂缩进），其余 ZIP 部件逐项保留。原件始终只读；若哈希不同、固定锚点缺失、参考文献不合格，脚本报错并中止，不能另建“相似模板”绕开。

### F｜机器结构检查 + 全页渲染检查（缺一不可）

```bash
python scripts/check_report.py "<PROJECT_ROOT>/deliverables/opening-report/<项目名>-毕业设计开题报告-vN.docx" \
  --json "<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/报告内容.json" \
  --output-report "<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/结构校验.json"

python /home/oai/skills/docx/render_docx.py \
  "<PROJECT_ROOT>/deliverables/opening-report/<项目名>-毕业设计开题报告-vN.docx" \
  --output_dir "<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/.render" --emit_pdf
```

得到 PDF 后，尽可能再执行 `python scripts/check_render.py "<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/.render/毕业设计开题报告.pdf" --output-report "<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/渲染预警.json"`，自动预警教师签字与审阅意见分离、末页孤立签名（该检查可选安装 PyMuPDF，仍然不能代替目视）。

在没有上述固定路径的环境中，可调用本地 Word/WPS/LibreOffice 输出逐页 PDF/图片；如果**根本无法渲染**，清楚汇报“未完成视觉验收”，不可说已经排版检查通过。

**截图验证分析（Screenshot Verification Analysis，交付前硬性环节，缺一不可）**：上述渲染产物即页面截图，必须**逐张分析**后才能写“视觉检查通过”、才能进入交付。固定三步——

1. **截图**：`render_docx.py` 或本地 Word/WPS/LibreOffice 逐页 PNG/PDF，只存 `<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/` 运行目录，不进交付目录。
2. **逐张分析**（缺一张即未完成）：封面字段错位、参考文献行距/编号/**两端对齐拉伸空隙（行内异常大空格）**、正文上标、跨页表格边框、悬空章题、孤立签字/日期、页码、页眉页脚、文字溢出、字体替代。
3. **留痕汇报**：执行汇报固定填写截图引擎/工具、截图张数（=页数）、实看张数、逐张结论 PASS/WARN/FAIL 与问题清单、返工复检次数、WPS/渲染实测边界声明。

红线：未逐张分析不得宣称排版/视觉验收通过、不得登记 record-use；无法截图时如实报“截图验证分析未完成”；发现错误**优先调整新写入文字量、段落拆分、章内措辞**，不得通过更改官方表格、页边距或签字区“修图”；固定模板约束内无法消除的报 WARN 交用户决策，不隐瞒；截图是验证手段不是交付物，结论写入执行汇报后随本轮中间文件清理。

### G｜清理中间件、一次性交付与停止

最终交付目录默认：`<PROJECT_ROOT>/deliverables/opening-report/`（项目资产包成品区，见 1.5）。**本轮交付必须恰好 3 个文件（一个版本一组），交付前清理全部过程文件**：

- **必须**：`<项目名>-毕业设计开题报告-vN.docx`（从官方空白模板复制填报，不交替代格式；重生成递增 N，不覆盖历史版本）。
- **必须**：`执行汇报-vN.md`（对照 `templates/execution-report.md`，列结构检查、渲染检查、文献核实数量和限制、交付目录清单）。
- **必须**：`文献核验台账-vN.md`（本次逐条文献核验留痕）。

**中间文件一律不得留在交付目录**：过程 JSON、结构/渲染检查报告、渲染 PDF/PNG、检索脚本与核验日志、下载的文献 PDF、临时依赖目录等，统一写入本轮运行目录 `<PROJECT_ROOT>/.skill-tmp/opening-report-writer/<run-id>/`（`project_assets.py workdir` 创建）；交付前**先 `record-use` 登记成品（第 1 章第 5 步）**，再 `project_assets.py cleanup --run-id <run-id>` **整体删除本轮运行目录**（只删本 Skill 自己的目录）；若交付目录混有历史遗留过程文件（lit_*、*.py、sitelib、.render、*.json 等非白名单文件），一并删除。**共享资产 project-assets/、用户原始资料、官方模板原件、最终交付（含历史版本）与其他 Skill 的运行目录任何情况下不得删除。**执行汇报必须记录"交付目录清单"并逐一核对恰为本轮版本 3 项（历史版本不计入、不删除）。不可向用户交假装已完工的虚构正文。

在对话中直接报告本次**实际完成了什么、什么没完成、未确认什么、文件路径在哪**。自动检查不是用户最终验收；**最终是否接受由用户决定**。不修改 Skill 自身以追求某次特定项目，改进规则须获得用户授权。

## 7. 按需索引（少读文件，提高可复用性）

| 文件 | 何时读取 |
|---|---|
| `references/official-template-invariants.md` | 每次填写模板之前；模板结构变化时 |
| `references/content-writing-guide.md` | 读完技术文档开始编写七大部分时 |
| `references/literature-policy.md` | 文献检索、引用与核验时 |
| `references/report-json-contract.md` | 拼装 JSON 与生成 Word 前 |
| `references/quality-gates.md` | 最终验收前 |
| `references/integration-contract.md` | 以后与 project-technical-doc 合并时 |
| `references/shared-project-assets-contract.md` | 每次运行开始；涉及跨 Skill 资产复用/变更时 |
| `scripts/project_assets.py` | 读写 project-assets/、创建/清理运行目录、record-use 时 |
| `references/reproduction-method.md` | 逆向复现或检查模板填报机制时 |
| `templates/evidence-register.md` | 研究内容或文献较多、需要事实追溯时 |
| `templates/execution-report.md` | 完成执行汇报时 |
| `scripts/build_report.py` | 只读复制官方模板并填写 |
| `scripts/check_report.py` | 固定结构、行距、上标、编号和字数检查 |
| `scripts/check_render.py` | 对已渲染 PDF 执行可选孤立签字分页预警 |
| `tests/test_pipeline.py` | 修改 Skill 后的回归测试，不含可引用文献 |

**质量优先级：官方模板原件完整性 ＞ 事实与文献真实性 ＞ 学校七项要求 ＞ 内容论证质量 ＞ 自动格式与逐页视觉验收。**任何一项硬性失败不得包装为 PASS。
