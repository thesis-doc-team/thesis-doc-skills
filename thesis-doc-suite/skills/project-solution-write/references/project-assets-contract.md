> **V1.4.0：** 本契约适用于用户确认题目后在 `projects/PROJECT-xxxx/` 中建立的正式项目资产。选题阶段独立使用 `discovery/` 索引和每个项目 `data/revisions/versions/`，具体见 `discovery-assets-and-iteration.md`。

# 项目级资产复用契约

## 1. 根规则

一个项目只维护一个 `<PROJECT_ROOT>/project-assets/`。若已有其他 Skill 的 `project.json / facts.json / references.json / schedule.json / activity.jsonl`，遵守既有 schema，不自动重置。项目不同 ID 时停止写入，不能跨项目借用器件/资料与事实。

`init` 与六件套 canonical 一致：写 `project.json`（`schema_version/project_id/name/metadata/created_at/updated_at`）并建空 `facts.json / references.json / schedule.json`，保证下游 `status` / `record-use` 不因缺文件失败；已有资产时只复用、绝不覆盖。

## 2. 新增可选资产

- `requirements.json`：`schema_version=1`、`project_id`、`items[]`，每条 `REQ-ID/name/origin/status/interpretation/acceptance`，状态 `confirmed/assumed/unknown`。
- `decisions.json`：`schema_version=1`、`project_id`、`items[]`，每条 `DEC-ID/question/choice/reason/evidence/status/depends_on`；`status=confirmed|proposed|blocked`。V1.1+ 可添加兼容的 `optimization` 对象：`priority`（cost/performance/function/balanced）、可选 `secondary_priority`（同四类且不得与主目标冲突）、`status`（confirmed/proposed）、`source`、`budget_cap`（如已知）、`performance_targets`（如已知）、`last_decision_id`；各关键 `DEC-ID` 的附加字段可以记录 `requirement_refs/hard_gates/alternatives/sacrifice/implementation_impact/verification`，**不能覆盖旧格式或替换用户已有值**。
- `facts.json` 的 `FACT-xxx`、`references.json` 的 `REF-xxx` 保留稳定 ID，来源类型与核实状态绝不能伪造。
- `requirements.json`/`decisions.json` 一律经 `project_workspace.py write-asset --kind requirements|decisions --input <file>` 写入：持 `.asset-write.lock` 排他锁、原子写、校验 schema_version/project_id/items 并追加 activity 事件；不要手写覆盖。

## 3. 生命周期

1. **先读** 项目身份与已存在的功能/决策，不重复创建。
2. 本轮新的用户事实才追加，Agent 推导只能写 proposed/assumed，不能无授权升级为 confirmed。
3. 用户明确更改需求时记录旧决策的被替代关系和原因；成品新建版本，不覆盖历史。
4. 成品用 `project_workspace.py record-use --file <成品> --doc-type introduction|implementation` 登记：路径 + SHA256 追加到 `activity.jsonl`（`document-published` 事件），与其它 Skill 同一本账，不得手写伪造。
5. 介绍 HTML 由同版本介绍 MD 派生，共用 `-vN`，不单独 `record-use`；介绍 MD 重新生成后必须重新生成 HTML，HTML 不得反向改写 MD。
6. 运行区由 `workdir` 创建、`cleanup` 删除：只删带 `.owned-by-project-solution-write` 标记的单个目录，遇符号链接/路径越界/标记不符一律拒绝；稳定项目资产、用户原件与历史成品保留。

不要为了执行 Skill 强行生成论文、周计划或大量不需要的 JSON；只保留当前任务真正会复用的资料。
