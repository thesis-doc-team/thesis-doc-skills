# 项目资产管理（Asset Management）

**一个项目 = 一个资产包（数据 + 成品 + 运行区）。** 不同 Skill 操作同一个项目时共用同一个资产包；不同项目之间完全隔离；项目资产永不写入插件安装目录。

---

## 1. 资产包结构

```
<PROJECT_ROOT>/                         ← 项目资产包根（由你指定，如 E:\thesis-work\env-monitor）
├── project-assets/                     ← 【数据层】跨 Skill 共享持久数据
│   ├── project.json                    ← 项目身份（schema_version=1、project_id、名称、元信息）
│   ├── facts.json                      ← FACT-xxx 技术事实（结论 + 出处 + 状态）
│   ├── references.json                 ← REF-xxx 参考文献库（元数据 + 核验状态）
│   ├── schedule.json                   ← 唯一项目级周计划基线（draft/confirmed）
│   ├── progress.json                   ← PROG-xxx 实际进展快照（可选，向后兼容）
│   └── activity.jsonl                  ← 审计流水（新增/变更/成品登记，追加写）
├── deliverables/                       ← 【成品层】正式交付，按文书类型分目录
│   ├── technical-document/             ← 技术文档 MD/HTML/执行汇报
│   ├── taskbook/                       ← 任务书 -vN.docx
│   ├── opening-report/                 ← 开题报告 -vN 三件套
│   ├── literature-review/              ← 文献综述 -vN.docx
│   ├── guidance/                       ← 指导记录 -vN.docx
│   └── midterm/                        ← 中期检查 -vN.docx
└── .skill-tmp/                         ← 【运行层】本轮中间文件（结束清理）
    └── <skill-name>/<run-id>/          ← 带所有权标记的运行区
```

### 与"workspace/projects/<id>/（data/outputs/runs）"的映射

设计要求中的三区概念与现有实现一一对应（实现以已验证机制为准）：

| 设计概念 | 现有实现 | 说明 |
|---|---|---|
| `data/` 持久化项目数据 | `project-assets/` | 项目信息、技术事实、文献库、计划、模板来源记录、审计流水 |
| `outputs/` 正式成品 | `deliverables/<文书类型>/` | 版本命名（-vN），不覆盖历史；HTML 成品在 technical-document/ |
| `runs/` 执行运行区 | `.skill-tmp/<skill-name>/<run-id>/` | 运行上下文、临时文件、渲染截图、结构/质量检查记录；结束自动清理，保留执行汇报中的验收证据 |

## 2. 数据 schema（schema_version = 1）

### 2.1 project.json —— 项目身份

```json
{
  "schema_version": 1,
  "project_id": "ENV-MONITOR-2099",
  "name": "基于STM32的环境监测系统",
  "metadata": { "student_name": "示例学生", "college": "示例学院" },
  "created_at": "2099-01-01T00:00:00+00:00",
  "updated_at": "2099-01-01T00:00:00+00:00"
}
```

- `project_id` 唯一且持久；读到的资产与本次任务 project_id 不一致时**立即停止合并**（防串项目）。
- `metadata` 放已确认的人员/院系信息（可缺省）；Skill 优先取此处，缺失字段留空。

### 2.2 facts.json —— 技术事实库（FACT-xxx）

```json
{
  "schema_version": 1, "project_id": "...", "updated_at": "...",
  "items": [
    {
      "id": "FACT-001",
      "statement": "主控为 STM32F103，通过 4G 模块经 MQTT 上报数据",
      "source": "source/main.c:120（或 技术手册.md §3.2）",
      "status": "implemented",
      "notes": "可选补充说明"
    }
  ]
}
```

| status | 含义 | 允许的口吻 |
|---|---|---|
| `implemented` | 有源码/测试直接证据 | "代码中由 … 模块实现 …" |
| `declared` | 资料声明、未验证实现 | "设计文档规定 … / 系统方案包括 …" |
| `proposed` | 设计决策或拟完成 | "设计为 … / 计划采用 …" |
| `unverified` | 信息缺失/冲突 | "待确认 …"，不杜撰细节 |

