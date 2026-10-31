# opening-report-writer 版本记录

## v4.1 — 2026-10-30（教师审阅意见默认填写拟稿 + 教师意见拟稿统一规范）

- 用户确认"开题报告中默认填写这个老师意见可以有"：教师审阅意见栏从"默认不填"改为**默认填写≥50字拟稿**；标签、导师签名与年月日仍留空不动。
- `build_report.py` 新增 `fill_teacher_opinion`（只写意见行空白书写区）；`validate_input`/`input.schema.json` 增必填 `teacher_opinion`（≥50字）；`check_report.py` 教师行由整行字节比对改为"标签/签名/日期段不动 + 书写区拟稿校验（≥50字、五号宋体、1.5倍、首行缩进420twips）"。
- SKILL.md §4 增"**教师意见拟稿统一规范（跨文书共用写法）**"：五要素链（主体选题→能力→文书质量→针对性→收束语"建议开题并按计划开展课题工作，最终评价以指导教师审定为准"）；与任务书/中期/文献综述四件套同源口径。
- 测试补教师意见专项回归（签名段不动、<50字拒绝），17/17 通过。

## v4.0 — 2026-10-30（按 thesis-midterm-check-write-v1.3 重构组织形式）

- **以用户上传 V3.4 开题 Skill 为升级基线**，不新建与之不兼容的系统，保留 `name: opening-report-writer`、文献和七章生成功能、官方模板与共享资产项目协议。
- 借鉴中期 Skill 的“0.边界、1.资产包、2.官方模板、3.匿名范本、4.写作与文献、5.执行、6.验收、7.索引”的主文档形式，并做清晰的独立分层。
- 官方空白模板哈希保持 `d4a43a96b90fe215f9983129396b7f20b68229b2d5e70c1f2558ff8adb993e5d` 不变；新增 `assets/template-lock.json`（来源、表格与版面属性）。
- 脱敏已填写范本从 `examples/` 迁入 `assets/reference-samples/`，新增 SHA256 清单、README、`samples-manifest.json`、格式统计，**当前完整范本只有一份，不伪称四份**；原人物信息源 DOCX 未打包。
- 新增范本文本逆向与“求同存异”规则 `references/genre-reverse-engineering.md`；项目技术事实与研究现状仍须有当前来源，旧范本文献不能复用。
- 新增可本地执行的逐页渲染 `scripts/render_visual.py`（LibreOffice+PyMuPDF），不再把 OpenAI 容器绝对路径视为唯一渲染方法；每页截图需 Agent 真实检查，脚本只做自动预检。
- **修复 V3.4 格式验收漏洞**：`check_report.py` 现在逐段强制检查普通正文/周计划 420twips 首行缩进；参考文献要左对齐、420twips 悬挂缩进且不得有自动列表 `numPr`。新增负面测试确保漏缩进不能再被 PASS。
- 新增 `manifest.txt`、`templates/input.schema.json`、`references/v4-alignment-map.md`、跨Skill集成片段、专门的清理/技术输入/模板边界指南，便于其它技能使用相同资产包和规范。
- 所有中间文件仍存 `.skill-tmp/opening-report-writer/<run-id>`，清理只作用于本轮有所有权标记的目录；历史 `-vN` 和项目资产不变。

---

# opening-report-writer 版本记录

## v3.4 — 2026-10-30（用户最新 V2 ZIP 基线增强：匿名写作范本）

- 从用户最初的已填写开题报告构造 `examples/anonymized-opening-report-reference.docx`，遮蔽封面个人信息和原始项目题目，清理作者元数据，并保留主要章段组织，**不包含含敏感信息的原文件**。
- 内置 `references/anonymized-sample-usage.md`：按章节逆向提取“结构、段落目的、过渡、分点、论证和引用写法”，明确旧范本缺陷不可继承，且绝不可作为新项目事实/文献/周计划来源。
- 新增 `scripts/sanitize_reference_sample.py`（维护专用）与 `scripts/check_reference_example.py`（匿名检查）及自动测试。
- 在 SKILL/README/质量门禁/官方模板约束中固定双资产优先级：**空白官方模板 > 当前技术事实与文献 > 匿名已填写范本**。无更换模板、无变更 V2 原有资产库与输出逻辑。
- 以用户 V2 ZIP 作为唯一升级基线，保留既有项目资产包、3 项交付及中间文件自动清理机制。

## v3.3 — 2026-10-30（实质性分页门禁）

- 补充**实质性分页门禁**：官方模板页数仅是参考，七项内容自然篇幅决定成品页数，不设固定页数指标；硬性 FAIL 仅限为凑/压页数增删事实或改版式、孤页两类。G4 门禁同步。

## v3.2 — 2026-10-30（截图验证分析环节）

- 阶段 F 统一加入**截图验证分析**（Screenshot Verification Analysis）：截图 → 逐张分析 → 留痕汇报固定三步与红线（未逐张分析不得宣称视觉通过、不得登记 record-use；截图非交付物，结论写入执行汇报后随中间文件清理）。G4 门禁与执行汇报模板同步固定字段。

