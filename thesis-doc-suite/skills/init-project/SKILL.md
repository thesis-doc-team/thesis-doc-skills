---
name: init-project
version: 0.1.0
disable-model-invocation: true
argument-hint: "<项目根目录> [project-id] [项目名称]"
description: 为一个毕业设计项目初始化共享资产包（一个项目=一个资产包：project-assets 数据层 + deliverables 成品层 + .skill-tmp 运行层）。在用户指定的项目根目录创建 schema_version=1 的项目资产骨架并登记 project_id；已初始化的项目绝不覆盖。当用户说"初始化项目""创建项目资产包""开始一个新毕设项目"时使用。
---

# init-project｜初始化项目资产包

## 目标

在用户指定的**项目根目录** `<PROJECT_ROOT>`（不是插件安装目录）创建一个项目的共享资产骨架：

```text
<PROJECT_ROOT>/
├── project-assets/          # 数据层（本 Skill 创建）
│   ├── project.json         # schema_version=1、project_id、name、metadata
│   ├── facts.json           # 空 FACT-xxx 列表
│   ├── references.json      # 空 REF-xxx 列表
│   ├── schedule.json        # plan=null
│   ├── progress.json        # 空 PROG-xxx 列表（可选扩展）
│   └── activity.jsonl       # 审计流水（init 事件）
├── deliverables/            # 成品层（本 Skill 创建子目录骨架）
└── .skill-tmp/              # 运行层（各 Skill 运行时自动创建，不需预建）
```

## 执行步骤

1. **确认三个参数**（缺失时询问，不要臆造）：
   - `<PROJECT_ROOT>`：真实项目根目录绝对路径（Windows 示例 `E:\thesis-work\my-project`）。目录不存在则先创建（征得用户同意）。
   - `project_id`：稳定唯一标识。**禁止复制示例 ID**；建议用课题简称拼音/字母数字（如 `env-monitor-2026`），创建后不可变。
   - `项目名称`：课题全称或简称。
2. **初始化**（幂等；已存在绝不覆盖）：

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/core/asset-management/project_assets.py" init \
     --root "<PROJECT_ROOT>" --project-id "<PROJECT_ID>" --name "<项目名称>"
   ```

   输出 `CREATED:` 表示新建成功；`EXISTS: …（未覆盖任何文件）` 表示此前已初始化（此时核对 project_id 是否一致，不一致立即停止并报告"拒绝串项目"）。
3. **创建成品骨架**：在 `<PROJECT_ROOT>/deliverables/` 下建立空子目录 `technical-document/`、`taskbook/`、`opening-report/`、`literature-review/`、`guidance/`、`midterm/`（已存在的不改动）。
4. **可选元信息**：用户提供姓名/学院/班级/学号/导师等时，写入 `project.json` 的 `metadata`（用 `core/asset-management/project_assets.py merge --root … --kind project --input <metadata.json>`）。用户未提供则留空，**不得从任何范本继承**。
5. **确认**：运行 `status --root <PROJECT_ROOT>` 并把输出（project_id、各数据规模）汇报给用户；提示下一步建议（放入技术资料 → `/thesis-doc-suite:check-project` → 生成技术文档或其他文书）。

## 红线

- 只写 `<PROJECT_ROOT>`，**绝不**把项目资产写进插件目录、`.claude/`、`.agents/` 或 Skill 自带目录。
- 已初始化的项目：不覆盖、不重建、不更换 project_id；需要变更元信息走 `merge --kind project` 的显式更新。
- 本 Skill 只做初始化与登记，不生成任何文书、不写入事实/文献/计划内容。