**AI 推测不得记为已实现**；每条必须带 `statement` 与 `source`（可定位到文件+章节/行号）；文书体裁不改变事实状态。

### 2.3 references.json —— 参考文献库（REF-xxx）

```json
{
  "schema_version": 1, "project_id": "...", "updated_at": "...",
  "items": [
    {
      "id": "REF-001",
      "citation": "作者. 题名[J]. 期刊, 年份, 卷(期): 页码.",
      "source_url": "https://example.invalid/record/001",
      "source_type": "journal",
      "verified": true,
      "checked_at": "2099-01-05",
      "doi": "10.xxxx/xxxxx（可选）",
      "tags": ["环境监测", "MQTT"],
      "project_relevance": "支撑通信方案对比",
      "notes": "限制/不足（可选）"
    }
  ]
}
```

- 必填：`id`、`citation`、`source_url`、`source_type`、`verified`；`verified=true` 必须有 `checked_at`（实际核验日期）。
- **不得伪造**：优先知网/万方/维普、期刊与学位论文库、IEEE/ACM、Crossref/DOI、官方标准；CSDN 等博客只能作为标注 `source_type=web` 的技术补充，不冒充学术论文。无法核实时 `verified=false` 并在汇报中显式标注。
- 稳定 ID（REF-xxx）与各文书正文 `[1]` 编号分离：正文编号按本次引用顺序生成，映射关系随成品登记。
- 去重：同 DOI/同题名不允许重复条目。

### 2.4 schedule.json —— 统一进度计划

```json
{
  "schema_version": 1, "project_id": "...", "updated_at": "...",
  "plan": {
    "id": "PLAN-2099-01",
    "status": "draft",
    "total_weeks": 30,
    "start_date": "2099-03-01", "end_date": "2099-12-31",
    "stages": [
      { "id": "STAGE-1", "from_week": 1, "to_week": 4, "task": "调研与开题准备" }
    ]
  }
}
```

- `status`：`draft`（草拟建议）/ `confirmed`（用户或正式安排确认后才可标记）。
- 周次必须从第 1 周连续覆盖到 `total_weeks`、不重不缺；`start_date/end_date` 同有或同无（不套用旧范本日期）。
- **原计划 ≠ 实际完成**；任务书/开题报告使用同一基线，不得在文书里私自改基线。

### 2.5 progress.json —— 实际进展快照（可选，PROG-xxx）

```json
{
  "schema_version": 1, "project_id": "...", "updated_at": "...",
  "items": [
    {
      "id": "PROG-001",
      "as_of": "2099-06-10",
      "category": "completed",
      "status": "confirmed",
      "description": "完成传感器驱动调试，示波器实测采样时序正确",
      "source": "测试记录 2099-06-10 / 用户确认"
    }
  ]
}
```

- `category`：`completed / in_progress / pending / risk / next_step`；`status`：`draft / confirmed`。
- 每条需 `as_of`、`source`、`description`；**不能以周计划冒充实际进展**；未证实的进展不能标 `confirmed`。
- 该文件可选：旧项目没有它也兼容；存在时所有 Skill 不得删除或覆盖。

### 2.6 activity.jsonl —— 审计流水（追加写）

每行一个 JSON 事件，主要 action：

```json
{"at": "...", "action": "init", "actor": "...", "project_id": "..."}
{"at": "...", "action": "merge", "kind": "references", "ids": ["REF-001"], "actor": "...", "reason": "新增资产"}
{"at": "...", "action": "document-published", "doc_type": "taskbook", "path": "E:\\...\\xxx-v1.docx", "reference_ids": ["REF-001"], "sha256": "…", "project_id": "..."}
```

成品登记（document-published）只记最终成品（含路径 + SHA-256 + 实际引用 REF），每个 -vN 版本单独一条；临时文件不可登记。

## 3. 读写规则与冲突处理

