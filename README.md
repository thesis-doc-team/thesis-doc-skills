# thesis-doc-skills

毕业设计（论文）文书生成 Skill 合集，面向 Claude Code / Codex。六个 Skill 共用**同一套项目级共享资产系统**：一个项目 = 一个资产包，数据、成品、运行区一处维护，跨文书复用不走样。

## Skill 一览

| Skill | 职责 | 主要产物 |
|---|---|---|
| `thesis-taskbook-write` | 毕业设计任务书编写 + 项目资产共管（REF/FACT/周计划的起点） | 任务书 DOCX |
| `project-technical-doc` | 项目源码/资料理解，提炼技术事实（FACT-xxx 主要提炼者） | 技术文档 MD + 可视化 HTML |
| `opening-report-writer` | 官方模板保护型开题报告写作 | 开题报告 DOCX + 执行汇报 + 文献核验台账 |
| `thesis-midterm-check-write` | 官方中期检查记录表填充（进展/问题整改/教师意见拟稿） | 中期检查记录表 DOCX |
| `literature-review-write` | 官方模板文献综述写作（引用核验、上标编号一致性） | 文献综述 DOCX |
| `thesis-guidance-record-write` | 官方 13 行指导记录表批量拟稿（问题→整改一一对应，≥8 次） | 指导记录 DOCX（待教师审核） |

## 一个项目 = 一个资产包

```text
<PROJECT_ROOT>/
├─ project-assets/     # 数据层：project/facts/references/schedule/activity（中期另有可选 progress.json）
├─ deliverables/       # 成品层：taskbook/ technical-document/ opening-report/ midterm/ literature-review/ guidance/，文件带 -vN 版本号
└─ .skill-tmp/         # 运行区：各 Skill 独立 <run-id> 目录，用完即清理
```

- **先读后写**：参考文献 REF-xxx、技术事实 FACT-xxx、周计划按稳定 ID 复用，杜绝跨文书"货不对板"。
- **版本意识**：重生成产出 `-v2`、`-v3`…，永不覆盖历史版本；每版单独 record-use 留痕，activity.jsonl 即变更史。
- **截图验证分析**（交付前硬性环节）：成品渲染全页截图 → **逐张分析**（缺一张即未完成）→ 留痕汇报（截图引擎/张数/实看张数/逐张 PASS·WARN·FAIL/返工复检次数/实测边界声明）；未逐张分析不得宣称视觉通过、不得登记 record-use。
- **实质性分页门禁**：模板/范本的空白页数**仅是参考**，成品页数按当次内容自然排布；不为凑/压页数增删事实、稀释堆砌文字或破坏官方固定框架；孤页先调措辞消除，仍不行如实报告请用户判断。
- **安全红线**：共享资产、用户资料、官方模板原件、历史交付版本永不删除；运行目录按所有权标记清理，不越界；不编造文献、事实、日期与教师评价。

## 安装

本仓库以插件形式分发：`thesis-doc-suite/` 是完整插件（`skills/` 下共 13 个 Skill）。使用方式二选一：

- 作为插件整体安装（推荐）：通过 `.claude-plugin/marketplace.json` 指向的 `thesis-doc-suite/` 安装。
- 单独取用某个 Skill：把 `thesis-doc-suite/skills/<skill-name>/` 放到项目的 `.claude/skills/`（Claude Code）或 `.agents/skills/`（Codex）下，按该 Skill 的 SKILL.md 提供输入。

Python 3.10+，依赖见各 Skill 的 `requirements.txt`。上表只列六个核心业务 Skill，完整清单见 [thesis-doc-suite/README.md](thesis-doc-suite/README.md)。
