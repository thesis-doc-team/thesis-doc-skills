# 项目资产兼容协议｜与 thesis-taskbook-write v1.1 共用数据基线

**原样维持五个核心资产**：
- `project-assets/project.json`：`schema_version=1`、稳定 `project_id`、`name`、`metadata`、时间戳。
- `project-assets/facts.json`：`items[]`；每条稳定 `FACT-xxx`、`statement`、`source`、`status`，状态 `implemented / declared / unverified / proposed`。
- `project-assets/references.json`：`items[]`；每条稳定 `REF-xxx`、`citation`、`source_url`、`source_type`、`verified`、`checked_at` 等；正文 `[1]` 不等于稳定 ID。
- `project-assets/schedule.json`：唯一 `plan`，稳定 `id`，`status=draft|confirmed`，`total_weeks`，阶段含 `id/from_week/to_week/task`，连续覆盖周次、无重周。
- `project-assets/activity.jsonl`：每次资产新增/变更/文书归档写入时间、actor、资产 ID 与变更理由；不存原文论文全文。

**在保持兼容基础上新增可选 `progress.json`**，记录中期时点进展，详见 `progress-asset-extension.md`。不存在时旧项目仍可正常使用，本 Skill 不能假定没有此文件就代表没有进度。

项目身份匹配、先读后写、真实文献核验、计划不悄悄覆盖、稳定 ID、不在 Skill 安装目录存项目数据、失败也删除临时产物、只记录真正交付文档，这些共同规则**与用户发来的任务书 Skill 保持一致**。两个 Skill 可装在不同编辑器，但只需指向同一 `PROJECT_ROOT`，不能各自重新初始化不同项目 ID 或生成“自己的一套”文献库。

本 Skill `scripts/project_assets.py` 从 `thesis-taskbook-write v1.1` 的兼容协议移植，公共命令 `init/status/merge/workdir/cleanup/record-use` 的字段约定保持兼容；`compose` 为中期稿专有、**不得交叉调用任务书的 compose 生成中期文书**；反向亦然。不同运行目录按 Skill 名隔离，`cleanup` 标记不通用，无法误删任务书的缓存。

补充：如果本项目已存在比 v1 更高版本的共同协议，**不得降级或覆盖**；应先审计迁移方案再执行。


## 题目唯一（强制）

`project.json` 的 `name` 是项目正式题目，同一项目的全部文书题目必须与之一致。`compose`（或对应校验入口）按 NFKC＋去空白归一化强校验，不一致即报错并指出两处题目。确需变更题目时，先更新 `project.json` 并留下审计记录，再重新生成全部文书——不得各文书各写一个题目，也不得靠换名、加空格绕过。