1. **先读后写**：任何 Skill 先 `status` 查看已有资产，可复用的直接引用稳定 ID，仅补充缺失且有证据的条目。
2. **不静默覆盖**：修改已有条目必须 `--replace --reason "真实理由"`，写入 `activity.jsonl`；后运行的 Skill 不得悄悄改写先前 Skill 的结论。
3. **冲突处理顺序**：检查来源和版本 → 分辨已有事实与新增建议 → 尽可能无冲突合并 → 无法自动解决时**生成冲突报告交用户裁决**，不猜测、不选边。
4. **职责边界**：每个 Skill 只写自己职责范围内的资产（如文献综述不改周计划、中期检查不重写技术事实）；共享数据一律经 `project_assets.py` 的校验接口读写。
5. **临时输入不是资产**：各文书的本轮草稿 JSON 只存在于运行区，不进 `project-assets/`；文书正文也不整体存入 facts.json（资产只收原子事实）。

## 4. 运行区与清理安全边界

- 每轮执行：`workdir` 创建 `.skill-tmp/<skill-name>/<run-id>/`（写入所有权标记文件）；所有中间物（渲染 PNG、审计 JSON、临时输入）只放这里。
- 结束（成功或失败均执行）：`cleanup --run-id` 删除本轮目录。安全约束：
  - 校验所有权标记，非本 Skill 创建的目录拒绝删除；
  - 拒绝符号链接越界（防止删到项目外）；
  - 永不删除：`project-assets/`、官方模板原件、用户原始资料、`deliverables/` 全部历史版本、其他 Skill 的运行区；
  - 清理受阻时如实报告残留路径与原因，不扩大删除范围。
- 渲染截图等验证材料是过程证据：结论写入执行汇报后随运行区清理；执行汇报本身进入成品区持久保留。

## 5. 版本命名与成品保护

- 成品文件名自带版本：`<课题简称>-毕业设计任务书-v2.docx`。重新生成只新建更高版本，**永不覆盖、永不删除历史版本**。
- 已存在的 `-vN` 目标路径会被拒绝写入（防覆盖保护），自动改用下一个 N。
- 每版验收后 `record-use` 单独登记；`activity.jsonl` 即成品变更史。

## 6. Schema 版本与迁移策略

- 当前 `schema_version=1`。演进原则：**只增字段、不改语义**；新字段一律可缺省，旧项目无该字段照常工作（如 progress.json 即是先例）。
- 必须破坏兼容时：递增 `schema_version`，`project_assets.py` 在读取到不认识的版本时**拒绝盲目复用并提示迁移**（fail-closed），随插件 CHANGELOG 附迁移说明与转换脚本。
- 稳定 ID（project_id / FACT / REF / PROG / PLAN / STAGE）永不因迁移改变；引用映射随成品登记保留。
- 新增 Skill 复用资产协议时，只需遵守本 schema 与读写规则，不需要迁移既有数据。

## 7. 命令行速查

```bash
PA=core\asset-management\project_assets.py   # 各业务 Skill 内 scripts\project_assets.py 为协议兼容副本

python $PA init        --root "E:\thesis-work\env-monitor" --project-id "ENV-MONITOR-2099" --name "项目名称"
python $PA status      --root "E:\thesis-work\env-monitor"
python $PA merge       --root "E:\thesis-work\env-monitor" --kind references --input new-refs.json
python $PA merge       --root "E:\thesis-work\env-monitor" --kind facts --input new-facts.json --replace --reason "源码v2核实修正"
python $PA workdir     --root "E:\thesis-work\env-monitor"          # 输出本轮 WORKDIR 路径
python $PA record-use  --root "E:\thesis-work\env-monitor" --file "...\xxx-v1.docx" --doc-type taskbook --ref-ids "REF-001,REF-002"
python $PA cleanup     --root "E:\thesis-work\env-monitor" --run-id <RUN_ID>
```

`--kind` 可选：`references | facts | schedule | progress | project`。`compose` 为各业务 Skill 专用装配命令（校验资产 ID、组装本轮输入），见各 SKILL.md。
