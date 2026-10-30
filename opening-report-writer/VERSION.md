# opening-report-writer 版本记录

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
