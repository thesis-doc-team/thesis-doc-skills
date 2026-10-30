# thesis-doc-skills

毕业设计（论文）文书生成 Skill 合集，面向 Claude Code / Codex。四个 Skill 共用**同一套项目级共享资产系统**：一个项目 = 一个资产包，数据、成品、运行区一处维护，跨文书复用不走样。

## Skill 一览

| Skill | 职责 | 主要产物 |
|---|---|---|
| `thesis-taskbook-write` | 毕业设计任务书编写 + 项目资产共管（REF/FACT/周计划的起点） | 任务书 DOCX |
| `project-technical-doc` | 项目源码/资料理解，提炼技术事实（FACT-xxx 主要提炼者） | 技术文档 MD + 可视化 HTML |
| `opening-report-writer` | 官方模板保护型开题报告写作 | 开题报告 DOCX + 执行汇报 + 文献核验台账 |
| `thesis-midterm-check-write` | 官方中期检查记录表填充（进展/问题整改/教师意见拟稿） | 中期检查记录表 DOCX |

## 一个项目 = 一个资产包

```text
<PROJECT_ROOT>/
├─ project-assets/     # 数据层：project/facts/references/schedule/activity（中期另有可选 progress.json）
├─ deliverables/       # 成品层：taskbook/ technical-document/ opening-report/ midterm/，文件带 -vN 版本号
└─ .skill-tmp/         # 运行区：各 Skill 独立 <run-id> 目录，用完即清理
```

- **先读后写**：参考文献 REF-xxx、技术事实 FACT-xxx、周计划按稳定 ID 复用，杜绝跨文书"货不对板"。
- **版本意识**：重生成产出 `-v2`、`-v3`…，永不覆盖历史版本；每版单独 record-use 留痕，activity.jsonl 即变更史。
- **安全红线**：共享资产、用户资料、官方模板原件、历史交付版本永不删除；运行目录按所有权标记清理，不越界。

## 安装

把某个 Skill 目录放到项目的 `.claude/skills/`（Claude Code）或 `.agents/skills/`（Codex）下，按各 Skill 的 README 提供输入即可。Python 3.10+，依赖见各自 `requirements.txt`。
