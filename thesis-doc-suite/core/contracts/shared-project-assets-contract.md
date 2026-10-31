# 项目级共享资产协议 v1（跨 Skill 统一契约 · 规范版）

> 本文件是 `thesis-doc-suite` 插件内**所有 Skill 共用的资产协议规范**（唯一可信契约来源）。
> 各业务 Skill 自带的 `references/shared-project-assets-contract.md` 是该协议在本 Skill 视角下的兼容说明；两者冲突时，**数据结构与读写规则以本文件为准**，文书体裁规则以各 Skill 自身 SKILL.md 为准。
> 此协议独立于任何文书体裁：任务书、开题报告、文献综述、指导记录、中期检查、技术文档、论文和答辩材料遵守同一套资产路径与读写约定，但各自仍负责自己的正文、模板、验证和交付。任何 Skill 都不替其他 Skill 生成文书。

## 0. 设计红线

1. **一个项目 = 一个资产包（数据 + 成品 + 运行区）**；不同项目必须隔离。
2. 项目资产**永不**写入插件安装目录、`.claude/skills/`、`.agents/skills/` 或任何 Skill 自带的 `assets/`、`references/`、`examples/`（内置目录只放通用规则与范本）。
3. `project_id` 唯一且持久。读到的 store 与本次任务 `project_id` 不一致时**立即停止合并**，防止串项目。
4. **先读后写**；共享资产不得被静默覆盖。变更已有条目必须 `--replace --reason` 并写入审计。
5. 共享资产、用户原始资料、官方模板原件、正式成品（含历史 `-vN` 版本）**永不删除**；清理只针对当前 Skill 自己的本轮运行目录。
6. 不为复用而生造事实/文献；AI 推测不得当作已确认事实入库。

## 1. 唯一持久化根目录与三区布局

每个真实项目一个独立的 `<PROJECT_ROOT>/`（项目资产包根，`--root` 指向这里）：

```text
<PROJECT_ROOT>/
├── project-assets/                  # 数据层：跨全部 Skill 的长期资产（schema_version=1）
│   ├── project.json                 # 项目标识、用户确认的人员/学校元信息
│   ├── facts.json                   # FACT-xxx 项目技术事实、来源、状态
│   ├── references.json              # REF-xxx 共享参考文献库、稳定编号、核验状态
│   ├── schedule.json                # 唯一项目级周计划基线（draft/confirmed）
│   ├── progress.json                # 可选：PROG-xxx 实际进展快照（中期检查扩展）
│   ├── visual-assets/               # 可选：VIS-xxx 视觉资产子层（technical-visual-assets 管理）
│   │   ├── index.json               #   VIS 索引：ID、类别、来源、许可、哈希
│   │   ├── diagrams/                #   可编辑 .mmd 源码与渲染 SVG（框架/架构/流程图）
│   │   ├── images/                  #   经用户许可保存的模块实物图等
│   │   └── requirements.json        #   四类覆盖与缺口报告
│   └── activity.jsonl               # 变更、引用、成品登记的审计流水
├── deliverables/                    # 成品层：按文书类型分目录，-vN 版本永不覆盖
│   ├── technical-document/          # project-technical-doc（MD + HTML）
│   ├── taskbook/                    # thesis-taskbook-write
│   ├── opening-report/              # opening-report-writer
│   ├── literature-review/           # literature-review-write
│   ├── guidance/                    # thesis-guidance-record-write
│   └── midterm/                     # thesis-midterm-check-write
└── .skill-tmp/                      # 运行层：本轮中间文件，结束即清理
    └── <skill-name>/<run-id>/       # 带所有权标记，只能被创建它的 Skill 清理
```

> 与"一个项目 = 数据区(data) + 成品区(outputs) + 运行区(runs)"概念的映射：`project-assets/ ≈ data`、`deliverables/ ≈ outputs`、`.skill-tmp/ ≈ runs`。实现以本布局为准（沿用已验证机制，见 docs/asset-management.md）。

## 2. 数据文件 Schema（schema_version=1）

### `project.json`
| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | int = 1 | 版本门禁 |
| `project_id` | string | 稳定唯一项目标识，创建后不可变 |
| `name` | string | 项目/课题名称 |
| `metadata` | object | 用户确认的人员元信息（姓名/学院/班级/学号/导师等），可为空 |
| `created_at` / `updated_at` | ISO 时间 | UTC 时间戳 |

### `facts.json` — `items[]`
每条 `FACT-xxx`：`id`、`statement`（原子结论）、`source`（文件+章节/行号定位）、`status` ∈ `implemented / declared / unverified / proposed`、可选 `notes`。**入库即定状态，文书体裁不改变事实状态**；正文引用时保持原状态口吻。

### `references.json` — `items[]`
每条 `REF-xxx` 必含：`id`、`citation`（著录文本，不带 `[n]` 本地编号）、`source_url`、`source_type`（`journal/conference/thesis/standard/web/tech-manual/...`）、`verified`（bool）；`verified=true` 必须有 `checked_at`。建议含 `doi`、`tags`、`project_relevance`、`limitations`。同 DOI/同题不得重复入库。正文 `[1]` 仅是各文书内部按**本次首次引用顺序**生成的临时编号，与稳定 ID 分离。