## v3.1 — 2026-10-30（项目资产包与版本意识）

- 新增 1.5 节：**一个项目 = 一个资产包目录**（`project-assets/` 数据层 + `deliverables/` 成品层 + `.skill-tmp/` 运行层），默认交付路径从 `output/opening-report/` 切到 `<PROJECT_ROOT>/deliverables/opening-report/`，便于按项目分类查找与整包迁移。
- **版本意识**：重新生成产出 `-v2`、`-v3`…不覆盖历史版本；每版单独 record-use 登记，activity.jsonl 成为变更史；历史版本永不清理。G5 门禁与执行汇报模板同步（本轮版本恰为 3 项）。
- 现网胡杨林项目已按该布局归位：`projects/胡杨林安全监测系统/`（含 project-assets/、deliverables/taskbook/、deliverables/opening-report/，成品均带 -v1）。

## v3.0 — 2026-10-30（共享资产阶段）

接入**项目级共享资产协议 v1**（`references/shared-project-assets-contract.md`），与 thesis-taskbook-write、project-technical-doc 共用 `<PROJECT_ROOT>/project-assets/` 一个数据资产库：

- 新增第 1 章"项目级共享资产"：先读后写、稳定 ID（REF-xxx/FACT-xxx/stage ID）、正文 `[1]..[N]` 仅本文书临时编号、draft≠confirmed、禁默改禁生造、record-use 强制登记、安全清理红线，全部烙印进 SKILL.md 并贯穿阶段 A/B/C/D/E/F/G。
- **复用优先**：任务书阶段已核验的参考文献与周计划直接按稳定 ID 采用，不再重新检索/另编，杜绝跨文书"货不对板"；周计划措辞可变、周次/顺序/日期不可暗改。
- 新增 `scripts/project_assets.py`（协议兼容副本，所有权常量归属本 Skill：`.skill-tmp/opening-report-writer/<run-id>/`）；过程目录从 `.work/` 迁移为该运行目录，交付前 `cleanup` 清理并 `record-use` 留痕。
- G5 门禁扩展为"交付目录整洁与共享资产纪律"（record-use 登记、共享资产/用户资料/官方模板/其他 Skill 目录不得删除）；执行汇报模板新增共享资产登记项。
- 新增回归测试 `tests/test_project_assets.py`（init→merge→record-use→workdir/cleanup 安全烟测）。
- 其余机制（模板 SHA256 保护、七章预设、真上标、左对齐文献、1.5 倍行距、周次 `--`、文献核验）与 v2.0 一致。

## v2.0 — 2026-10-30

首次真实任务（胡杨林安全监测系统开题报告）反哺升级：

- **交付整洁化（G5 新门禁）**：过程文件统一写入 `output/opening-report/.work/` 并在交付前整体删除；交付目录最终只保留 **开题报告 DOCX、执行汇报.md、文献核验台账.md** 三项，执行汇报新增"交付目录最终清单"逐项核对。
- **参考文献排版修正**：文献段落显式**左对齐 + 悬挂缩进**（`w:jc=left`），消除长 URL 外文条目在两端对齐下行内拉伸出的大空隙（v1.0 实测出现"OASIS.　MQTT　Version…"式排版事故）；`check_report.py` 终检强制校验该属性，逐页目视清单与 G3/G4 门禁同步增加该项。
- 回归测试补充：构建产物文献段落必须左对齐；终检必须拦下两端对齐的文献段落。
- 其余机制（模板 SHA256 保护、七章预设、真上标引用、1.5 倍行距、周次 `--`、文献核验门禁）与 v1.0 一致。

## v1.0 — 2026-10-30

- 逆向研究用户提供的 `project-technical-doc v5`，复用“事实来源 → 模板写作 → 自动校验 → 执行汇报”的组织原则；**不复用其技术文档或 HTML 主交付职责**。
- 内置用户当前发送的塔里木大学开题报告官方 DOCX 原件，新增 SHA256 不可变校验。
- 确认官方原件为 A4、固定封面/填写说明、正文及教师审阅意见 2×1 表格、签字留白。
- 新增七项学校要求到标准章节的映射与真论文检索规则；支持知网、万方、维普、学术出版平台及有限 CSDN 辅助引用。
- 提供 OOXML 原位填报生成器，仅 `word/document.xml` 的授权写作位置发生变化；其余 ZIP 部件保持原样。
- 提供正文真正上标、文末单次编号、五号宋体/Times New Roman、1.5 倍行距、周次双连字符的自动校验。
- 提供结构性自动化测试与逐页视觉验收流程。
- 新增可选 PDF 分页预警 `check_render.py`：当教师意见与签名跨页、末页只剩签名时给出 WARN；仍需人工目视。

**已知限制**：当前 Word 生成脚本以纯文本章段/标题/计划与参考文献为主，不包含自动插图、自动期刊搜索或直接打开知网付费全文的能力；最终 Word 的分页与签字区位置需经逐页渲染及人眼确认。不得声称该工具已代替用户完成学术核查。