### `schedule.json` — `plan`
唯一周计划基线：`plan.id`、`status` ∈ `draft/confirmed`（`confirmed` 仅在用户/正式安排确认后使用）、`total_weeks`、`stages[]`（每阶段 `id/from_week/to_week/task`，周次 1..N 连续覆盖、无重无缺）、可选 `start_date/end_date`（须同有同无）。**计划 ≠ 实际完成情况**。

### `progress.json` — `items[]`（可选扩展）
每条 `PROG-xxx`：`id`、`as_of`、`category` ∈ `completed/in_progress/pending/risk/next_step`、`status` ∈ `draft/confirmed`、`description`、`source`。旧项目可没有此文件；存在则不得删除或覆盖。周计划不能冒充实际进展。

### `visual-assets/`（可选子层，VIS-xxx）
`technical-visual-assets` 管理的公共图片资料层：每条视觉资产一个稳定 ID `VIS-` + 内容 SHA-256 前 12 位（内容不变则 ID 不变，天然去重）。四类固定类别：`system-framework` / `functional-architecture` / `flowchart` / `module-photo`。索引 `index.json` 逐图登记来源（用户拍摄 / 联网检索 + 用户许可下载 / 由技术 MD 生成）、复用许可、哈希与逐图人工确认状态（审核声明≠自动视觉核验）。子层遵守本协议全部红线：写入走同一把 `.asset-write.lock` 与 `activity.jsonl` 审计；只登记合格素材，不合格如实报 MISSING，宁缺毋滥；**只做素材与登记，不在文书中插图**。旧项目可没有此子层；存在则不得删除或覆盖。

### `activity.jsonl`
逐行 JSON 审计：`at`、`action`（`init/merge/document-published/...`）、`actor`、变更 `ids`、`reason`、成品 `path`、`sha256`、`doc_type`、`reference_ids`、`project_id`。自然形成资产与成品的变更史。

## 3. 读写规则与冲突处理

1. 每个 Skill 只读写**自身职责范围内**的资产；公共数据必须经 `project_assets.py` 的明确接口（`init/status/merge/compose/record-use/workdir/cleanup`）使用，不得各自维护第二套文献库/计划/事实。
2. **先读后写**：新增条目前先对照既有 `FACT-xxx/REF-xxx/PROG-xxx`，可复用的直接引用稳定 ID，不重复入库。
3. 共享资产冲突时：①检查来源与版本 → ②分辨已有事实与新增建议 → ③尽可能无冲突合并 → ④**不得静默覆盖已确认数据**（更新须 `--replace --reason` 并留审计）→ ⑤无法自动解决的冲突生成报告，交用户裁决。
4. 写入互斥：文件锁 `.asset-write.lock` 防并发写；发现锁存在时不得强制覆盖。
5. `record-use` 只登记**最终成品**（`.skill-tmp` 内文件拒绝登记），含路径、`doc_type`、实际使用的 `REF-xxx` 与 SHA-256；每个 `-vN` 版本单独登记。失败产物不登记。

## 4. 运行区与清理安全

- 运行区固定为 `.skill-tmp/<skill-name>/<run-id>/`，创建时写入所有权标记文件；`run-id` 受 `^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$` 约束。
- `cleanup` 只删除**本 Skill 自己创建**、带合法所有权标记的单个 run 目录；拒绝符号链接越界、拒绝路径脱离项目根、拒绝删除他人目录。
- 成功与失败均执行清理（`try/finally` 语义）；失败摘要先持久化到对话或成品汇报，再清理。
- 历史 `-vN` 成品、共享资产、用户资料、官方模板原件**不在清理范围**。

## 5. 成品版本化（-vN）

- 成品文件名自带版本号（如 `<课题简称>-毕业设计任务书-v2.docx`）；重新生成新建 `-v2/-v3…`，**永不覆盖、永不删除历史版本**。
- 数据层变更走 `--replace --reason` 的审计记录，与成品版本史在 `activity.jsonl` 互相印证。

## 6. 与 compose 的关系

`compose` 命令是**各 Skill 自有**的草稿装配器（校验所选稳定 ID、组装本轮临时输入 JSON），不属于公共协议；禁止跨 Skill 调用其他 Skill 的 `compose`。公共实现 `core/asset-management/project_assets.py` 不含 compose。

## 7. Schema 版本与迁移

- 当前 `schema_version=1`。新增字段必须向后兼容（旧 Skill 忽略未知字段）；破坏性变更须提升 `schema_version` 并提供迁移脚本与迁移说明（docs/asset-management.md 记录）。
- 新增 Skill 的最低义务：读 `project.json` 校验 `project_id`、复用稳定 ID、遵守第 3/4/5 节规则、用 `record-use` 登记成品。`progress.json` 等可选文件允许不使用。
